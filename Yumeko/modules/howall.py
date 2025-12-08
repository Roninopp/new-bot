import random
from pyrogram import Client, filters
from pyrogram.types import Message
from Yumeko import app
import config

# GIF URLs
HOT = "https://telegra.ph/file/daad931db960ea40c0fca.gif"
SMEXY = "https://telegra.ph/file/a23e9fd851fb6bc771686.gif"
LEZBIAN = "https://telegra.ph/file/5609b87f0bd461fc36acb.gif"
BIGBALL = "https://i.gifer.com/8ZUg.gif"
LANG = "https://telegra.ph/file/423414459345bf18310f5.gif"
CUTIE = "https://64.media.tumblr.com/d701f53eb5681e87a957a547980371d2/tumblr_nbjmdrQyje1qa94xto1_500.gif"
SMART = "https://i.pinimg.com/originals/04/45/b6/0445b6b3b9a16a99b0c8e7b4f9d7a94c.gif"
LOVE = "https://i.pinimg.com/originals/e5/3a/7e/e53a7e5b7d1f9c5f3b8b3f7e5a3b7e5b.gif"
SIGMA = "https://media.tenor.com/x8v1oNUOmg4AAAAd/gigachad-chad.gif"
CRINGE = "https://media1.tenor.com/m/9HZ5RQVCwOUAAAAC/goofy-ahh.gif"

@app.on_message(filters.command("horny", prefixes=config.config.COMMAND_PREFIXES) & filters.group)
async def horny(client: Client, message: Message):
    user = message.from_user
    mention = user.mention
    mm = random.randint(1, 100)
    
    HORNY = f"**🔥 {mention} is {mm}% Horny!**"
    await message.reply_animation(animation=HOT, caption=HORNY)

@app.on_message(filters.command("gay", prefixes=config.config.COMMAND_PREFIXES) & filters.group)
async def gay(client: Client, message: Message):
    user = message.from_user
    mention = user.mention
    mm = random.randint(1, 100)
    
    GAY = f"**🏳️‍🌈 {mention} is {mm}% Gay!**"
    await message.reply_animation(animation=SMEXY, caption=GAY)

@app.on_message(filters.command("lesbian", prefixes=config.config.COMMAND_PREFIXES) & filters.group)
async def lesbian(client: Client, message: Message):
    user = message.from_user
    mention = user.mention
    mm = random.randint(1, 100)
    
    FEK = f"**💜 {mention} is {mm}% Lesbian!**"
    await message.reply_animation(animation=LEZBIAN, caption=FEK)

@app.on_message(filters.command("boobs", prefixes=config.config.COMMAND_PREFIXES) & filters.group)
async def boobs(client: Client, message: Message):
    user = message.from_user
    mention = user.mention
    mm = random.randint(1, 100)
    
    BOOBS = f"**🍒 {mention}'s Boobs Size is {mm}!**"
    await message.reply_animation(animation=BIGBALL, caption=BOOBS)

@app.on_message(filters.command("cock", prefixes=config.config.COMMAND_PREFIXES) & filters.group)
async def cock(client: Client, message: Message):
    user = message.from_user
    mention = user.mention
    mm = random.randint(1, 100)
    
    COCK = f"**🍆 {mention}'s Cock Size is {mm}cm**"
    await message.reply_animation(animation=LANG, caption=COCK)

@app.on_message(filters.command("cute", prefixes=config.config.COMMAND_PREFIXES) & filters.group)
async def cute(client: Client, message: Message):
    user = message.from_user
    mention = user.mention
    mm = random.randint(1, 100)
    
    CUTE = f"**🍑 {mention} is {mm}% Cute**"
    await message.reply_animation(animation=CUTIE, caption=CUTE)

# NEW FEATURES BELOW

