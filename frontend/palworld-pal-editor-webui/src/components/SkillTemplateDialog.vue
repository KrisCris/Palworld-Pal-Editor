<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref } from 'vue'

import UiIcon from '@/components/modules/UiIcon.vue'
import { useCatalogsStore } from '@/stores/catalogs'
import { usePalEditorStore } from '@/stores/paleditor'
import { useBackendStore } from '@/stores/backend'
import { useTemplatesStore } from '@/stores/templates'

const props = defineProps({
  type: { type: String, required: true, validator: value => ['active', 'passive'].includes(value) },
})
const emit = defineEmits(['close'])
const catalogsStore = useCatalogsStore()
const palStore = usePalEditorStore()
const backend = useBackendStore()
const templatesStore = useTemplatesStore()
const dialog = ref(null)
const templateName = ref('')
const names = reactive({})
const expandedTemplates = reactive(new Set())
let previousFocus

const templates = computed(() => templatesStore.skillTemplates.filter(
  template => template.type === props.type,
))
const titleKey = computed(() => props.type === 'passive'
  ? 'SkillTemplate_Passive_Title'
  : 'SkillTemplate_Active_Title')

const skillCards = template => (template.type === 'passive'
  ? template.PassiveSkillList || []
  : template.EquipWaza || []
).map(skill => {
  const data = template.type === 'passive'
    ? catalogsStore.passiveSkillsByName[skill]
    : catalogsStore.activeSkillsByName[skill]
  return {
    id: skill,
    name: data?.I18n?.[0] || skill,
    summary: template.type === 'passive'
      ? data?.I18n?.[1] || skill
      : `${palStore.getTranslatedText('Editor_Skill_ATK')}${data?.Power ?? '-'} · ${palStore.getTranslatedText('Editor_Skill_CD')}${data?.CT ?? '-'}`,
    tier: template.type === 'passive' ? palStore.passiveTier(data?.Rating) : '',
    element: template.type === 'active' ? palStore.elementIconKey(data?.Element) : '',
  }
})
const summarySkills = template => skillCards(template).slice(0, 4)
const overflowSkills = template => skillCards(template).slice(4)
const isExpanded = template => expandedTemplates.has(template.templateId)

function toggleExpanded(template) {
  if (isExpanded(template)) expandedTemplates.delete(template.templateId)
  else expandedTemplates.add(template.templateId)
}

function syncNames() {
  for (const template of templates.value) names[template.templateId] = template.name
}

onMounted(async () => {
  previousFocus = document.activeElement
  if (!templatesStore.skillTemplates.length) await templatesStore.loadSkillTemplates()
  syncNames()
  await nextTick()
  dialog.value?.focus()
})

onBeforeUnmount(() => previousFocus?.focus?.())

async function saveTemplate() {
  if (await templatesStore.saveSkillTemplate(props.type, templateName.value)) {
    templateName.value = ''
    syncNames()
  }
}

async function renameTemplate(template) {
  const name = names[template.templateId]?.trim()
  if (name && name !== template.name) await templatesStore.renameTemplate(template.templateId, name)
}
</script>

