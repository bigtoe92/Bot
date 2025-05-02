import os
import discord
from discord.ext import commands, tasks
from datetime import datetime
import asyncio
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get the token from environment variables
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.reactions = True
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

CHANNEL_ID = 1359876124640809080
availability_message = None
message_id = None
availability_data = {}

EMOJI_TIMES = {
    "1️⃣": "10:00",
    "2️⃣": "11:00",
    "3️⃣": "12:00",
    "4️⃣": "13:00",
    "5️⃣": "14:00",
    "6️⃣": "15:00",
    "7️⃣": "16:00",
    "8️⃣": "17:00",
    "9️⃣": "18:00",
    "🔟": "19:00",
    "🔢": "20:00",
    "🕘": "21:00",
    "🕙": "22:00",
    "🕚": "23:00"
}

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    await asyncio.sleep(2)
    await setup_availability_message()
    check_old_messages.start()

async def setup_availability_message():
    global availability_message, message_id
    channel = await bot.fetch_channel(CHANNEL_ID)

    async for message in channel.history(limit=50):
        if message.author == bot.user and "Availability for" in message.content:
            availability_message = message
            message_id = message.id
            break

    if availability_message is None:
        availability_message = await channel.send(await build_message())
        message_id = availability_message.id
        for emoji in EMOJI_TIMES:
            await availability_message.add_reaction(emoji)
    else:
        await rebuild_availability_data()
        await update_message()

async def rebuild_availability_data():
    global availability_data
    availability_data = {emoji: [] for emoji in EMOJI_TIMES}
    message = availability_message
    for reaction in message.reactions:
        if reaction.emoji in EMOJI_TIMES:
            async for user in reaction.users():
                if user != bot.user:
                    availability_data[reaction.emoji].append(user.mention)

async def update_message():
    content = await build_message()
    await availability_message.edit(content=content)

async def build_message():
    date_str = datetime.now().strftime('%A, %B %d, %Y')
    message = f"**Availability for {date_str}:**\n"
    for emoji, time in EMOJI_TIMES.items():
        mentions = '\n'.join(availability_data.get(emoji, []))
        message += f"\n{emoji}: {time}"
        if mentions:
            message += f"\n{mentions}"
        message += "\n"
    return message

@bot.event
async def on_raw_reaction_add(payload):
    if payload.message_id != message_id:
        return

    emoji = str(payload.emoji)
    if emoji not in EMOJI_TIMES:
        return

    guild = bot.get_guild(payload.guild_id)
    member = guild.get_member(payload.user_id)
    if member and not member.bot:
        availability_data.setdefault(emoji, []).append(member.mention)
        await update_message()

@bot.event
async def on_raw_reaction_remove(payload):
    if payload.message_id != message_id:
        return

    emoji = str(payload.emoji)
    if emoji not in EMOJI_TIMES:
        return

    guild = bot.get_guild(payload.guild_id)
    member = guild.get_member(payload.user_id)
    if member and member.mention in availability_data.get(emoji, []):
        availability_data[emoji].remove(member.mention)
        await update_message()

@tasks.loop(minutes=1)
async def check_old_messages():
    now = datetime.now()
    if now.hour == 23:
        channel = await bot.fetch_channel(CHANNEL_ID)
        async for message in channel.history(limit=50):
            if message.author == bot.user and "Availability for" in message.content:
                await message.delete()
        await setup_availability_message()

# Start the bot using the token from env variable
if __name__ == "__main__":
    if not DISCORD_TOKEN:
        raise ValueError("DISCORD_TOKEN not set in environment variables.")
    bot.run(DISCORD_TOKEN)
