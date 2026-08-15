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
const friendshipPercent = computed(() => Math.min(
  100,
  Math.max(0, Number(props.data.FriendshipLevel || 0) * 100 / palStore.MAX_FRIENDSHIP_LEVEL),
))
const passiveName = skill => palStore.PASSIVE_SKILLS[skill]?.I18n?.[0] || skill
const activeName = skill => palStore.ACTIVE_SKILLS[skill]?.I18n?.[0] || skill
</script>

<template>
  <article class="pal-brief editor-glass-surface">
    <p class="pal-brief__title">{{ title }}</p>
    <header>
      <PalPortrait :src="palStore.backendAssetUrl(`/image/pals/${data.IconKey}`)" alt="" size="4.5rem" />
      <div>
        <strong :class="{ changed: changed('NickName') || changed('DisplayName') }">
          {{ data.NickName || data.DisplayName || data.CharacterID }}
        </strong>
        <span>{{ data.DisplayName }} · {{ data.CharacterID }}</span>
        <span :class="{ changed: changed('Level') }">
          {{ palStore.getTranslatedText('PalBrief_Level') }} {{ data.Level }}
        </span>
      </div>
      <b v-if="data.FavoriteIndex" class="pal-brief__favorite" :title="palStore.getTranslatedText('PalList_Sort_Priority')">
        ★{{ data.FavoriteIndex }}
      </b>
    </header>

    <div class="pal-brief__friendship" :class="{ changed: changed('FriendshipLevel') }">
      <span>{{ palStore.getTranslatedText('Editor_Friendship_Level') }}{{ data.FriendshipLevel }}</span>
      <i><b :style="{ width: `${friendshipPercent}%` }" /></i>
    </div>

    <dl class="pal-brief__metrics">
      <div :class="{ changed: changed('Rank') }"><dt>{{ palStore.getTranslatedText('Editor_Condenser_Rank') }}</dt><dd>{{ data.Rank }}</dd></div>
      <div :class="{ changed: changed('Talent_HP') }"><dt>{{ palStore.getTranslatedText('Editor_IV_HP') }}</dt><dd>{{ data.Talent_HP }}</dd></div>
      <div :class="{ changed: changed('Talent_Shot') }"><dt>{{ palStore.getTranslatedText('Editor_IV_ATK') }}</dt><dd>{{ data.Talent_Shot }}</dd></div>
      <div :class="{ changed: changed('Talent_Defense') }"><dt>{{ palStore.getTranslatedText('Editor_IV_DEF') }}</dt><dd>{{ data.Talent_Defense }}</dd></div>
      <div :class="{ changed: changed('ComputedMaxHP') }"><dt>{{ palStore.getTranslatedText('Editor_Estimated_HP') }}</dt><dd>{{ data.ComputedMaxHP == null ? '—' : data.ComputedMaxHP / 1000 }}</dd></div>
      <div :class="{ changed: changed('ComputedAttack') }"><dt>{{ palStore.getTranslatedText('Editor_Estimated_ATK') }}</dt><dd>{{ data.ComputedAttack ?? '—' }}</dd></div>
      <div :class="{ changed: changed('ComputedDefense') }"><dt>{{ palStore.getTranslatedText('Editor_Estimated_DEF') }}</dt><dd>{{ data.ComputedDefense ?? '—' }}</dd></div>
      <div :class="{ changed: changed('ComputedCraftSpeed') }"><dt>{{ palStore.getTranslatedText('Editor_Estimated_WorkSpeed') }}</dt><dd>{{ data.ComputedCraftSpeed ?? '—' }}</dd></div>
    </dl>

    <section v-if="data.PassiveSkillList?.length">
      <h4>{{ palStore.getTranslatedText('Editor_Passive_Skills') }}</h4>
      <div class="pal-brief__chips" :class="{ changed: changed('PassiveSkillList') }">
        <span v-for="skill in data.PassiveSkillList" :key="skill">{{ passiveName(skill) }}</span>
      </div>
    </section>
    <section v-if="data.EquipWaza?.length">
      <h4>{{ palStore.getTranslatedText('Editor_Equipped_Skills') }}</h4>
      <div class="pal-brief__chips" :class="{ changed: changed('EquipWaza') }">
        <span v-for="skill in data.EquipWaza" :key="skill">{{ activeName(skill) }}</span>
      </div>
    </section>
  </article>
</template>

<style scoped>
.pal-brief {
  display: grid;
  min-width: 0;
  gap: .65rem;
  padding: 1rem;
  border: 1px solid color-mix(in srgb, var(--editor-color-primary) 28%, var(--editor-color-glass-border));
  border-radius: var(--editor-radius-md);
  background: color-mix(in srgb, var(--editor-color-surface) 78%, transparent);
  box-shadow: var(--editor-shadow-compact);
  backdrop-filter: blur(18px) saturate(125%);
}
.pal-brief__title { margin: 0; color: var(--editor-color-primary); font-size: .72rem; text-transform: uppercase; }
header { display: grid; grid-template-columns: auto minmax(0, 1fr) auto; align-items: center; gap: .8rem; }
header div { display: grid; min-width: 0; }
header strong,
header span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
header strong { font-size: 1.05rem; }
header span { color: var(--editor-color-muted); font-size: .75rem; }
.pal-brief__favorite { color: #ffca46; }
.pal-brief__friendship { display: grid; gap: .25rem; font-size: .7rem; }
.pal-brief__friendship i { height: .4rem; overflow: hidden; border-radius: 999px; background: var(--editor-color-control); }
.pal-brief__friendship i b { display: block; height: 100%; background: linear-gradient(90deg, #e44f9f, #ff8bc8); }
.pal-brief__metrics { display: grid; margin: 0; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: .35rem; }
.pal-brief__metrics div { display: flex; justify-content: space-between; gap: .35rem; padding: .35rem .45rem; border-radius: .25rem; background: var(--editor-color-control); }
dt { overflow: hidden; color: var(--editor-color-muted); font-size: .66rem; text-overflow: ellipsis; white-space: nowrap; }
dd { margin: 0; font-size: .7rem; font-variant-numeric: tabular-nums; }
h4 { margin: 0 0 .3rem; color: var(--editor-color-muted); font-size: .65rem; }
.pal-brief__chips { display: flex; flex-wrap: wrap; gap: .3rem; }
.pal-brief__chips span { padding: .2rem .4rem; border: 1px solid var(--editor-color-border); border-radius: .25rem; font-size: .68rem; background: var(--editor-color-control); }
.changed { outline: 1px solid var(--editor-color-warning); outline-offset: 1px; }
@media (max-width: 700px) { .pal-brief__metrics { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
</style>
