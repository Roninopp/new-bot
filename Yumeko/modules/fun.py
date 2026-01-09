import random
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from pyrogram.enums import ParseMode
from Yumeko import app as bot
from Yumeko.vars import HUG_IMAGES, SLAP_IMAGES, KICK_IMAGES, KISS_IMAGES, PAT_IMAGES, SEX_IMAGES
import httpx
from Yumeko.vars import command_to_category
from httpx import RequestError
from config import config 
from Yumeko.decorator.save import save 
from Yumeko.decorator.errors import error


BASE_URL = config.BASE_URL

# Command handler for /hug
@bot.on_message(filters.command("hug", prefixes=config.COMMAND_PREFIXES) & filters.group)
@error
@save
async def hug_command(client: Client, message: Message):
    if not message.reply_to_message and len(message.command) < 2:
        await message.reply_text("𝗬𝗼𝘂 𝗻𝗲𝗲𝗱 𝘁𝗼 𝗿𝗲𝗽𝗹𝘆 𝘁𝗼 𝗮 𝘂𝘀𝗲𝗿'𝘀 𝗺𝗲𝘀𝘀𝗮𝗴𝗲 𝗼𝗿 𝗽𝗿𝗼𝘃𝗶𝗱𝗲 𝗮 𝘂𝘀𝗲𝗿𝗻𝗮𝗺𝗲 𝘁𝗼 𝘀𝗲𝗻𝗱 𝗮 𝗵𝘂𝗴 𝗿𝗲𝗾𝘂𝗲𝘀𝘁.")
        return

    user_a = message.from_user

    if message.reply_to_message:
        user_b = message.reply_to_message.from_user
    else:
        username = message.command[1]
        try:
            user_b = await client.get_users(username)
        except Exception as e:
            await message.reply_text(f"𝗖𝗼𝘂𝗹𝗱 𝗻𝗼𝘁 𝗳𝗶𝗻𝗱 𝘂𝘀𝗲𝗿 {username}.")
            return

    bot_id = (await client.get_me()).id
    if user_b.id == bot_id:
        await message.reply_text("𝑁𝑜 𝑡ℎ𝑎𝑛𝑘𝑠, 𝐼 𝑑𝑜𝑛'𝑡 𝑛𝑒𝑒𝑑 𝑎 ℎ𝑢𝑔 𝑟𝑖𝑔ℎ𝑡 𝑛𝑜𝑤.")
        return

    if user_a.id == user_b.id:
        await message.reply_text("𝑌𝑜𝑢 𝑐𝑎𝑛𝑛𝑜𝑡 𝑠𝑒𝑛𝑑 𝑎 ℎ𝑢𝑔 𝑟𝑒𝑞𝑢𝑒𝑠𝑡 𝑡𝑜 𝑦𝑜𝑢𝑟𝑠𝑒𝑙𝑓.")
        return

    inline_keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("𝗔𝗰𝗰𝗲𝗽𝘁", callback_data=f"accept_hug:{user_a.id}:{user_b.id}")]
        ]
    )

    await message.reply_text(
        f"🤗 **[{user_b.first_name}](tg://user?id={user_b.id})**, **[{user_a.first_name}](tg://user?id={user_a.id})** wants to send you a hug! 🤗\n\n"
        "Will you accept the hug?",
        reply_markup=inline_keyboard,
        parse_mode=ParseMode.MARKDOWN
    )

