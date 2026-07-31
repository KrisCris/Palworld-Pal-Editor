import { ref, computed, reactive, nextTick } from "vue";
import { defineStore } from "pinia";
import axios from "axios";
import {
    DEFAULT_UI_TRANSLATION,
    GAME_LANGUAGES,
    UI_TRANSLATIONS,
} from "../i18n/index.js";

export const backendErrorDetails = error => {
    const status = error?.response?.status;
    if (status >= 500) {
        const payload = error.response.data;
        const details = payload?.data?.error;
        return {
            kind: "application",
            message: payload?.msg || `${error.response.statusText || "HTTP"}: ${status}`,
            code: details?.code || `HTTP ${status}`,
            log: details?.log,
        };
    }
    if (!error?.response && error?.request) {
        return { kind: "connection", message: error.message || "Network Error" };
    }
    return null;
};

export function skillBadges(skill = {}) {
    return [
        skill.NonInheritable && "nonInheritable",
        skill.Exclusive && "exclusive",
        skill.BossSkill && "boss",
        (skill.HasSkillFruit || skill.SkillFruit) && "fruit",
        (skill.Disabled || skill.Assignable === false) && "disabled",
    ].filter(Boolean);
}

export function filterSkillOptions(skills, currentIds, hideInvalid) {
    const rows = Array.isArray(skills) ? skills : [];
    if (!hideInvalid) return rows.slice();

    const retainedIds = new Set(currentIds ?? []);
    return rows.filter(
        skill => (
            (!skill?.Invalid && skill?.Assignable !== false)
            || retainedIds.has(skill?.InternalName)
        ),
    );
}

export const canToggleBossVariant = pal => Boolean(
    pal?.HasBaseVariant && pal?.HasBossVariant,
);

export function filterPalSkins(skins, selectedPal, hideInvalid = false) {
    const target = selectedPal?.FamilyID
        || selectedPal?.DataAccessKeyOG
        || selectedPal?.CharacterID;
    return (skins ?? []).filter(skin =>
        skin?.TargetPalName === target
        && (!hideInvalid
            || !skin.Invalid
            || skin.SkinName === selectedPal?.SkinName)
    );
}

const SKILL_BADGE_ICONS = Object.freeze({
    nonInheritable: "✨",
    exclusive: "🔒",
    boss: "👑",
    fruit: "🍐",
    disabled: "⚠️",
});

const SKILL_BADGE_TRANSLATION_KEYS = Object.freeze({
    nonInheritable: "Editor_Skill_Badge_NonInheritable",
    exclusive: "Editor_Skill_Badge_Exclusive",
    boss: "Editor_Skill_Badge_Boss",
    fruit: "Editor_Skill_Badge_Fruit",
    disabled: "Editor_Skill_Badge_Disabled",
});

