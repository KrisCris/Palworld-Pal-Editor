"""Guild technology research: what a guild has unlocked, and unlocking more.

The lab belongs to the guild rather than to any player, so research is read against
a group id and the camps that group owns rather than against whoever is selected.
`snapshot` reports the tree with the interface language applied; `complete` unlocks
one research, one category, or all of it.
"""

from __future__ import annotations

from typing import Callable, Optional

from palworld_save_tools.gvas import GvasFile

from palworld_pal_editor.config import Config
from palworld_pal_editor.core.basecamp_data import BaseCampData
from palworld_pal_editor.core.guild_data import GuildData
from palworld_pal_editor.utils import LOGGER


CATEGORY_ORDER = (
    "Handcraft",
    "EmitFlame",
    "Watering",
    "Seeding",
    "GenerateElectricity",
    "Deforest",
    "Mining",
    "Cool",
    "ProductMedicine",
)


class GuildLab:
    """One guild's research rows: the thing a completion actually edits.

    `LOGGER.change_logger` logs a change to one property of one object, and there
    was no such object here -- `GuildLabData` holds every guild's lab at once, and
    the guild to edit arrives as an argument. This is that object, so a completion
    logs itself the way every other edit in the editor does.
    """

    def __init__(
        self,
        guild_id: str,
        rows: list,
        definitions: dict[str, dict],
        label: Callable[[str], str],
    ) -> None:
        self._guild_id = guild_id
        self._rows = rows
        self._definitions = definitions
        self._label = label

    def __str__(self) -> str:
        return f"Guild {self._guild_id} Lab"

    @property
    def research_work_amount(self) -> dict[str, float]:
        """Each known research's work amount, in tree order, labelled for the log.

        A research the save has no row for is missing from this rather than zero:
        there is nothing to read, and completing it appends a row rather than
        raising one that was already there.
        """
        amounts = {
            row["research_id"]: row.get("work_amount")
            for row in self._rows
            if isinstance(row, dict) and row.get("research_id") in self._definitions
        }
        return {
            self._label(research_id): amounts[research_id]
            for research_id in self._definitions
            if research_id in amounts
        }

    @LOGGER.change_logger("research_work_amount")
    def complete(self, selected: set[str]) -> int:
        """Bring every selected research up to the work its definition requires."""
        changed = 0
        present: set[str] = set()
        for row in self._rows:
            if not isinstance(row, dict):
                continue
            candidate = row.get("research_id")
            if isinstance(candidate, str):
                present.add(candidate)
            if candidate not in selected:
                continue
            required = self._definitions[candidate]["RequiredWorkAmount"]
            if row.get("work_amount") != required:
                row["work_amount"] = float(required)
                changed += 1
        for candidate in self._definitions:
            if candidate not in selected or candidate in present:
                continue
            self._rows.append(
                {
                    "research_id": candidate,
                    "work_amount": float(
                        self._definitions[candidate]["RequiredWorkAmount"]
                    ),
                }
            )
            changed += 1
        return changed


