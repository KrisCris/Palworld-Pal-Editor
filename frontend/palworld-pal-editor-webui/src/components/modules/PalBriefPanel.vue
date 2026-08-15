<script setup>
import { computed } from 'vue'

import PalPortrait from '@/components/modules/PalPortrait.vue'
import { usePalEditorStore } from '@/stores/paleditor'

const props = defineProps({
  data: { type: Object, default: () => ({}) },
  title: { type: String, default: '' },
  changedFields: { type: Object, default: () => ({}) },
})
const palStore = usePalEditorStore()
const changed = key => Object.hasOwn(props.changedFields, key)
const uiIcon = name => palStore.backendAssetUrl(`/image/ui/${name}`)
const friendshipPercent = computed(() => Math.min(
  100,
  Math.max(0, Number(props.data.FriendshipLevel || 0) * 100 / palStore.MAX_FRIENDSHIP_LEVEL),
))
const progressRows = computed(() => [
  { key: 'Rank', label: 'Editor_Condenser_Rank', icon: 'condense', value: Math.max(0, Number(props.data.Rank ?? 1) - 1) },
  { key: 'Rank_HP', label: 'Editor_Souls_HP', icon: 'stat-health', value: props.data.Rank_HP ?? 0 },
  { key: 'Rank_Attack', label: 'Editor_Souls_ATK', icon: 'stat-attack', value: props.data.Rank_Attack ?? 0 },
  { key: 'Rank_Defence', label: 'Editor_Souls_DEF', icon: 'stat-defense', value: props.data.Rank_Defence ?? 0 },
  { key: 'Rank_CraftSpeed', label: 'Editor_Souls_CraftSpeed', icon: 'stat-work-speed', value: props.data.Rank_CraftSpeed ?? 0 },
])
const statRows = computed(() => [
  {
    key: 'ComputedMaxHP', label: 'Editor_Estimated_HP', icon: 'stat-health',
    value: props.data.ComputedMaxHP == null ? '—' : props.data.ComputedMaxHP / 1000,
    ivKey: 'Talent_HP', ivLabel: 'Editor_IV_HP', iv: props.data.Talent_HP,
  },
  {
    key: 'ComputedAttack', label: 'Editor_Estimated_ATK', icon: 'stat-attack',
    value: props.data.ComputedAttack ?? '—', ivKey: 'Talent_Shot', ivLabel: 'Editor_IV_ATK', iv: props.data.Talent_Shot,
  },
  {
    key: 'ComputedDefense', label: 'Editor_Estimated_DEF', icon: 'stat-defense',
    value: props.data.ComputedDefense ?? '—', ivKey: 'Talent_Defense', ivLabel: 'Editor_IV_DEF', iv: props.data.Talent_Defense,
  },
  {
    key: 'ComputedCraftSpeed', label: 'Editor_Estimated_WorkSpeed', icon: 'stat-work-speed',
    value: props.data.ComputedCraftSpeed ?? '—',
  },
])
const suitabilityEntries = computed(() => Object.entries(props.data.Suitabilities || {})
  .filter(([, value]) => Number(value) > 0))
const activeSkills = computed(() => props.data.EquipWaza || [])
const passiveSkills = computed(() => props.data.PassiveSkillList || [])
const passiveName = skill => palStore.PASSIVE_SKILLS[skill]?.I18n?.[0] || skill
const activeName = skill => palStore.ACTIVE_SKILLS[skill]?.I18n?.[0] || skill
const elementIcon = skill => {
  const key = palStore.elementIconKey(palStore.ACTIVE_SKILLS[skill]?.Element)
  return key ? palStore.backendAssetUrl(`/image/elements/Element_${key}`) : uiIcon('stat-attack')
}
</script>

