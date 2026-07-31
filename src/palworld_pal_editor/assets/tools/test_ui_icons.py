from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).with_name("extract_ui_icons.py")
PNG_1X1 = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000d49444154789c6360000000020001e221bc330000000049454e44ae426082"
)


def png_bytes(width: int, height: int) -> bytes:
    data = bytearray(PNG_1X1)
    data[16:20] = width.to_bytes(4, "big")
    data[20:24] = height.to_bytes(4, "big")
    return bytes(data)

EXPECTED_SOURCES = {
    "stat-health": "Pal/Content/Pal/Texture/UI/Main_Menu/T_icon_status_00",
    "stat-attack": "Pal/Content/Pal/Texture/UI/Main_Menu/T_icon_status_02",
    "stat-defense": "Pal/Content/Pal/Texture/UI/Main_Menu/T_icon_status_03",
    "stat-work-speed": (
        "Pal/Content/Pal/Texture/StatusParameterIcon/T_icon_status_work_speed"
    ),
    "friendship": "Pal/Content/Pal/Texture/UI/Main_Menu/T_Icon_PalFriendship_Color",
    "gender-male": "Pal/Content/Pal/Texture/UI/Main_Menu/T_Icon_PanGender_Male",
    "gender-female": "Pal/Content/Pal/Texture/UI/Main_Menu/T_Icon_PanGender_Female",
    "rare": "Pal/Content/Pal/Texture/UI/InGame/T_icon_pal_rare",
    "boss": "Pal/Content/Pal/Texture/UI/InGame/T_icon_enemy_strong",
    "condense": "Pal/Content/Pal/Texture/UI/IngameMenu/T_icon_condense",
    "heal": (
        "Pal/Content/Pal/Texture/UI/InGame/SkillIcon/"
        "T_icon_skill_pal_HPRecovery"
    ),
    "revive": (
        "Pal/Content/Pal/Texture/UI/InGame/SkillIcon/T_icon_skill_pal_Revive"
    ),
}

EXPECTED_DIMENSIONS = {
    "stat-health": (24, 24),
    "stat-attack": (24, 24),
    "stat-defense": (24, 24),
    "stat-work-speed": (256, 256),
    "friendship": (64, 64),
    "gender-male": (34, 34),
    "gender-female": (34, 34),
    "rare": (36, 36),
    "boss": (64, 64),
    "condense": (28, 32),
    "heal": (128, 128),
    "revive": (128, 128),
}


def load_module():
    if not MODULE_PATH.is_file():
        raise AssertionError(f"missing UI icon extractor: {MODULE_PATH}")
    sys.path.insert(0, str(MODULE_PATH.parent))
    try:
        spec = importlib.util.spec_from_file_location("extract_ui_icons", MODULE_PATH)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.pop(0)


class UiIconExtractorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.module = load_module()

    def populate_exports(self, root: Path, *, missing: str | None = None) -> None:
        for logical_name, source in EXPECTED_SOURCES.items():
            if logical_name == missing:
                continue
            target = root.joinpath(*source.split("/")).with_suffix(".png")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(png_bytes(*EXPECTED_DIMENSIONS[logical_name]))

    def test_collect_outputs_maps_exact_allowlist_to_stable_runtime_paths(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            export_root = Path(directory)
            self.populate_exports(export_root)

            outputs = self.module.collect_outputs(export_root)

        self.assertEqual(dict(self.module.UI_ICON_SOURCES), EXPECTED_SOURCES)
        self.assertEqual(self.module.UI_ICON_DIMENSIONS, EXPECTED_DIMENSIONS)
        self.assertEqual(
            set(outputs),
            {f"icons/ui/{logical_name}.png" for logical_name in EXPECTED_SOURCES},
        )
        self.assertEqual(
            outputs["icons/ui/stat-health.png"],
            png_bytes(24, 24),
        )

    def test_collect_outputs_rejects_missing_or_invalid_png(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            export_root = Path(directory)
            self.populate_exports(export_root, missing="rare")
            with self.assertRaisesRegex(FileNotFoundError, "rare"):
                self.module.collect_outputs(export_root)

            self.populate_exports(export_root)
            invalid = export_root.joinpath(*EXPECTED_SOURCES["rare"].split("/")).with_suffix(
                ".png"
            )
            invalid.write_bytes(b"not a png")
            with self.assertRaisesRegex(ValueError, "rare"):
                self.module.collect_outputs(export_root)

            invalid.write_bytes(png_bytes(35, 36))
            with self.assertRaisesRegex(ValueError, "36x36"):
                self.module.collect_outputs(export_root)

    def test_validate_sources_rejects_duplicate_virtual_assets(self) -> None:
        duplicate = {
            "first": EXPECTED_SOURCES["rare"],
            "second": EXPECTED_SOURCES["rare"],
        }
        with self.assertRaisesRegex(ValueError, "duplicate"):
            self.module.validate_icon_sources(duplicate)

    def test_check_and_write_touch_only_allowlisted_targets(self) -> None:
        outputs = {
            f"icons/ui/{logical_name}.png": png_bytes(*EXPECTED_DIMENSIONS[logical_name])
            for logical_name in EXPECTED_SOURCES
        }
        with tempfile.TemporaryDirectory() as directory:
            assets = Path(directory)
            unrelated = assets / "icons/ui/keep-local.png"
            unrelated.parent.mkdir(parents=True)
            unrelated.write_bytes(b"keep")

            self.assertEqual(
                set(self.module.check_outputs(outputs, assets)),
                set(outputs),
            )
            self.module.write_outputs(outputs, assets)
            self.assertEqual(self.module.check_outputs(outputs, assets), [])
            self.assertEqual(unrelated.read_bytes(), b"keep")

            changed = assets / "icons/ui/stat-health.png"
            changed.write_bytes(b"drift")
            self.assertEqual(
                self.module.check_outputs(outputs, assets),
                ["icons/ui/stat-health.png"],
            )

    def test_write_outputs_rolls_back_the_complete_set_on_replace_failure(self) -> None:
        outputs = {
            f"icons/ui/{logical_name}.png": png_bytes(*EXPECTED_DIMENSIONS[logical_name])
            for logical_name in EXPECTED_SOURCES
        }
        with tempfile.TemporaryDirectory() as directory:
            assets = Path(directory)
            originals = {}
            for index, relative in enumerate(sorted(outputs)):
                target = assets.joinpath(*relative.split("/"))
                if index % 2 == 0:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(b"original-" + relative.encode())
                    originals[relative] = target.read_bytes()
                else:
                    originals[relative] = None

            replacements = 0

            def fail_on_fifth(source: Path, target: Path) -> None:
                nonlocal replacements
                replacements += 1
                if replacements == 5:
                    raise OSError("injected replacement failure")
                source.replace(target)

            with self.assertRaisesRegex(OSError, "injected"):
                self.module.write_outputs(
                    outputs,
                    assets,
                    replace_file=fail_on_fifth,
                )

            for relative, original in originals.items():
                target = assets.joinpath(*relative.split("/"))
                if original is None:
                    self.assertFalse(target.exists(), relative)
                else:
                    self.assertEqual(target.read_bytes(), original, relative)
            self.assertEqual(
                list(assets.glob(".ui-icons-*")),
                [],
            )


if __name__ == "__main__":
    unittest.main()
