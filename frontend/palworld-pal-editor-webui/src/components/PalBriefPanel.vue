<script setup>
import { computed } from 'vue'

import PalPortrait from '@/components/PalPortrait.vue'
import { useCatalogsStore } from '@/stores/catalogs'
import { usePalEditorStore } from '@/stores/paleditor'

const props = defineProps({
  data: { type: Object, default: () => ({}) },
  title: { type: String, default: '' },
  changedFields: { type: Object, default: () => ({}) },
  tone: { type: String, default: 'neutral' },
})
const catalogsStore = useCatalogsStore()
const palStore = usePalEditorStore()
const changed = key => Object.hasOwn(props.changedFields, key)
const uiIcon = name => palStore.backendAssetUrl(`/image/ui/${name}`)
const cleanLabel = key => palStore.getTranslatedText(key).replace(/\s*[:：]\s*$/, '').trim()
const attributeLabel = row => row.suffix
  ? `${cleanLabel(row.label)} ${cleanLabel(row.suffix)}`
  : cleanLabel(row.label)
const friendshipPercent = computed(() => Math.min(
  100,
  Math.max(0, Number(props.data.FriendshipLevel || 0) * 100 / palStore.MAX_FRIENDSHIP_LEVEL),
))
const potentialRows = computed(() => [
  { key: 'Rank', label: 'Editor_Condenser_Rank', icon: 'condense', value: Math.max(0, Number(props.data.Rank ?? 1) - 1) },
  { key: 'Talent_HP', label: 'Editor_IV_HP', suffix: 'Editor_IV', icon: 'stat-health', value: props.data.Talent_HP ?? 0 },
  { key: 'Talent_Shot', label: 'Editor_IV_ATK', suffix: 'Editor_IV', icon: 'stat-attack', value: props.data.Talent_Shot ?? 0 },
  { key: 'Talent_Defense', label: 'Editor_IV_DEF', suffix: 'Editor_IV', icon: 'stat-defense', value: props.data.Talent_Defense ?? 0 },
])
const soulRows = computed(() => [
  { key: 'Rank_HP', label: 'Editor_Souls_HP', icon: 'stat-health', value: props.data.Rank_HP ?? 0 },
  { key: 'Rank_Attack', label: 'Editor_Souls_ATK', icon: 'stat-attack', value: props.data.Rank_Attack ?? 0 },
  { key: 'Rank_Defence', label: 'Editor_Souls_DEF', icon: 'stat-defense', value: props.data.Rank_Defence ?? 0 },
  { key: 'Rank_CraftSpeed', label: 'Editor_Souls_CraftSpeed', icon: 'stat-work-speed', value: props.data.Rank_CraftSpeed ?? 0 },
])
const suitabilityEntries = computed(() => Object.entries(props.data.Suitabilities || {})
  .filter(([, value]) => Number(value) > 0))
const activeSkills = computed(() => props.data.EquipWaza || [])
const passiveSkills = computed(() => props.data.PassiveSkillList || [])
const passiveName = skill => catalogsStore.passiveSkillsByName[skill]?.I18n?.[0] || skill
const activeName = skill => catalogsStore.activeSkillsByName[skill]?.I18n?.[0] || skill
const portraitBorder = computed(() => props.data.IsAwakening
  ? 'var(--editor-color-awakened)'
  : props.data.IsBOSS
  ? 'var(--editor-color-danger)'
  : props.data.IsRarePal ? 'var(--editor-color-lucky)' : 'var(--editor-color-border)')
const elementIcon = skill => {
  const key = palStore.elementIconKey(catalogsStore.activeSkillsByName[skill]?.Element)
  return key ? palStore.backendAssetUrl(`/image/elements/Element_${key}`) : uiIcon('stat-attack')
}
</script>

