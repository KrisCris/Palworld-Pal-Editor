<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'

import PalPortrait from '@/components/modules/PalPortrait.vue'
import { formatContainerLabel } from '@/components/modules/pal-container-label'
import UiIcon from '@/components/modules/UiIcon.vue'
import { usePalEditorStore } from '@/stores/paleditor'

const emit = defineEmits(['close'])
const palStore = usePalEditorStore()
const containerLabel = container => formatContainerLabel(container, palStore.getTranslatedText)
const mode = ref('default')
const templateId = ref('')
const templateName = ref('')
const palJson = ref('')
const targetContainerId = ref('')
const dialog = ref(null)
let previousFocus
let appContent
let previousAriaHidden

const selectedTemplate = computed(() => palStore.PAL_TEMPLATES
  .find(template => template.Id === templateId.value))
const targetContainers = computed(() => palStore.PAL_CONTAINERS.filter(container => (
  (palStore.SELECTED_PLAYER_ID === palStore.PAL_GLOBAL_STORAGE_BTN
    ? container.StorageKind === 'global_palbox'
    : palStore.BASE_PAL_BTN_CLK_FLAG
      ? container.ContainerKind === 'base'
      : (container.OwnerPlayerUId === palStore.SELECTED_PLAYER_ID
        && ['party', 'storage'].includes(container.ContainerKind))
        || (container.StorageKind === 'dps'
          && container.StorageOwnerPlayerUid === palStore.SELECTED_PLAYER_ID))
)))
const canCreate = computed(() => Boolean(targetContainerId.value) && (mode.value === 'default'
  || (mode.value === 'template' && selectedTemplate.value)
  || (mode.value === 'json' && palJson.value.trim())))

const tabs = [
  ['default', 'AddPal_Tab_Default'],
  ['template', 'AddPal_Tab_Templates'],
  ['json', 'AddPal_Tab_Json'],
]

const passiveName = skill => palStore.PASSIVE_SKILLS[skill]?.I18n?.[0] || skill
const activeName = skill => palStore.ACTIVE_SKILLS[skill]?.I18n?.[0] || skill
const suitabilityName = suitability => suitability.split('::').pop()
const templateActiveSkills = template => [...new Set([
  ...(template.EquipWaza || []),
  ...(template.MasteredWaza || []),
])]

onMounted(async () => {
  previousFocus = document.activeElement
  appContent = document.querySelector('.app-content')
  previousAriaHidden = appContent?.getAttribute('aria-hidden')
  appContent?.setAttribute('aria-hidden', 'true')
  await palStore.fetchPalTemplates()
  await palStore.fetchPalContainers()
  targetContainerId.value = palStore.BASE_PAL_BTN_CLK_FLAG
    ? targetContainers.value.find(container => container.ContainerKind === 'base')?.StorageKey || ''
    : targetContainers.value.find(
      container => container.ContainerId === palStore.SELECTED_PLAYER_DATA?.PalStorageContainerId
    )?.StorageKey || targetContainers.value[0]?.StorageKey || ''
  await nextTick()
  dialog.value?.focus()
})

onBeforeUnmount(() => {
  if (previousAriaHidden === null) appContent?.removeAttribute('aria-hidden')
  else if (previousAriaHidden !== undefined) appContent?.setAttribute('aria-hidden', previousAriaHidden)
  previousFocus?.focus?.()
})

function trapFocus(event) {
  const controls = [...dialog.value.querySelectorAll(
    'button:not(:disabled), input:not(:disabled), textarea:not(:disabled), [href], [tabindex]:not([tabindex="-1"])'
  )].filter(control => control.offsetParent !== null)
  if (!controls.length) return event.preventDefault()
  const [first] = controls
  const last = controls.at(-1)
  if (event.shiftKey && document.activeElement === first) {
    event.preventDefault()
    last.focus()
  } else if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault()
    first.focus()
  }
}

