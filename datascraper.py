import discord
from discord.ext import commands
import asyncio

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

async def log_worker():
    while True:
        message = await log_queue.get()  # Use await to get from asyncio.Queue
        await log_to_channel(message)
        log_queue.task_done()
        await asyncio.sleep(1)  # Adjust the sleep time as needed

async def log_to_channel(message):
    channel = bot.get_channel(LOG_CHANNEL_ID)
    if channel:
        try:
            await channel.send(message)
        except discord.HTTPException as e:
            if e.status == 429:  # Rate limit error
                retry_after = int(e.response.headers.get('Retry-After', 1))
                await asyncio.sleep(retry_after)  # Wait for the specified time
                await log_to_channel(message)  # Retry sending the message

# Log when a member joins the server
@bot.event
async def on_member_join(member):
    if member.guild.id == TARGET_GUILD_ID:
        await log_queue.put(f'**{member.name}** has joined the server.')

# Log when a member leaves the server
@bot.event
async def on_member_remove(member):
    if member.guild.id == TARGET_GUILD_ID:
        await log_queue.put(f'**{member.name}** has left the server.')

# Log messages sent in the server
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    if message.guild.id == TARGET_GUILD_ID:
        await log_queue.put(f'**Message from {message.author.name}:** {message.content}')

# Log when a message is edited
@bot.event
async def on_message_edit(before, after):
    if before.guild.id == TARGET_GUILD_ID:
        await log_queue.put(f'**Message edited by {before.author.name}:**\n'
                             f'**Before:** "{before.content}"\n'
                             f'**After:** "{after.content}"')

# Log when a message is deleted
@bot.event
async def on_message_delete(message):
    if message.guild.id == TARGET_GUILD_ID:
        await log_queue.put(f'**Message deleted by {message.author.name}:** "{message.content}"')

# Log when a user mutes themselves
@bot.event
async def on_voice_state_update(member, before, after):
    if member.guild.id == TARGET_GUILD_ID:
        if before.self_mute != after.self_mute:
            if after.self_mute:
                await log_queue.put(f'**{member.name}** has muted themselves.')
            else:
                await log_queue.put(f'**{member.name}** has unmuted themselves.')

        if before.self_deaf != after.self_deaf:
            if after.self_deaf:
                await log_queue.put(f'**{member.name}** has deafened themselves.')
            else:
                await log_queue.put(f'**{member.name}** has undeafened themselves.')

        # Log when a user joins or leaves a voice channel
        if before.channel is None and after.channel is not None:
            await log_queue.put(f'**{member.name}** has joined the voice channel: **{after.channel.name}**')
        elif before.channel is not None and after.channel is None:
            await log_queue.put(f'**{member.name}** has left the voice channel: **{before.channel.name}**')

# Log when a user is assigned or removed from a role
@bot.event
async def on_member_update(before, after):
    if before.guild.id == TARGET_GUILD_ID:
        if before.roles != after.roles:
            added_roles = [role for role in after.roles if role not in before.roles]
            removed_roles = [role for role in before.roles if role not in after.roles]
            
            for role in added_roles:
                await log_queue.put(f'**{after.name}** has been given the role: **{role.name}**')
            
            for role in removed_roles:
                await log_queue.put(f'**{after.name}** has been removed from the role: **{role.name}**')

        # Log when a user changes their nickname
        if before.nick != after.nick:
            await log_queue.put(f'**{before.name}** changed their nickname from **{before.nick}** to **{after.nick}**')

# Log when a channel is created
@bot.event
async def on_guild_channel_create(channel):
    if channel.guild.id == TARGET_GUILD_ID:
        await log_queue.put(f'**Channel created:** **{channel.name}**')

# Log when a channel is deleted
@bot.event
async def on_guild_channel_delete(channel):
    if channel.guild.id == TARGET_GUILD_ID:
        await log_queue.put(f'**Channel deleted:** **{channel.name}**')

# Log when a user is banned
@bot.event
async def on_member_ban(guild, member):
    if guild.id == TARGET_GUILD_ID:
        await log_queue.put(f'**{member.name}** has been banned from the server.')

# Log when a user is unbanned
@bot.event
async def on_member_unban(guild, member):
    if guild.id == TARGET_GUILD_ID:
        await log_queue.put(f'**{member.name}** has been unbanned from the server.')

# Log when a user is kicked
@bot.event
async def on_member_remove(member):
    if member.guild.id == TARGET_GUILD_ID:
        await log_queue.put(f'**{member.name}** has been kicked from the server.')

# Log when multiple messages are deleted
@bot.event
async def on_bulk_message_delete(messages):
    if messages[0].guild.id == TARGET_GUILD_ID:  # Check the guild of the first message
        await log_queue.put(f'**{len(messages)} messages have been deleted.**')

# Log when a user invites someone to the server
@bot.event
async def on_invite_create(invite):
    if invite.guild.id == TARGET_GUILD_ID:
        await log_queue.put(f'**Invite created:** {invite.code} by **{invite.inviter.name}**')

# Run the bot
@bot.event
async def on_ready():
    # Start the log worker in your bot's startup
    bot.loop.create_task(log_worker())

bot.run('YOUR_BOT_TOKEN')
    
