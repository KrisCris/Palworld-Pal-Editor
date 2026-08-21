from __future__ import annotations

from typing import Optional

from palworld_save_tools.gvas import GvasFile

from palworld_pal_editor.core.basecamp_data import BaseCampData
from palworld_pal_editor.core.group_data import GroupData
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


class GuildLabData:
    """A narrow mutable view over guild laboratory progress in Level.sav."""

    def __init__(self, gvas_file: GvasFile, definitions: dict[str, dict]) -> None:
        self._definitions = definitions
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
            "EffectDescriptionTextId": definition["EffectDescriptionTextId"],
            "Essential": definition["Essential"],
            "Materials": definition["Materials"],
        }

    def snapshot(self, group_data: GroupData, camp_data: BaseCampData) -> dict:
        group_names = {
            str(group.group_id): group.guild_name for group in group_data.get_groups()
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
        changed = 0
        rows = raw.setdefault("research_info", [])
        present: set[str] = set()
        for row in rows:
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
            rows.append(
                {
                    "research_id": candidate,
                    "work_amount": float(
                        self._definitions[candidate]["RequiredWorkAmount"]
                    ),
                }
            )
            changed += 1
        LOGGER.info(
            "Completed guild laboratory research: "
            f"guild={guild_id} research={research_id} category={category} "
            f"all={all_research} changed={changed}"
        )
        return changed
