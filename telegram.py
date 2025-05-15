import requests
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def send_file_to_telegram_channel(file_path: str, token: str, channel_id: str) -> bool:
    """
    Sends a file to a Telegram channel.
    
    Args:
        file_path (str): Path to the file to send.
        token (str): Telegram bot token.
        channel_id (str): Telegram channel ID.
    
    Returns:
        bool: True if successful, False otherwise.
    """
    url = f"https://api.telegram.org/bot{token}/sendDocument"
    try:
        with open(file_path, 'rb') as file:
            response = requests.post(url, data={'chat_id': channel_id}, files={'document': file})
        if response.status_code == 200:
            logger.info(f"File sent successfully: {file_path}")
            return True
        else:
            logger.error(f"Failed to send file {file_path}: {response.text}")
            return False
    except Exception as e:
        logger.error(f"Error sending file {file_path}: {e}")
        return False