<template>
  <article :class="['pal-brief', 'editor-glass-surface', `pal-brief--${tone}`]">
    <p class="pal-brief__title">{{ title }}</p>
    <header>
      <PalPortrait :src="palStore.backendAssetUrl(`/image/pals/${data.IconKey}`)" alt="" size="4.25rem"
        :border-color="portraitBorder"
        :glow-color="data.IsAwakening ? 'var(--editor-color-awakened)' : ''">
        <template #top-left>
          <img v-if="data.IsBOSS" :src="uiIcon('boss')" alt="" @error="$event.currentTarget.hidden = true">
          <img v-else-if="data.IsRarePal" class="game-lucky-icon"
            :src="uiIcon('rare')" alt="" @error="$event.currentTarget.hidden = true">
        </template>
        <template #top-right>
          <img v-if="data.FavoriteIndex > 0" class="game-priority-icon"
            :src="uiIcon(`priority-${data.FavoriteIndex}`)" alt="" @error="$event.currentTarget.hidden = true">
          <img v-else-if="data.IsBOSS && data.IsRarePal" class="game-lucky-icon"
            :src="uiIcon('rare')" alt="" @error="$event.currentTarget.hidden = true">
        </template>
        <template #bottom-left>
          <img v-if="data.FavoriteIndex > 0 && data.IsBOSS && data.IsRarePal" class="game-lucky-icon"
            :src="uiIcon('rare')" alt="" @error="$event.currentTarget.hidden = true">
          <img v-if="data.IsImportedCharacter" class="game-dna-icon"
            :src="uiIcon('dna')" alt="" @error="$event.currentTarget.hidden = true">
        </template>
      </PalPortrait>
      <div class="pal-brief__identity">
        <strong :class="{ changed: changed('NickName') || changed('DisplayName') }">
          {{ data.NickName || data.DisplayName || data.CharacterID }}
        </strong>
        <span>{{ data.DisplayName }} · {{ data.CharacterID }}</span>
        <span :class="{ changed: changed('Level') }">
          {{ palStore.getTranslatedText('PalBrief_Level') }} {{ data.Level }}
        </span>
      </div>
    </header>

    <dl class="pal-brief__friendship-row" :class="{ changed: changed('FriendshipLevel') }">
      <div>
        <dt><img :src="uiIcon('friendship')" alt=""><span>{{ palStore.getTranslatedText('Editor_Friendship_Level') }}</span></dt>
        <dd>{{ data.FriendshipLevel }}</dd>
        <i><b :style="{ width: `${friendshipPercent}%` }" /></i>
      </div>
    </dl>

    <div class="pal-brief__attributes">
      <dl class="pal-brief__attribute-column">
        <div v-for="row in potentialRows" :key="row.key" :class="{ changed: changed(row.key) }">
          <dt><img :src="uiIcon(row.icon)" alt=""><span>{{ attributeLabel(row) }}</span></dt>
          <dd>{{ row.value }}</dd>
        </div>
      </dl>
      <dl class="pal-brief__attribute-column">
        <div v-for="row in soulRows" :key="row.key" :class="{ changed: changed(row.key) }">
          <dt><img :src="uiIcon(row.icon)" alt=""><span>{{ attributeLabel(row) }}</span></dt>
          <dd>{{ row.value }}</dd>
        </div>
      </dl>
    </div>

    <section v-if="suitabilityEntries.length" class="pal-brief__section">
      <h4>{{ palStore.getTranslatedText('Editor_Suitabilities') }}</h4>
      <div class="pal-brief__suitabilities" :class="{ changed: changed('Suitabilities') }">
        <span v-for="([key, value]) in suitabilityEntries" :key="key" :title="key.split('::').pop()">
          <img :src="palStore.backendAssetUrl(`/image/suitabilities/${key.split('::').pop()}`)" alt="">
          <b>{{ value }}</b>
        </span>
      </div>
    </section>

    <section v-if="activeSkills.length" class="pal-brief__section pal-brief__section--skills"
      :class="{ changed: changed('EquipWaza') }">
      <h4>{{ palStore.getTranslatedText('Editor_Equipped_Skills') }}</h4>
      <b v-if="activeSkills.length > 3" class="pal-brief__overflow">+{{ activeSkills.length - 3 }}</b>
      <div class="pal-brief__active-skills">
        <div v-for="skill in activeSkills.slice(0, 3)" :key="skill" :title="catalogsStore.activeSkillsByName[skill]?.I18n?.[1] || skill">
          <img :src="elementIcon(skill)" alt="">
          <strong>{{ activeName(skill) }}</strong>
          <small v-if="catalogsStore.activeSkillsByName[skill]">
            {{ palStore.getTranslatedText('Editor_Skill_ATK') }}{{ catalogsStore.activeSkillsByName[skill].Power }} ·
            {{ palStore.getTranslatedText('Editor_Skill_CD') }}{{ catalogsStore.activeSkillsByName[skill].CT }}
          </small>
        </div>
      </div>
    </section>

    <section v-if="passiveSkills.length" class="pal-brief__section pal-brief__section--skills"
      :class="{ changed: changed('PassiveSkillList') }">
      <h4>{{ palStore.getTranslatedText('Editor_Passive_Skills') }}</h4>
      <b v-if="passiveSkills.length > 4" class="pal-brief__overflow">+{{ passiveSkills.length - 4 }}</b>
      <div class="pal-brief__passive-skills">
        <div v-for="skill in passiveSkills.slice(0, 4)" :key="skill"
          :title="catalogsStore.passiveSkillsByName[skill]?.I18n?.[1] || skill">
          <i :class="`passive-tier--${palStore.passiveTier(catalogsStore.passiveSkillsByName[skill]?.Rating)}`" />
          <strong>{{ passiveName(skill) }}</strong>
        </div>
      </div>
    </section>
  </article>