@bot.on_callback_query(filters.regex(r"^accept_hug:(\d+):(\d+)$"))
@error
async def accept_hug_callback(client: Client, callback_query):
    data = callback_query.data.split(":")
    user_a_id = int(data[1])
    user_b_id = int(data[2])

    user_a = await client.get_users(user_a_id)
    user_b = await client.get_users(user_b_id)

    if callback_query.from_user.id != user_b.id:
        await callback_query.answer("𝗕𝘀𝗱𝗸 𝗼𝗻𝗹𝘆 𝘁𝗵𝗲 𝗿𝗲𝗰𝗶𝗽𝗶𝗲𝗻𝘁 𝗰𝗮𝗻 𝗮𝗰𝗰𝗲𝗽𝘁 𝘁𝗵𝗶𝘀 𝗵𝘂𝗴 𝗿𝗲𝗾𝘂𝗲𝘀𝘁.", show_alert=True)
        return

    hug_image_url = random.choice(HUG_IMAGES)
    await callback_query.message.delete()

    await client.send_photo(
        chat_id=callback_query.message.chat.id,
        photo=hug_image_url,
        caption=f"💞 **[{user_b.first_name}](tg://user?id={user_b.id})** accepted the hug from **[{user_a.first_name}](tg://user?id={user_a.id})**! 💞",
        parse_mode=ParseMode.MARKDOWN
    )

    await callback_query.answer()

# Command handler for /tickle
@bot.on_message(filters.command("tickle", prefixes=config.COMMAND_PREFIXES) & filters.group)
@error
@save
async def tickle_command(client: Client, message: Message):
    if not message.reply_to_message and len(message.command) < 2:
        await message.reply_text("𝗬𝗼𝘂 𝗻𝗲𝗲𝗱 𝘁𝗼 𝗿𝗲𝗽𝗹𝘆 𝘁𝗼 𝗮 𝘂𝘀𝗲𝗿'𝘀 𝗺𝗲𝘀𝘀𝗮𝗴𝗲 𝗼𝗿 𝗽𝗿𝗼𝘃𝗶𝗱𝗲 𝗮 𝘂𝘀𝗲𝗿𝗻𝗮𝗺𝗲 𝘁𝗼 𝘁𝗶𝗰𝗸𝗹𝗲 𝘁𝗵𝗲𝗺.")
        return

    user_a = message.from_user

    if message.reply_to_message:
        user_b = message.reply_to_message.from_user
    else:
        username = message.command[1]
        try:
            user_b = await client.get_users(username)
        except Exception as e:
            await message.reply_text(f"Could not find user {username}.")
            return

    bot_id = (await client.get_me()).id
    if user_b.id == bot_id:
        await message.reply_text("Haha! Nice try, but I'm tickle-proof! 🤖")
        return

    if user_a.id == user_b.id:
        await message.reply_text("Tickling yourself? That's... interesting! 😂")
        return

    await message.reply_text(
        f"😂 **[{user_a.first_name}](tg://user?id={user_a.id})** is tickling **[{user_b.first_name}](tg://user?id={user_b.id})**! "
        f"Can't stop laughing! 🤣✨",
        parse_mode=ParseMode.MARKDOWN
    )

# Command handler for /poke
@bot.on_message(filters.command("poke", prefixes=config.COMMAND_PREFIXES) & filters.group)
@error
@save
async def poke_command(client: Client, message: Message):
    if not message.reply_to_message and len(message.command) < 2:
        await message.reply_text("𝗬𝗼𝘂 𝗻𝗲𝗲𝗱 𝘁𝗼 𝗿𝗲𝗽𝗹𝘆 𝘁𝗼 𝗮 𝘂𝘀𝗲𝗿'𝘀 𝗺𝗲𝘀𝘀𝗮𝗴𝗲 𝗼𝗿 𝗽𝗿𝗼𝘃𝗶𝗱𝗲 𝗮 𝘂𝘀𝗲𝗿𝗻𝗮𝗺𝗲 𝘁𝗼 𝗽𝗼𝗸𝗲 𝘁𝗵𝗲𝗺.")
        return

    user_a = message.from_user

    if message.reply_to_message:
        user_b = message.reply_to_message.from_user
    else:
        username = message.command[1]
        try:
            user_b = await client.get_users(username)
        except Exception as e:
            await message.reply_text(f"Could not find user {username}.")
            return

    bot_id = (await client.get_me()).id
    if user_b.id == bot_id:
        await message.reply_text("Hey! Stop poking me! 👉😤")
        return

    if user_a.id == user_b.id:
        await message.reply_text("Poking yourself? Need attention? 😅")
        return

    await message.reply_text(
        f"👉 **[{user_a.first_name}](tg://user?id={user_a.id})** poked **[{user_b.first_name}](tg://user?id={user_b.id})**! "
        f"Hey! Pay attention! 👀",
        parse_mode=ParseMode.MARKDOWN
    )

