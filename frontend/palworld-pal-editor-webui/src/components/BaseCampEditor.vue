<script setup>
import { computed, ref, watch } from 'vue'
import { usePalEditorStore } from '@/stores/paleditor'

const palStore = usePalEditorStore()
const selectedCategoryId = ref('Handcraft')
const selectedResearchId = ref(null)
const graphMetrics = Object.freeze({
  levelHeight: 154,
  nodeWidth: 144,
  nodeHeight: 112,
  nodeGap: 48,
  paddingX: 56,
  paddingY: 20,
  railWidth: 68,
})

const guilds = computed(() => palStore.BASE_CAMP_RESEARCH?.Guilds ?? [])
const selectedGuild = computed(() => guilds.value.find(
  guild => guild.GuildId === palStore.SELECTED_RESEARCH_GUILD_ID,
) ?? guilds.value[0] ?? null)
const categories = computed(() => selectedGuild.value?.Categories ?? [])
const selectedCategory = computed(() => categories.value.find(
  category => category.Category === selectedCategoryId.value,
) ?? categories.value[0] ?? null)
const selectedResearch = computed(() => selectedCategory.value?.Research.find(
  research => research.ResearchId === selectedResearchId.value,
) ?? null)
const treeLayout = computed(() => {
  const research = selectedCategory.value?.Research ?? []
  const byId = new Map(research.map((node, index) => [node.ResearchId, { node, index }]))
  const children = new Map(research.map(node => [node.ResearchId, []]))
  const roots = []
  for (const node of research) {
    if (node.RequiredResearchId && byId.has(node.RequiredResearchId)) {
      children.get(node.RequiredResearchId).push(node.ResearchId)
    } else {
      roots.push(node.ResearchId)
    }
  }
  for (const ids of children.values()) {
    ids.sort((left, right) => byId.get(left).index - byId.get(right).index)
  }

  let leafColumn = 0
  const columns = new Map()
  const place = id => {
    const childIds = children.get(id) ?? []
    if (!childIds.length) {
      const column = leafColumn
      leafColumn += 1
      columns.set(id, column)
      return column
    }
    const childColumns = childIds.map(place)
    const column = childColumns.reduce((sum, value) => sum + value, 0) / childColumns.length
    columns.set(id, column)
    return column
  }
  roots.sort((left, right) => byId.get(left).index - byId.get(right).index).forEach(place)

  const maxLevel = Math.max(1, ...research.map(node => node.Level))
  const graphWidth = Math.max(
    640,
    graphMetrics.paddingX * 2
      + Math.max(0, leafColumn - 1) * (graphMetrics.nodeWidth + graphMetrics.nodeGap)
      + graphMetrics.nodeWidth,
  )
  const width = graphMetrics.railWidth + graphWidth
  const height = graphMetrics.paddingY * 2 + maxLevel * graphMetrics.levelHeight
  const positions = new Map(research.map(node => {
    const centerX = graphMetrics.railWidth + graphMetrics.paddingX
      + columns.get(node.ResearchId) * (graphMetrics.nodeWidth + graphMetrics.nodeGap)
      + graphMetrics.nodeWidth / 2
    const top = graphMetrics.paddingY + (node.Level - 1) * graphMetrics.levelHeight
    return [node.ResearchId, {
      left: centerX,
      top,
      anchorY: top + 34,
    }]
  }))
  const connections = research.flatMap(node => {
    const parent = positions.get(node.RequiredResearchId)
    const child = positions.get(node.ResearchId)
    if (!parent || !child) return []
    const startY = parent.anchorY + 34
    const endY = child.anchorY - 34
    const middleY = startY + (endY - startY) / 2
    return [{
      id: `${node.RequiredResearchId}-${node.ResearchId}`,
      parentId: node.RequiredResearchId,
      childId: node.ResearchId,
      completed: byId.get(node.RequiredResearchId).node.Completed && node.Completed,
      path: `M ${parent.left} ${startY} V ${middleY} H ${child.left} V ${endY}`,
    }]
  })
  return {
    width,
    height,
    levels: Array.from({ length: maxLevel }, (_, index) => index + 1),
    nodes: research.map(node => ({ ...node, ...positions.get(node.ResearchId) })),
    connections,
  }
})
const allCompleted = computed(() => categories.value.length > 0 && categories.value.every(
  category => category.Completed === category.Total,
))

