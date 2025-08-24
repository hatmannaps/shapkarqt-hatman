import os
import random
import asyncio
import json
from pathlib import Path
import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv
import stats

from memory import add_message_words, get_all_words, make_sentence

# ---------------------------
# 🔹 Load Token
# ---------------------------
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise SystemExit("⚠️ No DISCORD_TOKEN found in .env")

# ---------------------------
# 🔹 Friend Tracking Config
# ---------------------------
FRIEND_ID = 1090902910168203276 
ACTIVITY_FILE = Path("data/activity_hours.json")

# Ensure the activity file exists
ACTIVITY_FILE.parent.mkdir(parents=True, exist_ok=True)
if not ACTIVITY_FILE.exists():
    with ACTIVITY_FILE.open("w", encoding="utf-8") as f:
        json.dump({str(FRIEND_ID): 0}, f)

# ---------------------------
# 🔹 Bot Setup
# ---------------------------
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.members = True  #

bot = commands.Bot(command_prefix="!", intents=intents)

# Track recent activity
last_activity = {}  # {channel_id: timestamp}
last_speaker = None

# ---------------------------
# 🔹 Helper Functions
# ---------------------------
async def load_activity_hours():
    with ACTIVITY_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


async def save_activity_hours(data):
    with ACTIVITY_FILE.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def get_most_active_channel(guild: discord.Guild):
    """Return the channel with recent human activity (last 2 minutes)."""
    now = asyncio.get_event_loop().time()
    active = [(cid, t) for cid, t in last_activity.items() if now - t < 120]
    if not active:
        return None
    cid, _ = max(active, key=lambda x: x[1])
    return guild.get_channel(cid)

# ---------------------------
# 🔹 Events
# ---------------------------
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    speak_loop.start()
    cryptic_dm_loop.start()
    track_friend_activity.start()
    announce_friend_hours.start()


@bot.event
async def on_message(message: discord.Message):
    global last_speaker

    if message.author.bot:
        return

    # Learn words
    await add_message_words(str(message.author.id), message.content)

    # Update channel activity
    last_activity[message.channel.id] = message.created_at.timestamp()
    last_speaker = message.author.id

    # Reply with 20% chance
    if random.random() < 0.2:
        words = await get_all_words()
        sentence = make_sentence(words)
        await message.reply(sentence)

    await bot.process_commands(message)


# ---------------------------
# 🔹 Loops
# ---------------------------
@tasks.loop(seconds=30)
async def speak_loop():
    """Occasionally speak in the most active channel."""
    for guild in bot.guilds:
        channel = get_most_active_channel(guild)
        if not channel:
            continue
        # Only speak if humans are talking
        if last_speaker == bot.user.id:
            continue
        # 50% chance
        if random.random() < 0.5:
            words = await get_all_words()
            sentence = make_sentence(words)
            await channel.send(sentence)


@tasks.loop(minutes=5)
async def cryptic_dm_loop():
    """Rarely DM random human users cryptic messages."""
    for guild in bot.guilds:
        members = [m for m in guild.members if not m.bot]
        if not members:
            continue
        if random.random() < 0.01:  # 1% chance
            user = random.choice(members)
            words = await get_all_words()
            if not words:
                continue
            message = make_sentence(words, min_len=3, max_len=7)
            try:
                await user.send(message)
            except:
                pass  # ignore failures if DMs are closed


@tasks.loop(seconds=60)
async def track_friend_activity():
    """embed for pepi"""
    for guild in bot.guilds:
        member = guild.get_member(FRIEND_ID)
        if not member:
             print(f"Friend not found in guild {guild.name}")
            continue
        # check for game
        print(f"Checking activities for {member.display_name}: {member.activities}")
        playing = any(act.type == discord.ActivityType.playing for act in member.activities)
        if playing:
               print(f"{member.display_name} is playing!")
            data = await load_activity_hours()
            data[str(FRIEND_ID)] = data.get(str(FRIEND_ID), 0) + 60  # add 60 seconds
            await save_activity_hours(data)


@tasks.loop(minutes=30)
async def announce_friend_hours():
    """embed"""
    for guild in bot.guilds:
        member = guild.get_member(FRIEND_ID)
        if not member:
            continue
        if random.random() < 0.1:  # 10% chance
            data = await load_activity_hours()
            total_seconds = data.get(str(FRIEND_ID), 0)
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60

            embed = discord.Embed(
                title="🎮 Gaming Stats",
                description=f"{member.display_name} has been gaming for **{hours}h {minutes}m**!",
                color=0xff4500
            )
            # random channel
            channels = [c for c in guild.text_channels if c.permissions_for(guild.me).send_messages]
            if channels:
                channel = random.choice(channels)
                await channel.send(embed=embed)

# ---------------------------
#  run
# ---------------------------
stats.setup(bot)
bot.run(TOKEN)
