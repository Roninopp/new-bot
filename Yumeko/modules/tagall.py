import asyncio
import random
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import FloodWait
from pyrogram.enums import ChatMemberStatus, ChatMembersFilter
from Yumeko import app
import config

# Store active mention processes
active_mentions = {}

# Cool emoji list for mentions
MENTION_EMOJIS = [
    "😀", "😃", "😄", "😁", "😆", "😅", "🤣", "😂", "🙂", "🙃", "😉", "😊", "😇", "🥰", "😍", "🤩", "😘", "😗", "😚", "😙",
    "🥲", "😋", "😛", "😜", "🤪", "😝", "🤑", "🤗", "🤭", "🤫", "🤔", "🤐", "🤨", "😐", "😑", "😶", "😏", "😒", "🙄", "😬",
    "😌", "😔", "😪", "🤤", "😴", "😷", "🤒", "🤕", "🤢", "🤮", "🤧", "🥵", "🥶", "🥴", "😵", "🤯", "🤠", "🥳", "🥸", "😎",
    "🤓", "🧐", "😕", "😟", "🙁", "☹️", "😮", "😯", "😲", "😳", "🥺", "😦", "😧", "😨", "😰", "😥", "😢", "😭", "😱", "😖",
    "😣", "😞", "😓", "😩", "😫", "🥱", "😤", "😡", "😠", "🤬", "😈", "👿", "💀", "☠️", "💩", "🤡", "👹", "👺", "👻", "👽",
    "👾", "🤖", "😺", "😸", "😹", "😻", "😼", "😽", "🙀", "😿", "😾", "🙈", "🙉", "🙊", "💋", "💌", "💘", "💝", "💖", "💗",
    "💓", "💞", "💕", "💟", "❣️", "💔", "❤️", "🧡", "💛", "💚", "💙", "💜", "🤎", "🖤", "🤍", "💯", "💢", "💥", "💫", "💦",
    "💨", "💣", "💬", "👁️", "💭", "💤", "👋", "🤚", "🖐️", "✋", "🖖", "👌", "🤌", "🤏", "✌️", "🤞", "🤟", "🤘", "🤙", "👈",
    "👉", "👆", "🖕", "👇", "☝️", "👍", "👎", "✊", "👊", "🤛", "🤜", "👏", "🙌", "👐", "🤲", "🤝", "🙏", "✍️", "💅", "🤳",
    "💪", "🦾", "🦵", "🦶", "👂", "🦻", "👃", "🧠", "🦷", "🦴", "👀", "👅", "👄", "🧑", "👶", "🧒", "👦", "👧", "👨", "👩",
    "🧔", "👴", "👵", "🙍", "🙎", "🙅", "🙆", "💁", "🙋", "🧏", "🙇", "🤦", "🤷", "👮", "🕵️", "💂", "🥷", "👷", "🤴", "👸",
    "👳", "👲", "🧕", "🤵", "👰", "🤰", "🤱", "👼", "🎅", "🤶", "🦸", "🦹", "🧙", "🧚", "🧛", "🧜", "🧝", "🧞", "🧟", "💆",
    "💇", "🚶", "🧍", "🧎", "🏃", "💃", "🕺", "🕴️", "👯", "🧖", "🧗", "🤺", "🏇", "⛷️", "🏂", "🏌️", "🏄", "🚣", "🏊", "⛹️",
    "🏋️", "🚴", "🚵", "🤸", "🤼", "🤽", "🤾", "🤹", "🧘", "🛀", "🛌", "👭", "👫", "👬", "💏", "💑", "👪", "🗣️", "👤", "👥",
    "🫂", "👣", "🐵", "🐒", "🦍", "🦧", "🐶", "🐕", "🦮", "🐩", "🐺", "🦊", "🦝", "🐱", "🐈", "🦁", "🐯", "🐅", "🐆", "🐴",
    "🐎", "🦄", "🦓", "🦌", "🦬", "🐮", "🐂", "🐃", "🐄", "🐷", "🐖", "🐗", "🐽", "🐏", "🐑", "🐐", "🐪", "🐫", "🦙", "🦒",
    "🐘", "🦣", "🦏", "🦛", "🐭", "🐁", "🐀", "🐹", "🐰", "🐇", "🐿️", "🦫", "🦔", "🦇", "🐻", "🐨", "🐼", "🦥", "🦦", "🦨",
    "🦘", "🦡", "🐾", "🦃", "🐔", "🐓", "🐣", "🐤", "🐥", "🐦", "🐧", "🕊️", "🦅", "🦆", "🦢", "🦉", "🦤", "🪶", "🦩", "🦚",
    "🦜", "🐸", "🐊", "🐢", "🦎", "🐍", "🐲", "🐉", "🦕", "🦖", "🐳", "🐋", "🐬", "🦭", "🐟", "🐠", "🐡", "🦈", "🐙", "🐚",
    "🐌", "🦋", "🐛", "🐜", "🐝", "🪲", "🐞", "🦗", "🪳", "🕷️", "🕸️", "🦂", "🦟", "🪰", "🪱", "🦠", "💐", "🌸", "💮", "🏵️",
    "🌹", "🥀", "🌺", "🌻", "🌼", "🌷", "🌱", "🪴", "🌲", "🌳", "🌴", "🌵", "🌾", "🌿", "☘️", "🍀", "🍁", "🍂", "🍃", "🍇",
    "🍈", "🍉", "🍊", "🍋", "🍌", "🍍", "🥭", "🍎", "🍏", "🍐", "🍑", "🍒", "🍓", "🫐", "🥝", "🍅", "🫒", "🥥", "🥑", "🍆",
    "🥔", "🥕", "🌽", "🌶️", "🫑", "🥒", "🥬", "🥦", "🧄", "🧅", "🍄", "🥜", "🌰", "🍞", "🥐", "🥖", "🫓", "🥨", "🥯", "🥞",
    "🧇", "🧀", "🍖", "🍗", "🥩", "🥓", "🍔", "🍟", "🍕", "🌭", "🥪", "🌮", "🌯", "🫔", "🥙", "🧆", "🥚", "🍳", "🥘", "🍲",
    "🫕", "🥣", "🥗", "🍿", "🧈", "🧂", "🥫", "🍱", "🍘", "🍙", "🍚", "🍛", "🍜", "🍝", "🍠", "🍢", "🍣", "🍤", "🍥", "🥮",
    "🍡", "🥟", "🥠", "🥡", "🦀", "🦞", "🦐", "🦑", "🦪", "🍦", "🍧", "🍨", "🍩", "🍪", "🎂", "🍰", "🧁", "🥧", "🍫", "🍬",
    "🍭", "🍮", "🍯", "🍼", "🥛", "☕", "🫖", "🍵", "🍶", "🍾", "🍷", "🍸", "🍹", "🍺", "🍻", "🥂", "🥃", "🥤", "🧋", "🧃",
    "🧉", "🧊", "🥢", "🍽️", "🍴", "🥄", "🔪", "🏺", "🌍", "🌎", "🌏", "🌐", "🗺️", "🗾", "🧭", "🏔️", "⛰️", "🌋", "🗻", "🏕️",
    "🏖️", "🏜️", "🏝️", "🏞️", "🏟️", "🏛️", "🏗️", "🧱", "🪨", "🪵", "🛖", "🏘️", "🏚️", "🏠", "🏡", "🏢", "🏣", "🏤", "🏥", "🏦",
    "🏨", "🏩", "🏪", "🏫", "🏬", "🏭", "🏯", "🏰", "💒", "🗼", "🗽", "⛪", "🕌", "🛕", "🕍", "⛩️", "🕋", "⛲", "⛺", "🌁",
    "🌃", "🏙️", "🌄", "🌅", "🌆", "🌇", "🌉", "♨️", "🎠", "🎡", "🎢", "💈", "🎪", "🚂", "🚃", "🚄", "🚅", "🚆", "🚇", "🚈",
    "🚉", "🚊", "🚝", "🚞", "🚋", "🚌", "🚍", "🚎", "🚐", "🚑", "🚒", "🚓", "🚔", "🚕", "🚖", "🚗", "🚘", "🚙", "🛻", "🚚",
    "🚛", "🚜", "🏎️", "🏍️", "🛵", "🦽", "🦼", "🛺", "🚲", "🛴", "🛹", "🛼", "🚏", "🛣️", "🛤️", "⛽", "🚨", "🚥", "🚦", "🛑",
    "🚧", "⚓", "⛵", "🛶", "🚤", "🛳️", "⛴️", "🛥️", "🚢", "✈️", "🛩️", "🛫", "🛬", "🪂", "💺", "🚁", "🚟", "🚠", "🚡", "🛰️",
    "🚀", "🛸", "🛎️", "🧳", "⌛", "⏳", "⌚", "⏰", "⏱️", "⏲️", "🕰️", "🌑", "🌒", "🌓", "🌔", "🌕", "🌖", "🌗", "🌘", "🌙",
    "🌚", "🌛", "🌜", "☀️", "🌝", "🌞", "🪐", "⭐", "🌟", "🌠", "🌌", "☁️", "⛅", "⛈️", "🌤️", "🌥️", "🌦️", "🌧️", "🌨️", "🌩️",
    "🌪️", "🌫️", "🌬️", "🌀", "🌈", "🌂", "☂️", "☔", "⛱️", "⚡", "❄️", "☃️", "⛄", "☄️", "🔥", "💧", "🌊", "🎃", "🎄", "🎆",
    "🎇", "🧨", "✨", "🎈", "🎉", "🎊", "🎋", "🎍", "🎎", "🎏", "🎐", "🎑", "🧧", "🎀", "🎁", "🎗️", "🎟️", "🎫", "🎖️", "🏆",
    "🏅", "🥇", "🥈", "🥉", "⚽", "⚾", "🥎", "🏀", "🏐", "🏈", "🏉", "🎾", "🥏", "🎳", "🏏", "🏑", "🏒", "🥍", "🏓", "🏸",
    "🥊", "🥋", "🥅", "⛳", "⛸️", "🎣", "🤿", "🎽", "🎿", "🛷", "🥌", "🎯", "🪀", "🪁", "🎱", "🔮", "🪄", "🧿", "🎮", "🕹️",
    "🎰", "🎲", "🧩", "🧸", "🪅", "🪆", "♠️", "♥️", "♦️", "♣️", "♟️", "🃏", "🀄", "🎴", "🎭", "🖼️", "🎨", "🧵", "🪡", "🧶", "🪢"
]