<template>
  <Teleport to="body">
    <div class="skill-template-layer editor-modal-overlay" @pointerdown.self="emit('close')" @keydown.esc="emit('close')">
      <section ref="dialog" class="skill-template-dialog editor-glass-surface" role="dialog" aria-modal="true"
        aria-labelledby="skill-template-title" tabindex="-1">
        <header>
          <div>
            <p>{{ palStore.getTranslatedText('SkillTemplate_Eyebrow') }}</p>
            <h2 id="skill-template-title">{{ palStore.getTranslatedText(titleKey) }}</h2>
            <small>{{ palStore.getTranslatedText('SkillTemplate_Description') }}</small>
          </div>
          <button class="icon-button" :aria-label="palStore.getTranslatedText('Message_Close')" @click="emit('close')">
            <UiIcon name="close" />
          </button>
        </header>

        <div class="template-save">
          <label for="skill-template-name">{{ palStore.getTranslatedText('SkillTemplate_Save_Current') }}</label>
          <input id="skill-template-name" v-model="templateName" maxlength="64"
            :placeholder="palStore.getTranslatedText('SkillTemplate_Name_Placeholder')"
            @keydown.enter="saveTemplate">
          <button class="primary-button" :disabled="!templateName.trim()" @click="saveTemplate">
            <UiIcon name="save" /> {{ palStore.getTranslatedText('SkillTemplate_Save') }}
          </button>
        </div>

        <main>
          <article v-for="template in templates" :key="template.templateId" class="template-card">
            <div class="template-card__name">
              <input v-model="names[template.templateId]" maxlength="64"
                :title="template.name"
                :aria-label="palStore.getTranslatedText('SkillTemplate_Name')"
                @keydown.enter="renameTemplate(template)">
              <button class="icon-button" :title="palStore.getTranslatedText('SkillTemplate_Rename')"
                :aria-label="palStore.getTranslatedText('SkillTemplate_Rename')"
                :disabled="!names[template.templateId]?.trim() || names[template.templateId]?.trim() === template.name"
                @click="renameTemplate(template)"><UiIcon name="edit" /></button>
            </div>

            <div class="template-card__actions">
              <button class="danger-button" @click="templatesStore.removeSkillTemplate(template.templateId)">
                <UiIcon name="delete" /> {{ palStore.getTranslatedText('SkillTemplate_Delete') }}
              </button>
              <button class="primary-button" @click="palStore.applySkillTemplate(template.templateId)">
                <UiIcon name="check" /> {{ palStore.getTranslatedText('SkillTemplate_Apply') }}
              </button>
            </div>

            <div class="template-skills template-skills--summary">
              <div v-for="skill in summarySkills(template)" :key="skill.id" class="template-skill" :title="skill.summary">
                <span v-if="template.type === 'passive'"
                  :class="['passive-tier', `passive-tier--${skill.tier}`]" aria-hidden="true"></span>
                <img v-else-if="skill.element" class="element-icon"
                  :src="backend.backendAssetUrl(`/image/elements/Element_${skill.element}`)" alt="">
                <span class="template-skill__copy">
                  <strong>{{ skill.name }}</strong>
                  <small>{{ skill.summary }}</small>
                </span>
              </div>
            </div>

            <div v-if="overflowSkills(template).length && isExpanded(template)"
              class="template-skills template-skills--overflow">
              <div v-for="skill in overflowSkills(template)" :key="skill.id" class="template-skill" :title="skill.summary">
                <span v-if="template.type === 'passive'"
                  :class="['passive-tier', `passive-tier--${skill.tier}`]" aria-hidden="true"></span>
                <img v-else-if="skill.element" class="element-icon"
                  :src="backend.backendAssetUrl(`/image/elements/Element_${skill.element}`)" alt="">
                <span class="template-skill__copy">
                  <strong>{{ skill.name }}</strong>
                  <small>{{ skill.summary }}</small>
                </span>
              </div>
            </div>

            <button v-if="overflowSkills(template).length" class="template-skills__toggle" type="button"
              :aria-label="palStore.getTranslatedText(isExpanded(template) ? 'SkillTemplate_Collapse' : 'SkillTemplate_Expand')"
              :aria-expanded="isExpanded(template)" @click="toggleExpanded(template)">
              <span>+{{ overflowSkills(template).length }}</span>
              <UiIcon name="forward" :class="{ 'is-expanded': isExpanded(template) }" />
            </button>
          </article>
          <p v-if="!templates.length" class="empty-state">{{ palStore.getTranslatedText('SkillTemplate_Empty') }}</p>
        </main>
      </section>
    </div>
  </Teleport>
</template>

<style scoped>
.skill-template-layer {
  position: fixed;
  inset: 0;
  z-index: 2100;
  display: grid;
  place-items: center;
  padding: var(--editor-space-4);
}

.skill-template-dialog {
  display: grid;
  grid-template-rows: auto auto minmax(12rem, 1fr);
  width: min(50rem, calc(100vw - 2rem));
  max-height: min(40rem, calc(100vh - 2rem));
  overflow: hidden;
  border: 1px solid var(--editor-color-glass-border);
  border-radius: var(--editor-radius-lg);
}

header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--editor-space-4);
  padding: var(--editor-space-4) var(--editor-space-5);
  border-bottom: 1px solid var(--editor-color-border);
}

