import { ref, computed, reactive } from "vue";
import { defineStore } from "pinia";

class Player{
  constructor(obj) {
    this.id = obj.id;
    this.name = obj.name;
  }
}

class PalMeta {
  constructor(obj) {
    this.InstanceId = obj.InstanceId
    this.I18nName = obj.I18nName
    this.DisplayName = obj.DisplayName
    this.Gender = obj.Gender
    this.IsBOSS = obj.IsBOSS
    this.IsRarePal = obj.IsRarePal
    this.IsTower = obj.IsTower
    this.Level = obj.Level
    this.DataAccessKey = obj.DataAccessKey
    this.IconAccessKey = obj.IconAccessKey
  }
}

class PalAttributes {
  constructor(obj) {
    this.displayName = obj.displayName;
    this.level = obj.level;
    this.passives = obj.passives;
    this.masteredWaza = obj.masteredWaza;
  }
}

export const usePalEditorStore = defineStore("paleditor", () => {
  const msg = ref("");

  // flags
  const loading_flag = ref(false);
  const saveLoaded = ref(false);

  // data
  const palMap = ref(new Map());
  const playerMap = ref(new Map());

  // selected id
  const selectedPlayerId = ref(null);
  const selectedPalId = ref(null);

  // save path
  const palSavePath = ref(localStorage.getItem("palSavePath") || "");

  // const specie = computed(() => palData[palRawSpecieName.value])

  async function loadSave() {
    loading_flag.value = true
    const response = await fetch("/api/save/load", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ SavePath: palSavePath.value }),
    }).then((r) => r.json());
    loading_flag.value = false

    if (response.status != 0) {
      alert("Error Occured:\n" + response.msg);
      return;
    }

    playerMap.value.clear()
    for (let player of response.data) {
      let p = new Player(player)
      playerMap.value.set(p.id, p)
      console.log(`Found player: ${p.name} - ${p.id}`)
    }

    if (playerMap.value.size <= 0) {
      alert("No Player Found in the Gamesave")
    }
    saveLoaded.value = true
    localStorage.setItem("palSavePath", palSavePath.value)
  }

  async function selectPlayer(e) {
    let value = e.target.value
    let player = playerMap.value.get(value)
    if (player == undefined) {
      alert(`selected player ${value} is undefined...`)
      return;
    }
    console.log(`Player ${player.id} - ${player.name} selected.`)

    selectedPlayerId.value = null // clear selected playerId
    palMap.value.clear() // clear palbox
    loading_flag.value = true // set loading
    const response = await fetch("/api/player/player_pals", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ PlayerUId: player.id }),
    }).then((r) => r.json());
    loading_flag.value = false
    if (response.status != 0) {
      alert("Error Occured:\n" + response.msg);
      return;
    }

    // fill new palbox
    for (let pal of response.data) {
      let pal_meta = new PalMeta(pal)
      palMap.value.set(pal_meta.InstanceId, pal_meta)
      console.log(`Pal Loaded: ${pal_meta.DisplayName} - ${pal_meta.InstanceId}`)
    }
    selectedPlayerId.value = player.id // new player selected
  }

  return { playerMap, palMap, selectedPlayerId, selectedPalId, loading_flag, saveLoaded, palSavePath, loadSave, selectPlayer };
});
