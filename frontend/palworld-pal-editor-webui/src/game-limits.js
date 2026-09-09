// The ceilings the editor holds a value to.
//
// Two kinds, and the difference is the point. `MAX_LEVEL`, `MAX_SOULS_LEVEL`,
// `MAX_SUITABILITY_LEVEL` and `MAX_FRIENDSHIP_LEVEL` are the game's own limits,
// and are what a value is held to while `HIDE_INVALID_OPTIONS` is on.
// `MAX_INVALID_LEVEL` is not a game limit at all: it is how far the editor will
// still go once the user has turned that off, and the game's behaviour past its
// own ceiling is nobody's promise.
//
// They are plain constants rather than store state because nothing changes them,
// and both the stores and the controls need to say the same number.

export const MAX_LEVEL = 80;
export const MAX_INVALID_LEVEL = 100;
export const MAX_SOULS_LEVEL = 20;
export const MAX_SUITABILITY_LEVEL = 10;
export const MAX_FRIENDSHIP_LEVEL = 10;
export const MAX_EQUIP_WAZA = 3;