async def is_admin(client: Client, chat_id: int, user_id: int) -> bool:
    try:
        member = await client.get_chat_member(chat_id, user_id)
        return member.status in [ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR]
    except:
        return False

async def get_members(client: Client, chat_id: int, limit: int = 200):
    members = []
    try:
        async for member in client.get_chat_members(chat_id, limit=limit):
            if not member.user.is_bot and not member.user.is_deleted:
                members.append(member.user)
    except Exception as e:
        print(f"Error getting members: {e}")
    return members

async def mention_users(client: Client, message: Message, members: list, text: str, mode: str = "normal"):
    chat_id = message.chat.id
    mentioned_count = 0
    batch_size = 5 if mode == "normal" else 10 if mode == "fast" else 1
    
    for i in range(0, len(members), batch_size):
        if chat_id not in active_mentions:
            break
        batch = members[i:i + batch_size]
        mentions = " ".join([f"{random.choice(MENTION_EMOJIS)}[{user.first_name}](tg://user?id={user.id})" for user in batch])
        try:
            msg_text = f"{text}\n\n{mentions}" if text else mentions
            await client.send_message(chat_id, msg_text)
            mentioned_count += len(batch)
            await asyncio.sleep(1.5 if mode == "normal" else 0.8 if mode == "fast" else 2)
        except FloodWait as e:
            await asyncio.sleep(e.value)
        except Exception as e:
            print(f"Error mentioning: {e}")
            continue
    return mentioned_count

