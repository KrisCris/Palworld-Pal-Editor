import en from "./en.js";
import de from "./de.js";
import es from "./es.js";
import esMX from "./es-MX.js";
import fr from "./fr.js";
import id from "./id.js";
import it from "./it.js";
import ja from "./ja.js";
import ko from "./ko.js";
import pl from "./pl.js";
import ptBR from "./pt-BR.js";
import ru from "./ru.js";
import th from "./th.js";
import tr from "./tr.js";
import vi from "./vi.js";
import zhCN from "./zh-CN.js";
import zhTW from "./zh-TW.js";

export const GAME_LANGUAGES = Object.freeze({
    en: "English",
    de: "Deutsch",
    es: "Español",
    "es-MX": "Español (México)",
    fr: "Français",
    id: "Bahasa Indonesia",
    it: "Italiano",
    ja: "日本語",
    ko: "한국어",
    pl: "Polski",
    "pt-BR": "Português (Brasil)",
    ru: "Русский",
    th: "ไทย",
    tr: "Türkçe",
    vi: "Tiếng Việt",
    "zh-CN": "简体中文",
    "zh-TW": "繁體中文",
});

export const UI_TRANSLATIONS = Object.freeze({
    en,
    de,
    es,
    "es-MX": esMX,
    fr,
    id,
    it,
    ja,
    ko,
    pl,
    "pt-BR": ptBR,
    ru,
    th,
    tr,
    vi,
    "zh-CN": zhCN,
    "zh-TW": zhTW,
});
export const DEFAULT_UI_TRANSLATION = UI_TRANSLATIONS.en;

// One interface string, in the locale asked for, with `{{0}}`-style placeholders
// filled from `args`.
//
// A plain function rather than a store method because two stores need it and
// neither owns the other: the app shell answers `getTranslatedText` for the
// components (see AGENTS.md), and `stores/messages` renders queued messages.
// English is the fallback for a key a translation has not caught up with.
export function translate(locale, translationKey, args = []) {
    let translation = UI_TRANSLATIONS[locale]?.[translationKey]
        ?? DEFAULT_UI_TRANSLATION[translationKey];
    if (!translation) {
        console.warn(`Translation key "${translationKey}" not found.`);
        return "I18N_MISSING";
    }
    args.forEach((arg, index) => {
        translation = translation.replace(`{{${index}}}`, arg);
    });
    return translation;
}