# Command handler for /boop
@bot.on_message(filters.command("boop", prefixes=config.COMMAND_PREFIXES) & filters.group)
@error
@save
async def boop_command(client: Client, message: Message):
    if not message.reply_to_message and len(message.command) < 2:
        await message.reply_text("𝗬𝗼𝘂 𝗻𝗲𝗲𝗱 𝘁𝗼 𝗿𝗲𝗽𝗹𝘆 𝘁𝗼 𝗮 𝘂𝘀𝗲𝗿'𝘀 𝗺𝗲𝘀𝘀𝗮𝗴𝗲 𝗼𝗿 𝗽𝗿𝗼𝘃𝗶𝗱𝗲 𝗮 𝘂𝘀𝗲𝗿𝗻𝗮𝗺𝗲 𝘁𝗼 𝗯𝗼𝗼𝗽 𝘁𝗵𝗲𝗶𝗿 𝗻𝗼𝘀𝗲.")
        return

    user_a = message.from_user

    if message.reply_to_message:
        user_b = message.reply_to_message.from_user
    else:
        username = message.command[1]
        try:
            user_b = await client.get_users(username)
        except Exception as e:
            await message.reply_text(f"Could not find user {username}.")
            return

    bot_id = (await client.get_me()).id
    if user_b.id == bot_id:
        await message.reply_text("Boop! Right back at ya! 👃✨")
        return

    if user_a.id == user_b.id:
        await message.reply_text("Booping your own nose? That's adorable! 😊")
        return

    await message.reply_text(
        f"👃 **[{user_a.first_name}](tg://user?id={user_a.id})** booped **[{user_b.first_name}](tg://user?id={user_b.id})**'s nose! "
        f"Boop! So cute! 🥰",
        parse_mode=ParseMode.MARKDOWN
    )

# Command handler for /highfive
@bot.on_message(filters.command("highfive", prefixes=config.COMMAND_PREFIXES) & filters.group)
@error
@save
async def highfive_command(client: Client, message: Message):
    if not message.reply_to_message and len(message.command) < 2:
        await message.reply_text("𝗬𝗼𝘂 𝗻𝗲𝗲𝗱 𝘁𝗼 𝗿𝗲𝗽𝗹𝘆 𝘁𝗼 𝗮 𝘂𝘀𝗲𝗿'𝘀 𝗺𝗲𝘀𝘀𝗮𝗴𝗲 𝗼𝗿 𝗽𝗿𝗼𝘃𝗶𝗱𝗲 𝗮 𝘂𝘀𝗲𝗿𝗻𝗮𝗺𝗲 𝘁𝗼 𝗵𝗶𝗴𝗵-𝗳𝗶𝘃𝗲 𝘁𝗵𝗲𝗺.")
        return

    user_a = message.from_user

    if message.reply_to_message:
        user_b = message.reply_to_message.from_user
    else:
        username = message.command[1]
        try:
            user_b = await client.get_users(username)
        except Exception as e:
            await message.reply_text(f"Could not find user {username}.")
            return

    bot_id = (await client.get_me()).id
    if user_b.id == bot_id:
        await message.reply_text("✋ High five! Great job! 🎉")
        return

    if user_a.id == user_b.id:
        await message.reply_text("High-fiving yourself? That's just clapping with style! 👏")
        return

    await message.reply_text(
        f"✋ **[{user_a.first_name}](tg://user?id={user_a.id})** gave **[{user_b.first_name}](tg://user?id={user_b.id})** "
        f"an epic high-five! SLAP! 💥🙌",
        parse_mode=ParseMode.MARKDOWN
    )