@app.on_message(filters.command("tagall", prefixes=config.config.COMMAND_PREFIXES) & filters.group)
async def tagall(client: Client, message: Message):
    chat_id = message.chat.id
    if not await is_admin(client, chat_id, message.from_user.id):
        await message.reply_text("**❌ Only admins can use this command!**")
        return
    if chat_id in active_mentions:
        await message.reply_text("**⚠️ A mention process is already running! Use /cancel to stop it.**")
        return
    text = " ".join(message.command[1:]) if len(message.command) > 1 else "📢 **Attention Everyone!**"
    status_msg = await message.reply_text("**🔍 Fetching members...**")
    members = await get_members(client, chat_id)
    if not members:
        await status_msg.edit_text("**❌ No members found!**")
        return
    await status_msg.edit_text(f"**👥 Found {len(members)} members!**\n**🏷️ Starting mention process...**")
    active_mentions[chat_id] = True
    mentioned = await mention_users(client, message, members, text, mode="normal")
    if chat_id in active_mentions:
        del active_mentions[chat_id]
    await status_msg.edit_text(f"**✅ Mentioned {mentioned} members successfully!**")

@app.on_message(filters.command("fastag", prefixes=config.config.COMMAND_PREFIXES) & filters.group)
async def fastag(client: Client, message: Message):
    chat_id = message.chat.id
    if not await is_admin(client, chat_id, message.from_user.id):
        await message.reply_text("**❌ Only admins can use this command!**")
        return
    if chat_id in active_mentions:
        await message.reply_text("**⚠️ A mention process is already running! Use /cancel to stop it.**")
        return
    text = " ".join(message.command[1:]) if len(message.command) > 1 else "⚡ **Fast Mention!**"
    status_msg = await message.reply_text("**🔍 Fetching members...**")
    members = await get_members(client, chat_id)
    if not members:
        await status_msg.edit_text("**❌ No members found!**")
        return
    await status_msg.edit_text(f"**👥 Found {len(members)} members!**\n**⚡ Starting fast mention...**")
    active_mentions[chat_id] = True
    mentioned = await mention_users(client, message, members, text, mode="fast")
    if chat_id in active_mentions:
        del active_mentions[chat_id]
    await status_msg.edit_text(f"**✅ Fast mentioned {mentioned} members!**")

