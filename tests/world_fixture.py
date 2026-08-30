"""Opening the real save fixture, for the tests that mutate one.

Anything about moving, copying or deleting a Pal has to run against a save the game
wrote: the rules being checked are about container slots, guild handles, the locker
and three storage formats agreeing with each other, and a fake agrees with itself.
Each caller gets its own copy in a temp directory (AGENTS.md: never a personal save).
"""

import shutil
from pathlib import Path

from palworld_pal_editor.core.pal_objects import PalObjects
from palworld_pal_editor.core.pal_storage import PalStorageSaveFile
from palworld_pal_editor.core.save_manager import SaveManager


ROOT = Path(__file__).parents[1]
WORLD_FIXTURE = ROOT / "tests/saves/1.0/AF518B19A47340B8A55BC58137981393"
GPS_FIXTURE = ROOT / "tests/saves/1.0/GlobalPalStorage.sav"
EMPTY_DPS_FIXTURE = (
    ROOT
    / "tests/saves/1.0/8C439FF04713B5F986F9CAB485575089/Players/"
    "00000000000000000000000000000001_dps.sav"
)

LOSSY_UID = "a18b721d-0000-0000-0000-000000000000"
MINT_UID = "c8b99cc9-0000-0000-0000-000000000000"
# The one player in this save who is in a different guild from everyone else.
TIGEREST_UID = "285dab79-0000-0000-0000-000000000000"


def write_empty_global(path: Path) -> None:
    """A Global Palbox with nothing in it, made from an empty DPS of the same shape."""
    shutil.copy2(EMPTY_DPS_FIXTURE, path)
    storage = PalStorageSaveFile.open(path, "dps", LOSSY_UID)
    storage.gvas_file.header.save_game_class_name = (
        "/Script/Pal.PalGlobalPalStorageSaveGame"
    )
    storage.gvas_file.properties["SaveParameterArray"]["value"]["type_name"] = (
        "PalGlobalPalStorageSaveParameter"
    )
    path.write_bytes(storage.serialize())


def open_world(tmp_path: Path, *, global_palbox: Path | None = None) -> SaveManager:
    """A loaded session over a private copy of the fixture save.

    `global_palbox` is the Global Palbox to put beside it, since the save has one
    only when the world has unlocked it -- `GPS_FIXTURE` for a populated one, or a
    path `write_empty_global` has written for an empty one.
    """
    world = tmp_path / "world"
    shutil.copytree(WORLD_FIXTURE, world)
    if global_palbox is not None:
        shutil.copy2(global_palbox, world.parent / "GlobalPalStorage.sav")
    SaveManager._instance = None
    manager = SaveManager()
    assert manager.open(str(world)) is not None
    return manager


def locker_ids(manager: SaveManager) -> list[str]:
    """Every Pal the world save says is being held outside it."""
    return [
        str(PalObjects.get_BaseType(entry["InstanceId"]))
        for entry in manager.locker_entries()
    ]
