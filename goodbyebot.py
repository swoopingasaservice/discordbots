import discord
from discord.ext import commands
from discord import FFmpegPCMAudio
from discord import app_commands  # Import app_commands for slash commands
import os
import asyncio

# Set up your bot with necessary intents
intents = discord.Intents.default()
intents.members = True  # To track member joins, leaves, kicks, bans, etc.
intents.messages = True  # To allow reading message content (for commands)
intents.voice_states = True  # To track voice state updates

bot = commands.Bot(command_prefix="!", intents=intents)

# Path to your sound file (make sure this file exists)
SOUND_FILE_PATH = "goodbyehorses5.mp4"  # Change this to your sound file's path

async def play_sound(channel):
    """Play sound in a given voice channel."""
    if not os.path.exists(SOUND_FILE_PATH):
        print("Sound file not found!")
        return

    # Join the voice channel
    if channel:
        vc = await channel.connect()

        # Play the sound
        vc.play(FFmpegPCMAudio(SOUND_FILE_PATH), after=lambda e: print('done', e))
        
        # Wait for the sound to finish, then disconnect
        while vc.is_playing():
            await asyncio.sleep(1)
        
        await vc.disconnect()

@bot.tree.command(name="ping", description="Check if the bot is online.")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("Pong!")

@bot.tree.command(name="disconnect", description="Disconnect a member from a voice channel and play a sound.")
@app_commands.describe(member="The member to disconnect")
@commands.has_permissions(administrator=True)  # Ensure only admins can use this command
async def disconnect(interaction: discord.Interaction, member: discord.Member):
    """Disconnect a member from a voice channel and play a sound."""
    if member.voice:
        channel = member.voice.channel
        await member.move_to(None)  # Disconnect the member from the voice channel
        await play_sound(channel)  # Play the sound in the channel they were in
        await interaction.response.send_message(f"{member.mention} has been disconnected from the voice channel.")
    else:
        await interaction.response.send_message(f"{member.mention} is not in a voice channel.")

@bot.event
async def on_ready():
    """Sync the commands when the bot is ready."""
    await bot.tree.sync()
    print(f'Logged in as {bot.user}!')

@bot.event
async def on_member_ban(guild, user):
    """When a user is banned, play a sound in a voice channel."""
    print(f"{user} was banned from {guild.name}")
    
    # Find a voice channel to play the sound
    channel = discord.utils.get(guild.voice_channels, limit=1)  # Just get the first voice channel
    if channel:
        await play_sound(channel)  # Pass the channel to play_sound
    else:
        print(f"No voice channels found in {guild.name}.")

@bot.event
async def on_member_kick(member):
    """When a user is kicked, play a sound in a voice channel."""
    print(f"{member} was kicked from {member.guild.name}")
    
    # Find a voice channel to play the sound
    channel = discord.utils.get(member.guild.voice_channels, limit=1)  # Just get the first voice channel
    if channel:
        await play_sound(channel)  # Pass the channel to play_sound
    else:
        print(f"No voice channels found in {member.guild.name}.")

@bot.event
async def on_voice_state_update(member, before, after):
    """When a user disconnects from a voice channel, do not play a sound."""
    # This event is no longer needed for sound playback
    pass


# Run the bot with your token
bot.run('MTMwNDg5MTY1Njk4MTQ0NjY1Ng.GuesCu.kG4gQyVdSpT6N5hRuLVTmDWYw1GCO4r1RJn_uI')
