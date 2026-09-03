"""What this editor accepts as a Pal from outside a save, and what it hands out.

Two risks, and both corrupt a save quietly. A record read as the wrong format puts a
Global Palbox envelope where a world record belongs. An export that drops its
envelope cannot be told apart on the way back in, so the editor guesses -- which is
exactly what the fake world envelope used to make it do.
"""

import shutil
from pathlib import Path

import pytest

from palworld_pal_editor.core.pal_objects import PalObjects, json_native
from palworld_pal_editor.core.pal_sources import detach_native_record
from palworld_pal_editor.core.pal_storage import PalStorageSaveFile
from palworld_pal_editor.core.pal_storage_adapters import (
    DpsPalAdapter,
    GpsPalAdapter,
    WorldPalAdapter,
)
from palworld_pal_editor.core.save_manager import SaveManager


WORLD_FIXTURE = Path("tests/saves/1.0/AF518B19A47340B8A55BC58137981393")
GPS_FIXTURE = Path("tests/saves/1.0/GlobalPalStorage.sav")
DPS_FIXTURE = WORLD_FIXTURE / "Players/A18B721D000000000000000000000000_dps.sav"
LOSSY_UID = "a18b721d-0000-0000-0000-000000000000"


def storage_export(adapter_class, path: Path, kind: str):
    """One occupied slot of a real storage file, exported the way the API does."""
    adapter = adapter_class(PalStorageSaveFile.open(path, kind, LOSSY_UID))
    record = adapter.records()[0]
    return record, adapter.export(record)


def open_world_with_global(tmp_path: Path) -> SaveManager:
    world = tmp_path / "world"
    shutil.copytree(WORLD_FIXTURE, world)
    shutil.copy2(GPS_FIXTURE, world.parent / "GlobalPalStorage.sav")
    SaveManager._instance = None
    manager = SaveManager()
    assert manager.open(str(world)) is not None
    return manager


def test_a_global_palbox_export_carries_the_whole_pal_and_says_where_it_came_from():
    record, exported = storage_export(GpsPalAdapter, GPS_FIXTURE, "global_palbox")

    source = detach_native_record(exported)

    assert source.kind == "global_palbox"
    # Nothing is filtered on the way out and nothing on the way back in: an unknown
    # future gameplay field survives both because neither side enumerates them.
    assert source.save_parameter == json_native(record.pal.save_parameter)
    assert source.entity().CharacterID == record.pal.CharacterID


def test_a_dps_export_and_a_global_palbox_export_are_never_read_as_each_other():
    dps_record, dps_export = storage_export(DpsPalAdapter, DPS_FIXTURE, "dps")
    _, gps_export = storage_export(GpsPalAdapter, GPS_FIXTURE, "global_palbox")

    assert detach_native_record(dps_export).kind == "dps"
    assert detach_native_record(gps_export).kind == "global_palbox"
    # The two formats are the same shape apart from the name on the array, so the
    # name is the whole of the distinction and neither adapter may shrug at it.
    assert GpsPalAdapter.detach(dps_export) is None
    assert DpsPalAdapter.detach(gps_export) is None
    assert dps_record.pal.CharacterID is not None


def test_an_export_that_does_not_name_exactly_one_pal_is_refused():
    _, exported = storage_export(GpsPalAdapter, GPS_FIXTURE, "global_palbox")
    entry = exported["value"]["values"][0]

    for values in ([], [entry, entry]):
        exported["value"]["values"] = values
        with pytest.raises(ValueError):
            detach_native_record(exported)


def test_a_world_pal_is_recognised_and_a_player_in_the_same_array_is_not(tmp_path):
    manager = open_world_with_global(tmp_path)
    record = next(
        record
        for record in manager.pal_repository.records()
        if record.storage_kind == "world"
    )
    player_record = next(
        native
        for native in manager._entities_list
        if WorldPalAdapter.is_player(native)
    )

    assert detach_native_record(WorldPalAdapter.export(record)).kind == "world"
    # Players live in CharacterSaveParameterMap under the same shape as Pals, so
    # "it is a world record" is not enough to import one as a Pal.
    with pytest.raises(ValueError):
        detach_native_record(json_native(player_record))


def test_a_bare_save_parameter_is_not_a_record():
    record, _ = storage_export(GpsPalAdapter, GPS_FIXTURE, "global_palbox")

    # A payload with no envelope says nothing about which storage wrote it. This is
    # the shape a converter would produce if it flattened every format into one.
    with pytest.raises(ValueError):
        detach_native_record(json_native(record.pal.save_parameter))


def test_a_global_palbox_pal_imports_into_a_world_container_and_survives_a_save(
    tmp_path,
):
    manager = open_world_with_global(tmp_path)
    player = manager.get_player(LOSSY_UID)
    source_record = next(
        record
        for record in manager.pal_repository.records()
        if record.storage_kind == "global_palbox"
    )
    source_record.pal.NickName = "Imported"
    exported = manager.storage_adapters["global-palbox"].export(source_record)

    source = detach_native_record(exported)
    created = manager.pal_mutations.create(
        LOSSY_UID,
        WorldPalAdapter.storage_key(player.PalStorageContainerId),
        source.save_parameter,
    )

    # The payload crossed formats whole; everything about where it now lives was
    # written by the target.
    assert created.storage_kind == "world"
    assert created.pal.NickName == "Imported"
    assert created.pal.CharacterID == source_record.pal.CharacterID
    assert created.pal.InstanceId != source_record.pal.InstanceId
    assert str(created.pal.OwnerPlayerUId) == LOSSY_UID
    assert created.pal.PlayerUId == PalObjects.EMPTY_UUID
    assert created.pal.SlotId[0] == player.PalStorageContainerId
    assert str(created.group_id) == str(player.group_id)
    # The Global Palbox Pal it was copied from is still there.
    assert manager.get_record(source_record.record_key) is not None

    output = tmp_path / "written"
    assert manager.save(str(output)) is True
    assert manager.open(str(output)) is not None
    reloaded = manager.get_record(created.record_key)
    assert reloaded is not None
    assert reloaded.pal.NickName == "Imported"
    assert reloaded.pal.CharacterID == source_record.pal.CharacterID