</template>

<style scoped>
.pal-brief {
  --pal-brief-change: var(--editor-color-primary);
  display: grid;
  width: 28rem;
  min-width: 0;
  box-sizing: border-box;
  gap: .72rem;
  padding: 1rem;
  border: 1px solid color-mix(in srgb, var(--editor-color-primary) 30%, var(--editor-color-glass-border));
  border-radius: var(--editor-radius-md);
  background: var(--editor-color-glass-surface);
  -webkit-backdrop-filter: var(--editor-glass-filter);
  backdrop-filter: var(--editor-glass-filter);
  box-shadow: var(--editor-shadow-compact);
}

.pal-brief__title {
  margin: 0;
  color: var(--editor-color-primary);
  font-size: .68rem;
  letter-spacing: .06em;
  text-transform: uppercase;
}

header {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  gap: .7rem;
}

.pal-brief__identity { display: grid; min-width: 0; gap: .08rem; }
.pal-brief__identity strong,
.pal-brief__identity span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.pal-brief__identity strong { font-size: 1.08rem; }
.pal-brief__identity span { color: var(--editor-color-muted); font-size: .76rem; }

.pal-brief__attributes { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: .38rem; }
.pal-brief__attribute-column { display: grid; align-content: start; margin: 0; gap: .26rem; }
.pal-brief__friendship-row { margin: 0; }
.pal-brief__friendship-row > div,
.pal-brief__attribute-column > div {
  position: relative;
  display: grid;
  min-width: 0;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  gap: .25rem;
  min-height: 1.8rem;
  box-sizing: border-box;
  padding: .22rem .34rem;
  border: 1px solid color-mix(in srgb, var(--editor-color-border) 70%, transparent);
  border-radius: .25rem;
  background: color-mix(in srgb, var(--editor-color-control) 82%, transparent);
}

dt { display: flex; min-width: 0; align-items: center; gap: .28rem; }
dt img { width: .9rem; height: .9rem; flex: 0 0 auto; object-fit: contain; }
dt span { overflow: hidden; color: var(--editor-color-muted); font-size: .7rem; text-overflow: ellipsis; white-space: nowrap; }
dd { display: flex; align-items: center; gap: .22rem; margin: 0; font-size: .78rem; font-weight: 700; font-variant-numeric: tabular-nums; }

