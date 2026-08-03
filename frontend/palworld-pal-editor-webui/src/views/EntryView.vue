<script setup>
import { onMounted } from 'vue'

import PathPicker from '@/components/PathPicker.vue'
import UiIcon from '@/components/modules/UiIcon.vue'
import { usePalEditorStore } from '@/stores/paleditor'

const palStore = usePalEditorStore()

onMounted(palStore.get_updates)
</script>

<template>
  <PathPicker />

  <main id="entryDiv" class="entry-page">
    <section class="entry-shell">
      <header class="entry-intro">
        <h1>{{ palStore.getTranslatedText('Entry_Title') }}</h1>
        <p>{{ palStore.getTranslatedText('Entry_Intro') }}</p>
      </header>

      <section class="entry-load">
        <div class="entry-load-heading">
          <div>
            <h2>{{ palStore.getTranslatedText('Entry_Load_Title') }}</h2>
            <p>{{ palStore.getTranslatedText('Entry_Load_Subtitle') }}</p>
          </div>
        </div>

        <label for="entry-save-path">{{ palStore.getTranslatedText('Entry_Path_Label') }}</label>
        <div class="entry-path-row">
          <input
            id="entry-save-path"
            v-model="palStore.PAL_GAME_SAVE_PATH"
            type="text"
            placeholder="C:\Users\[Username]\AppData\Local\Pal\Saved\SaveGames\[SteamID]\[SaveID]"
            :disabled="palStore.LOADING_FLAG"
          >
          <button class="entry-path-button" type="button" :disabled="palStore.LOADING_FLAG" @click="palStore.show_file_picker">
            <UiIcon name="folder" />
            {{ palStore.getTranslatedText('EntryView_BTN_Path_Picker') }}
          </button>
          <button class="entry-load-button" type="button" :disabled="palStore.LOADING_FLAG" @click="palStore.loadSave">
            <UiIcon name="play" />
            {{ palStore.getTranslatedText('EntryView_BTN_Load') }}
          </button>
        </div>
      </section>

      <div class="entry-columns">
        <div class="entry-group entry-left">
          <section class="entry-support">
            <div class="entry-section-heading">
              <div>
                <h2>{{ palStore.getTranslatedText('Entry_Support_Title') }}</h2>
                <p>{{ palStore.getTranslatedText('Entry_Support_Subtitle') }}</p>
              </div>
            </div>

            <div class="entry-action-grid">
              <a class="entry-action" target="_blank" href="https://discord.gg/FnuA95nMJ8">
                <UiIcon name="message" />
                <span>
                  <strong>{{ palStore.getTranslatedText('Entry_Support_Community_Title') }}</strong>
                  <small>{{ palStore.getTranslatedText('Entry_Support_Community_Description') }}</small>
                </span>
              </a>
              <a class="entry-action" target="_blank" href="https://github.com/KrisCris/Palworld-Pal-Editor">
                <UiIcon name="pull-request" />
                <span>
                  <strong>{{ palStore.getTranslatedText('Entry_Support_Code_Title') }}</strong>
                  <small>{{ palStore.getTranslatedText('Entry_Support_Code_Description') }}</small>
                </span>
              </a>
              <a class="entry-action" target="_blank" href="https://github.com/KrisCris/Palworld-Pal-Editor/issues">
                <UiIcon name="bug" />
                <span>
                  <strong>{{ palStore.getTranslatedText('Entry_Support_Issue_Title') }}</strong>
                  <small>{{ palStore.getTranslatedText('Entry_Support_Issue_Description') }}</small>
                </span>
              </a>
              <button
                class="entry-action entry-action--support"
                type="button"
                @click="palStore.SHOW_DONATE_FLAG = true"
              >
                <UiIcon name="heart" />
                <span>
                  <strong>{{ palStore.getTranslatedText('Entry_Support_Author_Title') }}</strong>
                  <small>{{ palStore.getTranslatedText('Entry_Support_Author_Description') }}</small>
                </span>
              </button>
            </div>
          </section>

          <section class="entry-downloads">
            <div class="entry-section-heading">
              <h2>{{ palStore.getTranslatedText('Entry_Downloads_Title') }}</h2>
              <span>{{ palStore.getTranslatedText('Entry_Downloads_Subtitle') }}</span>
            </div>
            <div class="entry-download-grid">
              <a target="_blank" href="https://github.com/KrisCris/Palworld-Pal-Editor/releases">
                <UiIcon name="branch" />
                <span><strong>GitHub Releases</strong><small>{{ palStore.getTranslatedText('Entry_Download_GitHub_Description') }}</small></span>
              </a>
              <a target="_blank" href="https://www.nexusmods.com/palworld/mods/995?tab=files">
                <UiIcon name="download" />
                <span><strong>Nexus Mods</strong><small>{{ palStore.getTranslatedText('Entry_Download_Nexus_Description') }}</small></span>
              </a>
              <a v-if="['zh-CN', 'zh-TW'].includes(palStore.I18n)" target="_blank" href="https://space.bilibili.com/12184831">
                <UiIcon name="video" />
                <span><strong>_connlost Bilibili</strong><small>{{ palStore.getTranslatedText('Entry_Download_Bilibili_Description') }}</small></span>
              </a>
            </div>

            <aside v-if="palStore.IS_OFFICIAL_BUILD && palStore.UPDATE_DATA.version" class="entry-update" role="status">
              <strong>{{ palStore.getTranslatedText('EntryView_Update_Notice', [palStore.UPDATE_DATA.version]) }}</strong>
              <span>
                <a target="_blank" :href="palStore.UPDATE_DATA.download_nexus">Nexus Mods</a>
                <a target="_blank" :href="palStore.UPDATE_DATA.download_gh">GitHub</a>
              </span>
            </aside>
          </section>
        </div>

        <div class="entry-group entry-right">
          <section class="entry-instructions">
            <div class="entry-section-heading">
              <h2>{{ palStore.getTranslatedText('Entry_Instructions_Title') }}</h2>
              <span>{{ palStore.getTranslatedText('Entry_Instructions_Subtitle') }}</span>
            </div>
            <div class="entry-note-grid">
              <article>
                <UiIcon name="folder-check" />
                <strong>{{ palStore.getTranslatedText('Entry_Instruction_First_Title') }}</strong>
                <p>{{ palStore.getTranslatedText('Entry_Instruction_First_Description') }}</p>
              </article>
              <article>
                <UiIcon name="shield" />
                <strong>{{ palStore.getTranslatedText('Entry_Instruction_WebUI_Title') }}</strong>
                <p>{{ palStore.getTranslatedText('Entry_Instruction_WebUI_Description') }}</p>
              </article>
              <article>
                <UiIcon name="box" />
                <strong>{{ palStore.getTranslatedText('Entry_Instruction_Docker_Title') }}</strong>
                <p>{{ palStore.getTranslatedText('Entry_Instruction_Docker_Description') }}</p>
              </article>
            </div>
            <p class="entry-help"><UiIcon name="help" /> {{ palStore.getTranslatedText('Entry_Help') }}</p>
          </section>
        </div>
      </div>

    </section>

    <footer class="entry-footer">
      <span>VERSION: {{ palStore.VERSION }}</span>
      <span v-if="!palStore.IS_OFFICIAL_BUILD" class="entry-warning">
        <UiIcon name="warning" />
        {{ palStore.getTranslatedText('EntryView_Version_Warning') }}
      </span>
    </footer>
  </main>
