# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['src/palworld_pal_editor/__main__.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('src/palworld_pal_editor/assets/data', 'assets/data'),
        ('src/palworld_pal_editor/assets/icons', 'assets/icons'),
        ('src/palworld_pal_editor/webui', 'webui'),
    ],
    hiddenimports=['webview.platforms.qt', 'pkg_resources.extern'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
a.binaries = [binary for binary in a.binaries if binary[0] != 'libgbm.so.1']
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='palworld-pal-editor',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['icon.ico'],
)
