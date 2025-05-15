import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from concurrent.futures import ThreadPoolExecutor
import re
import logging
from ratelimit import limits, sleep_and_retry  # اضافه کردن ratelimit

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def is_valid_vpn_config(config: str, valid_protocols: list) -> bool:
    """
    Validates if a string is a valid VPN configuration link.
    
    Args:
        config (str): The configuration string to validate.
        valid_protocols (list): List of valid VPN protocols.
    
    Returns:
        bool: True if valid, False otherwise.
    """
    pattern = r'^(' + '|'.join(valid_protocols) + r'):\/\/[a-zA-Z0-9\-@:%._\+~#=]+'
    return bool(re.match(pattern, config))

@sleep_and_retry
@limits(calls=10, period=60)
def get_v2ray_links(url: str, valid_protocols: list, max_retries: int = 3) -> list:
    """
    Extracts VPN configuration links from a Telegram channel URL.
    
    Args:
        url (str): URL of the Telegram channel.
        valid_protocols (list): List of valid VPN protocols.
        max_retries (int): Number of retry attempts for HTTP requests.
    
    Returns:
        list: List of valid VPN configuration links.
    """
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
            if is_valid_vpn_config(text, valid_protocols):
                v2ray_configs.append(text)
        logger.info(f"Extracted {len(v2ray_configs)} configs from {url}")
        return v2ray_configs
    except requests.RequestException as e:
        logger.error(f"Error fetching {url}: {e}")
        return []

def fetch_all_configs(telegram_urls: list, valid_protocols: list, max_workers: int = 10) -> list:
    """
    Fetches VPN configurations from multiple Telegram URLs in parallel.
    
    Args:
        telegram_urls (list): List of Telegram channel URLs.
        valid_protocols (list): List of valid VPN protocols.
        max_workers (int): Maximum number of parallel workers.
    
    Returns:
        list: List of all unique VPN configurations.
    """
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        results = list(executor.map(lambda url: get_v2ray_links(url, valid_protocols), telegram_urls))
    all_configs = set(config for sublist in results if sublist for config in sublist)
    logger.info(f"Total unique configs fetched: {len(all_configs)}")
    return list(all_configs)

def get_region_from_ip(ip: str) -> str:
    """
    Retrieves the country of an IP address using multiple APIs.
    
    Args:
        ip (str): IP address to look up.
    
    Returns:
        str: Country code or None if not found.
    """
    api_endpoints = [
        f'https://ipapi.co/{ip}/json/',  # URL اصلاح‌شده
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
                logger.debug(f"Region found for IP {ip}: {result}")
                return result
    logger.warning(f"No region found for IP {ip}")
    return None