</template>

<style scoped>
.entry-page {
  display: grid;
  grid-template-rows: 1fr auto;
  min-height: 0;
  overflow: auto;
  align-content: center;
  padding: clamp(1.25rem, 2.4vw, 2.25rem);
}

.entry-shell {
  display: grid;
  width: 100%;
  max-width: min(92rem, 1920px);
  align-self: center;
  gap: var(--editor-space-4);
  margin-inline: auto;
}

.entry-intro {
  min-width: 0;
}

.entry-intro h1 {
  font-size: clamp(1.65rem, 3vw, 2.55rem);
  font-weight: 650;
  letter-spacing: -.035em;
  line-height: 1.08;
}

.entry-intro p,
.entry-section-heading p,
.entry-load-heading p,
.entry-section-heading > span,
.entry-action small,
.entry-download-grid small,
.entry-note-grid p {
  color: var(--editor-color-muted);
}

.entry-columns {
  display: grid;
  grid-template-columns: minmax(22rem, 42%) minmax(0, 58%);
  gap: var(--editor-space-4);
  align-items: stretch;
}

.entry-group {
  display: grid;
  align-content: start;
  gap: var(--editor-space-4);
  padding: var(--editor-space-4);
  border: 1px solid var(--editor-color-glass-border);
  border-radius: var(--editor-radius-md);
  background: color-mix(in srgb, var(--editor-color-glass-surface) 86%, transparent);
  box-shadow: inset 0 1px 0 color-mix(in srgb, white 12%, transparent);
}

