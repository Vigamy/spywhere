# -*- mode: python ; coding: utf-8 -*-

import os
import time

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

exe_name = 'install'
default_dist_exe = os.path.join('dist', f'{exe_name}.exe')
if os.name == 'nt' and os.path.exists(default_dist_exe):
    try:
        os.remove(default_dist_exe)
    except PermissionError:
        exe_name = f'install_{int(time.time())}'

a = Analysis(
    ['app/install.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('app/main_script.py', '.'),
        ('app/game.py', '.'),
        ('app/main_script_mac.py', '.'),
        ('.env', '.'),
    ]
    + collect_data_files('pygame')
    + collect_data_files('pyautogui')
    + collect_data_files('pyscreeze')
    + collect_data_files('mouseinfo'),
    hiddenimports=(
        collect_submodules('pygame')
        + collect_submodules('pyautogui')
        + collect_submodules('dotenv')
        + ['PIL', 'pyscreeze', 'pygetwindow', 'pymsgbox', 'pytweening', 'mouseinfo']
        + ['uuid', 'datetime', 'socket', 'getpass', 'json', 'math', 'random', 'dataclasses', 'pathlib']
    ),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name=exe_name,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

if os.name == 'posix':
    app = BUNDLE(
        exe,
        name='install.app',
        icon=None,
        bundle_identifier=None,
    )
