import os
import shutil
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def clean_old_configs(folder: str, days: int = 7) -> None:
    """
    Removes configuration files older than the specified number of days.
    
    Args:
        folder (str): Path to the folder containing configurations.
        days (int): Number of days to keep files.
    """
    threshold = datetime.now() - timedelta(days=days)
    for root, dirs, files in os.walk(folder):
        for file in files:
            file_path = os.path.join(root, file)
            if os.path.getmtime(file_path) < threshold.timestamp():
                os.remove(file_path)
                logger.info(f"Removed old config: {file_path}")

def save_configs_by_region(configs: list, config_folder: str, all_configs_folder: str) -> None:
    """
    Saves VPN configurations into region-specific folders and a combined file.
    
    Args:
        configs (list): List of VPN configuration strings.
        config_folder (str): Path to the folder for region-specific configs.
        all_configs_folder (str): Path to the folder for all configs.
    """
    if os.path.exists(config_folder):
        shutil.rmtree(config_folder)
        logger.info(f"Cleared existing folder: {config_folder}")

    if not os.path.exists(config_folder):
        os.makedirs(config_folder)

    for config in configs:
        try:
            ip = config.split('//')[1].split('/')[0]
            region = get_region_from_ip(ip)
            if region:
                region_folder = os.path.join(config_folder, region)
                if not os.path.exists(region_folder):
                    os.makedirs(region_folder)
                with open(os.path.join(region_folder, 'config.txt'), 'a', encoding='utf-8') as file:
                    file.write(config + '\n')
                logger.debug(f"Saved config to {region_folder}/config.txt")
        except Exception as e:
            logger.error(f"Error processing config {config}: {e}")

    if not os.path.exists(all_configs_folder):
        os.makedirs(all_configs_folder)

    all_configs_path = os.path.join(all_configs_folder, 'all_configs.txt')
    with open(all_configs_path, 'w', encoding='utf-8') as file:
        for config in configs:
            file.write(config + '\n')
    logger.info(f"Saved all configs to {all_configs_path}")

    clean_old_configs(config_folder)
    clean_old_configs(all_configs_folder)