export const usePalEditorStore = defineStore("paleditor", () => {
    const MAX_LEVEL = 80;
    const MAX_FRIENDSHIP_LEVEL = 10;
    const MAX_INVALID_LEVEL = 100;
    const MAX_SOULS_LEVEL = 20;
    const MAX_SUITABILITY_LEVEL = 10;
    class Player {
        constructor(obj) {
            this.InstanceId = obj.InstanceId;
            this.NickName = obj.NickName;
            this.Level = obj.Level;
            this.Exp = obj.Exp;
            this.UnusedStatusPoint = obj.UnusedStatusPoint;
            this.StatusPoints = obj.StatusPoints || {};
            this.StatusPointMaximums = obj.StatusPointMaximums || {};
            this.HasViewingCage = obj.HasViewingCage;
            this.OtomoCharacterContainerId = obj.OtomoCharacterContainerId;
            this.PalStorageContainerId = obj.PalStorageContainerId;
            this.pals = new Map();
            this.UnlockedRecipeTechnologyNames = obj.UnlockedRecipeTechnologyNames;
            this.TechnologyPoint = obj.TechnologyPoint;
            this.bossTechnologyPoint = obj.bossTechnologyPoint;
        }

        setStatusPoint(name) {
            let points = Number(this.StatusPoints[name]);
            if (!Number.isFinite(points)) points = 0;
            const maximum = this.StatusPointMaximums[name] ?? 0;
            points = Math.min(Math.max(Math.trunc(points), 0), maximum);
            this.StatusPoints[name] = points;
            updatePlayer({
                target: {
                    name: "set_StatusPoint",
                    value: { name: name, points: points },
                },
            });
        }

        levelDown() {
            if (this.Level > 1) {
                this.Level -= 1;
                updatePlayer({ target: { name: "Level", value: this.Level } });
            }
        }

        levelUp() {
            if (
                this.Level < MAX_LEVEL ||
                (!HIDE_INVALID_OPTIONS.value && this.Level < MAX_INVALID_LEVEL)
            ) {
                this.Level += 1;
                updatePlayer({ target: { name: "Level", value: this.Level } });
            }
        }

        maxLevel() {
            this.Level = HIDE_INVALID_OPTIONS.value
                ? MAX_LEVEL
                : MAX_INVALID_LEVEL;
            updatePlayer({ target: { name: "Level", value: this.Level } });
        }

        toggleTech(tech, status) {
            updatePlayer({
                target: {
                    name: "toggle_UnlockedRecipeTechnologyNames",
                    value: {
                        tech: tech,
                        status: status,
                    },
                },
            });
        }
    }

    class PalData {
        constructor(obj) {
            this.InstanceId = obj.InstanceId;
            this.OwnerPlayerUId = obj.OwnerPlayerUId;
            this.group_id = obj.group_id;
            this.ContainerId = obj.ContainerId;
            this.SlotIndex = obj.SlotIndex;
            this.OwnerName = obj.OwnerName;
            this.CharacterID = obj.CharacterID;
            this.FamilyID = obj.FamilyID;
            this.IconAccessKey = obj.IconAccessKey;
            this.DataAccessKey = obj.DataAccessKey;
            this.DataAccessKeyOG = obj.DataAccessKey;
            this.SelectionKey = PAL_STATIC_DATA.value[obj.CharacterID]
                ? obj.CharacterID
                : obj.DataAccessKey;
            this.I18nName = obj.I18nName;
            this.DisplayName = obj.DisplayName;
            this.NickName = obj.NickName;
            this.SkinName = obj.SkinName;
            this.Gender = obj.Gender;
            this.Level = obj.Level;
            this.FriendshipLevel = obj.FriendshipLevel;

            this.HasBaseVariant = obj.HasBaseVariant;
            this.HasBossVariant = obj.HasBossVariant;
            this.HasTowerVariant = obj.HasTowerVariant;
            this.HasWorkerSick = obj.HasWorkerSick;
            this.IsFaintedPal = obj.IsFaintedPal;
            this.Is_Unref_Pal = obj.Is_Unref_Pal;
            this.in_owner_palbox = obj.in_owner_palbox;

            this.IsHuman = obj.IsHuman;
            this.IsBOSS = obj.IsBOSS;
            this.IsRarePal = obj.IsRarePal;
            this.IsTower = obj.IsTower;
            this.IsRAID = obj.IsRAID;
            this.IsPREDATOR = obj.IsPREDATOR;
            this.IsOilrig = obj.IsOilrig;
            this.IsExpeditionPal = obj.IsExpeditionPal;

            this.ComputedMaxHP = obj.ComputedMaxHP;
            this.ComputedAttack = obj.ComputedAttack;
            this.ComputedDefense = obj.ComputedDefense;
            this.ComputedCraftSpeed = obj.ComputedCraftSpeed;

            this.Rank = obj.Rank;
            this.IsAwakening = obj.IsAwakening;
            this.Rank_HP = obj.Rank_HP;
            this.Rank_Attack = obj.Rank_Attack;
            this.Rank_Defence = obj.Rank_Defence;
            this.Rank_CraftSpeed = obj.Rank_CraftSpeed;

            this.Talent_HP = obj.Talent_HP;
            this.Talent_Melee = obj.Talent_Melee;
            this.Talent_Shot = obj.Talent_Shot;
            this.Talent_Defense = obj.Talent_Defense;

            this.PassiveSkillList = obj.PassiveSkillList;
            this.EquipWaza = obj.EquipWaza;
            this.MasteredWaza = obj.MasteredWaza;
            this.Suitabilities = obj.Suitabilities;
            this.SuitabilityMinimums = obj.SuitabilityMinimums;
        }

        displaySpecialType() {
            if (this.IsTower) return "🗼";
            if (this.IsBOSS) return "👑";
            if (this.IsRarePal) return "✨";
            if (this.IsRAID) return "RAID";
            if (this.IsPREDATOR) return "Rampaging";
            if (this.IsOilrig) return "Oilrig";
            return "N/A";
        }

        getRank() {
            return this.Rank - 1;
        }

        swapRare() {
            this.IsRarePal = !this.IsRarePal;
            updatePal({ target: { name: "IsRarePal", value: this.IsRarePal } });
        }

        swapBoss() {
            this.IsBOSS = !this.IsBOSS;
            updatePal({ target: { name: "IsBOSS", value: this.IsBOSS } });
        }

        toggleAwakening() {
            this.IsAwakening = !this.IsAwakening;
            updatePal({ target: { name: "IsAwakening", value: this.IsAwakening } });
        }

        levelDown() {
            if (this.Level > 1) {
                this.Level -= 1;
                updatePal({ target: { name: "Level", value: this.Level } });
            }
        }

        levelUp() {
            if (
                this.Level < MAX_LEVEL ||
                (!HIDE_INVALID_OPTIONS.value && this.Level < MAX_INVALID_LEVEL)
            ) {
                this.Level += 1;
                updatePal({ target: { name: "Level", value: this.Level } });
            }
        }

        maxLevel() {
            this.Level = HIDE_INVALID_OPTIONS.value
                ? MAX_LEVEL
                : MAX_INVALID_LEVEL;
            updatePal({ target: { name: "Level", value: this.Level } });
        }

        friendshipLevelDown() {
            if (this.FriendshipLevel > -3) {
                this.FriendshipLevel -= 1;
                updatePal({ target: { name: "FriendshipLevel", value: this.FriendshipLevel } });
            }
        }

        friendshipLevelUp() {
            if (this.FriendshipLevel < MAX_FRIENDSHIP_LEVEL) {
                this.FriendshipLevel += 1;
                updatePal({ target: { name: "FriendshipLevel", value: this.FriendshipLevel } });
            }
        }

        maxFriendshipLevel() {
            this.FriendshipLevel = MAX_FRIENDSHIP_LEVEL;
            updatePal({ target: { name: "FriendshipLevel", value: this.FriendshipLevel } });
        }

        displayGender() {
            if (this.Gender == "EPalGenderType::Female") {
                return "♀️";
            } else if (this.Gender == "EPalGenderType::Male") {
                return "♂️";
            } else {
                return "";
            }
        }

        swapGender() {
            let gender = HIDE_INVALID_OPTIONS.value ? "NONE" : "EPalGenderType::Female";
            if (this.Gender == "EPalGenderType::Female") {
                gender = "EPalGenderType::Male";
            }
            if (this.Gender == "EPalGenderType::Male") {
                gender = "EPalGenderType::Female";
            }
            updatePal({ target: { name: "Gender", value: gender } });
        }

        pop_PassiveSkillList(e) {
            const skill = e.target.name;
            updatePal({
                target: {
                    name: "pop_PassiveSkillList",
                    value: skill,
                },
            });
        }

        add_PassiveSkillList() {
            const skill = PAL_PASSIVE_SELECTED_ITEM.value;
            if (!PASSIVE_SKILLS.value[skill]) {
                showToast("Message_Select_Skill");
                return;
            }
            if (
                HIDE_INVALID_OPTIONS.value &&
                this.PassiveSkillList.length >= 4
            ) {
                showToast("Message_Passive_Limit");
                return;
            }
            updatePal({
                target: {
                    name: "add_PassiveSkillList",
                    value: skill,
                },
            });
        }

        isEquippedPassiveSkill(skill) {
            return this.PassiveSkillList.includes(skill);
        }

        isEquippedSkill(skill) {
            return this.EquipWaza.includes(skill);
        }

        isMasteredSkill(skill) {
            return this.MasteredWaza.includes(skill);
        }

        isEquipSkillFull() {
            return this.EquipWaza.length >= 3;
        }

        pop_EquipWaza(e) {
            const skill = e.target.name;
            updatePal({
                target: {
                    name: "pop_EquipWaza",
                    value: skill,
                },
            });
        }

        add_EquipWaza(e) {
            const skill = e.target.name;
            updatePal({
                target: {
                    name: "add_EquipWaza",
                    value: skill,
                },
            });
        }

        pop_MasteredWaza(e) {
            const skill = e.target.name;
            updatePal({
                target: {
                    name: "pop_MasteredWaza",
                    value: skill,
                },
            });
        }

        add_MasteredWaza() {
            const skill = PAL_ACTIVE_SELECTED_ITEM.value;
            if (!ACTIVE_SKILLS.value[skill]) {
                showToast("Message_Select_Skill");
                return;
            }
            updatePal({
                target: {
                    name: "add_MasteredWaza",
                    value: skill,
                },
            });
        }

        suitUp(e) {
            try {
                const name = e.target.name;
                const value = SELECTED_PAL_DATA.value.Suitabilities[name] + 1;
                this.set_Suitability(name, value);
            } catch (error) {
                console.log(error);
                return;
            }
        }

        suitDown(e) {
            try {
                const name = e.target.name;
                const value = SELECTED_PAL_DATA.value.Suitabilities[name] - 1;
                this.set_Suitability(name, value);
            } catch (error) {
                console.log(error);
                return;
            }
        }

        set_Suitability(name, value) {
            const min = this.SuitabilityMinimums[name] || 0;
            const max = MAX_SUITABILITY_LEVEL;
            if (HIDE_INVALID_OPTIONS.value && min == 0 && value != 0) {
                showToast("Message_Invalid_Suitability");
                return;
            }
            value = Math.min(Math.max(value, min), max);
            if (value == SELECTED_PAL_DATA.value.Suitabilities[name]) {
                return;
            }
            updatePal({
                target: {
                    name: "set_Suitability",
                    value: { name: name, level: value },
                },
            });
        }

        changeSpecie(characterId = this.SelectionKey) {
            updatePal({
                target: {
                    name: "CharacterID",
                    value: characterId,
                },
            });
        }
    }

    const PAL_BASE_WORKER_BTN = ref("PAL_BASE_WORKER_BTN");

    const TECH_LV_DICT = ref({});
    const PASSIVE_SKILLS = ref({});
    const PASSIVE_SKILLS_LIST = ref([]);
    const ACTIVE_SKILLS = ref({});
    const ACTIVE_SKILLS_LIST = ref([]);
    const PAL_STATIC_DATA = ref({});
    const PAL_STATIC_DATA_LIST = ref([]);
    const SKIN_DATA_LIST = ref([]);
    const I18nList = ref(GAME_LANGUAGES);

    // flags
    const SHOW_DONATE_FLAG = ref(false);
    const LOADING_FLAG = ref(false);
    const SAVE_LOADED_FLAG = ref(false);
    const HAS_WORKING_PAL_FLAG = ref(false);
    const BASE_PAL_BTN_CLK_FLAG = ref(false);
    const SHOW_PLAYER_EDIT_FLAG = ref(false);
    // const ADD_PAL_RESELECT_CTR = ref(0);
    // const DEL_PAL_RESELECT_CTR = ref(0)
    const UPDATE_PAL_RESELECT_CTR = ref(0);
    const SHOW_UNREF_PAL_FLAG = ref(false);
    const SHOW_OOB_PAL_FLAG = ref(true);
    const HIDE_INVALID_OPTIONS = ref(true);

    const PAL_LIST_SEARCH_KEYWORD = ref("");

    const IS_PAL_SAVE_PATH = ref(false);

    // data
    const BASE_PAL_MAP = ref(new Map());
    const PLAYER_MAP = ref(new Map());
    const PAL_PASSIVE_SELECTED_ITEM = ref("");
    const PAL_ACTIVE_SELECTED_ITEM = ref("");

    // display data
    const SELECTED_PAL_DATA = ref(new Map());
    const SELECTED_PLAYER_DATA = ref(new Map());
    const PAL_MAP = ref(new Map());

    // selected id
    const SELECTED_PLAYER_ID = ref(null);
    const SELECTED_PAL_ID = ref(null);

    // TODO Get rid of this...
    // let SELECTED_PAL_EL = null;

    // Configs
    const VERSION = ref("0.0.0");
    const UPDATE_DATA = ref({});
    const IS_OFFICIAL_BUILD = ref(false);
    const savedI18n = localStorage.getItem("PAL_I18n");
    const I18n = ref(GAME_LANGUAGES[savedI18n] ? savedI18n : "en");
    const PAL_GAME_SAVE_PATH = ref(localStorage.getItem("PAL_GAME_SAVE_PATH"));
    const HAS_PASSWORD = ref(false);
    const PAL_WRITE_BACK_PATH = ref("");
    const PATH_CONTEXT = ref(new Map());

    const SHOW_FILE_PICKER = ref(false);
    const PAL_FILE_PICKER_PATH = ref(PAL_GAME_SAVE_PATH.value);

    const CN_WARNING_ON_LOAD = ref(true);

    // auth
    let auth_token = localStorage.getItem("PAL_AUTH_TOKEN") || "";
    let configuredSavePath = "";
    const APP_STATE = ref("connecting");
    const IS_LOCKED = ref(true);
    const BACKEND_ERROR = ref(null);
    const AUTH_MESSAGE_KEY = ref("");
    const MESSAGE_QUEUE = ref([]);
    const CURRENT_MESSAGE = computed(() => MESSAGE_QUEUE.value[0] ?? null);
    let nextMessageId = 1;

    function showMessage(message) {
        const entry = { id: nextMessageId++, args: [], ...message };
        if (entry.presentation == "dialog") {
            const firstToast = MESSAGE_QUEUE.value.findIndex(
                item => item.presentation == "toast"
            );
            MESSAGE_QUEUE.value.splice(
                firstToast < 0 ? MESSAGE_QUEUE.value.length : firstToast,
                0,
                entry
            );
        } else {
            MESSAGE_QUEUE.value.push(entry);
        }
        return entry.id;
    }

    function showToast(messageKey, severity = "warning", args = []) {
        return showMessage({ severity, presentation: "toast", messageKey, args });
    }

    function dismissMessage(id) {
        const index = MESSAGE_QUEUE.value.findIndex(message => message.id == id);
        if (index >= 0) MESSAGE_QUEUE.value.splice(index, 1);
    }

    function getMessageText(message) {
        if (message?.message) return message.message;
        const args = (message?.args || []).map(arg =>
            arg?.translationKey ? getTranslatedText(arg.translationKey) : arg
        );
        return getTranslatedText(message?.messageKey, args);
    }

    function reportOperationError(operationKey, response) {
        return showMessage({
            severity: "error",
            presentation: "dialog",
            messageKey: "Message_Operation_Failed",
            args: [{ translationKey: operationKey }],
            code: response?.data?.error?.code || operationKey,
            log: response?.data?.error?.log || response?.msg,
        });
    }

    function reportFrontendError(error, context = "Frontend") {
        const exception = error instanceof Error ? error : new Error(String(error));
        console.error(context, exception);
        return showMessage({
            severity: "error",
            presentation: "dialog",
            messageKey: "Message_Unexpected_Frontend_Error",
            args: [context],
            code: exception.name,
            log: exception.stack || exception.message,
        });
    }

    function setBackendError(error) {
        BACKEND_ERROR.value = typeof error === "string"
            ? { kind: "application", message: error }
            : error;
        if (APP_STATE.value === "connecting") APP_STATE.value = "backend-error";
        LOADING_FLAG.value = false;
    }

    function handleRequestError(error, method) {
        const backendError = backendErrorDetails(error);
        if (backendError) {
            setBackendError(backendError);
            console.error(`${method}(): ${backendError.message}`);
            return false;
        }
        if (error.response) {
            const message = `${error.response.statusText}: ${error.response.status}`;
            console.log(message);
            return typeof error.response.data === "object"
                ? error.response.data
                : { msg: message };
        }
        LOADING_FLAG.value = false;
        reportFrontendError(error, method);
        return false;
    }

    async function GET(api) {
        try {
            const response = await axios.get(api, {
                headers: {
                    Authorization: "Bearer " + auth_token,
                },
            });

            return response.data;
        } catch (error) {
            return handleRequestError(error, "get");
        }
    }

    async function POST(api, data) {
        try {
            const response = await axios.post(api, data, {
                headers: { Authorization: "Bearer " + auth_token },
            });

            return response.data;
        } catch (error) {
            return handleRequestError(error, "post");
        }
    }

    async function PATCH(api, data) {
        try {
            const response = await axios.patch(api, data, {
                headers: { Authorization: "Bearer " + auth_token },
            });

            return response.data;
        } catch (error) {
            return handleRequestError(error, "patch");
        }
    }

    async function DELETE(api) {
        try {
            const response = await axios.delete(api, {
                headers: { Authorization: "Bearer " + auth_token },
            });

            return response.data;
        } catch (error) {
            return handleRequestError(error, "delete");
        }
    }

    async function auth() {
        const response = await GET("/api/auth/auth");
        if (response === false) return false;

        if (response.status == 0) {
            IS_LOCKED.value = false;
            return true;
        }
        requireAuth("AuthView_Session_Expired");
        return false;
    }

    function clearBackendError() {
        BACKEND_ERROR.value = null;
    }

    function requireAuth(messageKey = "") {
        auth_token = "";
        localStorage.removeItem("PAL_AUTH_TOKEN");
        AUTH_MESSAGE_KEY.value = messageKey;
        IS_LOCKED.value = true;
        APP_STATE.value = "auth-required";
        LOADING_FLAG.value = false;
    }

    async function unlock(password, remember = false) {
        AUTH_MESSAGE_KEY.value = "";
        APP_STATE.value = "connecting";
        LOADING_FLAG.value = true;
        const response = await POST("/api/auth/login", {
            password,
            remember,
        });
        if (response === false) return false;

        if (response.status == 0) {
            IS_LOCKED.value = false;
            auth_token = response.data.access_token;
            if (remember) {
                localStorage.setItem("PAL_AUTH_TOKEN", auth_token);
            } else {
                localStorage.removeItem("PAL_AUTH_TOKEN");
            }
            APP_STATE.value = "connecting";
            return await resumeBackendSave();
        } else if (response.status == 2) {
            requireAuth("AuthView_Wrong_Password");
        } else {
            setBackendError(getTranslatedText("BackendError_Request_Failed", [response.msg]));
        }
        LOADING_FLAG.value = false;
        return false;
    }

    async function fetch_config() {
        let no_set_loading_flag = LOADING_FLAG.value;
        if (!no_set_loading_flag) LOADING_FLAG.value = true;

        const response = await GET("/api/save/fetch_config");
        if (response === false) return false;

        if (response.status == 0) {
            if (response.data.I18nList) {
                I18nList.value = response.data.I18nList;
            }
            if (!localStorage.getItem("PAL_I18n") && I18nList.value[response.data.I18n]) {
                I18n.value = response.data.I18n;
            }
            if (!PAL_GAME_SAVE_PATH.value) {
                PAL_GAME_SAVE_PATH.value = response.data.Path;
            }
            configuredSavePath = response.data.Path;
            HAS_PASSWORD.value = response.data.HasPassword;
            VERSION.value = response.data.VERSION;
            IS_OFFICIAL_BUILD.value = response.data.IsOfficialBuild;
        } else if (response.status == 2) {
            requireAuth();
        } else {
            setBackendError(getTranslatedText("BackendError_Request_Failed", [response.msg]));
        }

        if (!no_set_loading_flag) LOADING_FLAG.value = false;
        return response.status == 0;
    }

    async function resumeBackendSave() {
        const response = await GET("/api/save/status");
        if (response === false) return false;
        if (response.status == 2) {
            requireAuth("AuthView_Session_Expired");
            LOADING_FLAG.value = false;
            return false;
        }
        if (response.status != 0) {
            setBackendError(getTranslatedText("BackendError_Request_Failed", [response.msg]));
            return false;
        }
        if (response.data.SaveLoaded) {
            if (configuredSavePath) {
                PAL_GAME_SAVE_PATH.value = configuredSavePath;
                PAL_WRITE_BACK_PATH.value = configuredSavePath;
            }
            return await hydrateLoadedSave();
        }
        reset();
        APP_STATE.value = "entry";
        LOADING_FLAG.value = false;
        return true;
    }

    async function bootstrap() {
        APP_STATE.value = "connecting";
        IS_LOCKED.value = true;
        clearBackendError();
        LOADING_FLAG.value = true;
        auth_token = auth_token || localStorage.getItem("PAL_AUTH_TOKEN") || "";

        if (!await fetch_config()) return false;
        if (HAS_PASSWORD.value) {
            if (!auth_token) {
                APP_STATE.value = "auth-required";
                LOADING_FLAG.value = false;
                return true;
            }
            if (!await auth()) {
                LOADING_FLAG.value = false;
                return false;
            }
            return await resumeBackendSave();
        }
        return await unlock("", false);
    }

    async function get_updates() {
        const response = await GET("/api/save/update");
        if (response === false) return;

        if (response.status == 0) {
            return UPDATE_DATA.value = response.data;
        }
    }

    function update_path_picker_result(data) {
        IS_PAL_SAVE_PATH.value = data.isPalDir;
        PAL_FILE_PICKER_PATH.value = data.currentPath;
        PATH_CONTEXT.value = new Map(Object.entries(data.children));
        SHOW_FILE_PICKER.value = true;
    }

    async function show_file_picker() {
        let no_set_loading_flag = LOADING_FLAG.value;
        if (!no_set_loading_flag) LOADING_FLAG.value = true;

        let response = undefined;
        if (PAL_GAME_SAVE_PATH.value) {
            response = await POST("/api/save/path", {
                path: PAL_GAME_SAVE_PATH.value,
            });
            if (response === false) return;
            if (response.status != 0) {
                PAL_GAME_SAVE_PATH.value = undefined;
                localStorage.removeItem("PAL_GAME_SAVE_PATH");
                response = await GET("/api/save/path");
            }
        } else {
            response = await GET("/api/save/path");
        }

        if (response === false) return false;

        if (response.status == 0) {
            update_path_picker_result(response.data);
        } else if (response.status == 2) {
            requireAuth("AuthView_Session_Expired");
        } else {
            reportOperationError("Operation_Select_Path", response);
        }

        if (!no_set_loading_flag) LOADING_FLAG.value = false;
    }

    async function path_back() {
        let no_set_loading_flag = LOADING_FLAG.value;
        if (!no_set_loading_flag) LOADING_FLAG.value = true;

        const response = await PATCH("/api/save/path");

        if (response === false) return;

        if (response.status == 0) {
            update_path_picker_result(response.data);
        } else if (response.status == 2) {
            requireAuth("AuthView_Session_Expired");
        } else {
            reportOperationError("Operation_Select_Path", response);
        }

        if (!no_set_loading_flag) LOADING_FLAG.value = false;
    }

    async function update_picker_result(path) {
        let no_set_loading_flag = LOADING_FLAG.value;
        if (!no_set_loading_flag) LOADING_FLAG.value = true;

        const response = await POST("/api/save/path", {
            path: path,
        });

        if (response === false) return;

        if (response.status == 0) {
            update_path_picker_result(response.data);
        } else if (response.status == 2) {
            requireAuth("AuthView_Session_Expired");
        } else {
            reportOperationError("Operation_Select_Path", response);
        }

        if (!no_set_loading_flag) LOADING_FLAG.value = false;
    }

    async function updateI18n() {
        localStorage.setItem("PAL_I18n", I18n.value);
        if (IS_LOCKED.value || BACKEND_ERROR.value) return true;

        sorryandfuckyou();
        let no_set_loading_flag = LOADING_FLAG.value;
        if (!no_set_loading_flag) LOADING_FLAG.value = true;

        const response = await PATCH("/api/save/i18n", { I18n: I18n.value });
        if (response === false) return false;

        if (response.status == 0) {
            // if on pal editor panel, refresh all translated texts (except for hardcoded ui)
            if (SAVE_LOADED_FLAG.value) {
                PLAYER_MAP.value.forEach((player, playerUId) => {
                    fetchPlayerPal(playerUId);
                });
                fetchPlayerPal(PAL_BASE_WORKER_BTN.value);
                await fetchStaticData();
            }
        } else if (response.status == 2) {
            requireAuth("AuthView_Session_Expired");
        } else {
            setBackendError(getTranslatedText("BackendError_Request_Failed", [response.msg]));
        }
        if (!no_set_loading_flag) LOADING_FLAG.value = false;
        return response.status == 0;
    }

    async function fetchStaticData() {
        let no_set_loading_flag = LOADING_FLAG.value;
        if (!no_set_loading_flag) LOADING_FLAG.value = true;
        const passive_skills_raw = await GET("/api/save/passive_skills");
        if (passive_skills_raw === false) return false;

        if (passive_skills_raw.status == 0) {
            PASSIVE_SKILLS.value = passive_skills_raw.data.dict;
            PASSIVE_SKILLS_LIST.value = passive_skills_raw.data.arr;
        } else if (passive_skills_raw.status == 2) {
            requireAuth("AuthView_Session_Expired");
            return false;
        } else {
            setBackendError(getTranslatedText("BackendError_Request_Failed", [passive_skills_raw.msg]));
            return false;
        }

        const active_skills_raw = await GET("/api/save/active_skills");
        if (active_skills_raw === false) return false;

        if (active_skills_raw.status == 0) {
            ACTIVE_SKILLS.value = active_skills_raw.data.dict;
            ACTIVE_SKILLS_LIST.value = active_skills_raw.data.arr;
        } else if (active_skills_raw.status == 2) {
            requireAuth("AuthView_Session_Expired");
            return false;
        } else {
            setBackendError(getTranslatedText("BackendError_Request_Failed", [active_skills_raw.msg]));
            return false;
        }

        const pal_data_raw = await GET("/api/save/pal_data");
        if (pal_data_raw === false) return false;

        if (pal_data_raw.status == 0) {
            PAL_STATIC_DATA.value = pal_data_raw.data.dict;
            PAL_STATIC_DATA_LIST.value = pal_data_raw.data.arr;
        } else if (pal_data_raw.status == 2) {
            requireAuth("AuthView_Session_Expired");
            return false;
        } else {
            setBackendError(getTranslatedText("BackendError_Request_Failed", [pal_data_raw.msg]));
            return false;
        }

        const tech_data_raw = await GET("/api/save/tech_data");
        if (tech_data_raw === false) return false;

        if (tech_data_raw.status == 0) {
            TECH_LV_DICT.value = tech_data_raw.data.techLvDict;
        } else if (tech_data_raw.status == 2) {
            requireAuth("AuthView_Session_Expired");
            return false;
        } else {
            setBackendError(getTranslatedText("BackendError_Request_Failed", [tech_data_raw.msg]));
            return false;
        }

        const skin_data_raw = await GET("/api/save/skin_data");
        if (skin_data_raw === false) return false;
        if (skin_data_raw.status == 0) {
            SKIN_DATA_LIST.value = skin_data_raw.data.arr;
        } else if (skin_data_raw.status == 2) {
            requireAuth("AuthView_Session_Expired");
            return false;
        } else {
            setBackendError(getTranslatedText("BackendError_Request_Failed", [skin_data_raw.msg]));
            return false;
        }
        if (!no_set_loading_flag) LOADING_FLAG.value = false;
        return true;
    }

    function reset(updateAppState = true) {
        LOADING_FLAG.value = false;
        HAS_WORKING_PAL_FLAG.value = false;
        SAVE_LOADED_FLAG.value = false;
        BASE_PAL_BTN_CLK_FLAG.value = false;
        SELECTED_PAL_ID.value = null;
        SELECTED_PLAYER_ID.value = null;

        BASE_PAL_MAP.value = new Map();
        PLAYER_MAP.value = new Map();
        PAL_PASSIVE_SELECTED_ITEM.value = "";
        PAL_ACTIVE_SELECTED_ITEM.value = "";

        PAL_LIST_SEARCH_KEYWORD.value = "";
        SHOW_UNREF_PAL_FLAG.value = false;
        SHOW_OOB_PAL_FLAG.value = true;
        SHOW_PLAYER_EDIT_FLAG.value = false;

        // display data
        SELECTED_PAL_DATA.value = new Map();
        PAL_MAP.value = new Map();

        PLAYER_MAP.value.clear();
        if (updateAppState) {
            APP_STATE.value = IS_LOCKED.value ? "auth-required" : "entry";
        }
    }

    function getTranslatedText(translationKey, args = []) {
        let translation = UI_TRANSLATIONS[I18n.value]?.[translationKey]
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

    async function updatePlayer(e) {
        let no_set_loading_flag = LOADING_FLAG.value;
        if (!no_set_loading_flag) LOADING_FLAG.value = true;

        // sometimes we manually construct a "e" target in a very hacked way
        let key = e.target.name;
        let value = e.target.value;

        if (SELECTED_PLAYER_ID.value == null) {
            showToast("Message_Select_Player");
            if (!no_set_loading_flag) LOADING_FLAG.value = false;
            return;
        }

        console.log(
            `Modify: Player: ${SELECTED_PLAYER_ID.value}, Target ${
                PLAYER_MAP.value.get(SELECTED_PLAYER_ID.value).NickName
            } key=${key}, value=${value}`
        );

        const response = await PATCH("/api/player/player_data", {
            key: key,
            value: value,
            PlayerUId: SELECTED_PLAYER_ID.value,
        });
        if (response === false) return;

        if (response.status == 0) {
            await loadPlayer(SELECTED_PLAYER_ID.value);
        } else if (response.status == 2) {
            requireAuth("AuthView_Session_Expired");
        } else {
            reportOperationError("Operation_Update_Player", response);
        }
        if (!no_set_loading_flag) LOADING_FLAG.value = false;
    }

    async function loadPlayer(playerUId, updatePal = false) {
        let no_set_loading_flag = LOADING_FLAG.value;
        if (!no_set_loading_flag) LOADING_FLAG.value = true;

        if (SELECTED_PLAYER_ID.value == null) {
            showToast("Message_Select_Player");
            if (!no_set_loading_flag) LOADING_FLAG.value = false;
            return;
        }

        const response = await POST("/api/player/player_data", {
            PlayerUId: playerUId,
        });
        if (response === false) return;

        if (response.status == 0) {
            const player_obj = new Player(response.data);
            if (!updatePal && PLAYER_MAP.value.has(playerUId)) {
                player_obj.pals = PLAYER_MAP.value.get(playerUId).pals;
            }

            PLAYER_MAP.value.set(playerUId, player_obj);

            const pal_id_bk = SELECTED_PAL_ID.value;
            // const pal_data_bk = SELECTED_PAL_DATA.value;
            await selectPlayer(playerUId, true);

            // player id and pal data never changed so this is safe
            // if (!updatePal) await selectPal({ target: SELECTED_PAL_EL });
            if (!updatePal && pal_id_bk) await selectPal(pal_id_bk, true);
        } else if (response.status == 2) {
            requireAuth("AuthView_Session_Expired");
        } else {
            reportOperationError("Operation_Load_Player", response);
        }

        if (!no_set_loading_flag) LOADING_FLAG.value = false;
    }

    async function loadPlayers() {
        let no_set_loading_flag = LOADING_FLAG.value;
        if (!no_set_loading_flag) LOADING_FLAG.value = true;

        const response = await GET("/api/player/players_data", {
            ReadPath: PAL_GAME_SAVE_PATH.value,
        });
        if (response === false) return false;

        if (response.status == 0) {
            if (response.data.hasWorkingPal) {
                HAS_WORKING_PAL_FLAG.value = true;
            }

            for (let player of response.data.players) {
                let p = new Player(player);
                PLAYER_MAP.value.set(p.InstanceId, p);
                // console.log(`Found player: ${p.NickName} - ${p.InstanceId}`);
            }

            if (PLAYER_MAP.value.size <= 0 && !HAS_WORKING_PAL_FLAG.value) {
                showToast("Message_No_Player");
            }
        } else if (response.status == 2) {
            requireAuth("AuthView_Session_Expired");
            return false;
        } else {
            setBackendError(getTranslatedText("BackendError_Request_Failed", [response.msg]));
            return false;
        }

        if (!no_set_loading_flag) LOADING_FLAG.value = false;
        return true;
    }

    async function sorryandfuckyou() {
        if (I18n.value == "zh-CN" && CN_WARNING_ON_LOAD.value) {
            showMessage({
                severity: "warning",
                presentation: "dialog",
                messageKey: "Message_CN_AntiScam",
            });
            CN_WARNING_ON_LOAD.value = false;
        }
    }

    async function loadSave() {
        let no_set_loading_flag = LOADING_FLAG.value;
        if (!no_set_loading_flag) LOADING_FLAG.value = true;

        const response = await POST("/api/save/load", {
            ReadPath: PAL_GAME_SAVE_PATH.value,
        });
        if (response === false) return;

        if (response.status == 0) {
            PAL_WRITE_BACK_PATH.value = PAL_GAME_SAVE_PATH.value;
            if (await hydrateLoadedSave()) {
                localStorage.setItem("PAL_GAME_SAVE_PATH", PAL_GAME_SAVE_PATH.value);
            }
        } else if (response.status == 2) {
            requireAuth("AuthView_Session_Expired");
        } else {
            setBackendError(getTranslatedText("BackendError_Request_Failed", [response.msg]));
        }
        if (!no_set_loading_flag) LOADING_FLAG.value = false;
    }

    async function hydrateLoadedSave() {
        reset(false);
        LOADING_FLAG.value = true;
        try {
            if (!await updateI18n()) return false;
            if (!await loadPlayers()) return false;
            if (!await fetchStaticData()) return false;
            const defaultPlayer = HAS_WORKING_PAL_FLAG.value
                ? PAL_BASE_WORKER_BTN.value
                : PLAYER_MAP.value.keys().next().value;
            if (defaultPlayer !== undefined) await selectPlayer(defaultPlayer);
            SAVE_LOADED_FLAG.value = true;
            IS_LOCKED.value = false;
            APP_STATE.value = "editor";
            return true;
        } finally {
            LOADING_FLAG.value = false;
        }
    }

    async function writeSave() {
        let retval = false;
        let no_set_loading_flag = LOADING_FLAG.value;
        if (!no_set_loading_flag) LOADING_FLAG.value = true;
        const response = await POST("/api/save/save", {
            WritePath: PAL_WRITE_BACK_PATH.value,
        });
        if (response === false) return;

        if (response.status == 0) {
            showToast("Message_Save_Success", "success", [PAL_WRITE_BACK_PATH.value]);
            retval = true;
        } else if (response.status == 2) {
            requireAuth("AuthView_Session_Expired");
        } else {
            reportOperationError("Operation_Save", response);
        }
        if (!no_set_loading_flag) LOADING_FLAG.value = false;
        return retval;
    }

    async function fetchPlayerPal(playerUId) {
        let no_set_loading_flag = LOADING_FLAG.value;
        if (!no_set_loading_flag) LOADING_FLAG.value = true;
        const response = await POST("/api/player/player_pals", {
            PlayerUId: playerUId,
        });
        if (response === false) return;

        if (response.status == 0) {
            // get old map
            let map =
                playerUId == PAL_BASE_WORKER_BTN.value
                    ? BASE_PAL_MAP.value
                    : PLAYER_MAP.value.get(playerUId).pals;
            // clear old map
            map.clear();
            // insert new data
            for (let pal of response.data) {
                let pal_data = new PalData(pal);
                map.set(pal_data.InstanceId, pal_data);
                // console.log(
                //   `Pal Loaded: ${pal_data.DisplayName} - ${pal_data.InstanceId}`
                // );
            }
        } else if (response.status == 2) {
            requireAuth("AuthView_Session_Expired");
        } else {
            reportOperationError("Operation_Load_Pals", response);
        }
        if (!no_set_loading_flag) LOADING_FLAG.value = false;
    }

    async function fetchPlayerData(playerUId) {
        let no_set_loading_flag = LOADING_FLAG.value;
        if (!no_set_loading_flag) LOADING_FLAG.value = true;

        if (SELECTED_PLAYER_ID.value == null) {
            showToast("Message_Select_Player");
            if (!no_set_loading_flag) LOADING_FLAG.value = false;
            return;
        }

        const response = await POST("/api/player/player_data", {
            PlayerUId: playerUId,
        });
        if (response === false) return;

        if (response.status == 0) {
            const player_obj = new Player(response.data);
            if (PLAYER_MAP.value.has(playerUId)) {
                player_obj.pals = PLAYER_MAP.value.get(playerUId).pals;
            }
            PLAYER_MAP.value.set(playerUId, player_obj);
        } else if (response.status == 2) {
            requireAuth("AuthView_Session_Expired");
        } else {
            reportOperationError("Operation_Load_Player_Data", response);
        }

        if (!no_set_loading_flag) LOADING_FLAG.value = false;
    }

    async function selectPlayer(playerUId, manual = false) {
        let no_set_loading_flag = LOADING_FLAG.value;
        if (!no_set_loading_flag) LOADING_FLAG.value = true;

        // clear selected playerId
        SELECTED_PLAYER_ID.value = null;
        SELECTED_PLAYER_DATA.value = null;
        BASE_PAL_BTN_CLK_FLAG.value = false;
        SHOW_PLAYER_EDIT_FLAG.value = false;

        // clear pal selection
        SELECTED_PAL_ID.value = null;
        SELECTED_PAL_DATA.value = null;

        // if data not present
        // need to change this in the future, so the pal list properly refreshes (for add / del pal)
        if (
            (playerUId == PAL_BASE_WORKER_BTN.value &&
                BASE_PAL_MAP.value.size == 0) ||
            (playerUId != PAL_BASE_WORKER_BTN.value &&
                PLAYER_MAP.value.get(playerUId).pals.size == 0)
        ) {
            await fetchPlayerPal(playerUId);
        }

        // set the pal_map
        PAL_MAP.value =
            playerUId == PAL_BASE_WORKER_BTN.value
                ? BASE_PAL_MAP.value
                : PLAYER_MAP.value.get(playerUId).pals;

        // properly setup selected player flag
        if (playerUId == PAL_BASE_WORKER_BTN.value) {
            BASE_PAL_BTN_CLK_FLAG.value = true;
        } else {
            SELECTED_PLAYER_ID.value = playerUId;
            if (!manual) {
                await fetchPlayerData(playerUId);
            }
            SHOW_PLAYER_EDIT_FLAG.value = true;
            SELECTED_PLAYER_DATA.value = PLAYER_MAP.value.get(playerUId);
        }

        if (!no_set_loading_flag) LOADING_FLAG.value = false;
    }

    async function fetchPalData(player, pal) {
        let no_set_loading_flag = LOADING_FLAG.value;
        if (!no_set_loading_flag) LOADING_FLAG.value = true;

        const response = await POST("/api/pal/paldata", {
            PlayerUId: player,
            InstanceId: pal,
        });
        if (response === false) return;

        if (response.status == 0) {
            // construct new pal
            let pal_data = new PalData(response.data);
            // update the pal from the correct pal container
            if (player == PAL_BASE_WORKER_BTN.value) {
                BASE_PAL_MAP.value.set(pal_data.InstanceId, pal_data);
            } else {
                PLAYER_MAP.value
                    .get(player)
                    .pals.set(pal_data.InstanceId, pal_data);
            }
        } else if (response.status == 2) {
            requireAuth("AuthView_Session_Expired");
        } else {
            reportOperationError("Operation_Load_Pal", response);
        }

        if (!no_set_loading_flag) LOADING_FLAG.value = false;
    }

    async function selectPal(palId, manual = false) {
        let no_set_loading_flag = LOADING_FLAG.value;
        if (!no_set_loading_flag) LOADING_FLAG.value = true;

        if (!manual) {
            // SELECTED_PAL_EL = e.target;
            SELECTED_PAL_DATA.value = null;
            SELECTED_PAL_ID.value = null;
        }

        // set selected pal, and print out debug info
        let palData = PAL_MAP.value.get(palId);
        if (palData == null) {
            showToast("Message_Select_Pal_Failed");
            if (!no_set_loading_flag) LOADING_FLAG.value = false;
            return;
        }
        // console.log(`Pal ${palData.DisplayName} - ${palData.InstanceId} selected.`);

        await fetchPalData(
            // get player id, or BASE INDICATION STR
            GET_PAL_OWNER_API_ID(),
            palId
        );

        // Update selected pal id and pal data
        SELECTED_PAL_DATA.value = PAL_MAP.value.get(palId);
        SELECTED_PAL_ID.value = SELECTED_PAL_DATA.value.InstanceId;
        SHOW_PLAYER_EDIT_FLAG.value = false;

        // Scroll to selected pal
        // if (!isElementInViewport(SELECTED_PAL_EL)) {
        //   SELECTED_PAL_EL.scrollIntoView({ behavior: "smooth" });
        // }
        if (!no_set_loading_flag) LOADING_FLAG.value = false;
    }

    function isElementInViewport(el) {
        const rect = el.getBoundingClientRect();
        return (
            rect.top >= 0 &&
            rect.left >= 0 &&
            rect.bottom <=
                (window.innerHeight || document.documentElement.clientHeight) &&
            rect.right <=
                (window.innerWidth || document.documentElement.clientWidth)
        );
    }

    async function updatePal(e) {
        // sometimes we manually construct a "e" target in a very hacked way
        let key = e.target.name;
        let value = e.target.value;
        if (
            (key === "add_MasteredWaza" || key === "add_EquipWaza")
            && ACTIVE_SKILLS.value[value]?.Assignable === false
        ) {
            showToast("Message_Skill_Not_Assignable");
            return;
        }

        let no_set_loading_flag = LOADING_FLAG.value;
        if (!no_set_loading_flag) LOADING_FLAG.value = true;

        // console.log(
        //   `Modify: PalOwner: ${GET_PAL_OWNER_API_ID()}, Target ${
        //     SELECTED_PAL_DATA.value.DisplayName
        //   } key=${key}, value=${value}`
        // );

        const response = await PATCH("/api/pal/paldata", {
            key: key,
            value: value,
            PlayerUId: GET_PAL_OWNER_API_ID(),
            PalGuid: SELECTED_PAL_ID.value,
        });
        if (response === false) return;

        if (response.status == 0) {
            // A hack way to trigger vue re-rendering.
            // The object is simply too nested that I can't figure out how to have vue properly refresh.
            if (SELECTED_PAL_ID.value) {
                await selectPal(SELECTED_PAL_ID.value, true);
                UPDATE_PAL_RESELECT_CTR.value++;
            }
        } else if (response.status == 2) {
            requireAuth("AuthView_Session_Expired");
        } else {
            reportOperationError("Operation_Update_Pal", response);
        }
        if (!no_set_loading_flag) LOADING_FLAG.value = false;
    }

    function GET_PAL_OWNER_API_ID() {
        return BASE_PAL_BTN_CLK_FLAG.value
            ? PAL_BASE_WORKER_BTN.value
            : SELECTED_PLAYER_ID.value;
    }

    async function dumpPalData() {
        let no_set_loading_flag = LOADING_FLAG.value;
        if (!no_set_loading_flag) LOADING_FLAG.value = true;

        const response = await POST("/api/pal/dump_data", {
            PlayerUId: GET_PAL_OWNER_API_ID(),
            PalGuid: SELECTED_PAL_ID.value,
        });

        if (response === false) return;

        if (response.status == 0) {
            const data = response.data;
            await navigator.clipboard.writeText(data);
            showToast("Message_Pal_Copied", "success");
            window.open("https://jsonformatter.curiousconcept.com/");
        } else if (response.status == 2) {
            requireAuth("AuthView_Session_Expired");
        } else {
            reportOperationError("Operation_Copy_Pal", response);
        }

        if (!no_set_loading_flag) LOADING_FLAG.value = false;
    }

    function isFilteredPal(pal) {
        if (!SHOW_UNREF_PAL_FLAG.value && pal.Is_Unref_Pal) {
            return true;
        }
        if (SHOW_UNREF_PAL_FLAG.value && !pal.Is_Unref_Pal) {
            return true;
        }

        // if (SHOW_OOB_PAL_FLAG.value && pal.in_owner_palbox) {
        //   return true
        // }

        if (!SHOW_OOB_PAL_FLAG.value && !pal.in_owner_palbox) {
            return true;
        }

        if (
            PAL_LIST_SEARCH_KEYWORD.value &&
            !pal.DisplayName.toLowerCase().includes(
                PAL_LIST_SEARCH_KEYWORD.value.toLowerCase()
            )
        ) {
            return true;
        }

        return false;
    }

    function getNextElement(map, currKey) {
        let found = false;
        let firstElement = null;
        let isFirstElement = true;
        for (let [key, value] of map) {
            if (isFirstElement) {
                firstElement = { key, value }; // Store the first element
                isFirstElement = false || isFilteredPal(value);
            }
            if (found) {
                if (isFilteredPal(value)) continue;
                return { key, value };
            }
            if (key == currKey) {
                found = true;
            }
        }
        return firstElement;
    }

    async function delPal() {
        let no_set_loading_flag = LOADING_FLAG.value;
        if (!no_set_loading_flag) LOADING_FLAG.value = true;

        const response = await DELETE(`/api/pal/pal/${SELECTED_PAL_ID.value}`);

        if (response === false) return;

        if (response.status == 0) {
            const nextNode = getNextElement(
                PAL_MAP.value,
                SELECTED_PAL_ID.value
            );
            PAL_MAP.value.delete(SELECTED_PAL_DATA.value.InstanceId);
            SELECTED_PAL_ID.value = null;
            // SELECTED_PAL_EL = null;
            SELECTED_PAL_DATA.value = null;
            // ADD_PAL_RESELECT_CTR.value++;
            if (nextNode) {
                SELECTED_PAL_ID.value = nextNode.key;
            }
        } else if (response.status == 2) {
            requireAuth("AuthView_Session_Expired");
        } else {
            reportOperationError("Operation_Delete_Pal", response);
        }

        if (!no_set_loading_flag) LOADING_FLAG.value = false;
    }

    async function addPal() {
        let no_set_loading_flag = LOADING_FLAG.value;
        if (!no_set_loading_flag) LOADING_FLAG.value = true;
        const PlayerUId = GET_PAL_OWNER_API_ID();
        if (PlayerUId == PAL_BASE_WORKER_BTN.value) {
            showToast("Message_Basecamp_Add_Unsupported");
            if (!no_set_loading_flag) LOADING_FLAG.value = false;
            return;
        }
        const response = await POST("/api/pal/add_pal", {
            PlayerUId: PlayerUId,
        });

        if (response === false) return;

        if (response.status == 0) {
            const pal_data = new PalData(response.data);
            const temp_map = new Map();
            PAL_MAP.value.forEach((v, k) => temp_map.set(k, v));
            PAL_MAP.value.clear();
            PAL_MAP.value.set(pal_data.InstanceId, pal_data);
            temp_map.forEach((v, k) => PAL_MAP.value.set(k, v));

            // ADD_PAL_RESELECT_CTR.value++
            SHOW_PLAYER_EDIT_FLAG.value = false;
            SELECTED_PAL_ID.value = pal_data.InstanceId;
            SELECTED_PAL_DATA.value = pal_data;
        } else if (response.status == 2) {
            requireAuth("AuthView_Session_Expired");
        } else {
            reportOperationError("Operation_Add_Pal", response);
        }

        if (!no_set_loading_flag) LOADING_FLAG.value = false;
    }

    async function dupePal() {
        let no_set_loading_flag = LOADING_FLAG.value;
        if (!no_set_loading_flag) LOADING_FLAG.value = true;
        const PlayerUId = GET_PAL_OWNER_API_ID();
        if (PlayerUId == PAL_BASE_WORKER_BTN.value) {
            showToast("Message_Basecamp_Add_Unsupported");
            if (!no_set_loading_flag) LOADING_FLAG.value = false;
            return;
        }
        const response = await POST("/api/pal/dupe_pal", {
            PlayerUId: PlayerUId,
            PalGuid: SELECTED_PAL_ID.value,
        });

        if (response === false) return;

        if (response.status == 0) {
            const pal_data = new PalData(response.data);
            const temp_map = new Map();
            PAL_MAP.value.forEach((v, k) => temp_map.set(k, v));
            PAL_MAP.value.clear();
            temp_map.forEach((v, k) => {
                PAL_MAP.value.set(k, v);
                if (v == SELECTED_PAL_DATA.value) {
                    PAL_MAP.value.set(pal_data.InstanceId, pal_data);
                }
            });
            // PAL_RESELECT_CTR.value++
            SELECTED_PAL_ID.value = pal_data.InstanceId;
            SELECTED_PAL_DATA.value = pal_data;
        } else if (response.status == 2) {
            requireAuth("AuthView_Session_Expired");
        } else {
            reportOperationError("Operation_Duplicate_Pal", response);
        }

        if (!no_set_loading_flag) LOADING_FLAG.value = false;
    }

    function displayPalElement(DataAccessKey) {
        const els = PAL_STATIC_DATA.value[DataAccessKey]?.Elements;
        if (!els) return;

        let str = "";
        for (let e of els) {
            str += displayElement(e);
        }
        return str;
    }

    function displayElement(element) {
        const elementEmojis = {
            Water: "💧",
            Fire: "🔥",
            Dragon: "🐉",
            Grass: "☘️",
            Leaf: "☘️",
            Ground: "🪨",
            Earth: "🪨",
            Ice: "❄️",
            Electric: "⚡",
            Electricity: "⚡",
            Neutral: "🔵",
            Normal: "🔵",
            Dark: "🌑",
        };
        return elementEmojis[element] || "";
    }

    function skillBadgeText(skill) {
        return skillBadges(skill)
            .map(badge => (
                `${SKILL_BADGE_ICONS[badge]} ${getTranslatedText(SKILL_BADGE_TRANSLATION_KEYS[badge])}`
            ))
            .join(" · ");
    }

    function displayRating(rating) {
        if (!rating) return "";
        if (rating >= 5) return "🟣";
        if (rating == 4) return "🟢";
        if (rating >= 2) return "🟡";
        if (rating < 0) return "🔴";
        return "⚪";
    }

    async function shownDonate() {
        let no_set_loading_flag = LOADING_FLAG.value;
        if (!no_set_loading_flag) LOADING_FLAG.value = true;
        await PATCH("/api/save/donate");
        if (!no_set_loading_flag) LOADING_FLAG.value = false;
    }

    async function showDonate() {
        let no_set_loading_flag = LOADING_FLAG.value;
        if (!no_set_loading_flag) LOADING_FLAG.value = true;
        const response = await GET("/api/save/donate");
        if (response === false) return;
        let res = false;
        if (response.status == 0) {
            res = response.data?.shouldShowDonate == true;
            IS_LOCKED.value = false;
        } else if (response.status == 2) {
            requireAuth("AuthView_Session_Expired");
        } else {
            reportOperationError("Operation_Donation", response);
        }
        if (!no_set_loading_flag) LOADING_FLAG.value = false;
        return res;
    }

    return {
        MAX_LEVEL,
        MAX_INVALID_LEVEL,
        MAX_SOULS_LEVEL,
        MAX_SUITABILITY_LEVEL,
        MAX_FRIENDSHIP_LEVEL,

        PAL_PASSIVE_SELECTED_ITEM,
        PAL_ACTIVE_SELECTED_ITEM,
        PAL_BASE_WORKER_BTN,
        PLAYER_MAP,
        PAL_MAP,
        SELECTED_PLAYER_ID,
        SELECTED_PLAYER_DATA,
        SELECTED_PAL_ID,
        SELECTED_PAL_DATA,
        SHOW_DONATE_FLAG,
        LOADING_FLAG,
        SAVE_LOADED_FLAG,
        // ADD_PAL_RESELECT_CTR,
        UPDATE_PAL_RESELECT_CTR,
        SHOW_UNREF_PAL_FLAG,
        SHOW_OOB_PAL_FLAG,
        HIDE_INVALID_OPTIONS,

        PAL_LIST_SEARCH_KEYWORD,

        IS_LOCKED,
        HAS_PASSWORD,
        APP_STATE,
        BACKEND_ERROR,
        AUTH_MESSAGE_KEY,
        MESSAGE_QUEUE,
        CURRENT_MESSAGE,

        PATH_CONTEXT,
        SHOW_FILE_PICKER,
        PAL_FILE_PICKER_PATH,
        IS_PAL_SAVE_PATH,

        SHOW_PLAYER_EDIT_FLAG,
        HAS_WORKING_PAL_FLAG,
        BASE_PAL_BTN_CLK_FLAG,
        PAL_GAME_SAVE_PATH,
        PAL_WRITE_BACK_PATH,
        VERSION,
        UPDATE_DATA,
        IS_OFFICIAL_BUILD,
        I18n,
        I18nList,
        PAL_STATIC_DATA,
        PAL_STATIC_DATA_LIST,
        SKIN_DATA_LIST,
        PASSIVE_SKILLS,
        PASSIVE_SKILLS_LIST,
        ACTIVE_SKILLS,
        ACTIVE_SKILLS_LIST,
        TECH_LV_DICT,

        getTranslatedText,
        getMessageText,

        isElementInViewport,
        isFilteredPal,

        displayPalElement,
        displayElement,
        filterSkillOptions,
        skillBadges,
        skillBadgeText,
        displayRating,

        reset,
        updateI18n,
        loadSave,
        selectPlayer,
        selectPal,
        updatePal,
        updatePlayer,
        writeSave,
        fetch_config,
        dumpPalData,
        delPal,
        addPal,
        dupePal,

        bootstrap,
        unlock,
        auth,
        requireAuth,
        clearBackendError,
        showMessage,
        dismissMessage,
        reportOperationError,
        reportFrontendError,
        show_file_picker,
        update_picker_result,
        path_back,

        showDonate,
        shownDonate,
        get_updates
    };
});
