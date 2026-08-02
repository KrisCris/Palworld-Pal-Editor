import en from "./en.js";
import fr from "./fr.js";
import ja from "./ja.js";
import zhCN from "./zh-CN.js";

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

export const UI_TRANSLATIONS = Object.freeze({ en, fr, ja, "zh-CN": zhCN });
export const DEFAULT_UI_TRANSLATION = en;
