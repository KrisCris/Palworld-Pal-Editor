import copy
from pathlib import Path
import tempfile
import unittest

from palworld_pal_editor.core.save_manager import SaveManager


SAVE = (
    Path(__file__).parents[1]
    / "tests/saves/1.0/AF518B19A47340B8A55BC58137981393"
)


def _guild_extra_entries(manager: SaveManager) -> dict[str, dict]:
    entries = manager.gvas_file.properties["worldSaveData"]["value"][
        "GuildExtraSaveDataMap"
    ]["value"]
    return {str(entry["key"]): entry for entry in entries}


def _lab_raw(entry: dict) -> dict:
    return entry["value"]["Lab"]["value"]["RawData"]["value"]


class GuildLabResearchTests(unittest.TestCase):
    def test_category_completion_isolated_to_selected_guild_and_known_rows(self):
        manager = SaveManager()
        self.assertIsNotNone(manager.open(str(SAVE)))
        snapshot = manager.get_lab_research()
        target = max(
            snapshot["Guilds"],
            key=lambda guild: sum(
                category["Completed"] for category in guild["Categories"]
            ),
        )
        other = next(
            guild
            for guild in snapshot["Guilds"]
            if guild["GuildId"] != target["GuildId"]
        )
        entries = _guild_extra_entries(manager)
        target_raw = _lab_raw(entries[target["GuildId"]])
        missing_handcraft = next(
            row
            for row in target_raw["research_info"]
            if row["research_id"]
            in {
                research["ResearchId"]
                for category in target["Categories"]
                if category["Category"] == "Handcraft"
                for research in category["Research"]
            }
        )
        target_raw["research_info"].remove(missing_handcraft)
        target_raw["research_info"].append(
            {"research_id": "FutureResearch", "work_amount": 123.5}
        )
        metadata_before = {
            "current_research_id": copy.deepcopy(
                target_raw["current_research_id"]
            ),
            "trailing_bytes": copy.deepcopy(target_raw["trailing_bytes"]),
        }
        other_before = copy.deepcopy(entries[other["GuildId"]])
        non_target_before = {
            row["ResearchId"]: row["WorkAmount"]
            for category in target["Categories"]
            if category["Category"] != "Handcraft"
            for row in category["Research"]
        }

        changed = manager.complete_lab_research(
            target["GuildId"], category="Handcraft"
        )

        self.assertGreater(changed, 0)
        refreshed = manager.get_lab_research()
        refreshed_target = next(
            guild
            for guild in refreshed["Guilds"]
            if guild["GuildId"] == target["GuildId"]
        )
        handcraft = next(
            category
            for category in refreshed_target["Categories"]
            if category["Category"] == "Handcraft"
        )
        self.assertEqual(handcraft["Total"], handcraft["Completed"])
        self.assertTrue(
            all(
                row["WorkAmount"] == row["RequiredWorkAmount"]
                for row in handcraft["Research"]
            )
        )
        self.assertEqual(
            non_target_before,
            {
                row["ResearchId"]: row["WorkAmount"]
                for category in refreshed_target["Categories"]
                if category["Category"] != "Handcraft"
                for row in category["Research"]
            },
        )
        self.assertEqual(other_before, entries[other["GuildId"]])
        self.assertEqual(
            {"research_id": "FutureResearch", "work_amount": 123.5},
            next(
                row
                for row in target_raw["research_info"]
                if row["research_id"] == "FutureResearch"
            ),
        )
        restored_missing = next(
            row
            for row in target_raw["research_info"]
            if row["research_id"] == missing_handcraft["research_id"]
        )
        self.assertEqual(
            next(
                row["RequiredWorkAmount"]
                for row in handcraft["Research"]
                if row["ResearchId"] == missing_handcraft["research_id"]
            ),
            restored_missing["work_amount"],
        )
        self.assertEqual(
            metadata_before,
            {
                "current_research_id": target_raw["current_research_id"],
                "trailing_bytes": target_raw["trailing_bytes"],
            },
        )

    def test_complete_all_roundtrips_exact_thresholds_and_lab_metadata(self):
        manager = SaveManager()
        self.assertIsNotNone(manager.open(str(SAVE)))
        snapshot = manager.get_lab_research()
        target = max(
            snapshot["Guilds"],
            key=lambda guild: sum(
                category["Completed"] for category in guild["Categories"]
            ),
        )
        entries = _guild_extra_entries(manager)
        target_raw = _lab_raw(entries[target["GuildId"]])
        metadata_before = (
            copy.deepcopy(target_raw["current_research_id"]),
            copy.deepcopy(target_raw["trailing_bytes"]),
        )
        target_raw["research_info"].pop()

        self.assertGreater(
            manager.complete_lab_research(target["GuildId"], all_research=True),
            0,
        )

        with tempfile.TemporaryDirectory(prefix="pal-editor-lab-") as directory:
            output = Path(directory)
            self.assertTrue(manager.save(str(output)))
            self.assertIsNotNone(manager.open(str(output)))
            reread = manager.get_lab_research()
            reread_target = next(
                guild
                for guild in reread["Guilds"]
                if guild["GuildId"] == target["GuildId"]
            )
            research = [
                row
                for category in reread_target["Categories"]
                for row in category["Research"]
            ]
            self.assertEqual(168, len(research))
            self.assertTrue(all(row["Completed"] for row in research))
            self.assertTrue(
                all(
                    row["WorkAmount"] == row["RequiredWorkAmount"]
                    for row in research
                )
            )
            reread_raw = _lab_raw(
                _guild_extra_entries(manager)[target["GuildId"]]
            )
            self.assertEqual(
                metadata_before,
                (
                    reread_raw["current_research_id"],
                    reread_raw["trailing_bytes"],
                ),
            )


if __name__ == "__main__":
    unittest.main()