# Command handler for /kickk
@bot.on_message(filters.command("kickk", prefixes=config.COMMAND_PREFIXES) & filters.group)
@error
@save
async def kick_command(client: Client, message: Message):
    if not message.reply_to_message and len(message.command) < 2:
        await message.reply_text("𝗬𝗼𝘂 𝗻𝗲𝗲𝗱 𝘁𝗼 𝗿𝗲𝗽𝗹𝘆 𝘁𝗼 𝗮 𝘂𝘀𝗲𝗿'𝘀 𝗺𝗲𝘀𝘀𝗮𝗴𝗲 𝗼𝗿 𝗽𝗿𝗼𝘃𝗶𝗱𝗲 𝗮 𝘂𝘀𝗲𝗿𝗻𝗮𝗺𝗲 𝘁𝗼 𝗸𝗶𝗰𝗸 𝘁𝗵𝗲𝗺.")
        return

    user_a = message.from_user

    if message.reply_to_message:
        user_b = message.reply_to_message.from_user
    else:
        username = message.command[1]
        try:
            user_b = await client.get_users(username)
        except Exception as e:
            await message.reply_text(f"Could not find user {username}.")
            return

    bot_id = (await client.get_me()).id
    if user_b.id == bot_id:
        await message.reply_text("Ouch! Kicking a bot is not nice.")
        return

    if user_a.id == user_b.id:
        await message.reply_text("You cannot kick yourself. That's just silly.")
        return

    kick_image_url = random.choice(KICK_IMAGES)

    await client.send_photo(
        chat_id=message.chat.id,
        photo=kick_image_url,
        caption=f"🥾 **[{user_a.first_name}](tg://user?id={user_a.id})** kicked **[{user_b.first_name}](tg://user?id={user_b.id})**! That must've hurt! 💥",
        parse_mode=ParseMode.MARKDOWN
    )

# Command handler for /kiss
@bot.on_message(filters.command("kiss", prefixes=config.COMMAND_PREFIXES) & filters.group)
@error
@save
async def kiss_command(client: Client, message: Message):
    if not message.reply_to_message and len(message.command) < 2:
        await message.reply_text("𝗬𝗼𝘂 𝗻𝗲𝗲𝗱 𝘁𝗼 𝗿𝗲𝗽𝗹𝘆 𝘁𝗼 𝗮 𝘂𝘀𝗲𝗿'𝘀 𝗺𝗲𝘀𝘀𝗮𝗴𝗲 𝗼𝗿 𝗽𝗿𝗼𝘃𝗶𝗱𝗲 𝗮 𝘂𝘀𝗲𝗿𝗻𝗮𝗺𝗲 𝘁𝗼 𝘀𝗲𝗻𝗱 𝗮 𝗸𝗶𝘀𝘀 𝗿𝗲𝗾𝘂𝗲𝘀𝘁.")
        return

    user_a = message.from_user

    if message.reply_to_message:
        user_b = message.reply_to_message.from_user
    else:
        username = message.command[1]
        try:
            user_b = await client.get_users(username)
        except Exception as e:
            await message.reply_text(f"Could not find user {username}.")
            return

    bot_id = (await client.get_me()).id
    if user_b.id == bot_id:
        await message.reply_text("Fuck off, I don't want a kiss from you.")
        return

    if user_a.id == user_b.id:
        await message.reply_text("Why are you single? You know, nowadays everyone is committed except you!")
        return

    inline_keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("𝗔𝗰𝗰𝗲𝗽𝘁", callback_data=f"accept_kiss:{user_a.id}:{user_b.id}")]
        ]
    )

    await message.reply_text(
        f"💞 **[{user_b.first_name}](tg://user?id={user_b.id})** see **[{user_a.first_name}](tg://user?id={user_a.id})** wants to kiss you! 💞\n\n"
        "Will you accept the kiss?",
        reply_markup=inline_keyboard,
        parse_mode=ParseMode.MARKDOWN
    )