@app.on_message(filters.command("smart", prefixes=config.config.COMMAND_PREFIXES) & filters.group)
async def smart(client: Client, message: Message):
    user = message.from_user
    mention = user.mention
    mm = random.randint(1, 100)
    
    SMART_TEXT = f"**🧠 {mention} is {mm}% Smart!**"
    await message.reply_animation(animation=SMART, caption=SMART_TEXT)

@app.on_message(filters.command("love", prefixes=config.config.COMMAND_PREFIXES) & filters.group)
async def love(client: Client, message: Message):
    user = message.from_user
    mention = user.mention
    mm = random.randint(1, 100)
    
    LOVE_TEXT = f"**💖 {mention} is {mm}% Lovely!**"
    await message.reply_animation(animation=LOVE, caption=LOVE_TEXT)

@app.on_message(filters.command("sigma", prefixes=config.config.COMMAND_PREFIXES) & filters.group)
async def sigma(client: Client, message: Message):
    user = message.from_user
    mention = user.mention
    mm = random.randint(1, 100)
    
    SIGMA_TEXT = f"**😎 {mention} is {mm}% Sigma Male!**"
    await message.reply_animation(animation=SIGMA, caption=SIGMA_TEXT)

@app.on_message(filters.command("cringe", prefixes=config.config.COMMAND_PREFIXES) & filters.group)
async def cringe(client: Client, message: Message):
    user = message.from_user
    mention = user.mention
    mm = random.randint(1, 100)
    
    CRINGE_TEXT = f"**🤡 {mention} is {mm}% Cringe!**"
    await message.reply_animation(animation=CRINGE, caption=CRINGE_TEXT)

@app.on_message(filters.command("lucky", prefixes=config.config.COMMAND_PREFIXES) & filters.group)
async def lucky(client: Client, message: Message):
    user = message.from_user
    mention = user.mention
    mm = random.randint(1, 100)
    
    LUCKY_TEXT = f"**🍀 {mention} is {mm}% Lucky today!**"
    await message.reply_text(LUCKY_TEXT)

@app.on_message(filters.command("ship", prefixes=config.config.COMMAND_PREFIXES) & filters.group)
async def ship(client: Client, message: Message):
    if not message.reply_to_message:
        await message.reply_text("**❌ Reply to someone to ship them!**")
        return
    
    user1 = message.from_user
    user2 = message.reply_to_message.from_user
    
    if user1.id == user2.id:
        await message.reply_text("**💔 You can't ship yourself!**")
        return
    
    compatibility = random.randint(1, 100)
    
    if compatibility < 30:
        emoji = "💔"
        status = "Terrible Match!"
    elif compatibility < 50:
        emoji = "😐"
        status = "Not Great..."
    elif compatibility < 70:
        emoji = "💕"
        status = "Good Match!"
    elif compatibility < 90:
        emoji = "💖"
        status = "Great Match!"
    else:
        emoji = "💘"
        status = "Perfect Match!"
    
    SHIP_TEXT = (
        f"**{emoji} Ship Result {emoji}**\n\n"
        f"**{user1.first_name}** 💕 **{user2.first_name}**\n\n"
        f"**Compatibility:** {compatibility}%\n"
        f"**Status:** {status}"
    )
    await message.reply_text(SHIP_TEXT)

__help__ = """
**🎮 Fun Commands:**

**Percentage Games:**
• `/horny` - Check your horny level 🔥
• `/gay` - Check your gay percentage 🏳️‍🌈
• `/lesbian` - Check your lesbian percentage 💜
• `/boobs` - Check boobs size 🍒
• `/cock` - Check cock size 🍆
• `/cute` - Check cuteness level 🍑
• `/smart` - Check intelligence level 🧠
• `/love` - Check how lovely you are 💖
• `/sigma` - Check your sigma male percentage 😎
• `/cringe` - Check your cringe level 🤡
• `/lucky` - Check today's luck 🍀

**Interactive:**
• `/ship` - Ship two users together (reply to someone) 💘

**Note:** These are just for fun, don't take them seriously! 😄
"""

__module__ = "Fun"
