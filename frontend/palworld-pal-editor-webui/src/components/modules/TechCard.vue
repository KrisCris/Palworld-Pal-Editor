<template>
    <div :class="['tech', { bossTech: item.BossTechnology }, { locked: isLocked }]" :style="bgStyle"
        @click="toggleLock">
        <div class="techHeader">{{ item.I18n.Type ?? "⚠️ INVALID" }}</div>
        <div class="techFooter">{{ item.I18n.Name ?? item.internalName }}</div>
    </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { usePalEditorStore } from '@/stores/paleditor'
const palStore = usePalEditorStore()

const props = defineProps({
    item: {
        type: Object,
        required: true
    }
})

function toggleLock() {
    palStore.SELECTED_PLAYER_DATA.toggleTech(props.item.InternalName, isLocked.value)
}

const bgStyle = computed(() => {
    let internalName = props.item.InternalName;
    const cat = internalName.split('_')[0] == "SkillUnlock" ? "pals" : "tech";
    if (cat == "pals") {
        internalName = internalName.replace("SkillUnlock_", "")
    }
    return {
        backgroundImage: `url('/image/${cat}/${internalName}')`
    }
})

const isLocked = computed(() => {
    return !palStore.SELECTED_PLAYER_DATA.UnlockedRecipeTechnologyNames.includes(props.item.InternalName)
})

</script>

<style scoped>
.tech {
    min-width: 8rem;
    max-width: 8rem;
    min-height: 10rem;
    max-width: 10rem;
    background-position: center;
    background-size: 90px 90px;
    background-repeat: no-repeat;
    position: relative;
    box-shadow: 3px 3px 3px rgb(0, 0, 0);
    background-color: #1455a4;
    margin: 8px;
    cursor: pointer;
}

.tech.bossTech {
    background-color: #6b2f77;
    border-color: #b74fff;
}

.tech.locked {
    filter: grayscale(100%);
}

.techHeader {
    position: absolute;
    top: 0;
    width: 100%;
    text-align: center;
    background-color: rgba(0, 0, 0, 0.6);
    color: #fff;
    font-size: small;
    padding: 2px 0;
}

.techFooter {
    position: absolute;
    bottom: 0;
    width: 100%;
    text-align: center;
    background-color: rgba(0, 0, 0, 0.2);
    text-shadow: -1px 0 black, 0 1px black, 1px 0 black, 0 -1px black;
    font-size: small;
    color: #fff;
    padding: 2px 0;
}
</style>