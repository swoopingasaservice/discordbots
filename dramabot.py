import discord
import requests

TOKEN = <addyourdiscordbottoken>  # Replace with your bot token
CHANNEL_ID = <channelID>  # Replace with your channel ID
API_URL = 'http://localhost:443/api/messages'  # Adjust the URL if needed

intents = discord.Intents.default()
intents.messages = True  # Ensure that the bot can read messages
intents.message_content = True  # Enable message content intent
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f'Logged in as {client.user}')

@client.event
async def on_message(message):
    # Log the entire message object for debugging
    print(f"Full message object: {message}")  # Log the entire message object
    # Check if the message is from the correct channel and is not from a bot
    if message.channel.id == CHANNEL_ID and not message.author.bot:
        # Log the message content and author for debugging
        print(f"Message received: '{message.content}' from {message.author}")
        # Send the message to your Express server
        requests.post(API_URL, json={'content': message.content, 'author': str(message.author)})

client.run(TOKEN)
