import os
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Bot configuration
TOKEN = os.getenv('BOT_TOKEN')  # Changed from DISCORD_TOKEN to BOT_TOKEN
if TOKEN is None:
    logging.error("BOT_TOKEN not found in environment variables or .env file")
    logging.error(f"Current working directory: {os.getcwd()}")
    logging.error(f"Environment variables: {[key for key in os.environ.keys() if not key.startswith('_')]}")
    raise ValueError("BOT_TOKEN environment variable is required")

# Handle multiple target channels
target_channel_str = os.getenv('TARGET_CHANNEL_ID', '0')
if ',' in target_channel_str:
    # If multiple channels are provided, split them and convert each to int
    TARGET_CHANNEL_IDS = [int(channel_id.strip()) for channel_id in target_channel_str.split(',')]
    # For backward compatibility, set TARGET_CHANNEL_ID to the first channel
    TARGET_CHANNEL_ID = TARGET_CHANNEL_IDS[0] if TARGET_CHANNEL_IDS else 0
else:
    # If only one channel is provided
    TARGET_CHANNEL_ID = int(target_channel_str)
    TARGET_CHANNEL_IDS = [TARGET_CHANNEL_ID]

TARGET_GUILD_ID = int(os.getenv('TARGET_GUILD_ID', 0))
SOURCE_CHANNEL_IDS = os.getenv('SOURCE_CHANNEL_IDS', '').split(',')
AUTHORIZED_USERS = os.getenv('AUTHORIZED_USERS', '').split(',')
AUTHORIZED_ROLES = os.getenv('AUTHORIZED_ROLES', '').split(',')
HISTORY_FILE = os.getenv('HISTORY_FILE', 'moderation_history.json')
COMMAND_PREFIX = os.getenv('COMMAND_PREFIX', '!')

# Constants
DEFAULT_EMBED_COLOR = 0x3498db  # Blue
ERROR_EMBED_COLOR = 0xe74c3c    # Red
SUCCESS_EMBED_COLOR = 0x2ecc71  # Green
WARNING_EMBED_COLOR = 0xf39c12  # Orange