@app.on_message(filters.command("singletag", prefixes=config.config.COMMAND_PREFIXES) & filters.group)
async def singletag(client: Client, message: Message):
    chat_id = message.chat.id
    if not await is_admin(client, chat_id, message.from_user.id):
        await message.reply_text("**❌ Only admins can use this command!**")
        return
    if chat_id in active_mentions:
        await message.reply_text("**⚠️ A mention process is already running! Use /cancel to stop it.**")
        return
    text = " ".join(message.command[1:]) if len(message.command) > 1 else "🎯 **Single Mention**"
    status_msg = await message.reply_text("**🔍 Fetching members...**")
    members = await get_members(client, chat_id)
    if not members:
        await status_msg.edit_text("**❌ No members found!**")
        return
    await status_msg.edit_text(f"**👥 Found {len(members)} members!**\n**🎯 Starting single mentions (slow)...**")
    active_mentions[chat_id] = True
    mentioned = await mention_users(client, message, members, text, mode="single")
    if chat_id in active_mentions:
        del active_mentions[chat_id]
    await status_msg.edit_text(f"**✅ Mentioned {mentioned} members individually!**")

@app.on_message(filters.command("cancel", prefixes=config.config.COMMAND_PREFIXES) & filters.group)
async def cancel_mention(client: Client, message: Message):
    chat_id = message.chat.id
    if not await is_admin(client, chat_id, message.from_user.id):
        await message.reply_text("**❌ Only admins can use this command!**")
        return
    if chat_id in active_mentions:
        del active_mentions[chat_id]
        await message.reply_text("**🛑 Mention process cancelled!**")
    else:
        await message.reply_text("**⚠️ No active mention process found!**")

