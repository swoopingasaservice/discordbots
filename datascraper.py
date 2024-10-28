import discord
from discord.ext import commands

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

# Replace with your channel ID
LOG_CHANNEL_ID = 1300179330940403777  # Replace with your actual channel ID

async def log_to_channel(message):
    channel = bot.get_channel(LOG_CHANNEL_ID)
    if channel:
        await channel.send(message)

# Log when a member joins the server
@bot.event
async def on_member_join(member):
    await log_to_channel(f'{member.name} has joined the server.')

# Log when a member leaves the server
@bot.event
async def on_member_remove(member):
    await log_to_channel(f'{member.name} has left the server.')

# Log messages sent in the server
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    await log_to_channel(f'Message from {message.author.name}: {message.content}')

# Log when a message is edited
@bot.event
async def on_message_edit(before, after):
    await log_to_channel(f'Message edited by {before.author.name}: "{before.content}" -> "{after.content}"')

# Log when a message is deleted
@bot.event
async def on_message_delete(message):
    await log_to_channel(f'Message deleted by {message.author.name}: "{message.content}"')

# Log when a user mutes themselves
@bot.event
async def on_voice_state_update(member, before, after):
    if before.self_mute != after.self_mute:
        if after.self_mute:
            await log_to_channel(f'{member.name} has muted themselves.')
        else:
            await log_to_channel(f'{member.name} has unmuted themselves.')

    if before.self_deaf != after.self_deaf:
        if after.self_deaf:
            await log_to_channel(f'{member.name} has deafened themselves.')
        else:
            await log_to_channel(f'{member.name} has undeafened themselves.')

    # Log when a user joins or leaves a voice channel
    if before.channel is None and after.channel is not None:
        await log_to_channel(f'{member.name} has joined the voice channel: {after.channel.name}')
    elif before.channel is not None and after.channel is None:
        await log_to_channel(f'{member.name} has left the voice channel: {before.channel.name}')

# Log when a user is assigned or removed from a role
@bot.event
async def on_member_update(before, after):
    if before.roles != after.roles:
        added_roles = [role for role in after.roles if role not in before.roles]
        removed_roles = [role for role in before.roles if role not in after.roles]
        
        for role in added_roles:
            await log_to_channel(f'{after.name} has been given the role: {role.name}')
        
        for role in removed_roles:
            await log_to_channel(f'{after.name} has been removed from the role: {role.name}')

    # Log when a user changes their nickname
    if before.nick != after.nick:
        await log_to_channel(f'{before.name} changed their nickname from {before.nick} to {after.nick}')

# Log when a channel is created
@bot.event
async def on_guild_channel_create(channel):
    await log_to_channel(f'Channel created: {channel.name}')

# Log when a channel is deleted
@bot.event
async def on_guild_channel_delete(channel):
    await log_to_channel(f'Channel deleted: {channel.name}')

# Log when a user is banned
@bot.event
async def on_member_ban(guild, member):
    await log_to_channel(f'{member.name} has been banned from the server.')

# Log when a user is unbanned
@bot.event
async def on_member_unban(guild, member):
    await log_to_channel(f'{member.name} has been unbanned from the server.')

# Log when a user is kicked
@bot.event
async def on_member_remove(member):
    await log_to_channel(f'{member.name} has been kicked from the server.')

# Log when multiple messages are deleted
@bot.event
async def on_bulk_message_delete(messages):
    await log_to_channel(f'{len(messages)} messages have been deleted.')

# Log when a user invites someone to the server
@bot.event
async def on_invite_create(invite):
    await log_to_channel(f'Invite created: {invite.code} by {invite.inviter.name}')


# Run the bot
bot.run('BOT_TOKEN')
