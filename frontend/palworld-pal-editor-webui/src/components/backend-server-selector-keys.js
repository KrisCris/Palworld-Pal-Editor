export function moveRecentFocus(event, actions) {
    const step = event.key === "ArrowDown" ? 1 : event.key === "ArrowUp" ? -1 : 0;
    if (!step || !actions.length) return false;
    event.preventDefault();
    const index = actions.indexOf(event.currentTarget);
    actions[(index + step + actions.length) % actions.length]?.focus();
    return true;
}