const translated = key => palStore.getTranslatedText(key)
const categoryName = category => translated(`BaseCamp_Research_Category_${category}`)
const categoryIcon = category => palStore.backendAssetUrl(`/image/lab/category-${category}`)
const researchIcon = research => palStore.backendAssetUrl(`/image/lab/${research.IconKey}`)
const effectName = effect => translated(`BaseCamp_Research_Effect_${effect}`)
const itemTypeName = itemType => translated(`BaseCamp_Research_Item_${itemType}`)
const formatNumber = value => new Intl.NumberFormat().format(value ?? 0)
const signedValue = value => `${Number(value) > 0 ? '+' : ''}${Number(value)}%`
const materialName = material => palStore.ITEM_STATIC_DATA[material.ItemId]?.Name ?? material.ItemId
const researchEffect = research => {
  if (!research) return ''
  const option = research.EffectWorkSuitability !== 'None'
    ? categoryName(research.EffectWorkSuitability)
    : research.EffectItemType !== 'None'
      ? itemTypeName(research.EffectItemType)
      : ''
  const value = research.EffectType === 'no' ? '' : signedValue(research.EffectValue)
  return [effectName(research.EffectType), option, value].filter(Boolean).join(' · ')
}

function selectCategory(category) {
  selectedCategoryId.value = category.Category
}

function selectResearch(research) {
  selectedResearchId.value = research.ResearchId
}

async function completeResearch() {
  if (!selectedResearch.value || selectedResearch.value.Completed) return
  await palStore.completeBaseCampResearch({ ResearchId: selectedResearch.value.ResearchId })
}

async function completeCategory() {
  if (!selectedCategory.value || selectedCategory.value.Completed === selectedCategory.value.Total) return
  if (!window.confirm(translated('BaseCamp_Research_Confirm_Category'))) return
  await palStore.completeBaseCampResearch({ Category: selectedCategory.value.Category })
}

async function completeAll() {
  if (allCompleted.value) return
  if (!window.confirm(translated('BaseCamp_Research_Confirm_All'))) return
  await palStore.completeBaseCampResearch({ All: true })
}

watch(selectedGuild, guild => {
  if (!guild) return
  if (!guild.Categories.some(category => category.Category === selectedCategoryId.value)) {
    selectedCategoryId.value = guild.Categories[0]?.Category ?? 'Handcraft'
  }
}, { immediate: true })

watch(selectedCategory, category => {
  const current = category?.Research.find(
    research => research.ResearchId === selectedResearchId.value,
  )
  if (current) return
  selectedResearchId.value = category?.Research.find(
    research => research.Available && !research.Completed,
  )?.ResearchId ?? category?.Research[0]?.ResearchId ?? null
}, { immediate: true })
</script>

