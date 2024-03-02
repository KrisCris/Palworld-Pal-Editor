import { ref, computed, reactive } from "vue";
import { defineStore } from "pinia";
import axios from "axios";

export const usePalEditorStore = defineStore("paleditor", () => {
  class Player {
    constructor(obj) {
      this.id = obj.id;
      this.name = obj.name;
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
      this.Gender = obj.Gender;
      this.HasWorkerSick = obj.HasWorkerSick;

      this.ComputedDefense = obj.ComputedDefense;
      this.ComputedAttack = obj.ComputedAttack;
      this.ComputedCraftSpeed = obj.ComputedCraftSpeed;
      this.MaxHP = obj.MaxHP;

      this.MasteredWaza = obj.MasteredWaza;
      this.PassiveSkillList = obj.PassiveSkillList;

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
    }

    displaySpecialType() {
      if (this.IsTower) return "🗼";
      if (this.IsBOSS) return "💀";
      if (this.IsRarePal) return "✨";
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

    removePassiveSkill(e) {
      const skill = e.target.name;
      updatePal({
        target: {
          name: "DelPassiveSkill",
          value: skill,
        },
      });
    }

    addPassiveSkill() {
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
          name: "AddPassiveSkill",
          value: skill,
        },
      });
    }

    removeActiveSkill(e) {
      const skill = e.target.name;
      updatePal({
        target: {
          name: "DelActiveSkill",
          value: skill,
        },
      });
    }

    addActiveSkill() {
      const skill = PAL_ACTIVE_SELECTED_ITEM.value;
      if (!ACTIVE_SKILLS.value[skill]) {
        alert("Select a skill first!");
        return;
      }
      updatePal({
        target: {
          name: "AddActiveSkill",
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
  const I18nList = ref({
    en: "English",
    "zh-CN": "中文",
  });

  // flags
  const LOADING_FLAG = ref(false);
  const SAVE_LOADED_FLAG = ref(false);
  const HAS_WORKING_PAL_FLAG = ref(false);
  const BASE_PAL_BTN_CLK_FLAG = ref(false);

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

  // selected pal EL, only for the use of scrollTo when out of window
  let SELECTED_PAL_EL = null;

  // Configs
  const I18n = ref(localStorage.getItem("PAL_I18n"));
  const PAL_GAME_SAVE_PATH = ref(localStorage.getItem("PAL_GAME_SAVE_PATH"));
  const HAS_PASSWORD = ref(false);
  const PAL_WRITE_BACK_PATH = ref("");

  // auth
  let auth_token = "";
  const IS_LOCKED = ref(true);

  async function get(api) {
    try {
      const response = await axios.get(api, {
        headers: {
          Authorization: "Bearer " + auth_token,
        },
      });

      console.log(response.data);
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

  async function post(api, data) {
    try {
      const response = await axios.post(api, data, {
        headers: { Authorization: "Bearer " + auth_token },
      });

      console.log(response.data);
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

  async function patch(api, data) {
    try {
      const response = await axios.patch(api, data, {
        headers: { Authorization: "Bearer " + auth_token },
      });

      console.log(response.data);
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
    
    const response = await get("/api/auth/auth");
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
    
    const response = await post("/api/auth/login", {
      password: e.target.value,
    });
    if (response === false) return;

    if (response.status == 0) {
      IS_LOCKED.value = false;
      auth_token = response.data.access_token;
    } else if (response.status == 2) {
      alert("Wrong Password, Try Again.");
      IS_LOCKED.value = true;
    } else {
      alert(`- login - Error occured: ${response.msg}`);
    }

    if (!no_set_loading_flag) LOADING_FLAG.value = false;
  }

  async function fetch_config() {
    let no_set_loading_flag = LOADING_FLAG.value;
    if (!no_set_loading_flag) LOADING_FLAG.value = true;
    
    const response = await get("/api/save/fetch_config");
    if (response === false) return;

    if (response.status == 0) {
      if (!I18n.value) {
        I18n.value = response.data.I18n;
      }
      if (!PAL_GAME_SAVE_PATH.value) {
        PAL_GAME_SAVE_PATH.value = response.data.Path;
      }
      HAS_PASSWORD.value = response.data.HasPassword;
      console.log(I18n.value, PAL_GAME_SAVE_PATH.value, HAS_PASSWORD.value);
    } else if (response.status == 2) {
      alert("Unauthorized Access, Please Login. ");
      IS_LOCKED.value = true;
    } else {
      alert("- fetch_config - Error occured: ", response.msg);
    }

    if (!no_set_loading_flag) LOADING_FLAG.value = false;
  }

  async function updateI18n() {
    let no_set_loading_flag = LOADING_FLAG.value;
    if (!no_set_loading_flag) LOADING_FLAG.value = true;

    const response = await patch("/api/save/i18n", { I18n: I18n.value });
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
      fetchStaticData();
    } else if (response.status == 2) {
      alert("Unauthorized Access, Please Login. ");
      IS_LOCKED.value = true;
    } else {
      alert(`- updateI18n - Error occured: ${response.msg}`);
    }
    if (!no_set_loading_flag) LOADING_FLAG.value = false;
  }

  async function fetchStaticData() {
    let no_set_loading_flag = LOADING_FLAG.value;
    if (!no_set_loading_flag) LOADING_FLAG.value = true;
    const passive_skills_raw = await get("/api/save/passive_skills");
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

    const active_skills_raw = await get("/api/save/active_skills");
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

    const pal_data_raw = await get("/api/save/pal_data");
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

    PLAYER_MAP.value.clear();
  }

  async function loadSave() {
    reset();

    let no_set_loading_flag = LOADING_FLAG.value;
    if (!no_set_loading_flag) LOADING_FLAG.value = true;

    await updateI18n();

    const response = await post("/api/save/load", {
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
        console.log(`Found player: ${p.name} - ${p.id}`);
      }

      if (PLAYER_MAP.value.size <= 0 && !HAS_WORKING_PAL_FLAG) {
        alert("No Player Found in the Gamesave");
      }

      await fetchStaticData();

      SAVE_LOADED_FLAG.value = true;

      // save path to localstorage
      localStorage.setItem("PAL_GAME_SAVE_PATH", PAL_GAME_SAVE_PATH.value);
      PAL_WRITE_BACK_PATH.value = PAL_GAME_SAVE_PATH.value;
    } else if (response.status == 2) {
      alert("Unauthorized Access, Please Login. ");
      IS_LOCKED.value = true;
    } else {
      alert(`- loadSave - Error occured: ${response.msg}`);
    }
    if (!no_set_loading_flag) LOADING_FLAG.value = false;
  }

  async function writeSave() {
    let no_set_loading_flag = LOADING_FLAG.value;
    if (!no_set_loading_flag) LOADING_FLAG.value = true;
    const response = await post("/api/save/save", {
      WritePath: PAL_WRITE_BACK_PATH.value,
    });
    if (response === false) return;

    if (response.status == 0) {
      alert(`Changes saved to ${PAL_WRITE_BACK_PATH.value}`);
    } else if (response.status == 2) {
      alert("Unauthorized Access, Please Login. ");
      IS_LOCKED.value = true;
    } else {
      alert(`- writeSave - Error occured: ${response.msg}`);
    }
    if (!no_set_loading_flag) LOADING_FLAG.value = false;
  }

  async function fetchPlayerPal(playerUId) {
    let no_set_loading_flag = LOADING_FLAG.value;
    if (!no_set_loading_flag) LOADING_FLAG.value = true;
    const response = await post("/api/player/player_pals", {
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
        console.log(
          `Pal Loaded: ${pal_data.DisplayName} - ${pal_data.InstanceId}`
        );
      }
    } else if (response.status == 2) {
      alert("Unauthorized Access, Please Login. ");
      IS_LOCKED.value = true;
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

    const response = await post("/api/pal/paldata", {
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
      SELECTED_PAL_EL = e.target;
      SELECTED_PAL_DATA.value = null;
      SELECTED_PAL_ID.value = null;
    }

    // set selected pal, and print out debug info
    let palId = e.target.value;
    let palData = PAL_MAP.value.get(palId);
    console.log(`Pal ${palData.DisplayName} - ${palData.InstanceId} selected.`);

    await fetchPalData(
      // get player id, or BASE INDICATION STR
      GET_PAL_OWNER_API_ID(),
      palId
    );

    // Update selected pal id and pal data
    SELECTED_PAL_DATA.value = PAL_MAP.value.get(palId);
    SELECTED_PAL_ID.value = SELECTED_PAL_DATA.value.InstanceId;

    // Scroll to selected pal
    if (!isElementInViewport(SELECTED_PAL_EL)) {
      SELECTED_PAL_EL.scrollIntoView({ behavior: "smooth" });
    }

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

    console.log(
      `Modify: PalOwner: ${GET_PAL_OWNER_API_ID()}, Target ${SELECTED_PAL_DATA.value.DisplayName} key=${key}, value=${value}`
    );

    const response = await patch("/api/pal/paldata", {
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
    } else if (response.status == 2) {
      alert("Unauthorized Access, Please Login. ");
      IS_LOCKED.value = true;
    } else {
      alert(`- updatePal - Error occured: ${response.msg}`);
    }
    if (!no_set_loading_flag) LOADING_FLAG.value = false;
  }

  function GET_PAL_OWNER_API_ID() {
    return BASE_PAL_BTN_CLK_FLAG.value
      ? PAL_BASE_WORKER_BTN.value
      : SELECTED_PLAYER_ID.value
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

    IS_LOCKED,
    HAS_PASSWORD,

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
    updateI18n,
    loadSave,
    selectPlayer,
    selectPal,
    updatePal,
    writeSave,
    fetch_config,

    login,
    auth,
  };
});
