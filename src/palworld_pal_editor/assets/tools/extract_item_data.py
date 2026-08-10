"""Generate the item catalog and item icons directly from an installed game."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from pathlib import Path

import extract_game_data
import game_data

ITEM_SOURCES = {
    "items": "Pal/Content/Pal/DataTable/Item/DT_ItemDataTable_Common",
    "icons": "Pal/Content/Pal/DataTable/Item/DT_ItemIconDataTable_Common",
    "recipes": "Pal/Content/Pal/DataTable/Item/DT_ItemRecipeDataTable_Common",
    "passives": "Pal/Content/Pal/DataTable/PassiveSkill/DT_PassiveSkill_Main_Common",
    "characters": (
        "Pal/Content/Pal/DataTable/Character/DT_PalMonsterParameter_Common"
    ),
}
ITEM_TEXT_TABLES = {
    "items": "DT_ItemNameText_Common",
    "item_descriptions": "DT_ItemDescriptionText_Common",
    "buildings": "DT_MapObjectNameText_Common",
    "pals": "DT_PalNameText_Common",
    "ui": "DT_UI_Common_Text_Common",
}
RUNTIME_ASSETS = (
    Path(__file__).parents[4] / "src/palworld_pal_editor/assets"
).resolve()
PROVENANCE_PATH = Path(__file__).with_name("item_provenance.json")
_SAFE_ICON_KEY = re.compile(r"^[A-Za-z0-9_.-]+$")
_QUOTED_PLACEHOLDER_END = re.compile(r"\|'(?=/>)")
_MISSING_PLACEHOLDER_PIPE = re.compile(r"(id=\|[^|<>]+)'(?=/>)")
_CHARACTER_PLACEHOLDER = re.compile(
    r"<characterName\s+id=\|([^|]+)\|(?:\s+[^>]*)?/>", re.IGNORECASE
)
_DYNAMIC_TYPES = {
    "None": None,
    "CommonWeapon": "weapon",
    "CommonArmor": "armor",
    "PalEgg": "egg",
}
_ITEM_STAT_FIELDS = {
    "Weight": "Weight",
    "Price": "Price",
    "PhysicalAttack": "PhysicalAttackValue",
    "HP": "HPValue",
    "PhysicalDefense": "PhysicalDefenseValue",
    "Shield": "ShieldValue",
    "MagicAttack": "MagicAttackValue",
    "MagicDefense": "MagicDefenseValue",
}


def _enum_tail(value: object, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise TypeError(f"{label} must be a nonempty enum string")
    return value.rsplit("::", 1)[-1]


def _item_group(type_a: str, type_b: str) -> str:
    no_subtype = type_b.casefold() == "none"
    if type_a == "Weapon":
        return "None" if no_subtype else "Weapon"
    if type_a == "Armor":
        return {
            "ArmorHead": "Head",
            "ArmorBody": "Body",
            "Shield": "Shield",
        }.get(type_b, "None")
    if type_a == "Accessory":
        return "Accessory"
    if type_a == "Food":
        return "Food"
    if type_a == "Essential":
        return "KeyItem"
    if type_a == "Glider":
        return "Glider"
    if type_a in {"CaptureItemModifier", "SphereModule"}:
        return "SphereModule"
    if type_a.casefold() == "none" or (type_a == "Consume" and no_subtype):
        return "None"
    return "Common"


def _text_key(row: dict, override_field: str, prefix: str, item_id: str) -> str:
    override = row.get(override_field)
    return (
        override
        if isinstance(override, str) and override.casefold() != "none"
        else f"{prefix}{item_id}"
    )


def _passive_effects(passive_id: str, row: dict) -> list[dict]:
    effects = []
    for index in range(1, 5):
        effect_type = _enum_tail(
            row.get(f"EffectType{index}"),
            f"{passive_id}.EffectType{index}",
        )
        target_type = _enum_tail(
            row.get(f"TargetType{index}"),
            f"{passive_id}.TargetType{index}",
        )
        value = row.get(f"EffectValue{index}")
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise TypeError(f"{passive_id}.EffectValue{index} must be numeric")
        if effect_type in {"None", "no"} or value == 0:
            continue
        effects.append(
            {
                "PassiveSkillId": passive_id,
                "EffectType": effect_type,
                "EffectValue": value,
                "TargetType": target_type,
            }
        )
    return effects


def _pal_gear_characters(
    items: dict[str, dict],
    characters: dict[str, dict],
    descriptions: dict[str, dict],
) -> dict[str, str]:
    character_index = game_data.casefold_index(characters)
    mappings = {}
    legal_gear = set()
    for item_id, row in sorted(items.items()):
        if row.get("TypeB") != "EPalItemTypeB::Essential_PalGear":
            continue
        if row.get("bLegalInGame") is True:
            legal_gear.add(item_id)
        description_key = _text_key(
            row, "OverrideDescription", "ITEM_DESC_", item_id
        )
        description = game_data._text_value(descriptions, description_key) or ""
        referenced = {
            character_index.get(value.casefold())
            for value in _CHARACTER_PLACEHOLDER.findall(description)
        }
        if None in referenced:
            raise ValueError(
                f"{item_id} description references an unknown Pal character"
            )
        if len(referenced) > 1:
            raise ValueError(
                f"{item_id} description references multiple Pal characters: "
                f"{sorted(referenced)}"
            )
        if referenced:
            mappings[item_id] = next(iter(referenced))

    missing = sorted(legal_gear - set(mappings))
    if missing:
        raise ValueError(
            f"Legal Pal gear character mappings are incomplete: missing={missing}"
        )
    return mappings


def build_item_records(
    items: dict[str, dict],
    icons: dict[str, dict],
    recipes: dict[str, dict],
    passives: dict[str, dict],
    pal_gear_characters: dict[str, str],
    texts: dict[str, dict[str, dict]],
) -> dict:
    """Project raw game tables into the runtime item catalog."""
    if set(texts) != set(ITEM_TEXT_TABLES) or any(
        set(locales) != set(game_data.LOCALE_DIRECTORIES) for locales in texts.values()
    ):
        raise ValueError("Item localization must contain every supported locale")

    icon_index = game_data.casefold_index(icons)
    passive_index = game_data.casefold_index(passives)
    blueprint_products: dict[str, str] = {}
    for recipe_id, recipe in sorted(recipes.items()):
        unlock_item = recipe.get("UnlockItemID")
        product_item = recipe.get("Product_Id")
        if not isinstance(unlock_item, str) or unlock_item.casefold() == "none":
            continue
        if not isinstance(product_item, str) or product_item.casefold() == "none":
            raise TypeError(f"{recipe_id}.Product_Id must identify an item")
        previous = blueprint_products.get(unlock_item)
        if previous is not None and previous != product_item:
            raise ValueError(
                f"Conflicting products for {unlock_item}: {previous}, {product_item}"
            )
        blueprint_products[unlock_item] = product_item

    records: dict[str, dict] = {}
    icon_sources: dict[str, str] = {}
    missing_localizations: list[str] = []

    for item_id, row in sorted(items.items()):
        type_a = _enum_tail(row.get("TypeA"), f"{item_id}.TypeA")
        type_b = _enum_tail(row.get("TypeB"), f"{item_id}.TypeB")
        dynamic_class = row.get("ItemDynamicClass")
        if dynamic_class not in _DYNAMIC_TYPES:
            raise ValueError(
                f"{item_id}.ItemDynamicClass is unsupported: {dynamic_class!r}"
            )
        for field in (
            "MaxStackCount",
            "Durability",
            "MagazineSize",
            "Rarity",
            "Rank",
            "SortId",
        ):
            if type(row.get(field)) is not int:
                raise TypeError(f"{item_id}.{field} must be an integer")
        if row["MaxStackCount"] < 1:
            raise ValueError(f"{item_id}.MaxStackCount must be positive")
        if type(row.get("bLegalInGame")) is not bool:
            raise TypeError(f"{item_id}.bLegalInGame must be a bool")
        legal = row["bLegalInGame"]

        icon_name = row.get("IconName")
        if not isinstance(icon_name, str) or not icon_name:
            raise TypeError(f"{item_id}.IconName must be a nonempty string")
        icon_id = icon_index.get(icon_name.casefold())
        if icon_id is not None and not _SAFE_ICON_KEY.fullmatch(icon_id):
            raise ValueError(f"{item_id}.IconName does not resolve safely: {icon_name}")
        if icon_id is None:
            if legal:
                raise ValueError(f"{item_id}.IconName does not resolve: {icon_name}")
        else:
            icon_path = f"icons/items/{icon_id}.png"
            source = game_data._texture_virtual_path(
                icons[icon_id], f"{item_id}:{icon_id}", "Icon"
            )
            if previous := icon_sources.get(icon_path):
                if previous != source:
                    raise ValueError(f"Conflicting item icon source for {icon_path}")
            else:
                icon_sources[icon_path] = source

        name_key = _text_key(row, "OverrideName", "ITEM_NAME_", item_id)
        description_key = _text_key(row, "OverrideDescription", "ITEM_DESC_", item_id)
        i18n: dict[str, dict[str, str]] = {}
        for locale in game_data.LOCALE_DIRECTORIES:
            name, name_missing = game_data._technology_text(
                texts, ("items",), name_key, locale, item_id
            )
            description, description_missing = game_data._technology_text(
                texts,
                ("item_descriptions",),
                description_key,
                locale,
                name,
            )
            description = _QUOTED_PLACEHOLDER_END.sub("|", description)
            description = _MISSING_PLACEHOLDER_PIPE.sub(r"\1|", description)
            description = game_data._expand_technology_text(
                description,
                locale,
                texts,
                items,
                missing_localizations,
                f"item:{item_id}:Description",
            )
            if name_missing:
                missing_localizations.append(f"item:{item_id}:{locale}:Name:{name_key}")
            if description_missing:
                missing_localizations.append(
                    f"item:{item_id}:{locale}:Description:{description_key}"
                )
            i18n[locale] = {
                "Name": name or item_id,
                "Description": description or name or item_id,
            }

        stats = {}
        for output_field, source_field in _ITEM_STAT_FIELDS.items():
            value = row.get(source_field)
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                raise TypeError(f"{item_id}.{source_field} must be numeric")
            stats[output_field] = value

        passive_ids = []
        effects = []
        for index in range(1, 5):
            source_field = "PassiveSkillName" if index == 1 else f"PassiveSkillName{index}"
            field = f"{item_id}.{source_field}"
            serialized_name = row.get(source_field)
            if serialized_name is None:
                continue
            if isinstance(serialized_name, str):
                value = serialized_name
            elif isinstance(serialized_name, dict) and isinstance(
                serialized_name.get("Key"), str
            ):
                value = serialized_name["Key"]
            else:
                raise TypeError(f"{field} has unsupported value: {serialized_name!r}")
            if value.casefold() == "none":
                continue
            passive_id = passive_index.get(value.casefold())
            if passive_id is None:
                raise ValueError(
                    f"{item_id}.PassiveSkillName{index} references unknown passive {value}"
                )
            passive_ids.append(passive_id)
            effects.extend(_passive_effects(passive_id, passives[passive_id]))

        record = {
            "InternalName": item_id,
            "I18n": i18n,
            "NameKey": name_key,
            "Group": _item_group(type_a, type_b),
            "TypeA": type_a,
            "TypeB": type_b,
            "DynamicType": _DYNAMIC_TYPES[dynamic_class],
            "MaxStackCount": row["MaxStackCount"],
            "MaxDurability": row["Durability"],
            "MagazineSize": row["MagazineSize"],
            "Rarity": row["Rarity"],
            "Rank": row["Rank"],
            "SortId": row["SortId"],
            "IconKey": icon_id,
            "Legal": legal,
            "Disabled": not legal,
            "MonsterOnly": type_a == "MonsterEquipWeapon",
            "Stats": stats,
            "PassiveSkillIds": passive_ids,
            "Effects": effects,
        }
        product_id = blueprint_products.get(item_id)
        product_row = items.get(product_id) if product_id else None
        if product_row is not None:
            product_icon_name = product_row.get("IconName")
            if not isinstance(product_icon_name, str) or not product_icon_name:
                raise TypeError(f"{product_id}.IconName must be a nonempty string")
            product_icon_id = icon_index.get(product_icon_name.casefold())
            if product_icon_id is None or not _SAFE_ICON_KEY.fullmatch(product_icon_id):
                raise ValueError(
                    f"{item_id} product icon does not resolve safely: {product_icon_name}"
                )
            record["OverlayIconKey"] = product_icon_id
        if item_id in pal_gear_characters:
            record["PalGearCharacterId"] = pal_gear_characters[item_id]
        records[item_id] = record
    return {
        "records": records,
        "icon_sources": dict(sorted(icon_sources.items())),
        "missing_localizations": sorted(set(missing_localizations)),
        "passive_reference_count": sum(
            len(record["PassiveSkillIds"]) for record in records.values()
        ),
        "pal_gear_count": len(pal_gear_characters),
    }


def _json_bytes(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def _output_root_hash(outputs: dict[str, bytes]) -> str:
    digest = hashlib.sha256()
    for path, data in sorted(outputs.items()):
        digest.update(path.encode("utf-8"))
        digest.update(b"\0")
        digest.update(hashlib.sha256(data).digest())
    return digest.hexdigest()


def build_outputs(
    toolchain: extract_game_data.Toolchain,
    game: Path,
    work: Path,
) -> tuple[dict[str, bytes], dict]:
    export_root = work / "export"
    table_sources = set(ITEM_SOURCES.values())
    table_sources.update(
        game_data.text_table_path(table_name, locale)
        for table_name in ITEM_TEXT_TABLES.values()
        for locale in game_data.LOCALE_DIRECTORIES
    )
    extract_game_data.export_sources(
        toolchain,
        game / extract_game_data._PAK_RELATIVE.parent,
        export_root,
        work / "profiles" / "tables",
        table_sources,
    )
    items = game_data.load_table(export_root, ITEM_SOURCES["items"])
    icons = game_data.load_table(export_root, ITEM_SOURCES["icons"])
    recipes = game_data.load_table(export_root, ITEM_SOURCES["recipes"])
    passives = game_data.load_table(export_root, ITEM_SOURCES["passives"])
    characters = game_data.load_table(export_root, ITEM_SOURCES["characters"])
    texts = {
        name: {
            locale: game_data.load_text_table(export_root, table_name, locale)
            for locale in game_data.LOCALE_DIRECTORIES
        }
        for name, table_name in ITEM_TEXT_TABLES.items()
    }
    pal_gear_characters = _pal_gear_characters(
        items, characters, texts["item_descriptions"]["ja"]
    )
    built = build_item_records(
        items, icons, recipes, passives, pal_gear_characters, texts
    )
    extract_game_data.export_sources(
        toolchain,
        game / extract_game_data._PAK_RELATIVE.parent,
        export_root,
        work / "profiles" / "icons",
        set(built["icon_sources"].values()),
    )
    outputs = {
        path: game_data._texture_png_path(export_root, source).read_bytes()
        for path, source in built["icon_sources"].items()
    }
    outputs["data/item_data.json"] = _json_bytes(built["records"])
    metadata = {
        "item_count": len(built["records"]),
        "icon_count": len(built["icon_sources"]),
        "missing_localizations": len(built["missing_localizations"]),
        "passive_reference_count": built["passive_reference_count"],
        "pal_gear_count": built["pal_gear_count"],
    }
    return outputs, metadata


def _provenance(
    build_id: str,
    toolchain: extract_game_data.Toolchain,
    outputs: dict[str, bytes],
    metadata: dict,
) -> dict:
    icons = {path: data for path, data in outputs.items() if path.endswith(".png")}
    return {
        "schema_version": 3,
        "game_build": build_id,
        "uex_revision": toolchain.uex_revision,
        "mapping_sha256": toolchain.mapping_sha256,
        "item_count": metadata["item_count"],
        "icon_count": metadata["icon_count"],
        "missing_localizations": metadata["missing_localizations"],
        "passive_reference_count": metadata["passive_reference_count"],
        "pal_gear_count": metadata["pal_gear_count"],
        "catalog_sha256": hashlib.sha256(outputs["data/item_data.json"]).hexdigest(),
        "icon_root_sha256": _output_root_hash(icons),
    }


def _changed_paths(assets: Path, outputs: dict[str, bytes]) -> list[str]:
    changed = []
    for relative, data in outputs.items():
        target = assets.joinpath(*relative.split("/"))
        if not target.is_file() or target.read_bytes() != data:
            changed.append(relative)
    item_icons = assets / "icons/items"
    expected = {Path(path).name for path in outputs if path.startswith("icons/items/")}
    if item_icons.is_dir():
        changed.extend(
            f"icons/items/{path.name}"
            for path in item_icons.glob("*.png")
            if path.name not in expected
        )
    return sorted(set(changed))


def _publish(assets: Path, outputs: dict[str, bytes], provenance: dict) -> None:
    assets.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="pal-item-stage-", dir=assets.parent) as d:
        stage = Path(d)
        for relative, data in outputs.items():
            target = stage.joinpath(*relative.split("/"))
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        provenance_stage = stage / "item_provenance.json"
        provenance_stage.write_bytes(_json_bytes(provenance))

        expected_icons = {
            Path(path).name for path in outputs if path.startswith("icons/items/")
        }
        icon_dir = assets / "icons/items"
        icon_dir.mkdir(parents=True, exist_ok=True)
        for stale in icon_dir.glob("*.png"):
            if stale.name not in expected_icons:
                stale.unlink()
        for relative in sorted(outputs):
            source = stage.joinpath(*relative.split("/"))
            target = assets.joinpath(*relative.split("/"))
            target.parent.mkdir(parents=True, exist_ok=True)
            os.replace(source, target)
        os.replace(provenance_stage, PROVENANCE_PATH)


def run(
    *,
    write: bool,
    game_dir: Path | None = None,
    uex: Path | None = None,
    usmap: Path | None = None,
    cache: Path | None = None,
    allow_unknown_build_write: bool = False,
    assets: Path = RUNTIME_ASSETS,
) -> dict:
    game = extract_game_data.find_game_dir(game_dir)
    build_id = extract_game_data.detect_build_id(game)
    existing = (
        json.loads(PROVENANCE_PATH.read_text(encoding="utf-8"))
        if PROVENANCE_PATH.is_file()
        else None
    )
    if (
        write
        and (existing is None or existing.get("game_build") != build_id)
        and not allow_unknown_build_write
    ):
        raise ValueError(
            "Refusing first/new-build item publication without "
            "--allow-unknown-build-write"
        )
    toolchain = extract_game_data.ensure_toolchain(
        cache or extract_game_data._default_cache(), uex, usmap
    )
    with tempfile.TemporaryDirectory(prefix="pal-item-data-") as d:
        outputs, metadata = build_outputs(toolchain, game, Path(d))
        provenance = _provenance(build_id, toolchain, outputs, metadata)
        changed = _changed_paths(Path(assets), outputs)
        if existing != provenance:
            changed.append("tools/item_provenance.json")
        changed = sorted(set(changed))
        if write:
            _publish(Path(assets), outputs, provenance)
    result = {
        "status": "written" if write else "ok",
        "game_build": build_id,
        **metadata,
        "changed_paths": changed,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--write", action="store_true")
    parser.add_argument("--game-dir", type=Path)
    parser.add_argument("--uex", type=Path)
    parser.add_argument("--usmap", type=Path)
    parser.add_argument("--cache", type=Path)
    parser.add_argument("--allow-unknown-build-write", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        args = _parser().parse_args(argv)
        run(
            write=args.write,
            game_dir=args.game_dir,
            uex=args.uex,
            usmap=args.usmap,
            cache=args.cache,
            allow_unknown_build_write=args.allow_unknown_build_write,
        )
        return 0
    except (OSError, TypeError, ValueError, RuntimeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
