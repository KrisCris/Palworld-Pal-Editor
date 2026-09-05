// Which skills a Pal may be given, and what the badges on one mean.
//
// The rules are the game's, not the backend's: a request carrying a skill this
// module refuses would be refused there too, and the picker greys the option out
// with the same answer that stops the request being made.

export function isSkillAssignable(skill = {}, isHuman = false) {
    if (skill.Disabled) return false;
    return isHuman
        ? skill.AssignableToHumans === true
        : skill.Assignable !== false;
}

export function skillBadges(skill = {}, isHuman = false) {
    return [
        skill.NonInheritable && "nonInheritable",
        skill.Exclusive && "exclusive",
        skill.BossSkill && "boss",
        (skill.HasSkillFruit || skill.SkillFruit) && "fruit",
        !isSkillAssignable(skill, isHuman) && "disabled",
    ].filter(Boolean);
}

// A skill the Pal already has stays on the list whatever the rules say about it,
// because a dropdown that cannot show the current value cannot show the Pal.
export function filterSkillOptions(skills, currentIds, hideInvalid, isHuman = false) {
    const rows = Array.isArray(skills) ? skills : [];
    if (!hideInvalid) return rows.slice();

    const retainedIds = new Set(currentIds ?? []);
    return rows.filter(
        skill => (
            (!skill?.Invalid && isSkillAssignable(skill, isHuman))
            || retainedIds.has(skill?.InternalName)
        ),
    );
}

const SKILL_BADGE_TRANSLATION_KEYS = Object.freeze({
    nonInheritable: "Editor_Skill_Badge_NonInheritable",
    exclusive: "Editor_Skill_Badge_Exclusive",
    boss: "Editor_Skill_Badge_Boss",
    fruit: "Editor_Skill_Badge_Fruit",
    disabled: "Editor_Skill_Badge_Disabled",
});

export const skillBadgeTranslationKey = badge => SKILL_BADGE_TRANSLATION_KEYS[badge];
