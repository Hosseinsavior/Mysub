import json
import os
from dotenv import load_dotenv
import logging
from fetcher import fetch_all_configs, get_region_from_ip
from storage import save_configs_by_region
from telegram import send_file_to_telegram_channel

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """
    Main function to fetch, save, and send VPN configurations.
    """
    # Load environment variables
    load_dotenv()
    telegram_token = os.getenv('TELEGRAM_TOKEN')
    channel_id = os.getenv('CHANNEL_ID')
    
    if not telegram_token or not channel_id:
        logger.error("TELEGRAM_TOKEN or CHANNEL_ID not set in .env")
        return

    # Load configuration
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
            telegram_urls = config['telegram_urls']
            config_folder = config['config_folder']
            all_configs_folder = config['all_configs_folder']
            valid_protocols = config['valid_protocols']
    except Exception as e:
        logger.error(f"Error loading config.json: {e}")
        return

    # Fetch configurations
    logger.info("Starting to fetch VPN configs...")
    all_v2ray_configs = fetch_all_configs(telegram_urls, valid_protocols)

    if all_v2ray_configs:
        # Save configurations
        save_configs_by_region(all_v2ray_configs, config_folder, all_configs_folder)
        
        # Send files to Telegram
        for region in os.listdir(config_folder):
            region_folder = os.path.join(config_folder, region)
            if os.path.isdir(region_folder):
                file_path = os.path.join(region_folder, 'config.txt')
                if os.path.exists(file_path):
                    send_file_to_telegram_channel(file_path, telegram_token, channel_id)
        
        logger.info("Configs saved and sent successfully.")
    else:
        logger.warning("No V2Ray configs found.")

if __name__ == "__main__":
    main()