@bot.on_callback_query(filters.regex(r"^accept_kiss:(\d+):(\d+)$"))
@error
async def accept_kiss_callback(client: Client, callback_query):
    data = callback_query.data.split(":")
    user_a_id = int(data[1])
    user_b_id = int(data[2])

    user_a = await client.get_users(user_a_id)
    user_b = await client.get_users(user_b_id)

    if callback_query.from_user.id != user_b.id:
        await callback_query.answer("𝗕𝘀𝗱𝗸 𝗼𝗻𝗹𝘆 𝘁𝗵𝗲 𝗿𝗲𝗰𝗶𝗽𝗶𝗲𝗻𝘁 𝗰𝗮𝗻 𝗮𝗰𝗰𝗲𝗽𝘁 𝘁𝗵𝗶𝘀 𝗸𝗶𝘀𝘀 𝗿𝗲𝗾𝘂𝗲𝘀𝘁.", show_alert=True)
        return

    kiss_image_url = random.choice(KISS_IMAGES)
    await callback_query.message.delete()

    await client.send_photo(
        chat_id=callback_query.message.chat.id,
        photo=kiss_image_url,
        caption=f"💋 **[{user_b.first_name}](tg://user?id={user_b.id})** accepted the kiss from **[{user_a.first_name}](tg://user?id={user_a.id})**! 💋",
        parse_mode=ParseMode.MARKDOWN
    )

    await callback_query.answer()

# Command handler for /pat
@bot.on_message(filters.command("pat", prefixes=config.COMMAND_PREFIXES) & filters.group)
@error
@save
async def pat_command(client: Client, message: Message):
    if not message.reply_to_message and len(message.command) < 2:
        await message.reply_text("𝗬𝗼𝘂 𝗻𝗲𝗲𝗱 𝘁𝗼 𝗿𝗲𝗽𝗹𝘆 𝘁𝗼 𝗮 𝘂𝘀𝗲𝗿'𝘀 𝗺𝗲𝘀𝘀𝗮𝗴𝗲 𝗼𝗿 𝗽𝗿𝗼𝘃𝗶𝗱𝗲 𝗮 𝘂𝘀𝗲𝗿𝗻𝗮𝗺𝗲 𝘁𝗼 𝗽𝗮𝘁 𝘁𝗵𝗲𝗺.")
        return

    user_a = message.from_user

    if message.reply_to_message:
        user_b = message.reply_to_message.from_user
    else:
        username = message.command[1]
        try:
            user_b = await client.get_users(username)
        except Exception as e:
            await message.reply_text(f"Could not find user {username}.")
            return

    bot_id = (await client.get_me()).id
    if user_b.id == bot_id:
        await message.reply_text("You can't pat a bot, but thanks for the gesture! 🤖")
        return

    if user_a.id == user_b.id:
        await message.reply_text("You can't pat yourself. You deserve pats from others!")
        return

    pat_image_url = random.choice(PAT_IMAGES)

    await client.send_photo(
        chat_id=message.chat.id,
        photo=pat_image_url,
        caption=f"🤗 **[{user_a.first_name}](tg://user?id={user_a.id})** gave a warm pat to **[{user_b.first_name}](tg://user?id={user_b.id})**! So sweet! 💖",
        parse_mode=ParseMode.MARKDOWN
    )