.entry-load {
  grid-template-columns: minmax(15rem, .75fr) minmax(0, 1.75fr);
  align-items: end;
  padding: var(--editor-space-4);
  border: 1px solid var(--editor-color-focus);
  border-left: .3rem solid var(--editor-color-focus);
  border-radius: var(--editor-radius-md);
  background: color-mix(in srgb, var(--editor-color-glass-surface) 90%, var(--editor-color-focus) 10%);
  box-shadow: inset 0 1px 0 color-mix(in srgb, white 14%, transparent);
}

.entry-support,
.entry-downloads,
.entry-load,
.entry-instructions {
  display: grid;
  align-content: start;
  gap: var(--editor-space-3);
}

.entry-downloads,
.entry-instructions {
  padding-top: var(--editor-space-4);
  border-top: 1px solid var(--editor-color-border);
}

.entry-section-heading,
.entry-load-heading,
.entry-footer {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--editor-space-3);
}

.entry-load-heading {
  grid-row: 1 / 3;
  align-self: center;
}

.entry-section-heading h2,
.entry-load-heading h2 {
  font-size: 1.15rem;
  font-weight: 650;
}

.entry-action-grid,
.entry-download-grid,
.entry-note-grid {
  display: grid;
  gap: var(--editor-space-2);
}

.entry-action-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.entry-download-grid,
.entry-note-grid {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.entry-action,
.entry-download-grid a {
  display: grid;
  min-width: 0;
  grid-template-columns: auto minmax(0, 1fr);
  gap: var(--editor-space-2);
  align-items: center;
  padding: var(--editor-space-3);
  border: 1px solid var(--editor-color-border);
  border-radius: var(--editor-radius-sm);
  color: var(--editor-color-text);
  background: var(--editor-color-control);
  text-decoration: none;
}

button.entry-action {
  width: 100%;
  font: inherit;
  text-align: left;
  cursor: pointer;
}

.entry-action:hover,
.entry-download-grid a:hover {
  border-color: var(--editor-color-focus);
  background: var(--editor-color-surface-raised);
}

.entry-action .ui-icon,
.entry-download-grid .ui-icon {
  color: var(--editor-color-focus);
}

.entry-action strong,
.entry-action small,
.entry-download-grid strong,
.entry-download-grid small {
  display: block;
}

.entry-action--support {
  border-color: color-mix(in srgb, var(--editor-color-danger) 68%, var(--editor-color-border));
  background: color-mix(in srgb, var(--editor-color-danger) 16%, var(--editor-color-control));
}

.entry-action--support .ui-icon {
  color: var(--editor-color-danger);
}

.entry-update {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--editor-space-3);
  padding: var(--editor-space-3);
  border: 1px solid var(--editor-color-focus);
  border-radius: var(--editor-radius-sm);
  background: color-mix(in srgb, var(--editor-color-focus) 12%, transparent);
}

.entry-update span {
  display: flex;
  gap: var(--editor-space-2);
}

.entry-update a {
  color: var(--editor-color-focus);
}

.entry-load label {
  grid-column: 2;
  color: var(--editor-color-muted);
}