class GuildLabData:
    """A narrow mutable view over guild laboratory progress in Level.sav."""

    def __init__(
        self,
        gvas_file: GvasFile,
        definitions: dict[str, dict],
        labels: Optional[dict[str, dict]] = None,
    ) -> None:
        self._definitions = definitions
        self._labels = labels or {}
        self._definition_order = {
            research_id: index for index, research_id in enumerate(definitions)
        }
        world = gvas_file.properties["worldSaveData"]["value"]
        guild_extra = world.get("GuildExtraSaveDataMap")
        self._entries = guild_extra.get("value", []) if guild_extra else []
        self._entry_map = {
            str(entry["key"]): entry
            for entry in self._entries
            if entry.get("key") is not None
        }
        self._levels = self._build_levels()

    def _locale(self) -> str:
        selected = Config.i18n
        return selected if selected in self._labels.get("category", {}) else "en"

    def _localized(self, i18n: dict, field: str, fallback: str = "") -> str:
        lang = self._locale()
        row = (i18n or {}).get(lang) or (i18n or {}).get("en") or {}
        return row.get(field) or fallback

    def _category_name(self, category: str) -> str:
        lang = self._locale()
        row = self._labels.get("category", {}).get(lang) or {}
        return row.get(category) or category

    def _build_levels(self) -> dict[str, int]:
        levels: dict[str, int] = {}
        visiting: set[str] = set()

        def level(research_id: str) -> int:
            if research_id in levels:
                return levels[research_id]
            if research_id in visiting:
                raise ValueError(f"Research prerequisite cycle at {research_id}")
            visiting.add(research_id)
            parent = self._definitions[research_id].get("RequiredResearchId")
            value = (
                1
                if not parent or parent not in self._definitions
                else level(parent) + 1
            )
            visiting.remove(research_id)
            levels[research_id] = value
            return value

        for research_id in self._definitions:
            level(research_id)
        return levels

    @staticmethod
    def _lab_raw(entry: dict) -> Optional[dict]:
        try:
            return entry["value"]["Lab"]["value"]["RawData"]["value"]
        except (KeyError, TypeError):
            return None

    def _guild_raw(self, guild_id: str) -> dict:
        entry = self._entry_map.get(str(guild_id))
        raw = self._lab_raw(entry) if entry else None
        if raw is None:
            raise ValueError(f"Guild laboratory not found: {guild_id}")
        return raw

    def _node(self, research_id: str, progress: dict[str, float]) -> dict:
        definition = self._definitions[research_id]
        required = definition["RequiredWorkAmount"]
        amount = progress.get(research_id, 0.0)
        parent = definition.get("RequiredResearchId")
        parent_complete = (
            not parent
            or parent not in self._definitions
            or progress.get(parent, 0.0)
            >= self._definitions[parent]["RequiredWorkAmount"]
        )
        return {
            "ResearchId": research_id,
            "TextId": definition["TextId"],
            "Name": self._localized(
                definition.get("I18n"), "Name", definition["TextId"]
            ),
            "EffectDescription": self._localized(
                definition.get("I18n"), "EffectDescription", ""
            ),
            "IconKey": definition["IconKey"],
            "Level": self._levels[research_id],
            "WorkAmount": amount,
            "RequiredWorkAmount": required,
            "RequiredResearchId": parent,
            "Completed": amount >= required,
            "Available": parent_complete,
            "SubCategory": definition["SubCategory"],
            "EffectType": definition["EffectType"],
            "EffectValue": definition["EffectValue"],
            "EffectWorkSuitability": definition["EffectWorkSuitability"],
            "EffectItemType": definition["EffectItemType"],
            "EffectCategoryName": self._category_name(
                definition["EffectWorkSuitability"]
            ),
            "EffectItemTypeName": self._localized_display_name(
                definition["EffectItemType"], "item"
            ),
            "EffectDescriptionTextId": definition["EffectDescriptionTextId"],
            "Essential": definition["Essential"],
            "Materials": definition["Materials"],
        }

    def _localized_display_name(self, key: str, kind: str) -> str:
        if key == "None" or not key:
            return ""
        lang = self._locale()
        row = self._labels.get(kind, {}).get(lang) or {}
        return row.get(key) or key

    def snapshot(self, guild_data: GuildData, camp_data: BaseCampData) -> dict:
        group_names = {
            str(group.group_id): group.guild_name for group in guild_data.get_groups()
        }
        camps_by_group: dict[str, list[dict]] = {}
        for camp in camp_data.get_camps():
            camps_by_group.setdefault(str(camp.owner_group_id), []).append(
                {"CampId": str(camp.id), "CampName": camp.name or str(camp.id)}
            )

        guilds = []
        for entry in self._entries:
            guild_id = str(entry.get("key"))
            raw = self._lab_raw(entry)
            if raw is None:
                continue
            rows = raw.get("research_info") or []
            progress = {
                row["research_id"]: float(row["work_amount"])
                for row in rows
                if isinstance(row, dict)
                and isinstance(row.get("research_id"), str)
                and isinstance(row.get("work_amount"), (int, float))
            }
            categories = []
            for category in CATEGORY_ORDER:
                research = [
                    self._node(research_id, progress)
                    for research_id, definition in self._definitions.items()
                    if definition["Category"] == category
                ]
                research.sort(
                    key=lambda row: (
                        row["Level"],
                        self._definition_order[row["ResearchId"]],
                    )
                )
                categories.append(
                    {
                        "Category": category,
                        "CategoryName": self._category_name(category),
                        "IconKey": f"category-{category}",
                        "Completed": sum(row["Completed"] for row in research),
                        "Total": len(research),
                        "Research": research,
                    }
                )
            guilds.append(
                {
                    "GuildId": guild_id,
                    "GuildName": group_names.get(guild_id) or "Unnamed Guild",
                    "Camps": camps_by_group.get(guild_id, []),
                    "CurrentResearchId": raw.get("current_research_id"),
                    "UnknownResearchCount": sum(
                        1
                        for row in rows
                        if not isinstance(row, dict)
                        or row.get("research_id") not in self._definitions
                    ),
                    "Categories": categories,
                }
            )
        return {"CategoryOrder": list(CATEGORY_ORDER), "Guilds": guilds}

    def complete(
        self,
        guild_id: str,
        *,
        research_id: str | None = None,
        category: str | None = None,
        all_research: bool = False,
    ) -> int:
        selectors = sum((research_id is not None, category is not None, all_research))
        if selectors != 1:
            raise ValueError("Select exactly one research completion scope")
        if research_id is not None and research_id not in self._definitions:
            raise ValueError(f"Unknown laboratory research: {research_id}")
        if category is not None and category not in CATEGORY_ORDER:
            raise ValueError(f"Unknown laboratory category: {category}")

        selected = {
            candidate
            for candidate, definition in self._definitions.items()
            if all_research
            or candidate == research_id
            or definition["Category"] == category
        }
        raw = self._guild_raw(str(guild_id))
        lab = GuildLab(
            str(guild_id),
            raw.setdefault("research_info", []),
            self._definitions,
            self._research_label,
        )
        changed = lab.complete(selected)
        # The scope asked for, which the per-research lines above cannot say: a
        # category whose research is already done reports the same nothing as one
        # the request never named.
        LOGGER.info(
            "Completed guild laboratory research: "
            f"guild={guild_id} research={research_id} category={category} "
            f"all={all_research} changed={changed}"
        )
        return changed

    def _research_label(self, research_id: str) -> str:
        """How the log names one research: its id, and its name in the UI language."""
        definition = self._definitions[research_id]
        name = self._localized(definition.get("I18n"), "Name", definition["TextId"])
        return f"{research_id} ({name})"