<template>
  <article class="pal-brief editor-glass-surface">
    <p class="pal-brief__title">{{ title }}</p>
    <header>
      <PalPortrait :src="palStore.backendAssetUrl(`/image/pals/${data.IconKey}`)" alt="" size="4.25rem" />
      <div class="pal-brief__identity">
        <strong :class="{ changed: changed('NickName') || changed('DisplayName') }">
          {{ data.NickName || data.DisplayName || data.CharacterID }}
        </strong>
        <span>{{ data.DisplayName }} · {{ data.CharacterID }}</span>
        <span :class="{ changed: changed('Level') }">
          {{ palStore.getTranslatedText('PalBrief_Level') }} {{ data.Level }}
        </span>
      </div>
      <img v-if="data.FavoriteIndex" class="pal-brief__favorite"
        :src="uiIcon(`priority-${data.FavoriteIndex}`)"
        :title="palStore.getTranslatedText('PalList_Sort_Priority')" alt="">
    </header>

    <div class="pal-brief__attributes">
      <dl class="pal-brief__attribute-column">
        <div v-for="row in progressRows" :key="row.key" :class="{ changed: changed(row.key) }">
          <dt><img :src="uiIcon(row.icon)" alt=""><span>{{ palStore.getTranslatedText(row.label) }}</span></dt>
          <dd>{{ row.value }}</dd>
        </div>
      </dl>
      <dl class="pal-brief__attribute-column">
        <div class="pal-brief__friendship" :class="{ changed: changed('FriendshipLevel') }">
          <dt><img :src="uiIcon('friendship')" alt=""><span>{{ palStore.getTranslatedText('Editor_Friendship_Level') }}</span></dt>
          <dd>{{ data.FriendshipLevel }}</dd>
          <i><b :style="{ width: `${friendshipPercent}%` }" /></i>
        </div>
        <div v-for="row in statRows" :key="row.key" :class="{ changed: changed(row.key) || (row.ivKey && changed(row.ivKey)) }">
          <dt><img :src="uiIcon(row.icon)" alt=""><span>{{ palStore.getTranslatedText(row.label) }}</span></dt>
          <dd>
            <small v-if="row.iv != null" :class="{ changed: changed(row.ivKey) }"
              :title="palStore.getTranslatedText(row.ivLabel)">IV {{ row.iv }}</small>
            {{ row.value }}
          </dd>
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
        <div v-for="skill in activeSkills.slice(0, 3)" :key="skill" :title="palStore.ACTIVE_SKILLS[skill]?.I18n?.[1] || skill">
          <img :src="elementIcon(skill)" alt="">
          <strong>{{ activeName(skill) }}</strong>
          <small v-if="palStore.ACTIVE_SKILLS[skill]">
            {{ palStore.getTranslatedText('Editor_Skill_ATK') }}{{ palStore.ACTIVE_SKILLS[skill].Power }} ·
            {{ palStore.getTranslatedText('Editor_Skill_CD') }}{{ palStore.ACTIVE_SKILLS[skill].CT }}
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
          :title="palStore.PASSIVE_SKILLS[skill]?.I18n?.[1] || skill">
          <i :class="`passive-tier--${palStore.passiveTier(palStore.PASSIVE_SKILLS[skill]?.Rating)}`" />
          <strong>{{ passiveName(skill) }}</strong>
        </div>
      </div>
    </section>
  </article>
</template>

<style scoped>
.pal-brief {
  display: grid;
  width: 20.5rem;
  min-width: 0;
  box-sizing: border-box;
  gap: .58rem;
  padding: .85rem;
  border: 1px solid color-mix(in srgb, var(--editor-color-primary) 30%, var(--editor-color-glass-border));
  border-radius: var(--editor-radius-md);
  background: color-mix(in srgb, var(--editor-color-surface) 74%, transparent);
  box-shadow: var(--editor-shadow-compact);
  backdrop-filter: blur(20px) saturate(130%);
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
.pal-brief__identity strong { font-size: 1rem; }
.pal-brief__identity span { color: var(--editor-color-muted); font-size: .68rem; }
.pal-brief__favorite { width: 1.35rem; height: 1.35rem; object-fit: contain; }

.pal-brief__attributes { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: .38rem; }
.pal-brief__attribute-column { display: grid; align-content: start; margin: 0; gap: .26rem; }
.pal-brief__attribute-column > div {
  position: relative;
  display: grid;
  min-width: 0;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  gap: .25rem;
  min-height: 1.55rem;
  box-sizing: border-box;
  padding: .22rem .34rem;
  border: 1px solid color-mix(in srgb, var(--editor-color-border) 70%, transparent);
  border-radius: .25rem;
  background: color-mix(in srgb, var(--editor-color-control) 82%, transparent);
}

dt { display: flex; min-width: 0; align-items: center; gap: .28rem; }
dt img { width: .9rem; height: .9rem; flex: 0 0 auto; object-fit: contain; }
dt span { overflow: hidden; color: var(--editor-color-muted); font-size: .6rem; text-overflow: ellipsis; white-space: nowrap; }
dd { display: flex; align-items: center; gap: .22rem; margin: 0; font-size: .67rem; font-weight: 700; font-variant-numeric: tabular-nums; }
dd small { padding: .08rem .2rem; border-radius: .2rem; color: #7dd3fc; background: rgb(14 116 144 / .22); font-size: .5rem; font-weight: 700; }

.pal-brief__friendship { padding-bottom: .34rem !important; }
.pal-brief__friendship > i { position: absolute; right: .34rem; bottom: .16rem; left: .34rem; height: .18rem; overflow: hidden; border-radius: 999px; background: rgb(255 255 255 / .08); }
.pal-brief__friendship > i b { display: block; height: 100%; background: linear-gradient(90deg, #d94691, #ff85c2); }

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
.pal-brief__active-skills strong { font-size: .65rem; }
.pal-brief__active-skills small { color: var(--editor-color-muted); font-size: .52rem; }

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
.pal-brief__passive-skills i { width: .42rem; height: .85rem; flex: 0 0 auto; border-radius: 999px; background: #94a3b8; }
.pal-brief__passive-skills i.passive-tier--negative { background: #ef4444; }
.pal-brief__passive-skills i.passive-tier--positive { background: #2dd4bf; }
.pal-brief__passive-skills i.passive-tier--high { background: #38bdf8; }
.pal-brief__passive-skills i.passive-tier--top { background: #a78bfa; box-shadow: 0 0 .4rem #8b5cf6; }
.pal-brief__passive-skills strong { overflow: hidden; font-size: .61rem; text-overflow: ellipsis; white-space: nowrap; }
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

.changed { outline: 1px solid var(--editor-color-warning); outline-offset: 1px; }

@media (max-width: 700px) {
  .pal-brief { width: min(20.5rem, calc(100vw - 3rem)); }
}
</style>