async function createPal() {
  const options = mode.value === 'template'
    ? { Mode: 'template', TemplateId: templateId.value }
    : mode.value === 'json'
      ? { Mode: 'json', PalJson: palJson.value }
      : { Mode: 'default' }
  options.TargetStorageKey = targetContainerId.value
  if (await palStore.addPal(options)) emit('close')
}

async function saveTemplate() {
  if (await palStore.savePalTemplate(templateName.value)) templateName.value = ''
}

async function deleteTemplate(id) {
  if (await palStore.deletePalTemplate(id) && templateId.value === id) {
    templateId.value = ''
  }
}
</script>

<template>
  <Teleport to="body">
    <div class="add-pal-layer editor-modal-overlay" @pointerdown.self="emit('close')" @keydown.esc="emit('close')">
    <section ref="dialog" class="add-pal-dialog editor-glass-surface" role="dialog" aria-modal="true" aria-labelledby="add-pal-title"
      tabindex="-1" @keydown.esc="emit('close')" @keydown.tab="trapFocus">
      <header>
        <div>
          <p>{{ palStore.getTranslatedText('AddPal_Eyebrow') }}</p>
          <h2 id="add-pal-title">{{ palStore.getTranslatedText('AddPal_Title') }}</h2>
          <small>{{ palStore.getTranslatedText('AddPal_Subtitle') }}</small>
        </div>
        <button class="icon-button" :aria-label="palStore.getTranslatedText('AddPal_Cancel')"
          @click="emit('close')"><UiIcon name="close" /></button>
      </header>

      <div class="add-pal-tabs" role="tablist">
        <button v-for="tab in tabs" :key="tab[0]" role="tab"
          :aria-selected="mode === tab[0]" @click="mode = tab[0]">
          {{ palStore.getTranslatedText(tab[1]) }}
        </button>
      </div>

      <main>
        <section v-if="mode === 'default'" class="default-pal-panel">
          <PalPortrait :src="palStore.backendAssetUrl('/image/pals/SheepBall')" alt="" size="5rem" />
          <div>
            <h3>{{ palStore.getTranslatedText('AddPal_Default_Title') }}</h3>
            <p>{{ palStore.getTranslatedText('AddPal_Default_Description_Target') }}</p>
            <small>SheepBall</small>
          </div>
        </section>

        <section v-else-if="mode === 'template'" class="template-panel">
          <div class="template-save">
            <div>
              <strong>{{ palStore.getTranslatedText('AddPal_Save_Template') }}</strong>
              <small>{{ palStore.getTranslatedText('AddPal_Save_Template_Hint') }}</small>
            </div>
            <input v-model="templateName" maxlength="64"
              :placeholder="palStore.getTranslatedText('AddPal_Template_Name')">
            <button class="secondary-button" :disabled="!templateName.trim() || !palStore.SELECTED_PAL_ID"
              @click="saveTemplate">{{ palStore.getTranslatedText('AddPal_Save') }}</button>
          </div>

          <div v-if="palStore.PAL_TEMPLATES.length" class="template-grid">
            <article v-for="template in palStore.PAL_TEMPLATES" :key="template.Id"
              :class="['template-card', { selected: templateId === template.Id }]">
              <button class="template-select" @click="templateId = template.Id">
                <PalPortrait :src="palStore.backendAssetUrl(`/image/pals/${template.IconAccessKey}`)"
                  alt="" size="3rem" />
                <span>
                  <strong>{{ template.Name }}</strong>
                  <small>{{ template.DisplayName }} · Lv. {{ template.Level }}</small>
                  <small>{{ template.CharacterID }}</small>
                </span>
              </button>
              <button class="template-delete"
                :aria-label="palStore.getTranslatedText('AddPal_Delete_Template', [template.Name])"
                @click="deleteTemplate(template.Id)"><UiIcon name="delete" /></button>
              <div class="template-details">
                <span>{{ palStore.getTranslatedText('Editor_Condenser_Rank') }}{{ template.Rank }}</span>
                <span>{{ palStore.getTranslatedText('Editor_IV_HP') }}{{ template.Talent_HP }}</span>
                <span>{{ palStore.getTranslatedText('Editor_IV_ATK') }}{{ template.Talent_Shot }}</span>
                <span>{{ palStore.getTranslatedText('Editor_IV_DEF') }}{{ template.Talent_Defense }}</span>
                <span v-for="(value, suitability) in template.Suitabilities" :key="suitability"
                  :title="palStore.getTranslatedText('Editor_Suitabilities')">
                  {{ suitabilityName(suitability) }} {{ value }}
                </span>
                <span v-for="skill in template.PassiveSkillList" :key="`passive-${skill}`"
                  :title="palStore.getTranslatedText('Editor_Passive_Skills')">{{ passiveName(skill) }}</span>
                <span v-for="skill in templateActiveSkills(template)" :key="`active-${skill}`"
                  :title="palStore.getTranslatedText('Editor_Mastered_Skills')">{{ activeName(skill) }}</span>
              </div>
            </article>
          </div>
          <p v-else class="empty-state">{{ palStore.getTranslatedText('AddPal_Template_Empty') }}</p>
        </section>

        <section v-else class="json-panel">
          <label for="pal-json">{{ palStore.getTranslatedText('AddPal_Json_Label') }}</label>
          <p>{{ palStore.getTranslatedText('AddPal_Json_Hint') }}</p>
          <textarea id="pal-json" v-model="palJson" rows="13" spellcheck="false"
            :placeholder="palStore.getTranslatedText('AddPal_Json_Placeholder')" />
        </section>
      </main>

      <footer>
        <label class="target-container">
          <span>{{ palStore.getTranslatedText('Editor_Move_Target') }}</span>
          <select v-model="targetContainerId">
            <option v-for="container in targetContainers" :key="container.StorageKey"
              :value="container.StorageKey" :disabled="container.Occupied >= container.Size">
              {{ containerLabel(container) }} ({{ container.Occupied }}/{{ container.Size }})
            </option>
          </select>
        </label>
        <div>
          <button class="secondary-button" @click="emit('close')">
            {{ palStore.getTranslatedText('AddPal_Cancel') }}
          </button>
          <button class="primary-button" :disabled="!canCreate || palStore.LOADING_FLAG" @click="createPal">
            <UiIcon name="plus" /> {{ palStore.getTranslatedText('AddPal_Create') }}
          </button>
        </div>
      </footer>
    </section>
    </div>
  </Teleport>