@app.on_message(filters.command("admintag", prefixes=config.config.COMMAND_PREFIXES) & filters.group)
async def admintag(client: Client, message: Message):
    chat_id = message.chat.id
    if not await is_admin(client, chat_id, message.from_user.id):
        await message.reply_text("**❌ Only admins can use this command!**")
        return
    text = " ".join(message.command[1:]) if len(message.command) > 1 else "👑 **Calling All Admins!**"
    status_msg = await message.reply_text("**🔍 Fetching admins...**")
    admins = []
    try:
        async for admin in client.get_chat_members(chat_id, filter=ChatMembersFilter.ADMINISTRATORS):
            if not admin.user.is_bot:
                admins.append(admin.user)
    except Exception as e:
        await status_msg.edit_text(f"**❌ Error:** `{str(e)}`")
        return
    if not admins:
        await status_msg.edit_text("**❌ No admins found!**")
        return
    mentions = " ".join([f"{random.choice(MENTION_EMOJIS)}[{admin.first_name}](tg://user?id={admin.id})" for admin in admins])
    msg_text = f"{text}\n\n{mentions}"
    await message.reply_text(msg_text)
    await status_msg.delete()

@app.on_message(filters.command("botstag", prefixes=config.config.COMMAND_PREFIXES) & filters.group)
async def botstag(client: Client, message: Message):
    chat_id = message.chat.id
    if not await is_admin(client, chat_id, message.from_user.id):
        await message.reply_text("**❌ Only admins can use this command!**")
        return
    text = " ".join(message.command[1:]) if len(message.command) > 1 else "🤖 **Calling All Bots!**"
    status_msg = await message.reply_text("**🔍 Fetching bots...**")
    bots = []
    try:
        async for member in client.get_chat_members(chat_id, filter=ChatMembersFilter.BOTS):
            bots.append(member.user)
    except Exception as e:
        await status_msg.edit_text(f"**❌ Error:** `{str(e)}`")
        return
    if not bots:
        await status_msg.edit_text("**❌ No bots found!**")
        return
    mentions = " ".join([f"{random.choice(MENTION_EMOJIS)}[{bot.first_name}](tg://user?id={bot.id})" for bot in bots])
    msg_text = f"{text}\n\n{mentions}"
    await message.reply_text(msg_text)
    await status_msg.delete()

__help__ = """
**📢 Mention All Module:**

Tag/mention members in your group with cool random emojis! 😎

**Commands:**
• `/tagall [text]` - Tag all members with emojis (5 per message)
• `/fastag [text]` - Fast tag with emojis (10 per message)
• `/singletag [text]` - Tag one by one with emojis (spam-safe)
• `/admintag [text]` - Tag only admins with emojis
• `/botstag [text]` - Tag all bots with emojis
• `/cancel` - Cancel ongoing mention process

**Features:**
• 🎨 Random emoji for each user mention!
• Multiple tagging modes for different needs
• Admin + Owner access (both work!)
• Flood protection built-in
• Cancelable processes
• Custom messages support

**Examples:**
`/tagall Meeting in 5 minutes!`
`/fastag Everyone please vote!`
`/admintag Need admin help here`

**Note:** Only group admins and owners can use these commands.
Each user gets a random emoji when mentioned! 🎉
"""

__module__ = "Mention All"
