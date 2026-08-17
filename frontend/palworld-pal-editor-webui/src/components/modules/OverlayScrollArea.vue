<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'

defineProps({
  fitContent: { type: Boolean, default: false },
})

const root = ref(null)
const track = ref(null)
const thumb = ref(null)
const dragging = ref(false)
const thumbHeight = ref(0)
const thumbTop = ref(0)
const scrollable = ref(false)

let viewport = null
let resizeObserver = null
let mutationObserver = null
let scheduledFrame = 0
let dragStartY = 0
let dragStartScrollTop = 0

const thumbStyle = computed(() => ({
  height: `${thumbHeight.value}px`,
  transform: `translateY(${thumbTop.value}px)`,
}))

function updateMetrics() {
  scheduledFrame = 0
  if (!viewport || !track.value) return

  const maxScrollTop = viewport.scrollHeight - viewport.clientHeight
  const trackHeight = track.value.clientHeight
  scrollable.value = maxScrollTop > 1 && trackHeight > 0
  if (!scrollable.value) {
    thumbHeight.value = 0
    thumbTop.value = 0
    return
  }

  const nextThumbHeight = Math.max(24, trackHeight * viewport.clientHeight / viewport.scrollHeight)
  const maxThumbTop = Math.max(0, trackHeight - nextThumbHeight)
  thumbHeight.value = nextThumbHeight
  thumbTop.value = maxScrollTop ? maxThumbTop * viewport.scrollTop / maxScrollTop : 0
}

function scheduleMetrics() {
  if (scheduledFrame) return
  scheduledFrame = requestAnimationFrame(updateMetrics)
}

function scrollFromTrackPointer(clientY) {
  if (!viewport || !track.value || !scrollable.value) return
  const trackRect = track.value.getBoundingClientRect()
  const maxThumbTop = Math.max(0, trackRect.height - thumbHeight.value)
  const maxScrollTop = viewport.scrollHeight - viewport.clientHeight
  const nextThumbTop = Math.min(maxThumbTop, Math.max(0, clientY - trackRect.top - thumbHeight.value / 2))
  viewport.scrollTop = maxThumbTop ? nextThumbTop / maxThumbTop * maxScrollTop : 0
}

function onTrackPointerDown(event) {
  if (event.button !== 0 || event.target !== track.value) return
  event.preventDefault()
  scrollFromTrackPointer(event.clientY)
}

function beginDrag(event) {
  if (event.button !== 0 || !viewport) return
  event.preventDefault()
  dragging.value = true
  dragStartY = event.clientY
  dragStartScrollTop = viewport.scrollTop
  event.currentTarget.setPointerCapture?.(event.pointerId)
}

function dragThumb(event) {
  if (!dragging.value || !viewport || !track.value) return
  const maxThumbTop = Math.max(0, track.value.clientHeight - thumbHeight.value)
  const maxScrollTop = viewport.scrollHeight - viewport.clientHeight
  viewport.scrollTop = dragStartScrollTop + (event.clientY - dragStartY) / Math.max(1, maxThumbTop) * maxScrollTop
}

function endDrag(event) {
  if (!dragging.value) return
  dragging.value = false
  event.currentTarget.releasePointerCapture?.(event.pointerId)
}

function refresh() {
  nextTick(scheduleMetrics)
}

defineExpose({ refresh })

onMounted(() => {
  viewport = root.value?.querySelector('.overlay-scroll-area__viewport') || null
  if (!viewport) return

  viewport.addEventListener('scroll', scheduleMetrics, { passive: true })
  viewport.addEventListener('load', scheduleMetrics, true)
  resizeObserver = typeof ResizeObserver === 'undefined' ? null : new ResizeObserver(scheduleMetrics)
  resizeObserver?.observe(root.value)
  resizeObserver?.observe(viewport)
  mutationObserver = typeof MutationObserver === 'undefined' ? null : new MutationObserver(scheduleMetrics)
  mutationObserver?.observe(viewport, { childList: true, subtree: true, characterData: true })
  scheduleMetrics()
})

onBeforeUnmount(() => {
  if (scheduledFrame) cancelAnimationFrame(scheduledFrame)
  viewport?.removeEventListener('scroll', scheduleMetrics)
  viewport?.removeEventListener('load', scheduleMetrics, true)
  resizeObserver?.disconnect()
  mutationObserver?.disconnect()
})
</script>

<template>
  <div ref="root" :class="['overlay-scroll-area', { 'is-dragging': dragging, 'is-fit-content': fitContent }]">
    <slot />
    <span ref="track" :class="['overlay-scroll-area__track', { 'is-scrollable': scrollable }]" aria-hidden="true"
      @pointerdown="onTrackPointerDown">
      <span ref="thumb" class="overlay-scroll-area__thumb" :style="thumbStyle"
        @pointerdown.stop="beginDrag" @pointermove="dragThumb" @pointerup="endDrag" @pointercancel="endDrag" />
    </span>
  </div>
</template>

<style scoped>
.overlay-scroll-area {
  position: relative;
  width: 100%;
  height: 100%;
  min-width: 0;
  min-height: 0;
  overflow: hidden;
}

.overlay-scroll-area :deep(.overlay-scroll-area__viewport) {
  width: 100%;
  height: 100%;
  box-sizing: border-box;
  scrollbar-width: none;
}

.overlay-scroll-area.is-fit-content {
  height: auto;
}

.overlay-scroll-area.is-fit-content :deep(.overlay-scroll-area__viewport) {
  height: auto;
  max-height: inherit;
}

.overlay-scroll-area :deep(.overlay-scroll-area__viewport::-webkit-scrollbar) {
  display: none;
  width: 0;
  height: 0;
}

.overlay-scroll-area__track {
  position: absolute;
  z-index: 4;
  top: 3px;
  right: 2px;
  bottom: 3px;
  width: 8px;
  border-radius: 999px;
  background: transparent;
  opacity: 0;
  pointer-events: none;
  transition: opacity .14s ease;
}

.overlay-scroll-area:hover > .overlay-scroll-area__track.is-scrollable,
.overlay-scroll-area:focus-within > .overlay-scroll-area__track.is-scrollable,
.overlay-scroll-area.is-dragging > .overlay-scroll-area__track.is-scrollable {
  opacity: 1;
  pointer-events: auto;
}

.overlay-scroll-area__thumb {
  position: absolute;
  top: 0;
  right: 1px;
  left: 1px;
  min-height: 24px;
  border-radius: 999px;
  background: rgb(160 160 165 / 72%);
  box-shadow: 0 0 0 1px rgb(0 0 0 / 24%);
  cursor: grab;
  touch-action: none;
}

.overlay-scroll-area__thumb:hover {
  background: #c4c4ca;
}

.overlay-scroll-area__thumb:active {
  cursor: grabbing;
}
</style>
