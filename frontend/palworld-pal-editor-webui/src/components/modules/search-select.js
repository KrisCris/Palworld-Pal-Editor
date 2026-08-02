const normalized = value => String(value ?? '').trim().toLocaleLowerCase()

export const filterSearchOptions = (options, query) => {
  const needle = normalized(query)
  if (!needle) return options
  return options.filter(option => [option.label, option.description, option.meta, option.value]
    .some(value => normalized(value).includes(needle)))
}

export const closeDisclosureOnOutsidePointer = (disclosure, target) => {
  if (disclosure?.open && !disclosure.contains(target)) disclosure.open = false
}