<template>
  <section class="basecamp-editor">
    <header class="lab-header">
      <div>
        <p class="lab-header__eyebrow">{{ translated('BaseCamp_Research_BaseCamp') }}</p>
        <h1>{{ translated('BaseCamp_Research_Title') }}</h1>
      </div>
      <div class="lab-header__actions">
        <label v-if="guilds.length > 1" class="guild-select">
          <span>{{ translated('BaseCamp_Research_Guild') }}</span>
          <select v-model="palStore.SELECTED_RESEARCH_GUILD_ID" :disabled="palStore.LOADING_FLAG">
            <option v-for="guild in guilds" :key="guild.GuildId" :value="guild.GuildId">
              {{ guild.GuildName }}
            </option>
          </select>
        </label>
        <div v-else-if="selectedGuild" class="guild-name">
          <span>{{ translated('BaseCamp_Research_Guild') }}</span>
          <strong>{{ selectedGuild.GuildName }}</strong>
        </div>
        <button class="lab-action lab-action--danger" :disabled="allCompleted || palStore.LOADING_FLAG" @click="completeAll">
          {{ translated('BaseCamp_Research_Complete_All') }}
        </button>
      </div>
    </header>

    <div v-if="!selectedGuild" class="lab-empty">
      {{ translated('BaseCamp_Research_No_Data') }}
    </div>

    <div v-else class="lab-workspace">
      <nav class="category-rail" :aria-label="translated('BaseCamp_Research_Categories')">
        <button v-for="category in categories" :key="category.Category"
          class="category-button" :class="{ 'category-button--active': category.Category === selectedCategory?.Category }"
          @click="selectCategory(category)">
          <img :src="categoryIcon(category.Category)" alt="">
          <span>{{ categoryName(category.Category) }}</span>
          <strong>{{ category.Completed }}<small>/{{ category.Total }}</small></strong>
        </button>
      </nav>

      <section class="research-tree">
        <header class="research-tree__header">
          <div class="research-tree__title">
            <img :src="categoryIcon(selectedCategory.Category)" alt="">
            <div>
              <p>{{ translated('BaseCamp_Research_Research_Level') }}</p>
              <h2>{{ categoryName(selectedCategory.Category) }}</h2>
            </div>
            <strong>{{ selectedCategory.Completed }}<small>/{{ selectedCategory.Total }}</small></strong>
          </div>
          <button class="lab-action" :disabled="selectedCategory.Completed === selectedCategory.Total || palStore.LOADING_FLAG"
            @click="completeCategory">
            {{ translated('BaseCamp_Research_Complete_Category') }}
          </button>
        </header>

        <div class="research-scroll">
          <div class="research-canvas" :style="{ width: `${treeLayout.width}px`, height: `${treeLayout.height}px` }">
            <div v-for="level in treeLayout.levels" :key="level" class="research-level-band"
              :style="{ top: `${graphMetrics.paddingY + (level - 1) * graphMetrics.levelHeight}px`, height: `${graphMetrics.levelHeight}px` }">
              <div class="research-level__label">
                <img :src="categoryIcon(selectedCategory.Category)" alt="">
                <span>{{ translated('BaseCamp_Research_Level') }}</span>
                <strong>{{ level }}</strong>
              </div>
            </div>

            <svg class="research-connections" :width="treeLayout.width" :height="treeLayout.height" aria-hidden="true">
              <path v-for="connection in treeLayout.connections" :key="connection.id" :d="connection.path"
                :class="{
                  'research-connection--completed': connection.completed,
                  'research-connection--selected': connection.parentId === selectedResearch?.ResearchId
                    || connection.childId === selectedResearch?.ResearchId,
                }" />
            </svg>

            <button v-for="research in treeLayout.nodes" :key="research.ResearchId"
              class="research-node" :class="{
                'research-node--selected': research.ResearchId === selectedResearch?.ResearchId,
                'research-node--completed': research.Completed,
                'research-node--locked': !research.Available && !research.Completed,
              }" :style="{ left: `${research.left}px`, top: `${research.top}px` }"
              :title="researchEffect(research)" @click="selectResearch(research)">
              <span class="research-node__diamond">
                <img :src="researchIcon(research)" alt="">
                <span v-if="research.Completed" class="research-node__check">✓</span>
              </span>
              <span class="research-node__effect">{{ effectName(research.EffectType) }}</span>
              <small>{{ researchEffect(research) }}</small>
            </button>
          </div>
        </div>
      </section>

      <aside class="effect-panel">
        <template v-if="selectedResearch">
          <p class="effect-panel__eyebrow">{{ translated('BaseCamp_Research_Effect') }}</p>
          <div class="effect-panel__badge" :class="{ 'effect-panel__badge--completed': selectedResearch.Completed }">
            <img :src="researchIcon(selectedResearch)" alt="">
          </div>
          <h2>{{ effectName(selectedResearch.EffectType) }}</h2>
          <p class="effect-panel__effect">{{ researchEffect(selectedResearch) }}</p>

          <div class="effect-panel__status">
            <span>{{ translated('BaseCamp_Research_Progress') }}</span>
            <strong>{{ formatNumber(selectedResearch.WorkAmount) }} / {{ formatNumber(selectedResearch.RequiredWorkAmount) }}</strong>
          </div>
          <div class="progress-track"><span :style="{ width: `${Math.min(100, selectedResearch.WorkAmount / selectedResearch.RequiredWorkAmount * 100)}%` }"></span></div>

          <p class="research-status" :class="{
            'research-status--completed': selectedResearch.Completed,
            'research-status--locked': !selectedResearch.Available && !selectedResearch.Completed,
          }">
            {{ translated(selectedResearch.Completed
              ? 'BaseCamp_Research_Completed'
              : selectedResearch.Available
                ? 'BaseCamp_Research_Available'
              : 'BaseCamp_Research_Locked') }}
          </p>

          <button class="lab-action lab-action--primary" :disabled="selectedResearch.Completed || palStore.LOADING_FLAG"
            @click="completeResearch">
            {{ translated('BaseCamp_Research_Complete_Node') }}
          </button>

          <div v-if="selectedResearch.Materials.length" class="materials">
            <h3>{{ translated('BaseCamp_Research_Materials') }}</h3>
            <div v-for="material in selectedResearch.Materials" :key="material.ItemId" class="material-row">
              <span>{{ materialName(material) }}</span><strong>×{{ material.Count }}</strong>
            </div>
          </div>

          <code class="research-id">{{ selectedResearch.ResearchId }}</code>
        </template>
      </aside>
    </div>
  </section>