# Command handler for /sex
@bot.on_message(filters.command("sex", prefixes=config.COMMAND_PREFIXES) & filters.group)
@error
@save
async def sex_command(client: Client, message: Message):
    if not message.reply_to_message and len(message.command) < 2:
        await message.reply_text("𝗬𝗼𝘂 𝗻𝗲𝗲𝗱 𝘁𝗼 𝗿𝗲𝗽𝗹𝘆 𝘁𝗼 𝗮 𝘂𝘀𝗲𝗿'𝘀 𝗺𝗲𝘀𝘀𝗮𝗴𝗲 𝗼𝗿 𝗽𝗿𝗼𝘃𝗶𝗱𝗲 𝗮 𝘂𝘀𝗲𝗿𝗻𝗮𝗺𝗲 𝘁𝗼 𝘀𝗲𝗻𝗱 𝗮 𝘀𝗲𝘅 𝗿𝗲𝗾𝘂𝗲𝘀𝘁.")
        return

    user_a = message.from_user

    if message.reply_to_message:
        user_b = message.reply_to_message.from_user
    else:
        username = message.command[1]
        user_b = await client.get_users(username)

    bot_id = (await client.get_me()).id
    if user_b.id == bot_id:
        await message.reply_text("Fuck off, I don't want to have sex with you.")
        return

    if user_a.id == user_b.id:
        await message.reply_text("Why are you single? You know, nowadays everyone is committed except you!")
        return

    inline_keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("𝗔𝗰𝗰𝗲𝗽𝘁", callback_data=f"accept_sex:{user_a.id}:{user_b.id}")]
        ]
    )

    await message.reply_text(
        f"💞 **[{user_b.first_name}](tg://user?id={user_b.id})** see **[{user_a.first_name}](tg://user?id={user_a.id})** wants to have sex with you! 💞\n\n"
        "Will you accept?",
        reply_markup=inline_keyboard,
        parse_mode=ParseMode.MARKDOWN
    )

@bot.on_callback_query(filters.regex(r"^accept_sex:(\d+):(\d+)$"))
@error
async def accept_sex_callback(client: Client, callback_query):
    data = callback_query.data.split(":")
    user_a_id = int(data[1])
    user_b_id = int(data[2])

    user_a = await client.get_users(user_a_id)
    user_b = await client.get_users(user_b_id)

    if callback_query.from_user.id != user_b.id:
        await callback_query.answer("Only the recipient can accept this sex request.", show_alert=True)
        return

    sex_image_url = random.choice(SEX_IMAGES)
    await callback_query.message.delete()

    await client.send_photo(
        chat_id=callback_query.message.chat.id,
        photo=sex_image_url,
        caption=f"💋 **[{user_b.first_name}](tg://user?id={user_b.id})** had done sex with **[{user_a.first_name}](tg://user?id={user_a.id})**! 💋\n\nWhat do you think will they have a baby ?..",
        parse_mode=ParseMode.MARKDOWN
    )

    await callback_query.answer()

