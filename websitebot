import discord
from discord import app_commands
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')

# Set up intents and client
intents = discord.Intents.default()
intents.voice_states = True  # Enable voice state intents
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

@client.event
async def on_ready():
    print(f'{client.user} has connected to Discord!')
    await tree.sync()

@client.event
async def on_voice_state_update(member, before, after):
    # Check if the user joined a voice channel
    if after.channel is not None and member != client.user:
        # Provide a link to the video when a user joins
        await after.channel.send(f"{member.mention} has joined the voice channel! Watch the video here: [Watch Video](https://www.google.com)")  # Replace with your video link

@tree.command(name="join_video", description="Join a voice channel to watch a video together")
async def join_video(interaction: discord.Interaction):
    if interaction.user.voice:
        channel = interaction.user.voice.channel
        await interaction.response.send_message(f"Joining {channel.name} to watch a video together!")
        # You can add logic here to join the voice channel if needed
    else:
        await interaction.response.send_message("You need to be in a voice channel to use this command.")

client.run(DISCORD_TOKEN)
