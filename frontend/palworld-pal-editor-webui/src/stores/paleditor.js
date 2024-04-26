import { ref, computed, reactive, nextTick } from "vue";
import { defineStore } from "pinia";
import axios from "axios";

export const usePalEditorStore = defineStore("paleditor", () => {
  class Player {
    constructor(obj) {
      this.id = obj.id;
      this.name = obj.name;
      this.hasViewingCage = obj.hasViewingCage;
      this.OtomoCharacterContainerId = obj.OtomoCharacterContainerId
      this.PalStorageContainerId = obj.PalStorageContainerId
      this.pals = new Map();
    }
  }

  class PalData {
    constructor(obj) {
      this.Talent_Defense = obj.Talent_Defense;
      this.Talent_Shot = obj.Talent_Shot;
      this.Talent_Melee = obj.Talent_Melee;
      this.Talent_HP = obj.Talent_HP;

      this.Rank_CraftSpeed = obj.Rank_CraftSpeed;
      this.Rank_Defence = obj.Rank_Defence;
      this.Rank_Attack = obj.Rank_Attack;
      this.Rank_HP = obj.Rank_HP;
      this.Rank = obj.Rank;

      this.Level = obj.Level;
      this.NickName = obj.NickName;
      this.IsRarePal = obj.IsRarePal;
      this.IsBOSS = obj.IsBOSS;
      this.IsTower = obj.IsTower;
      this.IsRAID = obj.IsRAID;
      this.Gender = obj.Gender;
      this.HasWorkerSick = obj.HasWorkerSick;
      this.IsFaintedPal = obj.IsFaintedPal;

      this.ComputedDefense = obj.ComputedDefense;
      this.ComputedAttack = obj.ComputedAttack;
      this.ComputedCraftSpeed = obj.ComputedCraftSpeed;
      this.ComputedMaxHP = obj.ComputedMaxHP;

      this.MasteredWaza = obj.MasteredWaza;
      this.EquipWaza = obj.EquipWaza;
      this.PassiveSkillList = obj.PassiveSkillList;

      this.group_id = obj.group_id;
      this.ContainerId = obj.ContainerId;
      this.SlotIndex = obj.SlotIndex;
      this.DisplayName = obj.DisplayName;
      this.I18nName = obj.I18nName;
      this.DataAccessKey = obj.DataAccessKey;
      this.IconAccessKey = obj.IconAccessKey;
      this.OwnerName = obj.OwnerName;
      this.OwnerPlayerUId = obj.OwnerPlayerUId;
      this.InstanceId = obj.InstanceId;
      this.HasTowerVariant = obj.HasTowerVariant;
      this.IsPal = obj.IsPal;
      this.IsHuman = obj.IsHuman;
      this.Is_Unref_Pal = obj.Is_Unref_Pal;
      this.in_owner_palbox = obj.in_owner_palbox;
    }

    displaySpecialType() {
      if (this.IsTower) return "🗼";
      if (this.IsBOSS) return "💀";
      if (this.IsRarePal) return "✨";
      if (this.IsRAID) return "RAID";
      return "N/A";
    }

    getRank() {
      return this.Rank - 1;
    }

    swapTower() {
      this.IsTower = !this.IsTower;
      updatePal({ target: { name: "IsTower", value: this.IsTower } });
    }

    swapBoss() {
      this.IsBOSS = !this.IsBOSS;
      updatePal({ target: { name: "IsBOSS", value: this.IsBOSS } });
    }

    swapRare() {
      this.IsRarePal = !this.IsRarePal;
      updatePal({ target: { name: "IsRarePal", value: this.IsRarePal } });
    }

    levelDown() {
      if (this.Level > 1) {
        this.Level -= 1;
        updatePal({ target: { name: "Level", value: this.Level } });
      }
    }

    levelUp() {
      if (this.Level < 50) {
        this.Level += 1;
        updatePal({ target: { name: "Level", value: this.Level } });
      }
    }

    maxLevel() {
      this.Level = 50;
      updatePal({ target: { name: "Level", value: this.Level } });
    }

    displayGender() {
      if (this.Gender == "EPalGenderType::Female") {
        return "♀️";
      } else if (this.Gender == "EPalGenderType::Male") {
        return "♂️";
      } else {
        return null;
      }
    }

    swapGender() {
      if (this.Gender == "EPalGenderType::Female") {
        this.Gender = "EPalGenderType::Male";
      } else if (this.Gender == "EPalGenderType::Male") {
        this.Gender = "EPalGenderType::Female";
      } else return;
      updatePal({ target: { name: "Gender", value: this.Gender } });
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
        alert("Select a skill first!");
        return;
      }
      if (this.PassiveSkillList.length >= 4) {
        alert("you can't add more than 4 passive skills");
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
        alert("Select a skill first!");
        return;
      }
      updatePal({
        target: {
          name: "add_MasteredWaza",
          value: skill,
        },
      });
    }

    changeSpecie() {
      updatePal({
        target: {
          name: "CharacterID",
          value: this.DataAccessKey,
        },
      });
    }
  }

  const PAL_BASE_WORKER_BTN = ref("PAL_BASE_WORKER_BTN");

  // i18n mapping of passive and active skills
  const PASSIVE_SKILLS = ref({});
  const PASSIVE_SKILLS_LIST = ref([]);
  const ACTIVE_SKILLS = ref({});
  const ACTIVE_SKILLS_LIST = ref([]);
  const PAL_STATIC_DATA = ref({});
  const PAL_STATIC_DATA_LIST = ref([]);
  const I18nList = ref({});

  const TranslationKeyMap = ref({})
  const I18nLoadingPromises = {}

  // flags
  const LOADING_FLAG = ref(false);
  const SAVE_LOADED_FLAG = ref(false);
  const HAS_WORKING_PAL_FLAG = ref(false);
  const BASE_PAL_BTN_CLK_FLAG = ref(false);
  // const ADD_PAL_RESELECT_CTR = ref(0);
  // const DEL_PAL_RESELECT_CTR = ref(0)
  const UPDATE_PAL_RESELECT_CTR = ref(0);
  const SHOW_UNREF_PAL_FLAG = ref(false);
  const SHOW_OOB_PAL_FLAG = ref(true);
  const HIDE_INVALID_OPTIONS = ref(true)

  const PAL_LIST_SEARCH_KEYWORD = ref("")

  const IS_PAL_SAVE_PATH = ref(false)

  // data
  const BASE_PAL_MAP = ref(new Map());
  const PLAYER_MAP = ref(new Map());
  const PAL_PASSIVE_SELECTED_ITEM = ref("");
  const PAL_ACTIVE_SELECTED_ITEM = ref("");

  // display data
  const SELECTED_PAL_DATA = ref(new Map());
  const PAL_MAP = ref(new Map());

  // selected id
  const SELECTED_PLAYER_ID = ref(null);
  const SELECTED_PAL_ID = ref(null);

  // TODO Get rid of this...
  // let SELECTED_PAL_EL = null;

  // Configs
  const I18n = ref(localStorage.getItem("PAL_I18n"));
  const PAL_GAME_SAVE_PATH = ref(localStorage.getItem("PAL_GAME_SAVE_PATH"));
  const HAS_PASSWORD = ref(false);
  const PAL_WRITE_BACK_PATH = ref("");
  const PATH_CONTEXT = ref(new Map())

  const SHOW_FILE_PICKER = ref(false)
  const PAL_FILE_PICKER_PATH = ref(PAL_GAME_SAVE_PATH.value)

  // auth
  let auth_token = "";
  const IS_LOCKED = ref(true);

  async function GET(api) {
    try {
      const response = await axios.get(api, {
        headers: {
          Authorization: "Bearer " + auth_token,
        },
      });

      // console.log(response.data);
      return response.data;
    } catch (error) {
      if (error.response) {
        console.log(error.response.data);
        return error.response.data;
      } else if (error.request) {
        alert(
          `no response from the backend, make sure it is running, error: ${error.request}`
        );
        return false;
      } else {
        alert(`get(): ${error.message}`);
        return false;
      }
    }
  }

  async function POST(api, data) {
    try {
      const response = await axios.post(api, data, {
        headers: { Authorization: "Bearer " + auth_token },
      });

      // console.log(response.data);
      return response.data;
    } catch (error) {
      if (error.response) {
        console.log(error.response.data);
        return error.response.data;
      } else if (error.request) {
        alert(
          `no response from the backend, make sure it is running, error: ${error.request}`
        );
        return false;
      } else {
        alert(`post(): ${error.message}`);
        return false;
      }
    }
  }

  async function PATCH(api, data) {
    try {
      const response = await axios.patch(api, data, {
        headers: { Authorization: "Bearer " + auth_token },
      });

      // console.log(response.data);
      return response.data;
    } catch (error) {
      if (error.response) {
        console.log(error.response.data);
        return error.response.data;
      } else if (error.request) {
        alert(
          `no response from the backend, make sure it is running, error: ${error.request}`
        );
        return false;
      } else {
        alert(`patch(): ${error.message}`);
        return false;
      }
    }
  }

  async function DELETE(api) {
    try {
      const response = await axios.delete(api, {
        headers: { Authorization: "Bearer " + auth_token },
      });

      // console.log(response.data);
      return response.data;
    } catch (error) {
      if (error.response) {
        console.log(error.response.data);
        return error.response.data;
      } else if (error.request) {
        alert(
          `no response from the backend, make sure it is running, error: ${error.request}`
        );
        return false;
      } else {
        alert(`patch(): ${error.message}`);
        return false;
      }
    }
  }

  async function auth() {
    let no_set_loading_flag = LOADING_FLAG.value;
    if (!no_set_loading_flag) LOADING_FLAG.value = true;

    const response = await GET("/api/auth/auth");
    if (response === false) return;

    if (response.status == 0) {
      IS_LOCKED.value = false;
    } else if (response.status == 2) {
      IS_LOCKED.value = true;
      reset();
    } else {
      alert(`- auth - Error occured: ${response.msg}`);
    }

    if (!no_set_loading_flag) LOADING_FLAG.value = false;
  }

  async function login(e) {
    let no_set_loading_flag = LOADING_FLAG.value;
    if (!no_set_loading_flag) LOADING_FLAG.value = true;

    const response = await POST("/api/auth/login", {
      password: e.target.value,
    });
    if (response === false) return;

    if (response.status == 0) {
      IS_LOCKED.value = false;
      auth_token = response.data.access_token;
    } else if (response.status == 2) {
      alert("Wrong Password, Try Again.");
      IS_LOCKED.value = true;
      reset();
    } else {
      alert(`- login - Error occured: ${response.msg}`);
    }

    if (!no_set_loading_flag) LOADING_FLAG.value = false;
  }

  async function fetch_config() {
    let no_set_loading_flag = LOADING_FLAG.value;
    if (!no_set_loading_flag) LOADING_FLAG.value = true;

    const response = await GET("/api/save/fetch_config");
    if (response === false) return;

    if (response.status == 0) {
      I18nList.value = response.data.I18nList
      if (!I18n.value || !I18nList.value[I18n.value]) {
        I18n.value = response.data.I18n;
      }
      // TranslationKeyMap[I18n.value] = await import(`../i18n/${I18n.value}.js`)
      if (!PAL_GAME_SAVE_PATH.value) {
        PAL_GAME_SAVE_PATH.value = response.data.Path;
      }
      HAS_PASSWORD.value = response.data.HasPassword;
    } else if (response.status == 2) {
      alert("Unauthorized Access, Please Login. ");
      IS_LOCKED.value = true;
      reset();
    } else {
      alert("- fetch_config - Error occured: ", response.msg);
    }

    if (!no_set_loading_flag) LOADING_FLAG.value = false;
  }

  function update_path_picker_result(data) {
    IS_PAL_SAVE_PATH.value = data.isPalDir
    PAL_FILE_PICKER_PATH.value = data.currentPath
    PATH_CONTEXT.value = new Map(Object.entries(data.children))
    SHOW_FILE_PICKER.value = true
  }

  async function show_file_picker() {
    let no_set_loading_flag = LOADING_FLAG.value;
    if (!no_set_loading_flag) LOADING_FLAG.value = true;

    const response = await GET("/api/save/path");

    if (response === false) return;

    if (response.status == 0) {
      update_path_picker_result(response.data)
    } else if (response.status == 2) {
      alert("Unauthorized Access, Please Login. ");
      IS_LOCKED.value = true;
      reset();
    } else {
      alert(`- show_file_picker - Error occured: ${response.msg}`);
    }

    if (!no_set_loading_flag) LOADING_FLAG.value = false;
  }

  async function path_back() {
    let no_set_loading_flag = LOADING_FLAG.value;
    if (!no_set_loading_flag) LOADING_FLAG.value = true;

    const response = await PATCH("/api/save/path");

    if (response === false) return;

    if (response.status == 0) {
      update_path_picker_result(response.data)
    } else if (response.status == 2) {
      alert("Unauthorized Access, Please Login. ");
      IS_LOCKED.value = true;
      reset();
    } else {
      alert(`- show_file_picker - Error occured: ${response.msg}`);
    }

    if (!no_set_loading_flag) LOADING_FLAG.value = false;
  }

  async function update_picker_result(path) {
    let no_set_loading_flag = LOADING_FLAG.value;
    if (!no_set_loading_flag) LOADING_FLAG.value = true;

    const response = await POST("/api/save/path", {
      path: path
    });

    if (response === false) return;

    if (response.status == 0) {
      update_path_picker_result(response.data)
    } else if (response.status == 2) {
      alert("Unauthorized Access, Please Login. ");
      IS_LOCKED.value = true;
      reset();
    } else {
      alert(`- show_file_picker - Error occured: ${response.msg}`);
    }

    if (!no_set_loading_flag) LOADING_FLAG.value = false;
  }

  async function updateI18n() {
    let no_set_loading_flag = LOADING_FLAG.value;
    if (!no_set_loading_flag) LOADING_FLAG.value = true;

    const response = await PATCH("/api/save/i18n", { I18n: I18n.value });
    if (response === false) return;

    if (response.status == 0) {
      localStorage.setItem("PAL_I18n", I18n.value);
      // if on pal editor panel, refresh all translated texts (except for hardcoded ui)
      if (SAVE_LOADED_FLAG.value) {
        PLAYER_MAP.value.forEach((player, playerUId) => {
          fetchPlayerPal(playerUId);
        });
        fetchPlayerPal(PAL_BASE_WORKER_BTN.value);
      }
      if (!IS_LOCKED.value)
        fetchStaticData();
    } else if (response.status == 2) {
      alert("Unauthorized Access, Please Login. ");
      IS_LOCKED.value = true;
      reset();
    } else {
      alert(`- updateI18n - Error occured: ${response.msg}`);
    }
    if (!no_set_loading_flag) LOADING_FLAG.value = false;
  }

  async function fetchStaticData() {
    let no_set_loading_flag = LOADING_FLAG.value;
    if (!no_set_loading_flag) LOADING_FLAG.value = true;
    const passive_skills_raw = await GET("/api/save/passive_skills");
    if (passive_skills_raw === false) return;

    if (passive_skills_raw.status == 0) {
      PASSIVE_SKILLS.value = passive_skills_raw.data.dict;
      PASSIVE_SKILLS_LIST.value = passive_skills_raw.data.arr;
    } else if (passive_skills_raw.status == 2) {
      IS_LOCKED.value = true;
      reset();
    } else {
      alert(
        `- fetchStaticData:passive_skill - Error occured: ${passive_skills_raw.msg}`
      );
    }

    const active_skills_raw = await GET("/api/save/active_skills");
    if (active_skills_raw === false) return;

    if (active_skills_raw.status == 0) {
      ACTIVE_SKILLS.value = active_skills_raw.data.dict;
      ACTIVE_SKILLS_LIST.value = active_skills_raw.data.arr;
    } else if (active_skills_raw.status == 2) {
      IS_LOCKED.value = true;
      reset();
    } else {
      alert(
        `- fetchStaticData:active_skill - Error occured: ${active_skills_raw.msg}`
      );
    }

    const pal_data_raw = await GET("/api/save/pal_data");
    if (pal_data_raw === false) return;

    if (pal_data_raw.status == 0) {
      PAL_STATIC_DATA.value = pal_data_raw.data.dict;
      PAL_STATIC_DATA_LIST.value = pal_data_raw.data.arr;
    } else if (pal_data_raw.status == 2) {
      IS_LOCKED.value = true;
      reset();
    } else {
      alert(`- fetchStaticData:pal_data - Error occured: ${pal_data_raw.msg}`);
    }
    if (!no_set_loading_flag) LOADING_FLAG.value = false;
  }

  function reset() {
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

    // display data
    SELECTED_PAL_DATA.value = new Map();
    PAL_MAP.value = new Map();

    PLAYER_MAP.value.clear();
  }

  function getTranslatedText(translationKey) {
    const I18nKey = I18n.value || "en"

    if (TranslationKeyMap.value[I18nKey]) {
      const i18nData = TranslationKeyMap.value[I18n.value]
      return i18nData[translationKey] || "I18N_MISSING"
    }

    if (!I18nLoadingPromises[I18nKey]) {
      I18nLoadingPromises[I18nKey] = import(`../i18n/${I18nKey}.js`)
        .then(module => {
          console.log(`${I18nKey} imported`)
          TranslationKeyMap.value[I18nKey] = module.default
          delete I18nLoadingPromises[I18nKey]
        })
        .catch(error => {
          console.error(`Failed to load UI language file for ${I18nKey}, fallback to "en":`, error);
          if (TranslationKeyMap.value["en"]) {
            TranslationKeyMap.value[I18nKey] = TranslationKeyMap.value["en"]
            delete I18nLoadingPromises[I18nKey]
          } else {
            import(`../i18n/en.js`).then(module => {
                console.log(`en imported`)
                TranslationKeyMap.value[I18nKey] = module.default
                delete I18nLoadingPromises[I18nKey]
              })
          }
        })
    }

    return I18nLoadingPromises[I18nKey].then(() => {
      const i18nData = TranslationKeyMap.value[I18nKey];
      return i18nData?.translationKey || "I18N_MISSING";
    });
  }

  async function updatePlayer(e) {
    let no_set_loading_flag = LOADING_FLAG.value;
    if (!no_set_loading_flag) LOADING_FLAG.value = true;

    // sometimes we manually construct a "e" target in a very hacked way
    let key = e.target.name;
    let value = e.target.value;

    if (SELECTED_PLAYER_ID.value == null) {
      alert("Select a player first!");
      return;
    }

    // console.log(
    //   `Modify: Player: ${SELECTED_PLAYER_ID.value}, Target ${
    //     PLAYER_MAP.value.get(SELECTED_PLAYER_ID.value).name
    //   } key=${key}, value=${value}`
    // );

    const response = await PATCH("/api/player/player_data", {
      key: key,
      value: value,
      PlayerUId: SELECTED_PLAYER_ID.value,
    });
    if (response === false) return;

    if (response.status == 0) {
      await loadPlayer(SELECTED_PLAYER_ID.value);
    } else if (response.status == 2) {
      alert("Unauthorized Access, Please Login. ");
      IS_LOCKED.value = true;
      reset();
    } else {
      alert(`- updatePlayer - Error occured: ${response.msg}`);
    }
    if (!no_set_loading_flag) LOADING_FLAG.value = false;
  }

  async function loadPlayer(playerUId, updatePal = false) {
    let no_set_loading_flag = LOADING_FLAG.value;
    if (!no_set_loading_flag) LOADING_FLAG.value = true;

    if (SELECTED_PLAYER_ID.value == null) {
      alert("Select a player first!");
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
      await selectPlayer({ target: { value: playerUId } });

      // player id and pal data never changed so this is safe
      // if (!updatePal) await selectPal({ target: SELECTED_PAL_EL });
      if (!updatePal) await selectPal({ target: { value: pal_id_bk } }, true);
    } else if (response.status == 2) {
      alert("Unauthorized Access, Please Login. ");
      IS_LOCKED.value = true;
      reset();
    } else {
      alert(`- loadPlayer - Error occured: ${response.msg}`);
    }

    if (!no_set_loading_flag) LOADING_FLAG.value = false;
  }

  async function loadPlayers() {
    let no_set_loading_flag = LOADING_FLAG.value;
    if (!no_set_loading_flag) LOADING_FLAG.value = true;

    const response = await GET("/api/player/players_data", {
      ReadPath: PAL_GAME_SAVE_PATH.value,
    });
    if (response === false) return;

    if (response.status == 0) {
      if (response.data.hasWorkingPal) {
        HAS_WORKING_PAL_FLAG.value = true;
      }

      for (let player of response.data.players) {
        let p = new Player(player);
        PLAYER_MAP.value.set(p.id, p);
        // console.log(`Found player: ${p.name} - ${p.id}`);
      }

      if (PLAYER_MAP.value.size <= 0 && !HAS_WORKING_PAL_FLAG) {
        alert("No Player Found in the Gamesave");
      }
    } else if (response.status == 2) {
      alert("Unauthorized Access, Please Login. ");
      IS_LOCKED.value = true;
      reset();
    } else {
      alert(`- loadPlayers - Error occured: ${response.msg}`);
    }

    if (!no_set_loading_flag) LOADING_FLAG.value = false;
  }

  async function loadSave() {
    reset();

    let no_set_loading_flag = LOADING_FLAG.value;
    if (!no_set_loading_flag) LOADING_FLAG.value = true;

    await updateI18n();

    const response = await POST("/api/save/load", {
      ReadPath: PAL_GAME_SAVE_PATH.value,
    });
    if (response === false) return;

    if (response.status == 0) {
      await loadPlayers();
      await fetchStaticData();

      SAVE_LOADED_FLAG.value = true;

      // save path to localstorage
      localStorage.setItem("PAL_GAME_SAVE_PATH", PAL_GAME_SAVE_PATH.value);
      PAL_WRITE_BACK_PATH.value = PAL_GAME_SAVE_PATH.value;
    } else if (response.status == 2) {
      alert("Unauthorized Access, Please Login. ");
      IS_LOCKED.value = true;
      reset();
    } else {
      alert(`- loadSave - Error occured: ${response.msg}`);
    }
    if (!no_set_loading_flag) LOADING_FLAG.value = false;
  }

  async function writeSave() {
    let no_set_loading_flag = LOADING_FLAG.value;
    if (!no_set_loading_flag) LOADING_FLAG.value = true;
    const response = await POST("/api/save/save", {
      WritePath: PAL_WRITE_BACK_PATH.value,
    });
    if (response === false) return;

    if (response.status == 0) {
      alert(`Changes saved to ${PAL_WRITE_BACK_PATH.value}`);
      // YOU HAVE TO RELOAD FOR NOW, THIS HOW MY BACKEND WORKS.
      // loadSave()
    } else if (response.status == 2) {
      alert("Unauthorized Access, Please Login. ");
      IS_LOCKED.value = true;
      reset();
    } else {
      alert(`- writeSave - Error occured: ${response.msg}`);
    }
    if (!no_set_loading_flag) LOADING_FLAG.value = false;
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
      alert("Unauthorized Access, Please Login. ");
      IS_LOCKED.value = true;
      reset();
    } else {
      alert(`- fetchPlayerPal - Error occured: ${response.msg}`);
    }
    if (!no_set_loading_flag) LOADING_FLAG.value = false;
  }

  async function selectPlayer(e) {
    let no_set_loading_flag = LOADING_FLAG.value;
    if (!no_set_loading_flag) LOADING_FLAG.value = true;

    let playerUId = e.target.value;

    // clear selected playerId
    SELECTED_PLAYER_ID.value = null;
    BASE_PAL_BTN_CLK_FLAG.value = false;

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
    if (playerUId == PAL_BASE_WORKER_BTN.value)
      BASE_PAL_BTN_CLK_FLAG.value = true;
    else SELECTED_PLAYER_ID.value = playerUId;

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
        PLAYER_MAP.value.get(player).pals.set(pal_data.InstanceId, pal_data);
      }
    } else if (response.status == 2) {
      alert("Unauthorized Access, Please Login. ");
      IS_LOCKED.value = true;
      reset();
    } else {
      alert(`- fetchPlayerPal - Error occured: ${response.msg}`);
    }

    if (!no_set_loading_flag) LOADING_FLAG.value = false;
  }

  async function selectPal(e, manual = false) {
    let no_set_loading_flag = LOADING_FLAG.value;
    if (!no_set_loading_flag) LOADING_FLAG.value = true;

    // sometimes we manually construct a "e" target in a very hacked way
    if (!manual) {
      // SELECTED_PAL_EL = e.target;
      SELECTED_PAL_DATA.value = null;
      SELECTED_PAL_ID.value = null;
    }

    // set selected pal, and print out debug info
    let palId = e.target.value;
    let palData = PAL_MAP.value.get(palId);
    if (palData == null) {
      alert("Error selecting pal, try again or reload");
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
      rect.right <= (window.innerWidth || document.documentElement.clientWidth)
    );
  }

  async function updatePal(e) {
    let no_set_loading_flag = LOADING_FLAG.value;
    if (!no_set_loading_flag) LOADING_FLAG.value = true;

    // sometimes we manually construct a "e" target in a very hacked way
    let key = e.target.name;
    let value = e.target.value;

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
      await selectPal({ target: { value: SELECTED_PAL_ID.value } }, true);
      UPDATE_PAL_RESELECT_CTR.value++;
    } else if (response.status == 2) {
      alert("Unauthorized Access, Please Login. ");
      IS_LOCKED.value = true;
      reset();
    } else {
      alert(`- updatePal - Error occured: ${response.msg}`);
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
      alert("Pal Data Copied to Clipboard!");
      window.open("https://jsonformatter.curiousconcept.com/");
    } else if (response.status == 2) {
      alert("Unauthorized Access, Please Login. ");
      IS_LOCKED.value = true;
      reset();
    } else {
      alert(`- updatePal - Error occured: ${response.msg}`);
    }

    if (!no_set_loading_flag) LOADING_FLAG.value = false;
  }

  function isFilteredPal(pal) {
    if (!SHOW_UNREF_PAL_FLAG.value && pal.Is_Unref_Pal) {
      return true
    }
    if (SHOW_UNREF_PAL_FLAG.value && !pal.Is_Unref_Pal) {
      return true
    }

    // if (SHOW_OOB_PAL_FLAG.value && pal.in_owner_palbox) {
    //   return true
    // }

    if (!SHOW_OOB_PAL_FLAG.value && !pal.in_owner_palbox) {
      return true
    }

    if (PAL_LIST_SEARCH_KEYWORD.value && 
      !pal.DisplayName.toLowerCase().includes(PAL_LIST_SEARCH_KEYWORD.value.toLowerCase())) {
      return true
    }
    
    return false
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
      const nextNode = getNextElement(PAL_MAP.value, SELECTED_PAL_ID.value);
      PAL_MAP.value.delete(SELECTED_PAL_DATA.value.InstanceId);
      SELECTED_PAL_ID.value = null;
      // SELECTED_PAL_EL = null;
      SELECTED_PAL_DATA.value = null;
      // ADD_PAL_RESELECT_CTR.value++;
      if (nextNode) {
        SELECTED_PAL_ID.value = nextNode.key;
      }
    } else if (response.status == 2) {
      alert("Unauthorized Access, Please Login. ");
      IS_LOCKED.value = true;
      reset();
    } else {
      alert(`- delPal - Error occured: ${response.msg}`);
    }

    if (!no_set_loading_flag) LOADING_FLAG.value = false;
  }

  async function addPal() {
    let no_set_loading_flag = LOADING_FLAG.value;
    if (!no_set_loading_flag) LOADING_FLAG.value = true;
    const PlayerUId = GET_PAL_OWNER_API_ID();
    if (PlayerUId == PAL_BASE_WORKER_BTN.value) {
      alert("Adding pals to basecamp is unsupported!");
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
      SELECTED_PAL_ID.value = pal_data.InstanceId;
      SELECTED_PAL_DATA.value = pal_data;
    } else if (response.status == 2) {
      alert("Unauthorized Access, Please Login. ");
      IS_LOCKED.value = true;
      reset();
    } else {
      alert(`- delPal - Error occured: ${response.msg}`);
    }

    if (!no_set_loading_flag) LOADING_FLAG.value = false;
  }

  async function dupePal() {
    let no_set_loading_flag = LOADING_FLAG.value;
    if (!no_set_loading_flag) LOADING_FLAG.value = true;
    const PlayerUId = GET_PAL_OWNER_API_ID();
    if (PlayerUId == PAL_BASE_WORKER_BTN.value) {
      alert("Adding pals to basecamp is unsupported!");
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
      alert("Unauthorized Access, Please Login. ");
      IS_LOCKED.value = true;
      reset();
    } else {
      alert(`- delPal - Error occured: ${response.msg}`);
    }

    if (!no_set_loading_flag) LOADING_FLAG.value = false;
  }

  function displayPalElement(DataAccessKey) {
    const els = PAL_STATIC_DATA.value[DataAccessKey]?.Elements;
    if (!els) return
    
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
      Ground: "🪨",
      Ice: "❄️",
      Electric: "⚡",
      Neutral: "🔵",
      Dark: "🌑",
    };
    return elementEmojis[element] || "";
  }

  function skillIcon(atk) {
    if (ACTIVE_SKILLS.value[atk]?.IsUniqueSkill) return "✨";
    if (ACTIVE_SKILLS.value[atk]?.HasSkillFruit) return "🍐";
    return ""
  }

  function displayRating(rating) {
    if (rating === undefined) return ""
    if (rating < 0) return "🔴";
    if (rating > 1) return "🟡";
    return "⚪";
  }

  return {
    PAL_PASSIVE_SELECTED_ITEM,
    PAL_ACTIVE_SELECTED_ITEM,
    PAL_BASE_WORKER_BTN,
    PLAYER_MAP,
    PAL_MAP,
    SELECTED_PLAYER_ID,
    SELECTED_PAL_ID,
    SELECTED_PAL_DATA,
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

    PATH_CONTEXT,
    SHOW_FILE_PICKER,
    PAL_FILE_PICKER_PATH,
    IS_PAL_SAVE_PATH,

    HAS_WORKING_PAL_FLAG,
    BASE_PAL_BTN_CLK_FLAG,
    PAL_GAME_SAVE_PATH,
    PAL_WRITE_BACK_PATH,
    I18n,
    I18nList,
    PAL_STATIC_DATA,
    PAL_STATIC_DATA_LIST,
    PASSIVE_SKILLS,
    PASSIVE_SKILLS_LIST,
    ACTIVE_SKILLS,
    ACTIVE_SKILLS_LIST,

    getTranslatedText,
    
    isElementInViewport,
    isFilteredPal,

    displayPalElement,
    displayElement,
    skillIcon,
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

    login,
    auth,
    show_file_picker,
    update_picker_result,
    path_back
  };
});