</template>

<style scoped>
.basecamp-editor { display: grid; min-width: 0; min-height: 0; height: 100%; grid-template-rows: auto minmax(0, 1fr); overflow: hidden; color: var(--editor-color-text); }
.lab-header { display: flex; align-items: center; justify-content: space-between; gap: 1rem; margin-bottom: .6rem; padding: .7rem .85rem; border: 1px solid var(--editor-color-glass-border); border-radius: var(--editor-radius-md); background: linear-gradient(135deg, color-mix(in srgb, var(--editor-color-focus) 8%, var(--editor-color-surface-raised)), var(--editor-color-surface)); }
.lab-header h1 { margin: .05rem 0; font-size: clamp(1.2rem, 2vw, 1.7rem); }
.lab-header p { margin: 0; color: var(--editor-color-muted); }
.lab-header__eyebrow, .effect-panel__eyebrow, .research-tree__title p { font-size: .72rem; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; }
.lab-header__actions { display: flex; flex-wrap: wrap; align-items: end; justify-content: end; gap: .6rem; }
.guild-select, .guild-name { display: grid; gap: .2rem; color: var(--editor-color-muted); font-size: .72rem; }
.guild-select select { min-width: 11rem; padding: .55rem .7rem; border: 1px solid var(--editor-color-border); border-radius: var(--editor-radius-sm); color: var(--editor-color-text); background: var(--editor-color-surface); }
.guild-name strong { color: var(--editor-color-text); font-size: .9rem; }
.lab-action { min-height: 2.35rem; padding: .5rem .75rem; border: 1px solid color-mix(in srgb, var(--editor-color-focus) 55%, var(--editor-color-border)); border-radius: var(--editor-radius-sm); color: var(--editor-color-text); background: color-mix(in srgb, var(--editor-color-focus) 13%, var(--editor-color-control)); font-weight: 700; cursor: pointer; }
.lab-action:hover:not(:disabled) { background: color-mix(in srgb, var(--editor-color-focus) 24%, var(--editor-color-control)); }
.lab-action--primary { width: 100%; }
.lab-action--danger { border-color: color-mix(in srgb, var(--editor-color-danger) 55%, var(--editor-color-border)); background: color-mix(in srgb, var(--editor-color-danger) 13%, var(--editor-color-control)); }
.lab-action:disabled { opacity: .45; cursor: default; }
.lab-workspace { display: grid; min-width: 0; min-height: 0; height: 100%; grid-template-columns: minmax(9.5rem, 13rem) minmax(24rem, 1fr) minmax(13rem, 17rem); gap: .65rem; overflow: hidden; }
.category-rail, .research-tree, .effect-panel { min-width: 0; min-height: 0; height: 100%; border: 1px solid var(--editor-color-glass-border); border-radius: var(--editor-radius-md); background: var(--editor-color-glass-surface); }
.category-rail { display: grid; align-content: start; gap: .35rem; padding: .55rem; overflow: auto; scrollbar-gutter: stable; }
.category-button { display: grid; grid-template-columns: 2rem minmax(0, 1fr) auto; align-items: center; gap: .5rem; min-height: 3.4rem; padding: .45rem .55rem; border: 1px solid var(--editor-color-border); border-radius: var(--editor-radius-sm); color: var(--editor-color-text); background: color-mix(in srgb, var(--editor-color-surface) 85%, transparent); text-align: left; cursor: pointer; }
.category-button:hover, .category-button--active { border-color: var(--editor-color-focus); background: color-mix(in srgb, var(--editor-color-focus) 17%, var(--editor-color-surface)); box-shadow: inset .18rem 0 var(--editor-color-focus); }
.category-button img, .research-tree__title img, .research-level__label img { width: 1.75rem; height: 1.75rem; object-fit: contain; }
.category-button strong, .research-tree__title > strong { color: var(--editor-color-focus); font-size: 1.05rem; }
.category-button small, .research-tree__title small { opacity: .65; font-size: .72em; }
.research-tree { display: grid; grid-template-rows: auto minmax(0, 1fr); overflow: hidden; }
.research-tree__header { display: flex; align-items: center; justify-content: space-between; gap: .75rem; padding: .7rem .85rem; border-bottom: 1px solid var(--editor-color-border); background: color-mix(in srgb, var(--editor-color-focus) 7%, var(--editor-color-surface)); }
.research-tree__title { display: grid; min-width: 0; grid-template-columns: 2.2rem minmax(0, 1fr) auto; align-items: center; gap: .5rem; }
.research-tree__title h2, .research-tree__title p { margin: 0; }
.research-scroll { min-width: 0; min-height: 0; overflow: auto; scrollbar-gutter: stable; background-image: radial-gradient(circle, color-mix(in srgb, var(--editor-color-focus) 14%, transparent) 1px, transparent 1px); background-size: 2rem 2rem; }
.research-canvas { position: relative; min-width: 100%; min-height: 100%; }
.research-level-band { position: absolute; right: 0; left: 0; z-index: 0; border-bottom: 1px solid color-mix(in srgb, var(--editor-color-focus) 16%, transparent); pointer-events: none; }
.research-level__label { position: sticky; left: 0; display: grid; width: 4.25rem; height: 100%; place-items: center; align-content: center; gap: .1rem; border-right: 1px solid color-mix(in srgb, var(--editor-color-focus) 18%, var(--editor-color-border)); color: var(--editor-color-focus); background: color-mix(in srgb, var(--editor-color-focus) 7%, var(--editor-color-surface)); }
.research-level__label span { font-size: .7rem; text-transform: uppercase; }
.research-level__label strong { font-size: 1.25rem; }
.research-connections { position: absolute; inset: 0; z-index: 1; overflow: visible; pointer-events: none; }
.research-connections path { fill: none; stroke: color-mix(in srgb, var(--editor-color-muted) 72%, var(--editor-color-border)); stroke-width: 3; stroke-linejoin: round; vector-effect: non-scaling-stroke; }
.research-connections .research-connection--completed { stroke: color-mix(in srgb, var(--editor-color-focus) 78%, var(--editor-color-text)); }
.research-connections .research-connection--selected { stroke: var(--editor-color-focus); stroke-width: 4; }
.research-node { position: absolute; z-index: 2; display: grid; width: 9rem; height: 7rem; justify-items: center; align-content: start; gap: .35rem; padding: .45rem; border: 1px solid transparent; border-radius: var(--editor-radius-sm); color: var(--editor-color-text); background: color-mix(in srgb, var(--editor-color-surface) 76%, transparent); cursor: pointer; transform: translateX(-50%); }
.research-node:hover, .research-node--selected { border-color: var(--editor-color-focus); background: color-mix(in srgb, var(--editor-color-focus) 11%, transparent); }
.research-node__diamond { position: relative; display: grid; width: 3.4rem; height: 3.4rem; place-items: center; border: .22rem solid var(--editor-color-muted); color: var(--editor-color-text); background: var(--editor-color-surface-raised); transform: rotate(45deg); }
.research-node__diamond img { width: 2.35rem; height: 2.35rem; object-fit: contain; transform: rotate(-45deg); opacity: .58; }
.research-node--completed .research-node__diamond { border-color: var(--editor-color-focus); background: color-mix(in srgb, var(--editor-color-focus) 24%, var(--editor-color-surface)); box-shadow: 0 0 .8rem color-mix(in srgb, var(--editor-color-focus) 30%, transparent); }
.research-node--completed .research-node__diamond img { opacity: 1; }
.research-node--locked { opacity: .45; }
.research-node__check { position: absolute; right: -.35rem; bottom: -.35rem; display: grid; width: 1.1rem; height: 1.1rem; place-items: center; border-radius: 50%; color: var(--editor-color-background); background: var(--editor-color-focus); font-size: .75rem; transform: rotate(-45deg); }
.research-node__effect { max-width: 100%; overflow: hidden; font-size: .76rem; font-weight: 700; text-overflow: ellipsis; white-space: nowrap; }
.research-node small { display: -webkit-box; overflow: hidden; color: var(--editor-color-muted); font-size: .64rem; -webkit-box-orient: vertical; -webkit-line-clamp: 2; }
.effect-panel { display: flex; flex-direction: column; gap: .7rem; padding: 1rem; overflow: auto; scrollbar-gutter: stable; }
.effect-panel h2, .effect-panel p { margin: 0; }
.effect-panel__badge { display: grid; width: 5rem; height: 5rem; place-items: center; align-self: center; border: .25rem solid var(--editor-color-muted); background: var(--editor-color-surface-raised); transform: rotate(45deg); }
.effect-panel__badge img { width: 3.1rem; height: 3.1rem; object-fit: contain; opacity: .62; transform: rotate(-45deg); }
.effect-panel__badge--completed { border-color: var(--editor-color-focus); box-shadow: 0 0 1rem color-mix(in srgb, var(--editor-color-focus) 30%, transparent); }
.effect-panel__badge--completed img { opacity: 1; }
.effect-panel__effect { color: var(--editor-color-focus); font-weight: 700; }
.effect-panel__status, .material-row { display: flex; justify-content: space-between; gap: .5rem; font-size: .8rem; }
.progress-track { height: .45rem; overflow: hidden; border-radius: 999px; background: var(--editor-color-control); }
.progress-track span { display: block; height: 100%; background: var(--editor-color-focus); }
.research-status { padding: .45rem .6rem; border: 1px solid var(--editor-color-border); border-radius: var(--editor-radius-sm); color: var(--editor-color-focus); text-align: center; }
.research-status--completed { color: var(--editor-color-success); }
.research-status--locked { color: var(--editor-color-muted); }
.materials { display: grid; gap: .35rem; padding-top: .5rem; border-top: 1px solid var(--editor-color-border); }
.materials h3 { margin: 0 0 .2rem; font-size: .78rem; text-transform: uppercase; }
.research-id { overflow-wrap: anywhere; color: var(--editor-color-muted); font-size: .62rem; text-align: center; }
.lab-empty { display: grid; min-height: 16rem; place-items: center; border: 1px solid var(--editor-color-border); border-radius: var(--editor-radius-md); color: var(--editor-color-muted); }
@media (max-width: 1180px) {
  .lab-workspace { grid-template-columns: minmax(9rem, 12rem) minmax(22rem, 1fr); grid-template-rows: minmax(15rem, 1fr) minmax(11rem, .65fr); }
  .effect-panel { grid-column: 1 / -1; }
}
@media (max-width: 760px) {
  .basecamp-editor { height: auto; overflow: visible; }
  .lab-header { align-items: stretch; flex-direction: column; }
  .lab-header__actions { justify-content: stretch; }
  .lab-workspace { display: flex; height: auto; flex-direction: column; overflow: visible; }
  .category-rail { height: auto; grid-template-columns: repeat(2, minmax(0, 1fr)); overflow: visible; }
  .research-tree { height: min(38rem, 70dvh); }
  .effect-panel { height: auto; overflow: visible; }
}
@media (max-width: 480px) { .category-rail { grid-template-columns: 1fr; } }
</style>