# Command handler for /slap
@bot.on_message(filters.command("slap", prefixes=config.COMMAND_PREFIXES) & filters.group)
@error
@save
async def slap_command(client: Client, message: Message):
    if not message.reply_to_message and len(message.command) < 2:
        await message.reply_text("𝗬𝗼𝘂 𝗻𝗲𝗲𝗱 𝘁𝗼 𝗿𝗲𝗽𝗹𝘆 𝘁𝗼 𝗮 𝘂𝘀𝗲𝗿'𝘀 𝗺𝗲𝘀𝘀𝗮𝗴𝗲 𝗼𝗿 𝗽𝗿𝗼𝘃𝗶𝗱𝗲 𝗮 𝘂𝘀𝗲𝗿𝗻𝗮𝗺𝗲 𝘁𝗼 𝘀𝗹𝗮𝗽 𝘁𝗵𝗲𝗺.")
        return

    user_a = message.from_user

    if message.reply_to_message:
        user_b = message.reply_to_message.from_user
    else:
        username = message.command[1]
        try:
            user_b = await client.get_users(username)
        except Exception as e:
            await message.reply_text(f"𝖢𝗈𝗎𝗅𝖽 𝗇𝗈𝗍 𝖿𝗂𝗇𝖽 𝗎�—Œ𝖾𝗋{username}.")
            return

    bot_id = (await client.get_me()).id
    if user_b.id == bot_id:
        await message.reply_text("𝖧𝖾𝗒, 𝖽𝗈𝗇'𝗍 𝗌𝗅𝖺𝗉 𝗆𝖾! 𝖨'𝗆 𝗃𝗎𝗌𝗍 𝖺 𝖻𝗈𝗍.")
        return

    if user_a.id == user_b.id:
        await message.reply_text("𝖸𝗈𝗎 𝖼𝖺𝗇𝗇𝗈𝗍 𝗌𝗅𝖺𝗉 𝗒𝗈𝗎𝗋𝗌𝖾𝗅𝖿. 𝖳𝗁𝖺𝗍'𝗌 𝗐𝖾𝗂𝗋𝖽.")
        return

    slap_image_url = random.choice(SLAP_IMAGES)

    await client.send_photo(
        chat_id=message.chat.id,
        photo=slap_image_url,
        caption=f"💋 **[{user_a.first_name}](tg://user?id={user_a.id})** slapped **[{user_b.first_name}](tg://user?id={user_b.id})**! That must've hurt! 💥",
        parse_mode=ParseMode.MARKDOWN
    )

# Function to fetch the image from the API
async def fetch_image(category: str) -> str:
    """Fetch an image URL from the waifu.pics API."""
    url = f"{BASE_URL}/sfw/{category}"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
            return data.get("url", None)
    except RequestError as e:
        return None
    except ValueError as e:
        return None
    except Exception as e:
        return None

@bot.on_message(filters.command(list(command_to_category.keys()), prefixes=config.COMMAND_PREFIXES))
@error
@save
async def send_waifu_image(client: Client, message: Message):
    """Send an image for the requested category."""
    command = message.text.strip("/").lower()
    category = command_to_category.get(command, command)

    try:
        image_url = await fetch_image(category)
        if image_url:
            await message.reply_photo(photo=image_url)
        else:
            await message.reply_text(
                f"𝖲𝗈𝗋𝗋𝗒, 𝖨 𝖼𝗈𝗎𝗅𝖽𝗇'𝗍 𝖿𝖾𝗍𝖼𝗁 𝖺𝗇 𝗂𝗆𝖺𝗀𝖾 𝖿𝗈𝗋 '{𝖼𝖺𝗍𝖾𝗀𝗈𝗋𝗒}'. 𝖯𝗅𝖾𝖺𝗌𝖾 𝗍𝗋𝗒 𝖺𝗀𝖺𝗂𝗇 𝗅𝖺𝗍𝖾𝗋."
            )
    except Exception as e:
        await message.reply_text(
            "𝖠𝗇 𝗎𝗇𝖾𝗑𝗉𝖾𝖼𝗍𝖾𝖽 𝖾𝗋𝗋𝗈𝗋 𝗈𝖼𝖼𝗎𝗋𝗋𝖾𝖽. 𝖯𝗅𝖾𝖺𝗌𝖾 𝗍𝗋𝗒 𝖺𝗀𝖺𝗂𝗇 𝗅𝖺𝗍𝖾𝗋 𝗈𝗋 𝖼𝗈𝗇𝗍𝖺𝖼𝗍 𝗍𝗁𝖾 𝖻𝗈𝗍 𝖺𝖽𝗆𝗂𝗇."
        )

__module__ = "𝖥𝗎𝗇"