</template>

<style scoped>
.add-pal-layer {
  position: fixed;
  inset: 0;
  z-index: 1900;
  display: grid;
  place-items: center;
  padding: var(--editor-space-4);
}

.add-pal-dialog {
  display: grid;
  grid-template-rows: auto auto minmax(18rem, 1fr) auto;
  width: min(58rem, calc(100vw - 2rem));
  max-height: min(44rem, calc(100vh - 2rem));
  overflow: hidden;
  border: 1px solid var(--editor-color-glass-border);
  border-radius: var(--editor-radius-lg);
}

header,
footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--editor-space-4);
  padding: var(--editor-space-4) var(--editor-space-5);
}

header p,
header h2,
header small,
.default-pal-panel h3,
.default-pal-panel p,
.json-panel p { margin: 0; }
header p { color: var(--editor-color-primary); font-size: .75rem; text-transform: uppercase; }
header small,
footer,
.template-save small,
.json-panel p { color: var(--editor-color-muted); }

.add-pal-tabs {
  display: flex;
  gap: var(--editor-space-1);
  padding: 0 var(--editor-space-5);
  border-bottom: 1px solid var(--editor-color-border);
}

.add-pal-tabs button {
  padding: var(--editor-space-3) var(--editor-space-4);
  border: 0;
  border-bottom: 2px solid transparent;
  color: var(--editor-color-muted);
  background: transparent;
  cursor: pointer;
}

.add-pal-tabs button[aria-selected="true"] {
  border-color: var(--editor-color-primary);
  color: var(--editor-color-text);
}

