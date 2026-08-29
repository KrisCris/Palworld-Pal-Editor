<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import OverlayScrollArea from '@/components/modules/OverlayScrollArea.vue'
import SearchSelect from '@/components/modules/SearchSelect.vue'
import { usePalEditorStore } from '@/stores/paleditor'

const palStore = usePalEditorStore()
const selectedCategoryId = ref('Handcraft')
const selectedResearchId = ref(null)
const researchScroll = ref(null)
const researchScale = ref(1)
const graphMetrics = Object.freeze({
  levelHeight: 154,
  nodeWidth: 144,
  nodeHeight: 128,
  nodeGap: 48,
  paddingX: 56,
  paddingY: 0,
  railWidth: 68,
})

const guilds = computed(() => palStore.BASE_CAMP_RESEARCH?.Guilds ?? [])
const guildOptions = computed(() => guilds.value.map(guild => ({
  value: guild.GuildId,
  label: guild.GuildName,
})))
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
      + (graphMetrics.levelHeight - graphMetrics.nodeHeight) / 2
    return [node.ResearchId, {
      left: centerX,
      top,
    }]
  }))
  const connections = research.flatMap(node => {
    const parent = positions.get(node.RequiredResearchId)
    const child = positions.get(node.ResearchId)
    if (!parent || !child) return []
    const startY = parent.top + graphMetrics.nodeHeight * .6
    const endY = child.top + 4
    const separatorY = graphMetrics.paddingY
      + byId.get(node.RequiredResearchId).node.Level * graphMetrics.levelHeight
    return [{
      id: `${node.RequiredResearchId}-${node.ResearchId}`,
      parentId: node.RequiredResearchId,
      childId: node.ResearchId,
      completed: byId.get(node.RequiredResearchId).node.Completed && node.Completed,
      path: `M ${parent.left} ${startY} V ${separatorY} H ${child.left} V ${endY}`,
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
const categoryIcon = category => palStore.backendAssetUrl(`/image/lab/category-${category}`)
const researchIcon = research => palStore.backendAssetUrl(`/image/lab/${research.IconKey}`)
const formatNumber = value => new Intl.NumberFormat().format(value ?? 0)
const materialName = material => palStore.ITEM_STATIC_DATA[material.ItemId]?.Name ?? material.ItemId

const updateResearchScale = async () => {
  await nextTick()
  const availableWidth = researchScroll.value?.clientWidth
  if (!availableWidth || !treeLayout.value.width) return
  const nextScale = Math.max(.65, Math.min(1, availableWidth / treeLayout.value.width))
  if (Math.abs(nextScale - researchScale.value) > .001) researchScale.value = nextScale
}

let researchResizeObserver
let researchResizeFrame

const scheduleResearchScale = () => {
  if (researchResizeFrame) return
  researchResizeFrame = requestAnimationFrame(async () => {
    researchResizeFrame = undefined
    await updateResearchScale()
  })
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
  if (!await palStore.confirmMessage('BaseCamp_Research_Confirm_Category')) return
  await palStore.completeBaseCampResearch({ Category: selectedCategory.value.Category })
}

async function completeAll() {
  if (allCompleted.value) return
  if (!await palStore.confirmMessage('BaseCamp_Research_Confirm_All')) return
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

watch(() => [treeLayout.value.width, treeLayout.value.height], updateResearchScale, { immediate: true })

onMounted(() => {
  if (typeof ResizeObserver === 'undefined' || !researchScroll.value) return
  researchResizeObserver = new ResizeObserver(scheduleResearchScale)
  researchResizeObserver.observe(researchScroll.value)
})

onBeforeUnmount(() => {
  researchResizeObserver?.disconnect()
  if (researchResizeFrame) cancelAnimationFrame(researchResizeFrame)
})
</script>

<template>
  <section class="basecamp-editor">
    <header class="lab-header">
      <div>
        <p class="lab-header__eyebrow">{{ translated('BaseCamp_Research_BaseCamp') }}</p>
        <h1>{{ translated('BaseCamp_Research_Title') }}</h1>
      </div>
      <div class="lab-header__actions">
        <div v-if="guilds.length > 1" class="guild-select">
          <span>{{ translated('BaseCamp_Research_Guild') }}</span>
          <SearchSelect v-model="palStore.SELECTED_RESEARCH_GUILD_ID"
            :options="guildOptions"
            :placeholder="translated('BaseCamp_Research_Guild')"
            :search-placeholder="translated('Editor_Select_Search')"
            :no-results="translated('Editor_Select_No_Results')"
            :aria-label="translated('BaseCamp_Research_Guild')"
            :show-tooltip="false" />
        </div>
        <div v-else-if="selectedGuild" class="guild-name">
          <span>{{ translated('BaseCamp_Research_Guild') }}</span>
          <strong>{{ selectedGuild.GuildName }}</strong>
        </div>
        <button class="editor-button editor-button--danger" :disabled="allCompleted" @click="completeAll">
          {{ translated('BaseCamp_Research_Complete_All') }}
        </button>
      </div>
    </header>

    <div v-if="!selectedGuild" class="lab-empty">
      {{ translated('BaseCamp_Research_No_Data') }}
    </div>

    <div v-else class="lab-workspace">
      <nav class="category-rail" :aria-label="translated('BaseCamp_Research_Categories')">
        <OverlayScrollArea>
          <div class="category-rail__list overlay-scroll-area__viewport">
            <button v-for="category in categories" :key="category.Category"
              class="category-button" :class="{ 'category-button--active': category.Category === selectedCategory?.Category }"
              @click="selectCategory(category)">
              <img :src="categoryIcon(category.Category)" alt="">
              <span>{{ category.CategoryName ?? category.Category }}</span>
              <strong>{{ category.Completed }}<small>/{{ category.Total }}</small></strong>
            </button>
          </div>
        </OverlayScrollArea>
      </nav>

      <section class="research-tree">
        <header class="research-tree__header">
          <div class="research-tree__title">
            <img :src="categoryIcon(selectedCategory.Category)" alt="">
            <div>
              <p>{{ translated('BaseCamp_Research_Research_Level') }}</p>
              <h2>{{ selectedCategory.CategoryName ?? selectedCategory.Category }}</h2>
            </div>
            <strong>{{ selectedCategory.Completed }}<small>/{{ selectedCategory.Total }}</small></strong>
          </div>
          <button class="editor-button" :disabled="selectedCategory.Completed === selectedCategory.Total"
            @click="completeCategory">
            {{ translated('BaseCamp_Research_Complete_Category') }}
          </button>
        </header>

        <OverlayScrollArea>
          <div ref="researchScroll" class="research-scroll overlay-scroll-area__viewport">
          <div class="research-canvas-frame"
            :style="{ width: `${treeLayout.width * researchScale}px`, height: `${treeLayout.height * researchScale}px` }">
            <div class="research-level-rail"
              :style="{ width: `${graphMetrics.railWidth}px`, height: `${treeLayout.height}px`, transform: `scale(${researchScale})` }">
              <div v-for="level in treeLayout.levels" :key="level" class="research-level__label"
                :style="{ top: `${graphMetrics.paddingY + (level - 1) * graphMetrics.levelHeight}px`, height: `${graphMetrics.levelHeight}px` }">
                <img :src="categoryIcon(selectedCategory.Category)" alt="">
                <span>{{ translated('BaseCamp_Research_Level') }}</span>
                <strong>{{ level }}</strong>
              </div>
            </div>
            <div class="research-canvas"
              :style="{ width: `${treeLayout.width}px`, height: `${treeLayout.height}px`, transform: `translateX(-50%) scale(${researchScale})` }">
            <div v-for="level in treeLayout.levels" :key="level" class="research-level-band"
              :style="{ top: `${graphMetrics.paddingY + (level - 1) * graphMetrics.levelHeight}px`, height: `${graphMetrics.levelHeight}px` }">
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
              :title="research.EffectDescription" @click="selectResearch(research)">
              <span class="research-node__diamond">
                <img :src="researchIcon(research)" alt="">
                <span v-if="research.Completed" class="research-node__check">✓</span>
              </span>
              <span class="research-node__effect">{{ research.Name ?? research.EffectType }}</span>
              <small>{{ research.EffectDescription }}</small>
            </button>
            </div>
          </div>
          </div>
        </OverlayScrollArea>
      </section>

      <aside class="effect-panel">
        <OverlayScrollArea>
          <div class="effect-panel__content overlay-scroll-area__viewport">
            <template v-if="selectedResearch">
          <p class="effect-panel__eyebrow">{{ translated('BaseCamp_Research_Effect') }}</p>
          <div class="effect-panel__badge" :class="{ 'effect-panel__badge--completed': selectedResearch.Completed }">
            <img :src="researchIcon(selectedResearch)" alt="">
          </div>
          <h2>{{ selectedResearch.Name ?? selectedResearch.EffectType }}</h2>
          <p class="effect-panel__effect">{{ selectedResearch.EffectDescription }}</p>

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

          <button class="editor-button editor-button--primary" :disabled="selectedResearch.Completed"
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
          </div>
        </OverlayScrollArea>
      </aside>
    </div>
  </section>
</template>

<style scoped>
.basecamp-editor { display: grid; min-width: 0; min-height: 0; height: 100%; grid-template-rows: auto minmax(0, 1fr); overflow: hidden; color: var(--editor-color-text); }
.lab-header { display: flex; align-items: center; justify-content: space-between; gap: 1rem; margin-bottom: .6rem; padding: .7rem .85rem; border: 1px solid var(--editor-color-glass-border); border-radius: var(--editor-radius-md); background: var(--editor-color-glass-surface); -webkit-backdrop-filter: var(--editor-glass-filter); backdrop-filter: var(--editor-glass-filter); box-shadow: var(--editor-glass-shadow); }
.lab-header h1 { margin: .05rem 0; font-size: clamp(1.2rem, 2vw, 1.7rem); }
.lab-header p { margin: 0; color: var(--editor-color-muted); }
.lab-header__eyebrow, .effect-panel__eyebrow, .research-tree__title p { font-size: .72rem; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; }
.lab-header__actions { display: flex; flex-wrap: wrap; align-items: end; justify-content: end; gap: .6rem; }
.guild-select, .guild-name { display: grid; gap: .2rem; color: var(--editor-color-muted); font-size: .72rem; }
.guild-select :deep(.search-select) { min-width: 11rem; }
.guild-select :deep(.search-select summary) { min-height: var(--editor-control-height); }
.guild-name strong { color: var(--editor-color-text); font-size: .9rem; }
.lab-workspace { display: grid; min-width: 0; min-height: 0; height: 100%; grid-template-columns: minmax(9.5rem, 13rem) minmax(24rem, 1fr) minmax(13rem, 17rem); gap: .65rem; overflow: hidden; }
.category-rail, .research-tree, .effect-panel { min-width: 0; min-height: 0; height: 100%; border: 1px solid var(--editor-color-glass-border); border-radius: var(--editor-radius-md); background: var(--editor-color-glass-surface); }
.category-rail__list { display: grid; align-content: start; gap: .35rem; padding: .55rem; overflow-y: auto; }
.category-button { display: grid; grid-template-columns: 2rem minmax(0, 1fr) auto; align-items: center; gap: .5rem; min-height: 3.4rem; padding: .45rem .55rem; border: 1px solid var(--editor-color-border); border-radius: var(--editor-radius-sm); color: var(--editor-color-text); background: color-mix(in srgb, var(--editor-color-surface) 85%, transparent); text-align: left; cursor: pointer; }
.category-button:hover, .category-button--active { border-color: var(--editor-color-focus); background: color-mix(in srgb, var(--editor-color-focus) 17%, var(--editor-color-surface)); box-shadow: inset .18rem 0 var(--editor-color-focus); }
.category-button img, .research-tree__title img, .research-level__label img { width: 1.75rem; height: 1.75rem; object-fit: contain; }
.category-button strong, .research-tree__title > strong { color: var(--editor-color-focus); font-size: 1.05rem; }
.category-button small, .research-tree__title small { opacity: .65; font-size: .72em; }
.research-tree { display: grid; grid-template-rows: auto minmax(0, 1fr); overflow: hidden; }
.research-tree__header { display: flex; align-items: center; justify-content: space-between; gap: .75rem; padding: .7rem .85rem; border-bottom: 1px solid var(--editor-color-border); background: var(--editor-color-glass-surface); -webkit-backdrop-filter: var(--editor-glass-filter); backdrop-filter: var(--editor-glass-filter); }
.research-tree__title { display: grid; min-width: 0; grid-template-columns: 2.2rem minmax(0, 1fr) auto; align-items: center; gap: .5rem; }
.research-tree__title h2, .research-tree__title p { margin: 0; }
.research-scroll { min-width: 0; min-height: 0; overflow-y: auto; }
.research-canvas-frame { position: relative; min-width: 100%; min-height: 100%; }
.research-level-rail { position: absolute; top: 0; left: 0; z-index: 3; transform-origin: top left; pointer-events: none; }
.research-canvas { position: absolute; top: 0; left: 50%; transform-origin: top center; }
.research-level-band { position: absolute; right: 0; left: 0; z-index: 0; border-bottom: 1px solid color-mix(in srgb, var(--editor-color-focus) 16%, transparent); pointer-events: none; }
.research-level__label { position: absolute; left: 0; display: grid; width: 4.25rem; place-items: center; align-content: center; gap: .1rem; border-right: 1px solid color-mix(in srgb, var(--editor-color-focus) 18%, var(--editor-color-border)); color: var(--editor-color-focus); background: var(--editor-color-glass-surface); -webkit-backdrop-filter: var(--editor-glass-filter); backdrop-filter: var(--editor-glass-filter); }
.research-level__label span { font-size: .7rem; text-transform: uppercase; }
.research-level__label strong { font-size: 1.25rem; }
.research-connections { position: absolute; inset: 0; z-index: 1; overflow: visible; pointer-events: none; }
.research-connections path { fill: none; stroke: color-mix(in srgb, var(--editor-color-muted) 72%, var(--editor-color-border)); stroke-width: 3; stroke-linejoin: round; vector-effect: non-scaling-stroke; }
.research-connections .research-connection--completed { stroke: color-mix(in srgb, var(--editor-color-focus) 78%, var(--editor-color-text)); }
.research-connections .research-connection--selected { stroke: var(--editor-color-focus); stroke-width: 4; }
.research-node { position: absolute; z-index: 2; display: grid; width: 9rem; min-height: 8rem; justify-items: center; align-content: center; gap: .25rem; padding: .45rem; border: 1px solid transparent; border-radius: var(--editor-radius-sm); color: var(--editor-color-text); background: transparent; cursor: pointer; transform: translateX(-50%); }
.research-node:hover, .research-node--selected { border-color: var(--editor-color-focus); background: color-mix(in srgb, var(--editor-color-focus) 11%, transparent); }
.research-node__diamond { position: relative; display: grid; width: 3.4rem; height: 3.4rem; margin-bottom: .45rem; place-items: center; border: .22rem solid var(--editor-color-muted); color: var(--editor-color-text); background: var(--editor-color-surface-raised); transform: rotate(45deg); }
.research-node__diamond img { width: 2.35rem; height: 2.35rem; object-fit: contain; transform: rotate(-45deg); opacity: .58; }
.research-node--completed .research-node__diamond { border-color: var(--editor-color-focus); background: color-mix(in srgb, var(--editor-color-focus) 24%, var(--editor-color-surface)); box-shadow: 0 0 .8rem color-mix(in srgb, var(--editor-color-focus) 30%, transparent); }
.research-node--completed .research-node__diamond img { opacity: 1; }
.research-node--locked { opacity: .45; }
.research-node__check { position: absolute; right: -.35rem; bottom: -.35rem; display: grid; width: 1.1rem; height: 1.1rem; place-items: center; border-radius: 50%; color: var(--editor-color-background); background: var(--editor-color-focus); font-size: .75rem; transform: rotate(-45deg); }
.research-node__effect { max-width: 100%; overflow: hidden; font-size: .76rem; font-weight: 700; text-overflow: ellipsis; white-space: nowrap; }
.research-node small { color: var(--editor-color-muted); font-size: .64rem; line-height: 1.25; text-align: center; overflow-wrap: anywhere; }
.effect-panel__content { display: flex; flex-direction: column; gap: .7rem; padding: 1rem; overflow-y: auto; }
.effect-panel h2, .effect-panel p { margin: 0; }
.effect-panel__badge { display: grid; width: 5rem; height: 5rem; place-items: center; align-self: center; border: .25rem solid var(--editor-color-muted); background: var(--editor-color-surface-raised); transform: rotate(45deg); }
.effect-panel__badge img { width: 3.1rem; height: 3.1rem; object-fit: contain; opacity: .62; transform: rotate(-45deg); }
.effect-panel__badge--completed { border-color: var(--editor-color-focus); box-shadow: 0 0 1rem color-mix(in srgb, var(--editor-color-focus) 30%, transparent); }
.effect-panel__badge--completed img { opacity: 1; }
.effect-panel__effect { color: var(--editor-color-focus); font-weight: 700; }
.effect-panel__content h2 { margin-top: .7rem; margin-bottom: -.75rem; }
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
  .basecamp-editor { height: auto; overflow: visible; }
  .lab-header { align-items: stretch; flex-direction: column; }
  .lab-header__actions { justify-content: stretch; }
  .lab-workspace { display: flex; height: auto; flex-direction: column; overflow: visible; }
  .category-rail { height: auto; }
  .category-rail__list { grid-template-columns: repeat(3, minmax(0, 1fr)); }
  .research-tree { height: min(38rem, 70dvh); }
  .effect-panel { height: auto; }
  .effect-panel__content { overflow: visible; }
}
@media (max-width: 480px) { .category-rail__list { grid-template-columns: 1fr; } }
</style>