__help__ = """**𝖴𝗌𝖾𝗋 𝖢𝗈𝗆𝗆𝖺𝗇𝖽𝗌:**
  ✧ `/𝗁𝗎𝗀`**:** Send a hug request to someone special!
  ✧ `/𝗄𝗂𝗌𝗌`**:** Send a kiss request to someone!
  ✧ `/𝗉𝖺𝗍`**:** Give someone a warm pat!
  ✧ `/𝗌𝗅𝖺𝗉`**:** Slap someone (playfully)!
  ✧ `/𝗄𝗂𝖼𝗄𝗄`**:** Kick someone (just for fun)!
  ✧ `/𝗌𝖾𝗑`**:** Send a spicy request!
  ✧ `/𝗍𝗂𝖼𝗄𝗅𝖾`**:** Tickle someone and make them laugh!
  ✧ `/𝗉𝗈𝗄𝖾`**:** Poke someone to get their attention!
  ✧ `/𝖻𝗈𝗈𝗉`**:** Boop someone's nose cutely!
  ✧ `/𝗁𝗂𝗀𝗁𝖿𝗂𝗏𝖾`**:** Give someone an epic high-five!

**𝖠𝗇𝗂𝗆𝖾 𝖨𝗆𝖺𝗀𝖾 𝖢𝗈𝗆𝗆𝖺𝗇𝖽𝗌:**
  ✧ `/𝗌𝗁𝗂𝗇𝗈𝖻𝗎`**:** Fetches a random Shinobu image.
  ✧ `/𝗆𝖾𝗀𝗎𝗆𝗂𝗇`**:** Fetches a random Megumin image.
  ✧ `/𝖻𝗎𝗅𝗅𝗒`**:** Fetches a random bully image.
  ✧ `/𝖼𝗎𝖽𝖽𝗅𝖾`**:** Fetches a random cuddle image.
  ✧ `/𝖼𝗋𝗒`**:** Fetches a random cry image.
  ✧ `/𝖺𝗐𝗈𝗈`**:** Fetches a random awoo image.
  ✧ `/𝗅𝗂𝖼𝗄`**:** Fetches a random lick image.
  ✧ `/𝗌𝗆𝗎𝗀`**:** Fetches a random smug image.
  ✧ `/𝗒𝖾𝖾𝗍`**:** Fetches a random yeet image.
  ✧ `/𝖻𝗅𝗎𝗌𝗁`**:** Fetches a random blush image.
  ✧ `/𝗌𝗆𝗂𝗅𝖾`**:** Fetches a random smile image.
  ✧ `/𝗐𝖺𝗏𝖾`**:** Fetches a random wave image.
  ✧ `/𝗁𝗂𝗀𝗁𝖿𝗂𝗏𝖾`**:** Fetches a random high-five image.
  ✧ `/𝗁𝖺𝗇𝖽𝗁𝗈𝗅𝖽`**:** Fetches a random hand-holding image.
  ✧ `/𝗇𝗈𝗆`**:** Fetches a random nom image.
  ✧ `/𝖻𝗂𝗍𝖾`**:** Fetches a random bite image.
  ✧ `/𝗀𝗅𝗈𝗆𝗉`**:** Fetches a random glomp image.
  ✧ `/𝗁𝖺𝗉𝗉𝗒`**:** Fetches a random happy image.
  ✧ `/𝗐𝗂𝗇𝗄`**:** Fetches a random wink image.
  ✧ `/𝖽𝖺𝗇𝖼𝖾`**:** Fetches a random dance image.
  ✧ `/𝖼𝗋𝗂𝗇𝗀𝖾`**:** Fetches a random cringe image.
 
𝖴𝗌𝖾 𝗍𝗁𝖾𝗌𝖾 𝖼𝗈𝗆𝗆𝖺𝗇𝖽𝗌 𝗍𝗈 𝗀𝖾𝗍 𝗋𝖺𝗇𝖽𝗈𝗆 𝖺𝗇𝗂𝗆𝖾-𝗌𝗍𝗒𝗅𝖾 𝗂𝗆𝖺𝗀𝖾𝗌 𝖿𝗋𝗈𝗆 𝗍𝗁𝖾 𝗐𝖺𝗂𝖿𝗎.𝗉𝗂𝖼𝗌 𝖠𝖯𝖨!
"""