.entry-path-row {
  display: grid;
  grid-column: 2;
  grid-template-columns: minmax(8rem, 1fr) auto auto;
  gap: var(--editor-space-2);
}

.entry-path-row input,
.entry-path-row button {
  min-height: 2.65rem;
  border: 1px solid var(--editor-color-border);
  border-radius: var(--editor-radius-sm);
  color: var(--editor-color-text);
  background: var(--editor-color-control);
}

.entry-path-row input {
  min-width: 0;
  padding: 0 var(--editor-space-3);
}

.entry-path-row button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: .4rem;
  padding: 0 var(--editor-space-3);
  cursor: pointer;
}

.entry-path-row .entry-load-button {
  border-color: var(--editor-color-focus);
  color: var(--editor-color-background);
  background: var(--editor-color-focus);
}

.entry-path-row button:hover {
  background: var(--editor-color-surface-raised);
}

.entry-path-row .entry-load-button:hover {
  background: color-mix(in srgb, var(--editor-color-focus) 82%, white);
}

.entry-path-row :disabled {
  color: var(--editor-color-muted);
  background: var(--editor-color-surface-subtle);
  cursor: not-allowed;
}

.entry-path-row :focus-visible,
.entry-action:focus-visible,
.entry-download-grid a:focus-visible {
  outline: 2px solid var(--editor-color-focus);
  outline-offset: 2px;
}

.entry-note-grid article {
  display: grid;
  align-content: start;
  gap: var(--editor-space-2);
  min-width: 0;
  padding: var(--editor-space-3);
  border: 1px solid var(--editor-color-border);
  border-radius: var(--editor-radius-sm);
  background: color-mix(in srgb, var(--editor-color-background) 45%, transparent);
}

.entry-note-grid .ui-icon {
  color: var(--editor-color-ancient);
}

.entry-help {
  display: flex;
  align-items: center;
  gap: var(--editor-space-2);
  padding-top: var(--editor-space-3);
  border-top: 1px solid var(--editor-color-border);
  color: var(--editor-color-muted);
}

.entry-help .ui-icon {
  color: var(--editor-color-focus);
}

.entry-footer {
  width: 100%;
  margin-top: var(--editor-space-4);
  color: var(--editor-color-muted);
  font-size: .82rem;
}

.entry-warning {
  display: inline-flex;
  align-items: center;
  gap: .35rem;
  color: var(--editor-color-danger);
}

@media (max-width: 900px) {
  .entry-page {
    grid-template-rows: auto auto;
    align-content: start;
  }

  .entry-columns {
    grid-template-columns: 1fr;
  }

  .entry-left,
  .entry-right {
    display: contents;
  }

  .entry-load,
  .entry-instructions,
  .entry-support,
  .entry-downloads {
    padding: var(--editor-space-4);
    border: 1px solid var(--editor-color-glass-border);
    border-radius: var(--editor-radius-md);
    background: color-mix(in srgb, var(--editor-color-glass-surface) 86%, transparent);
    box-shadow: inset 0 1px 0 color-mix(in srgb, white 12%, transparent);
  }

  .entry-load {
    grid-template-columns: 1fr;
    border-color: var(--editor-color-focus);
    border-left-width: .3rem;
  }

  .entry-load-heading,
  .entry-load label,
  .entry-path-row {
    grid-column: auto;
    grid-row: auto;
  }

  .entry-instructions { order: 2; }
  .entry-support { order: 3; }
  .entry-downloads { order: 4; }
}

@media (max-width: 680px) {
  .entry-page {
    padding: 1rem;
  }

  .entry-action-grid,
  .entry-download-grid,
  .entry-note-grid {
    grid-template-columns: 1fr;
  }

  .entry-path-row {
    grid-template-columns: 1fr 1fr;
  }

  .entry-path-row input {
    grid-column: 1 / -1;
  }

  .entry-section-heading,
  .entry-footer {
    align-items: flex-start;
    flex-direction: column;
  }
}

@media (max-width: 440px) {
  .entry-path-row {
    grid-template-columns: 1fr;
  }

  .entry-path-row input {
    grid-column: auto;
  }
}
</style>
