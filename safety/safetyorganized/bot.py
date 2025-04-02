import discord
import asyncio
import logging
from discord.ext import commands, tasks
from config import TOKEN, TARGET_CHANNEL_ID
from cache import user_cache

def setup_bot():
    """Set up and configure the bot"""
    intents = discord.Intents.default()
    intents.members = True
    intents.message_content = True
    
    bot = commands.Bot(command_prefix="!", intents=intents)
    
    # Register events
    @bot.event
    async def on_ready():
        logging.info(f'{bot.user.name} has connected to Discord!')
        
        # Set bot status
        await bot.change_presence(activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="for safety issues"
        ))
        
        # Sync commands
        try:
            synced = await bot.tree.sync()
            logging.info(f"Synced {len(synced)} command(s)")
        except Exception as e:
            logging.error(f"Failed to sync commands: {e}")
            
        # Start the background task for polling guilds
        poll_guilds.start()
        logging.info("Started guild polling background task")
    
    @bot.event
    async def on_guild_join(guild):
        """Log when the bot joins a new guild"""
        logging.info(f"Joined new guild: {guild.name} (ID: {guild.id})")
        
        # Try to send a message to the target channel
        target_channel = bot.get_channel(TARGET_CHANNEL_ID)
        if target_channel:
            await target_channel.send(f"🔔 Bot has joined a new server: **{guild.name}** (ID: {guild.id})")
    
    @bot.event
    async def on_guild_remove(guild):
        """Log when the bot is removed from a guild"""
        logging.info(f"Removed from guild: {guild.name} (ID: {guild.id})")
        
        # Try to send a message to the target channel
        target_channel = bot.get_channel(TARGET_CHANNEL_ID)
        if target_channel:
            await target_channel.send(f"🔔 Bot has been removed from server: **{guild.name}** (ID: {guild.id})")
    @tasks.loop(minutes=5)
    async def poll_guilds():
        """Poll all guilds for new moderation actions every 5 minutes"""
        try:
            logging.info("Polling guilds for new moderation actions...")
            
            # Process each guild the bot is in
            for guild in bot.guilds:
                try:
                    logging.info(f"Checking guild: {guild.name} ({guild.id})")
                    
                    # Import this from your commands.py
                    from commands import fetch_historical_moderation_actions
                    
                    # Fetch new moderation actions in silent mode
                    await fetch_historical_moderation_actions(bot, guild, silent=True)
                    
                    # Add a small delay between guilds to avoid rate limiting
                    await asyncio.sleep(2)
                    
                except Exception as e:
                    logging.error(f"Error processing guild {guild.name}: {str(e)}")
                    continue
                    
            logging.info("Finished polling guilds")
            
        except Exception as e:
            logging.error(f"Error in poll_guilds task: {str(e)}")
    
    @poll_guilds.before_loop
    async def before_poll_guilds():
        """Wait until the bot is ready before starting the polling task"""
        await bot.wait_until_ready()
    
    return bot

def run_bot(bot):
    """Run the bot with the token"""
    bot.run(TOKEN)
