import { ref, computed, reactive } from "vue";
import { defineStore } from "pinia";

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
    this.MasteredWaza = obj.MasteredWaza;
    this.PassiveSkillList = obj.PassiveSkillList;
    this.ComputedDefense = obj.ComputedDefense;
    this.ComputedAttack = obj.ComputedAttack;
    this.MaxHP = obj.MaxHP;
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
    this.DisplayName = obj.DisplayName;
    this.I18nName = obj.I18nName;
    this.DataAccessKey = obj.DataAccessKey;
    this.IconAccessKey = obj.IconAccessKey;
    this.OwnerName = obj.OwnerName;
    this.OwnerPlayerUId = obj.OwnerPlayerUId;
    this.InstanceId = obj.InstanceId;

    this.dirty = false;
  }
}

export const usePalEditorStore = defineStore("paleditor", () => {
  const PAL_BASE_WORKER_BTN = ref("PAL_BASE_WORKER_BTN");
  const msg = ref("");

  // flags
  const LOADING_FLAG = ref(false);
  const SAVE_LOADED_FLAG = ref(false);
  const HAS_WORKING_PAL_FLAG = ref(false);
  const BASE_PAL_BTN_CLK_FLAG = ref(false);

  // data
  const BASE_PAL_MAP = ref(new Map());
  const PLAYER_MAP = ref(new Map());
  // display data
  const PAL_MAP = ref();
  const SELECTED_PAL_DATA = ref();

  // selected id
  const SELECTED_PLAYER_ID = ref(null);
  const SELECTED_PAL_ID = ref(null);

  // save path
  const PAL_SAVE_PATH = ref(localStorage.getItem("PAL_SAVE_PATH") || "");

  // EDIT PAL INFO

  // const specie = computed(() => palData[palRawSpecieName.value])

  function reset_flags() {
    LOADING_FLAG.value = false;
    HAS_WORKING_PAL_FLAG.value = false;
    SAVE_LOADED_FLAG.value = false;
    BASE_PAL_BTN_CLK_FLAG.value = false;
    SELECTED_PAL_ID.value = null;
    SELECTED_PLAYER_ID.value = null;
  }

  async function loadSave() {
    reset_flags();
    LOADING_FLAG.value = true;
    const response = await fetch("/api/save/load", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ SavePath: PAL_SAVE_PATH.value }),
    })
      .then((r) => r.json())
      .catch((error) => {
        alert("Error occured, please check backend:", error);
        LOADING_FLAG = false;
      });

    LOADING_FLAG.value = false;

    if (response.status != 0) {
      alert("Error Occured:\n" + response.msg);
      return;
    }

    if (response.data.hasWorkingPal) {
      HAS_WORKING_PAL_FLAG.value = true;
    }

    PLAYER_MAP.value.clear();
    for (let player of response.data.players) {
      let p = new Player(player);
      PLAYER_MAP.value.set(p.id, p);
      console.log(`Found player: ${p.name} - ${p.id}`);
    }

    if (PLAYER_MAP.value.size <= 0 && !HAS_WORKING_PAL_FLAG) {
      alert("No Player Found in the Gamesave");
    }
    SAVE_LOADED_FLAG.value = true;
    localStorage.setItem("PAL_SAVE_PATH", PAL_SAVE_PATH.value);
  }

  async function updatePlayerPalList(playerUId) {
    const response = await fetch("/api/player/player_pals", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        PlayerUId: playerUId,
      }),
    })
      .then((r) => r.json())
      .catch((error) => {
        return error;
      });
    if (response.status != 0) {
      return response.msg;
    }

    let map =
      playerUId == PAL_BASE_WORKER_BTN.value
        ? BASE_PAL_MAP.value
        : PLAYER_MAP.value.get(playerUId).pals;
    map.clear();
    for (let pal of response.data) {
      let pal_data = new PalData(pal);
      map.set(pal_data.InstanceId, pal_data);
      console.log(
        `Pal Loaded: ${pal_data.DisplayName} - ${pal_data.InstanceId}`
      );
    }
    return true;
  }

  async function selectPlayer(e) {
    let playerUId = e.target.value;

    LOADING_FLAG.value = true; // set loading
    SELECTED_PLAYER_ID.value = null; // clear selected playerId
    BASE_PAL_BTN_CLK_FLAG.value = false;
    // clear pal selection
    SELECTED_PAL_ID.value = null;
    SELECTED_PAL_DATA.value = null;

    // if data not present
    if (
      (playerUId == PAL_BASE_WORKER_BTN.value && BASE_PAL_MAP.value.size == 0) ||
      (playerUId != PAL_BASE_WORKER_BTN.value &&
        PLAYER_MAP.value.get(playerUId).pals.size == 0)
    ) {
      let retval = await updatePlayerPalList(playerUId);
      if (retval !== true) {
        alert("error occured, check backend terminal", retval);
      }
    }
    LOADING_FLAG.value = false;
    PAL_MAP.value =
      playerUId == PAL_BASE_WORKER_BTN.value
        ? BASE_PAL_MAP.value
        : PLAYER_MAP.value.get(playerUId).pals;
    if (playerUId == PAL_BASE_WORKER_BTN.value) BASE_PAL_BTN_CLK_FLAG.value = true;
    else SELECTED_PLAYER_ID.value = playerUId;
  }

  async function updatePalData(player, pal) {
    const response = await fetch("/api/pal/paldata", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        PlayerUId: player,
        InstanceId: pal,
      }),
    })
      .then((r) => r.json())
      .catch((error) => {
        return error;
      });
    
    if (response.status != 0) {
      return response.msg
    }
    let pal_data = new PalData(response.data)
    if (player == PAL_BASE_WORKER_BTN.value) BASE_PAL_MAP.value.set(pal_data.InstanceId, pal_data)
    else PLAYER_MAP.value.get(player).pals.set(pal_data.InstanceId, pal_data)
    return true;
  }

  async function selectPal(e) {
    let palid = e.target.value;
    let pal_data = PAL_MAP.value.get(palid);
    console.log(
      `Pal ${pal_data.DisplayName} - ${pal_data.InstanceId} selected.`
    );

    SELECTED_PAL_DATA.value = null;
    SELECTED_PAL_ID.value = null;

    if (!pal_data.dirty) {
      let retval = await updatePalData(
        BASE_PAL_BTN_CLK_FLAG.value
          ? PAL_BASE_WORKER_BTN.value
          : SELECTED_PLAYER_ID.value,
        palid
      );
      if (retval !== true) {
        alert("Error on selecting pal, check backend log: ", retval);
      }
    }

    SELECTED_PAL_DATA.value = PAL_MAP.value.get(palid);
    SELECTED_PAL_ID.value = SELECTED_PAL_DATA.value.InstanceId;
  }

  return {
    PAL_BASE_WORKER_BTN,
    PLAYER_MAP,
    PAL_MAP,
    SELECTED_PLAYER_ID,
    SELECTED_PAL_ID,
    SELECTED_PAL_DATA,
    LOADING_FLAG,
    SAVE_LOADED_FLAG,
    HAS_WORKING_PAL_FLAG,
    BASE_PAL_BTN_CLK_FLAG,
    PAL_SAVE_PATH,
    loadSave,
    selectPlayer,
    selectPal,
  };
});
