import sys
from cx_Freeze import setup, Executable

options = {
    "excludes": [],
    "zip_include_packages": [],
    "include_files": [
        ("src/palworld_pal_editor/assets/", "assets/"),
        ("src/palworld_pal_editor/webui/", "webui"),
    ]
}


if sys.platform == "win32":
    base = "Win32GUI"
    target_name = "Palworld_Pal_Editor.exe"
else:
    base = None
    target_name = "Palworld_Pal_Editor"

executables = [
    Executable(
        "./src/palworld_pal_editor/__main__.py",
        base=base,
        icon="./icon.ico",
        target_name=target_name,
    )
]


setup(
    name="Palworld Pal Editor",
    version="0.2.1",
    description="A Palworld Pal Editor developed by _connlost with ❤️.",
    options={"build_exe": options},
    executables=executables,
)