header p,
header h2,
header small { margin: 0; }
header p { color: var(--editor-color-primary); font-size: .75rem; text-transform: uppercase; }
header small { color: var(--editor-color-muted); }

.template-save {
  display: grid;
  grid-template-columns: auto minmax(10rem, 1fr) auto;
  align-items: center;
  gap: var(--editor-space-3);
  padding: var(--editor-space-4) var(--editor-space-5);
  background: color-mix(in srgb, var(--editor-color-surface-raised) 70%, transparent);
}

main {
  display: grid;
  align-content: start;
  gap: var(--editor-space-3);
  min-height: 0;
  overflow: auto;
  padding: var(--editor-space-4) var(--editor-space-5) var(--editor-space-5);
}

.template-card {
  display: grid;
  grid-template-columns: minmax(13rem, 1fr) auto;
  align-items: center;
  gap: var(--editor-space-3);
  padding: var(--editor-space-3);
  border: 1px solid var(--editor-color-border);
  border-radius: var(--editor-radius-md);
  background: var(--editor-color-surface-raised);
}

.template-card__name,
.template-card__actions { display: flex; align-items: center; gap: var(--editor-space-2); }
.template-card__name input { min-width: 0; }
.template-skills {
  position: relative;
  grid-column: 1 / -1;
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: var(--editor-space-2);
}
.template-skills--overflow {
  padding-top: var(--editor-space-2);
  border-top: 1px solid var(--editor-color-border);
}
.template-skill {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  align-items: center;
  gap: .45rem;
  min-width: 0;
  padding: .55rem .65rem;
  border: 1px solid var(--editor-color-border);
  border-radius: var(--editor-radius-sm);
  background: var(--editor-color-control);
}
.template-skill__copy { display: grid; min-width: 0; gap: .12rem; }
.template-skill strong,
.template-skill small { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.template-skill strong { font-size: .82rem; }
.template-skill small { color: var(--editor-color-muted); font-size: .7rem; }
.template-skills__toggle {
  grid-column: 1 / -1;
  justify-self: end;
  display: inline-flex;
  align-items: center;
  gap: .3rem;
  min-height: 1.8rem;
  padding: 0 .55rem;
  color: var(--editor-color-primary);
  background: var(--editor-color-control);
  font-size: .72rem;
}
.template-skills__toggle :deep(svg) {
  transform: rotate(90deg);
  transition: transform 140ms ease;
}
.template-skills__toggle :deep(svg.is-expanded) {
  transform: rotate(-90deg);
}
.passive-tier { width: .65rem; height: .65rem; border-radius: 50%; background: var(--editor-color-muted); }
.passive-tier--top { background: var(--editor-color-passive-top); }
.passive-tier--high { background: var(--editor-color-passive-high); }
.passive-tier--positive { background: var(--editor-color-passive-positive); }
.passive-tier--negative { background: var(--editor-color-passive-negative); }
.element-icon { width: 1.3rem; height: 1.3rem; object-fit: contain; }

input {
  box-sizing: border-box;
  width: 100%;
  min-height: var(--editor-control-height);
  padding: 0 var(--editor-space-3);
  border: 1px solid var(--editor-color-border);
  border-radius: var(--editor-radius-sm);
  color: var(--editor-color-text);
  background: var(--editor-color-control);
}

button {
  min-height: 2.25rem;
  border: 1px solid var(--editor-color-border);
  border-radius: var(--editor-radius-sm);
  cursor: pointer;
}
.primary-button,
.danger-button { display: inline-flex; align-items: center; gap: .4rem; padding: 0 var(--editor-space-3); }
.primary-button { color: var(--editor-color-background); background: var(--editor-color-primary); }
.danger-button { color: var(--editor-color-danger); background: var(--editor-color-control); }
.icon-button { display: grid; width: 2.25rem; place-items: center; padding: 0; color: var(--editor-color-text); background: var(--editor-color-control); }
button:disabled { opacity: .4; cursor: not-allowed; }
.empty-state { min-height: 10rem; display: grid; place-items: center; color: var(--editor-color-muted); }

@media (max-width: 760px) {
  .template-save,
  .template-card { grid-template-columns: 1fr; }
  .template-card__actions { justify-content: flex-end; }
  .template-skills { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
</style>
