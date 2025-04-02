import logging
import os
import discord
from dotenv import load_dotenv
from bot import setup_bot, run_bot
from data import load_moderation_history
from commands import register_commands
from config import HISTORY_FILE

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("safetybot.log"),
        logging.StreamHandler()
    ]
)

# Load environment variables
load_dotenv()

# Check for history file
if os.path.exists(HISTORY_FILE):
    logging.info(f"Found history file at {os.path.abspath(HISTORY_FILE)}")
else:
    logging.warning(f"History file not found at {os.path.abspath(HISTORY_FILE)}")

# Initialize bot
bot = setup_bot()

# Register commands
register_commands(bot)

# Load data
history_data = load_moderation_history()

# Log how many users are in the history
logging.info(f"Loaded {len(history_data)} users in moderation history")

# Run the bot
if __name__ == "__main__":
    run_bot(bot)
