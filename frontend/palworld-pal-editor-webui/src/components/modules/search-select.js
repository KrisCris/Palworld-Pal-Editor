const normalized = value => String(value ?? '').trim().toLocaleLowerCase()

export const filterSearchOptions = (options, query) => {
  const needle = normalized(query)
  if (!needle) return options
  return options.filter(option => [option.label, option.description, option.meta, option.searchMeta, option.value]
    .some(value => normalized(value).includes(needle)))
}

export const closeDisclosureOnOutsidePointer = (disclosure, target) => {
  if (disclosure?.open && !disclosure.contains(target)) disclosure.open = false
}

// Where a reopened option list has to sit for its current selection to be on
// screen. A dropdown of several hundred passives that always opens at the top
// does not show what the control is set to, and the option it is set to is the
// one the reader came back to look at.
//
// `null` means leave the scroll alone: nothing is selected, or the list is short
// enough to show whole. An option already in view is answered with the offset it
// already has, so reopening never shuffles rows under the pointer.
export const scrollOffsetForOption = (viewport, option) => {
  if (!viewport || !option) return null
  const maxOffset = viewport.scrollHeight - viewport.clientHeight
  if (maxOffset <= 0) return null

  const offset = viewport.scrollTop || 0
  const top = option.offsetTop
  const bottom = top + option.offsetHeight
  if (top >= offset && bottom <= offset + viewport.clientHeight) return offset

  const centred = top + option.offsetHeight / 2 - viewport.clientHeight / 2
  return Math.round(Math.min(Math.max(centred, 0), maxOffset))
}