main { min-height: 0; overflow: auto; padding: var(--editor-space-5); }
.default-pal-panel { display: flex; align-items: center; gap: var(--editor-space-5); min-height: 15rem; }
.default-pal-panel div { display: grid; gap: var(--editor-space-2); }

.template-panel { display: grid; gap: var(--editor-space-4); }
.template-save { display: grid; grid-template-columns: minmax(12rem, 1fr) minmax(10rem, 1fr) auto; align-items: end; gap: var(--editor-space-3); }
.template-save div { display: grid; }
input,
textarea,
select {
  box-sizing: border-box;
  width: 100%;
  border: 1px solid var(--editor-color-border);
  border-radius: var(--editor-radius-sm);
  color: var(--editor-color-text);
  background: var(--editor-color-control);
}
input { min-height: var(--editor-control-height); padding: 0 var(--editor-space-3); }
select { min-height: var(--editor-control-height); padding: 0 var(--editor-space-3); }
textarea { resize: vertical; padding: var(--editor-space-3); font: .8rem/1.5 ui-monospace, monospace; }

.template-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: var(--editor-space-2); }
.template-card { position: relative; border: 1px solid var(--editor-color-border); border-radius: var(--editor-radius-md); background: var(--editor-color-surface-raised); }
.template-card.selected { border-color: var(--editor-color-primary); box-shadow: inset .2rem 0 var(--editor-color-primary); }
.template-select { display: flex; width: 100%; align-items: center; gap: var(--editor-space-3); padding: var(--editor-space-3) 3rem var(--editor-space-3) var(--editor-space-3); border: 0; color: inherit; background: transparent; text-align: left; cursor: pointer; }
.template-select > span { display: grid; min-width: 0; }
.template-select small { overflow: hidden; color: var(--editor-color-muted); text-overflow: ellipsis; white-space: nowrap; }
.template-delete { position: absolute; top: var(--editor-space-2); right: var(--editor-space-2); }
.template-details { display: none; position: absolute; z-index: 2; right: var(--editor-space-2); left: var(--editor-space-2); top: calc(100% - .2rem); padding: var(--editor-space-3); border: 1px solid var(--editor-color-border); border-radius: var(--editor-radius-sm); background: var(--editor-color-surface); box-shadow: var(--editor-shadow-compact); }
.template-card:hover .template-details,
.template-card:focus-within .template-details { display: flex; flex-wrap: wrap; gap: var(--editor-space-1); }
.template-details span { padding: .15rem .4rem; border-radius: 999px; background: var(--editor-color-control); font-size: .7rem; }
.empty-state { min-height: 10rem; display: grid; place-items: center; color: var(--editor-color-muted); }

.json-panel { display: grid; gap: var(--editor-space-2); }
footer { border-top: 1px solid var(--editor-color-border); }
footer div { display: flex; gap: var(--editor-space-2); }
.target-container { display: grid; min-width: min(24rem, 50vw); gap: var(--editor-space-1); }
button { min-height: 2.25rem; border: 1px solid var(--editor-color-border); border-radius: var(--editor-radius-sm); }
.primary-button,
.secondary-button { padding: 0 var(--editor-space-4); }
.primary-button { color: var(--editor-color-background); background: var(--editor-color-primary); }
.secondary-button,
.icon-button,
.template-delete { color: var(--editor-color-text); background: var(--editor-color-surface-raised); }
.icon-button,
.template-delete { display: grid; width: 2.25rem; place-items: center; padding: 0; }
button:disabled { opacity: .45; cursor: not-allowed; }
button:focus-visible,
input:focus-visible,
textarea:focus-visible { outline: 2px solid var(--editor-color-focus); outline-offset: 2px; }

@media (max-width: 700px) {
  .template-save,
  .template-grid { grid-template-columns: 1fr; }
  footer { align-items: stretch; flex-direction: column; }
  footer div { justify-content: flex-end; }
}
</style>
