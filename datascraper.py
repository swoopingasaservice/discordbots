import discord
from discord.ext import commands
import asyncio
import json
from datetime import datetime

# Set up the bot with a command prefix and intents
intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.guild_messages = True
intents.message_content = True
intents.members = True
intents.voice_states = True  # Required for voice state updates
intents.presences = True  # Required for presence updates
intents.invites = True  # Required for invite events

bot = commands.Bot(command_prefix='!', intents=intents)

# Replace with your channel ID and guild ID
LOG_CHANNEL_ID = 1300179330940403777  # Replace with your actual channel ID
TARGET_GUILD_ID = 1300179329443037376  # Replace with your actual guild ID

# Queue for logging messages
log_queue = asyncio.Queue()

def get_timestamp():
    """Get the current timestamp in a formatted string."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

async def log_to_channel(message):
    """Send a structured log message to the designated channel."""
    channel = bot.get_channel(LOG_CHANNEL_ID)
    if channel:
        try:
            await channel.send(message)
        except discord.HTTPException as e:
            if e.status == 429:  # Rate limit error
                retry_after = int(e.response.headers.get('Retry-After', 1))
                await asyncio.sleep(retry_after)  # Wait for the specified time
                await log_to_channel(message)  # Retry sending the message

async def log_message(action, user, details):
    """Log a message with structured data."""
    timestamp = get_timestamp()
    log_entry = {
        "timestamp": timestamp,
        "action": action,
        "user": {
            "name": user.name,
            "id": user.id
        },
        "details": details
    }
    log_entry_json = json.dumps(log_entry, indent=4)  # Convert to JSON format with indentation
    formatted_message = f"**[{timestamp}]** {action} | **User:** {user.name} (ID: {user.id}) | **Details:** {details}"
    await log_queue.put(formatted_message)  # Add to the log queue

async def log_worker():
    """Worker to process log messages from the queue."""
    while True:
        message = await log_queue.get()  # Use await to get from asyncio.Queue
        await log_to_channel(message)
        log_queue.task_done()
        await asyncio.sleep(1)  # Adjust the sleep time as needed

# Event handlers for logging various actions
@bot.event
async def on_member_join(member):
    """Log when a member joins the server."""
    if member.guild.id == TARGET_GUILD_ID:
        await log_message("Member Join", member, "has joined the server.")

@bot.event
async def on_member_remove(member):
    """Log when a member leaves the server."""
    if member.guild.id == TARGET_GUILD_ID:
        await log_message("Member Leave", member, "has left the server.")

@bot.event
async def on_message(message):
    """Log messages sent in the server."""
    if message.author == bot.user:
        return
    if message.guild.id == TARGET_GUILD_ID:
        await log_message("Message Sent", message.author, f"sent: {message.content}")

@bot.event
async def on_message_edit(before, after):
    """Log when a message is edited."""
    if before.guild.id == TARGET_GUILD_ID:
        await log_message("Message Edit", before.author, 
                          f"edited a message:\n**Before:** \"{before.content}\"\n**After:** \"{after.content}\"")

@bot.event
async def on_message_delete(message):
    """Log when a message is deleted."""
    if message.guild.id == TARGET_GUILD_ID:
        await log_message("Message Delete", message.author, f"deleted: \"{message.content}\"")

@bot.event
async def on_voice_state_update(member, before, after):
    """Log when a user mutes/unmutes or joins/leaves a voice channel."""
    if member.guild.id == TARGET_GUILD_ID:
        if before.self_mute != after.self_mute:
            action = "muted" if after.self_mute else "unmuted"
            await log_message("Voice State Update", member, f"has {action} themselves.")

        if before.self_deaf != after.self_deaf:
            action = "deafened" if after.self_deaf else "undeafened"
            await log_message("Voice State Update", member, f"has {action} themselves.")

        # Log when a user joins or leaves a voice channel
        if before.channel is None and after.channel is not None:
            await log_message("Voice Channel Join", member, f"has joined the voice channel: **{after.channel.name}**")
        elif before.channel is not None and after.channel is None:
            await log_message("Voice Channel Leave", member, f"has left the voice channel: **{before.channel.name}**")

@bot.event
async def on_member_update(before, after):
    """Log when a user is assigned or removed from a role or changes their nickname."""
    if before.guild.id == TARGET_GUILD_ID:
        if before.roles != after.roles:
            added_roles = [role for role in after.roles if role not in before.roles]
            removed_roles = [role for role in before.roles if role not in after.roles]
            
            for role in added_roles:
                await log_message("Role Update", after, f"has been given the role: **{role.name}**")
            
            for role in removed_roles:
                await log_message("Role Update", after, f"has been removed from the role: **{role.name}**")

        # Log when a user changes their nickname
        if before.nick != after.nick:
            await log_message("Nickname Change", before, 
                              f"changed their nickname from **{before.nick}** to **{after.nick}**")

@bot.event
async def on_guild_channel_create(channel):
    """Log when a channel is created."""
    if channel.guild.id == TARGET_GUILD_ID:
        await log_message("Channel Create", channel.guild, f"Channel created: **{channel.name}**")

@bot.event
async def on_guild_channel_delete(channel):
    """Log when a channel is deleted."""
    if channel.guild.id == TARGET_GUILD_ID:
        await log_message("Channel Delete", channel.guild, f"Channel deleted: **{channel.name}**")

@bot.event
async def on_member_ban(guild, member):
    """Log when a user is banned."""
    if guild.id == TARGET_GUILD_ID:
        await log_message("Member Ban", member, "has been banned from the server.")

@bot.event
async def on_member_unban(guild, member):
    """Log when a user is unbanned."""
    if guild.id == TARGET_GUILD_ID:
        await log_message("Member Unban", member, "has been unbanned from the server.")

@bot.event
async def on_bulk_message_delete(messages):
    """Log when multiple messages are deleted."""
    if messages[0].guild.id == TARGET_GUILD_ID:  # Check the guild of the first message
        await log_message("Bulk Message Delete", messages[0].author, f"{len(messages)} messages have been deleted.")

@bot.event
async def on_invite_create(invite):
    """Log when a user invites someone to the server."""
    if invite.guild.id == TARGET_GUILD_ID:
        await log_message("Invite Create", invite.inviter, f"Invite created: {invite.code}")

@bot.event
async def on_ready():
    """Run when the bot is ready."""
    bot.loop.create_task(log_worker())  # Start the log worker in your bot's startup
    print(f'Bot is ready and logged in as {bot.user.name}')



bot.run('YOUR_BOT_TOKEN')
    
