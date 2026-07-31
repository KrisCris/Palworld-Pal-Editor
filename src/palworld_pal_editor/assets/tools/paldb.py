from urllib.parse import parse_qs, urlsplit


PAL_ICON_ID_ALIASES = {
    # The 1.0 technology/save ID spells this differently from the Pal ID.
    "Thunderdog_Ice": "ThunderDog_Ice",
}


def logical_pal_icon_id(value: str) -> str:
    return PAL_ICON_ID_ALIASES.get(value, value)


def hover_id(value: str, namespace: str) -> str | None:
    target = parse_qs(urlsplit(value).query).get("s", [""])[0]
    prefix = f"{namespace}/"
    return target[len(prefix) :] if target.startswith(prefix) else None


def labeled_int(root, label: str) -> int:
    for row in root.find_all("div", recursive=False):
        columns = row.find_all("div", recursive=False)
        if columns and columns[0].get_text(" ", strip=True) == label:
            return int(columns[-1].get_text(strip=True))
    raise ValueError(f"PalDB field {label!r} was not found")