.pal-brief__friendship-row > div { padding-bottom: .38rem; }
.pal-brief__friendship-row i { position: absolute; right: .34rem; bottom: .16rem; left: .34rem; height: .18rem; overflow: hidden; border-radius: 999px; background: rgb(255 255 255 / .08); }
.pal-brief__friendship-row i b { display: block; height: 100%; background: linear-gradient(90deg, #d94691, #ff85c2); }

.pal-brief__section { position: relative; min-width: 0; }
h4 { margin: 0 0 .28rem; color: var(--editor-color-muted); font-size: .61rem; letter-spacing: .03em; }

.pal-brief__suitabilities { display: flex; min-width: 0; gap: .3rem; overflow: hidden; }
.pal-brief__suitabilities span {
  position: relative;
  display: grid;
  width: 1.75rem;
  height: 1.75rem;
  flex: 0 0 auto;
  place-items: center;
  border: 1px solid var(--editor-color-border);
  border-radius: .28rem;
  background: color-mix(in srgb, var(--editor-color-control) 78%, transparent);
}
.pal-brief__suitabilities img { width: 1.35rem; height: 1.35rem; object-fit: contain; }
.pal-brief__suitabilities b {
  position: absolute;
  right: -.14rem;
  bottom: -.14rem;
  display: grid;
  min-width: .78rem;
  height: .78rem;
  padding: 0 .1rem;
  place-items: center;
  border-radius: 999px;
  color: white;
  background: #087ea4;
  font-size: .48rem;
  line-height: 1;
}

.pal-brief__section--skills { padding: .34rem; border-radius: .3rem; background: rgb(0 0 0 / .12); }
.pal-brief__active-skills { display: grid; gap: .25rem; }
.pal-brief__active-skills > div {
  display: grid;
  min-width: 0;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  gap: .35rem;
  min-height: 1.6rem;
  padding: .22rem .35rem;
  border-left: 2px solid #38bdf8;
  background: color-mix(in srgb, var(--editor-color-control) 78%, transparent);
}
.pal-brief__active-skills img { width: 1.05rem; height: 1.05rem; object-fit: contain; }
.pal-brief__active-skills strong,
.pal-brief__active-skills small { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.pal-brief__active-skills strong { font-size: .72rem; }
.pal-brief__active-skills small { color: var(--editor-color-muted); font-size: .6rem; }

.pal-brief__passive-skills { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: .25rem; }
.pal-brief__passive-skills > div {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: .3rem;
  min-height: 1.45rem;
  padding: .2rem .32rem;
  border: 1px solid var(--editor-color-border);
  border-radius: .22rem;
  background: color-mix(in srgb, var(--editor-color-control) 78%, transparent);
}
.pal-brief__passive-skills i { width: .42rem; height: .85rem; flex: 0 0 auto; border-radius: 999px; background: var(--editor-color-muted); }
.pal-brief__passive-skills i.passive-tier--negative { background: var(--editor-color-passive-negative); }
.pal-brief__passive-skills i.passive-tier--positive { background: var(--editor-color-passive-positive); }
.pal-brief__passive-skills i.passive-tier--high { background: var(--editor-color-passive-high); }
.pal-brief__passive-skills i.passive-tier--top { background: var(--editor-color-passive-top); }
.pal-brief__passive-skills strong { overflow: hidden; font-size: .7rem; text-overflow: ellipsis; white-space: nowrap; }
.pal-brief__overflow {
  position: absolute;
  top: .22rem;
  right: .3rem;
  padding: .08rem .28rem;
  border-radius: 999px;
  color: white;
  background: var(--editor-color-primary);
  font-size: .52rem;
  line-height: 1.2;
}

.pal-brief__identity .changed {
  color: var(--editor-color-text);
  text-decoration: underline .12rem var(--pal-brief-change);
  text-underline-offset: .18rem;
}

.pal-brief__friendship-row.changed > div,
.pal-brief__attribute-column > .changed,
.pal-brief__suitabilities.changed,
.pal-brief__section.changed {
  border-color: color-mix(in srgb, var(--pal-brief-change) 55%, var(--editor-color-border));
  background: color-mix(in srgb, var(--pal-brief-change) 9%, var(--editor-color-control));
  box-shadow: inset .18rem 0 var(--pal-brief-change);
}

.pal-brief__suitabilities.changed { padding: .28rem; border-radius: .3rem; }

@media (max-width: 700px) {
  .pal-brief { width: min(28rem, calc(100vw - 3rem)); }
}
</style>
