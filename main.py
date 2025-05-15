import os
import json
import logging
import re
import requests
import shutil
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from dotenv import load_dotenv
from ratelimit import limits, sleep_and_retry

# تنظیم لاگ‌گیری
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# بارگذاری تنظیمات
load_dotenv()
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHANNEL_ID = os.getenv('CHANNEL_ID')

with open('config.json', 'r') as f:
    config = json.load(f)
    TELEGRAM_URLS = config['telegram_urls']
    CONFIG_FOLDER = config['config_folder']
    ALL_CONFIGS_FOLDER = config['all_configs_folder']

VALID_PROTOCOLS = ['vless', 'vmess', 'ss', 'trojan', 'tuic']

def is_valid_vpn_config(config: str) -> bool:
    """Validates if a string is a valid VPN configuration."""
    pattern = r'^(vless|vmess|ss|trojan|tuic):\/\/[a-zA-Z0-9\-@:%._\+~#=]+'
    return bool(re.match(pattern, config))

@sleep_and_retry
@limits(calls=10, period=60)
def get_v2ray_links(url: str, max_retries: int = 3) -> list:
    """Extracts VPN configuration links from a Telegram channel URL."""
    session = requests.Session()
    retries = Retry(total=max_retries, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
    session.mount('http://', HTTPAdapter(max_retries=retries))
    session.mount('https://', HTTPAdapter(max_retries=retries))
    try:
        response = session.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        v2ray_configs = []
        for tag in soup.find_all(['div', 'span', 'code'], class_=['tgme_widget_message_text', 'js-message_text']):
            text = tag.get_text().strip()
            if is_valid_vpn_config(text):
                v2ray_configs.append(text)
        return v2ray_configs
    except requests.RequestException as e:
        logger.error(f"Error fetching {url}: {e}")
        return []

def get_region_from_ip(ip: str) -> str:
    """Fetches the country of an IP address using multiple APIs."""
    api_endpoints = [
        f'https://ipapi.co/{ip}/json/',
        f'http://ipwho.is/{ip}?output=json',
        f'http://www.geoplugin.net/json.gp?ip={ip}',
        f'https://api.ipbase.com/v1/json/{ip}'
    ]

    def fetch_api(endpoint):
        try:
            response = requests.get(endpoint, timeout=5)
            if response.status_code == 200:
                data = response.json()
                return data.get('country')
        except Exception:
            return None
        return None

    with ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(fetch_api, api_endpoints))
        for result in results:
            if result:
                return result
    return None

def save_configs_by_region(configs: list):
    """Saves VPN configs into region-based folders."""
    if os.path.exists(CONFIG_FOLDER):
        shutil.rmtree(CONFIG_FOLDER)
    os.makedirs(CONFIG_FOLDER)

    for config in configs:
        ip = config.split('//')[1].split('/')[0]
        region = get_region_from_ip(ip)
        if region:
            region_folder = os.path.join(CONFIG_FOLDER, region)
            os.makedirs(region_folder, exist_ok=True)
            with open(os.path.join(region_folder, 'config.txt'), 'a', encoding='utf-8') as file:
                file.write(config + '\n')

    os.makedirs(ALL_CONFIGS_FOLDER, exist_ok=True)
    with open(os.path.join(ALL_CONFIGS_FOLDER, 'all_configs.txt'), 'a', encoding='utf-8') as file:
        for config in configs:
            file.write(config + '\n')

def send_file_to_telegram_channel(file_path: str, token: str, channel_id: str):
    """Sends a file to a Telegram channel."""
    url = f"https://api.telegram.org/bot{token}/sendDocument"
    try:
        with open(file_path, 'rb') as file:
            response = requests.post(url, data={'chat_id': channel_id}, files={'document': file})
        response.raise_for_status()
        logger.info(f"File {file_path} sent successfully.")
    except requests.RequestException as e:
        logger.error(f"Failed to send file {file_path}: {e}")

def clean_old_configs(folder: str, days: int = 7):
    """Removes config files older than the specified number of days."""
    from datetime import datetime, timedelta
    threshold = datetime.now() - timedelta(days=days)
    for root, dirs, files in os.walk(folder):
        for file in files:
            file_path = os.path.join(root, file)
            if os.path.getmtime(file_path) < threshold.timestamp():
                os.remove(file_path)

def main():
    logger.info("Starting VPN config fetcher...")
    clean_old_configs(CONFIG_FOLDER)
    clean_old_configs(ALL_CONFIGS_FOLDER)

    with ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(get_v2ray_links, TELEGRAM_URLS))
    all_v2ray_configs = list(set(config for sublist in results if sublist for config in sublist))

    if all_v2ray_configs:
        save_configs_by_region(all_v2ray_configs)
        for region in os.listdir(CONFIG_FOLDER):
            region_folder = os.path.join(CONFIG_FOLDER, region)
            if os.path.isdir(region_folder):
                file_path = os.path.join(region_folder, 'config.txt')
                send_file_to_telegram_channel(file_path, TELEGRAM_TOKEN, CHANNEL_ID)
        logger.info("Configs saved and sent successfully.")
    else:
        logger.warning("No V2Ray configs found.")

if __name__ == "__main__":
    main()
