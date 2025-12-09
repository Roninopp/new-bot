from html import escape
from secrets import choice
from typing import List
from io import BytesIO
import os
import requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from pyrogram import emoji, enums, filters, Client
from pyrogram.errors import ChannelPrivate, ChatAdminRequired, RPCError, UserNotParticipant
from pyrogram.types import Message, User, ChatMemberUpdated
from Yumeko import app
from Yumeko.database.welcome_db import Greetings
from Yumeko.decorator.chatadmin import can_change_info, chatadmin
from Yumeko.helper.welcome_helper import *
from config import config

ChatType = enums.ChatType

# Constants for image generation
WELCOME_CARD_WIDTH = 1024
WELCOME_CARD_HEIGHT = 500
PROFILE_PIC_SIZE = 200
BACKGROUND_COLOR = (41, 128, 185)  # Nice blue
TEXT_COLOR = (255, 255, 255)  # White
SHADOW_COLOR = (0, 0, 0, 128)  # Semi-transparent black


async def escape_mentions_using_curly_brackets_wl(
    user: User,
    m,
    text: str,
    parse_words: list,
) -> str:
    teks = await escape_invalid_curly_brackets(text, parse_words)
    if teks:
        chat_title = m.chat.title if hasattr(m.chat, 'title') and m.chat.title else "this chat"
        teks = teks.format(
            first=escape(user.first_name),
            last=escape(user.last_name or user.first_name),
            fullname=" ".join(
                [
                    escape(user.first_name),
                    escape(user.last_name),
                ]
                if user.last_name
                else [escape(user.first_name)],
            ),
            username=(
                "@" + (await escape_markdown(escape(user.username)))
                if user.username
                else (await (mention_html(escape(user.first_name), user.id)))
            ),
            mention=await (mention_html(escape(user.first_name), user.id)),
            chatname=chat_title,
            id=user.id,
        )
    else:
        teks = ""

    return teks


def create_circular_mask(size):
    """Create a circular mask for profile picture"""
    mask = Image.new('L', (size, size), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, size, size), fill=255)
    return mask


async def download_profile_pic(user: User, c: Client):
    """Download user profile picture"""
    try:
        photos = []
        async for photo in c.get_chat_photos(user.id, limit=1):
            photos.append(photo)
        
        if photos:
            photo_path = await c.download_media(photos[0].file_id)
            return photo_path
    except Exception as e:
        print(f"Error downloading profile pic: {e}")
    return None


def get_font(size, bold=False):
    """Get font with fallback options"""
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "arial.ttf"
    ]
    
    for font_path in font_paths:
        try:
            if os.path.exists(font_path):
                return ImageFont.truetype(font_path, size)
        except:
            continue
    
    # Fallback to default font
    return ImageFont.load_default()


async def create_welcome_card(user: User, chat_title: str, member_count: int, profile_pic_path=None):
    """Create a professional welcome card"""
    try:
        # Create base image with gradient background
        img = Image.new('RGB', (WELCOME_CARD_WIDTH, WELCOME_CARD_HEIGHT), BACKGROUND_COLOR)
        draw = ImageDraw.Draw(img, 'RGBA')
        
        # Create gradient effect
        for i in range(WELCOME_CARD_HEIGHT):
            alpha = int(255 * (1 - i / WELCOME_CARD_HEIGHT) * 0.3)
            draw.rectangle(
                [(0, i), (WELCOME_CARD_WIDTH, i + 1)],
                fill=(0, 0, 0, alpha)
            )
        
        # Add decorative circles
        draw = ImageDraw.Draw(img, 'RGBA')
        draw.ellipse([(-100, -100), (200, 200)], fill=(255, 255, 255, 20))
        draw.ellipse([(WELCOME_CARD_WIDTH - 200, WELCOME_CARD_HEIGHT - 100), 
                     (WELCOME_CARD_WIDTH + 100, WELCOME_CARD_HEIGHT + 200)], 
                     fill=(255, 255, 255, 20))
        
        # Load and process profile picture
        if profile_pic_path and os.path.exists(profile_pic_path):
            try:
                profile_pic = Image.open(profile_pic_path)
                profile_pic = profile_pic.resize((PROFILE_PIC_SIZE, PROFILE_PIC_SIZE), Image.Resampling.LANCZOS)
                
                # Create circular mask
                mask = create_circular_mask(PROFILE_PIC_SIZE)
                
                # Create circular profile pic
                circular_pic = Image.new('RGBA', (PROFILE_PIC_SIZE, PROFILE_PIC_SIZE), (0, 0, 0, 0))
                circular_pic.paste(profile_pic.convert('RGB'), (0, 0))
                circular_pic.putalpha(mask)
                
                # Add white border
                border_size = 8
                border_pic = Image.new('RGBA', (PROFILE_PIC_SIZE + border_size * 2, 
                                                PROFILE_PIC_SIZE + border_size * 2), (255, 255, 255, 255))
                border_mask = create_circular_mask(PROFILE_PIC_SIZE + border_size * 2)
                border_pic.putalpha(border_mask)
                
                # Position profile picture
                profile_x = (WELCOME_CARD_WIDTH - PROFILE_PIC_SIZE) // 2
                profile_y = 80
                
                img.paste(border_pic, (profile_x - border_size, profile_y - border_size), border_pic)
                img.paste(circular_pic, (profile_x, profile_y), circular_pic)
                
                # Clean up
                try:
                    os.remove(profile_pic_path)
                except:
                    pass
            except Exception as e:
                print(f"Error processing profile pic: {e}")
        else:
            # Draw default avatar circle if no profile pic
            profile_x = (WELCOME_CARD_WIDTH - PROFILE_PIC_SIZE) // 2
            profile_y = 80
            draw = ImageDraw.Draw(img, 'RGBA')
            
            # White border
            draw.ellipse([
                (profile_x - 8, profile_y - 8),
                (profile_x + PROFILE_PIC_SIZE + 8, profile_y + PROFILE_PIC_SIZE + 8)
            ], fill=(255, 255, 255, 255))
            
            # Avatar circle
            draw.ellipse([
                (profile_x, profile_y),
                (profile_x + PROFILE_PIC_SIZE, profile_y + PROFILE_PIC_SIZE)
            ], fill=(52, 152, 219, 255))
            
            # Draw user initial
            initial = user.first_name[0].upper() if user.first_name else "U"
            initial_font = get_font(80, bold=True)
            
            # Get text size for centering
            bbox = draw.textbbox((0, 0), initial, font=initial_font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            text_x = profile_x + (PROFILE_PIC_SIZE - text_width) // 2
            text_y = profile_y + (PROFILE_PIC_SIZE - text_height) // 2
            
            draw.text((text_x, text_y), initial, font=initial_font, fill=(255, 255, 255, 255))
        
        # Draw text
        draw = ImageDraw.Draw(img)
        
        # Welcome text
        welcome_font = get_font(48, bold=True)
        welcome_text = "WELCOME!"
        bbox = draw.textbbox((0, 0), welcome_text, font=welcome_font)
        text_width = bbox[2] - bbox[0]
        draw.text(
            ((WELCOME_CARD_WIDTH - text_width) // 2, 300),
            welcome_text,
            font=welcome_font,
            fill=TEXT_COLOR
        )
        
        # User name
        name_font = get_font(36, bold=True)
        user_name = user.first_name[:30]  # Limit length
        bbox = draw.textbbox((0, 0), user_name, font=name_font)
        text_width = bbox[2] - bbox[0]
        draw.text(
            ((WELCOME_CARD_WIDTH - text_width) // 2, 360),
            user_name,
            font=name_font,
            fill=TEXT_COLOR
        )
        
        # Chat info
        info_font = get_font(24)
        chat_info = f"You are member #{member_count} of {chat_title[:40]}"
        bbox = draw.textbbox((0, 0), chat_info, font=info_font)
        text_width = bbox[2] - bbox[0]
        draw.text(
            ((WELCOME_CARD_WIDTH - text_width) // 2, 420),
            chat_info,
            font=info_font,
            fill=(255, 255, 255, 200)
        )
        
        # Save to BytesIO
        output = BytesIO()
        img.save(output, format='PNG', optimize=True)
        output.seek(0)
        
        return output
        
    except Exception as e:
        print(f"Error creating welcome card: {e}")
        return None


async def send_welcome_message(c: Client, chat_id: int, user: User, chat_obj):
    """Send welcome message - either card or custom text
    
    NOTE: Bot MUST be an admin in Private Supergroups to receive new_chat_members events.
    This is a Telegram API limitation for private groups.
    """
    try:
        db = Greetings(chat_id)
        
        # Check if welcome is enabled
        status = db.get_welcome_status()
        if not status:
            print(f"[WELCOME] Welcome disabled for chat {chat_id}")
            return
        
        oo = db.get_welcome_text()
        UwU = db.get_welcome_media()
        mtype = db.get_welcome_msgtype()
        
        # Check if custom welcome is set
        is_custom_welcome = (mtype is not None and mtype is not False) or (UwU is not None and UwU is not False)
        
        # Get member count
        try:
            member_count = await c.get_chat_members_count(chat_id)
        except:
            member_count = 0
        
        # Create a minimal message object for formatting
        class MinimalMsg:
            def __init__(self, chat):
                self.chat = chat
        
        minimal_msg = MinimalMsg(chat_obj)
        
        parse_words = ["first", "last", "fullname", "username", "mention", "id", "chatname"]
        
        if is_custom_welcome:
            # Custom welcome
            print(f"[WELCOME] Sending custom welcome")
            hmm = await escape_mentions_using_curly_brackets_wl(user, minimal_msg, oo, parse_words)
            tek, button = await parse_button(hmm)
            button = await build_keyboard(button)
            button = ikb(button) if button else None

            if "%%%" in tek:
                filter_reply = tek.split("%%%")
                teks = choice(filter_reply)
            else:
                teks = tek

            if not teks:
                teks = f"Welcome {user.mention}!"

            # Clean previous welcome if enabled
            ifff = db.get_current_cleanwelcome_id()
            gg = db.get_current_cleanwelcome_settings()
            if ifff and gg:
                try:
                    await c.delete_messages(chat_id, int(ifff))
                except:
                    pass
            
            if not UwU:
                jj = await c.send_message(
                    chat_id,
                    text=teks,
                    reply_markup=button,
                    disable_web_page_preview=True,
                )
            else:
                jj = await (await send_cmd(c, mtype))(
                    chat_id,
                    UwU,
                    caption=teks,
                    reply_markup=button,
                )

            if jj:
                db.set_cleanwlcm_id(int(jj.id))
            
        else:
            # Welcome card
            print(f"[WELCOME] Sending welcome card")
            profile_pic_path = await download_profile_pic(user, c)
            
            # Get chat title - works for both public and private groups
            chat_title = "this group"
            if hasattr(chat_obj, 'title') and chat_obj.title:
                chat_title = chat_obj.title
            
            print(f"[WELCOME] Chat title: {chat_title}, Member count: {member_count}")
            
            welcome_card = await create_welcome_card(user, chat_title, member_count, profile_pic_path)
            
            if welcome_card:
                # Clean previous welcome if enabled
                ifff = db.get_current_cleanwelcome_id()
                gg = db.get_current_cleanwelcome_settings()
                if ifff and gg:
                    try:
                        await c.delete_messages(chat_id, int(ifff))
                    except:
                        pass
                
                caption = f"Welcome to {chat_title}, {user.mention}! 🎉"
                jj = await c.send_photo(
                    chat_id,
                    photo=welcome_card,
                    caption=caption
                )
                
                if jj:
                    db.set_cleanwlcm_id(int(jj.id))
            else:
                # Fallback to text
                teks = f"Welcome {user.mention} to {chat_title}! 🎉\nYou are member #{member_count}"
                jj = await c.send_message(chat_id, text=teks)
                if jj:
                    db.set_cleanwlcm_id(int(jj.id))
        
        print(f"[WELCOME] ✓ Welcome sent successfully!")
        
    except Exception as e:
        print(f"[WELCOME] Error sending welcome: {e}")
        import traceback
        traceback.print_exc()


# Handler 1: Manual adds (when admin adds someone)
# NOTE: Bot MUST be an admin to receive this event in Private Supergroups
@app.on_message(filters.new_chat_members)
async def on_new_member_added(c: Client, m: Message):
    print(f"\n[WELCOME] ========== MANUAL ADD EVENT ==========")
    print(f"[WELCOME] Chat ID: {m.chat.id}")
    print(f"[WELCOME] Chat Type: {m.chat.type}")
    print(f"[WELCOME] Chat Username: {m.chat.username if hasattr(m.chat, 'username') else 'None (Private Group)'}")
    print(f"[WELCOME] Chat Title: {m.chat.title if hasattr(m.chat, 'title') else 'No Title'}")
    
    # Process ALL group types - both public and private
    # ChatType.GROUP = old-style groups
    # ChatType.SUPERGROUP = supergroups (both public and private)
    # ChatType.CHANNEL = channels (sometimes used for private supergroups)
    if m.chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP, ChatType.CHANNEL]:
        print(f"[WELCOME] Skipping - not a group/supergroup/channel")
        return
    
    # Additional check: Skip if it's actually a private chat somehow
    if m.chat.type == ChatType.PRIVATE:
        print(f"[WELCOME] Skipping - private chat")
        return
    
    for user in m.new_chat_members:
        print(f"[WELCOME] New member: {user.first_name} (ID: {user.id})")
        
        # Skip bot itself
        if user.id == c.me.id:
            print(f"[WELCOME] Skipping - it's the bot itself")
            continue
        
        await send_welcome_message(c, m.chat.id, user, m.chat)


# Handler 2: Users joining via link (chat_member_updated)
# NOTE: Bot MUST be an admin to receive this event in Private Supergroups
@app.on_chat_member_updated()
async def on_member_joined_group(c: Client, update: ChatMemberUpdated):
    # Skip private chats
    if update.chat.type == ChatType.PRIVATE:
        return
    
    # Process ALL group types - treat public and private groups the same
    if update.chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP, ChatType.CHANNEL]:
        return
    
    # Detect new member joining
    old_member = update.old_chat_member
    new_member = update.new_chat_member
    
    # Check if it's actually a new join
    if old_member or not new_member:
        return
    
    # Check if member actually joined (not kicked, banned, left)
    if new_member.status not in ["member", "administrator", "creator"]:
        return
    
    user = new_member.user
    
    print(f"\n[WELCOME] ========== JOIN VIA LINK EVENT ==========")
    print(f"[WELCOME] Chat ID: {update.chat.id}")
    print(f"[WELCOME] Chat Type: {update.chat.type}")
    print(f"[WELCOME] Chat Username: {update.chat.username if hasattr(update.chat, 'username') else 'None (Private Group)'}")
    print(f"[WELCOME] Chat Title: {update.chat.title if hasattr(update.chat, 'title') else 'No Title'}")
    print(f"[WELCOME] New member: {user.first_name} (ID: {user.id})")
    
    # Skip bot itself
    if user.id == c.me.id:
        print(f"[WELCOME] Skipping - it's the bot itself")
        return
    
    await send_welcome_message(c, update.chat.id, user, update.chat)
    
    # Check if it's actually a new join
    if old_member or not new_member:
        return
    
    # Check if member actually joined (not kicked, banned, left)
    if new_member.status not in ["member", "administrator", "creator"]:
        return
    
    user = new_member.user
    
    print(f"\n[WELCOME] ========== JOIN VIA LINK EVENT ==========")
    print(f"[WELCOME] Chat: {update.chat.id} | Type: {update.chat.type} | Title: {update.chat.title}")
    print(f"[WELCOME] New member: {user.first_name} (ID: {user.id})")
    
    # Skip bot itself
    if user.id == c.me.id:
        print(f"[WELCOME] Skipping bot itself")
        return
    
    await send_welcome_message(c, update.chat.id, user, update.chat)


@app.on_message(filters.command("cleanwelcome", config.COMMAND_PREFIXES))
@can_change_info
async def cleanwlcm(_, m: Message):
    db = Greetings(m.chat.id)
    status = db.get_current_cleanwelcome_settings()
    args = m.text.split(" ", 1)

    if len(args) >= 2:
        if args[1].lower() == "on":
            db.set_current_cleanwelcome_settings(True)
            await m.reply_text("Turned on!")
            return
        if args[1].lower() == "off":
            db.set_current_cleanwelcome_settings(False)
            await m.reply_text("Turned off!")
            return
        await m.reply_text("what are you trying to do ??")
        return
    await m.reply_text(f"Current settings:- {status}")
    return


@app.on_message(filters.command("cleangoodbye", config.COMMAND_PREFIXES))
@can_change_info
async def cleangdbye(_, m: Message):
    db = Greetings(m.chat.id)
    status = db.get_current_cleangoodbye_settings()
    args = m.text.split(" ", 1)

    if len(args) >= 2:
        if args[1].lower() == "on":
            db.set_current_cleangoodbye_settings(True)
            await m.reply_text("Turned on!")
            return
        if args[1].lower() == "off":
            db.set_current_cleangoodbye_settings(False)
            await m.reply_text("Turned off!")
            return
        await m.reply_text("what are you trying to do ??")
        return
    await m.reply_text(f"Current settings:- {status}")
    return


@app.on_message(filters.command("setwelcome", config.COMMAND_PREFIXES))
@can_change_info
async def save_wlcm(_, m: Message):
    db = Greetings(m.chat.id)
    if m and not m.from_user:
        return
    args = m.text.split(None, 1)

    if len(args) >= 4096:
        await m.reply_text("Word limit exceed !!")
        return
    
    if not (m.reply_to_message and m.reply_to_message.text) and len(m.command) == 0:
        await m.reply_text(
            "Error: There is no text in here! and only text with buttons are supported currently !",
        )
        return
    
    text, msgtype, file = await get_wlcm_type(m)
    
    if not m.reply_to_message and msgtype == Types.TEXT and len(m.command) <= 2:
        await m.reply_text(f"<code>{m.text}</code>\n\nError: There is no data in here!")
        return

    if not text and not file:
        await m.reply_text("Please provide some data!")
        return

    if not msgtype:
        await m.reply_text("Please provide some data for this to reply with!")
        return

    db.set_welcome_text(text, msgtype, file)
    await m.reply_text("Saved welcome! Note: Custom welcome card is disabled. Using your custom message.")
    return


@app.on_message(filters.command("setgoodbye", config.COMMAND_PREFIXES))
@can_change_info
async def save_gdbye(_, m: Message):
    db = Greetings(m.chat.id)
    if m and not m.from_user:
        return
    args = m.text.split(None, 1)

    if len(args) >= 4096:
        await m.reply_text("Word limit exceeds !!")
        return
    
    if not (m.reply_to_message and m.reply_to_message.text) and len(m.command) == 0:
        await m.reply_text(
            "Error: There is no text in here! and only text with buttons are supported currently !",
        )
        return
    
    text, msgtype, file = await get_wlcm_type(m)

    if not m.reply_to_message and msgtype == Types.TEXT and len(m.command) <= 2:
        await m.reply_text(f"<code>{m.text}</code>\n\nError: There is no data in here!")
        return

    if not text and not file:
        await m.reply_text("Please provide some data!")
        return

    if not msgtype:
        await m.reply_text("Please provide some data for this to reply with!")
        return

    db.set_goodbye_text(text, msgtype, file)
    await m.reply_text("Saved goodbye!")
    return


@app.on_message(filters.command("resetgoodbye", config.COMMAND_PREFIXES))
@can_change_info
async def resetgb(_, m: Message):
    db = Greetings(m.chat.id)
    if m and not m.from_user:
        return
    text = "Sad to see you leaving {first}.\nTake Care!"
    db.set_goodbye_text(text, None)
    await m.reply_text("Ok Done!")
    return


@app.on_message(filters.command("resetwelcome", config.COMMAND_PREFIXES))
@can_change_info
async def resetwlcm(_, m: Message):
    db = Greetings(m.chat.id)
    if m and not m.from_user:
        return
    text = "Hey {first}, welcome to {chatname}!"
    db.set_welcome_text(text, None)
    await m.reply_text("Done! Welcome card is now enabled with default settings.")
    return


@app.on_message(filters.left_chat_member)
async def member_has_left(c: Client, m: Message):
    # Only process groups
    if m.chat.type == ChatType.PRIVATE:
        return
    
    db = Greetings(m.chat.id)
    status = db.get_goodbye_status()
    
    if not status:
        return
    
    oo = db.get_goodbye_text()
    UwU = db.get_goodbye_media()
    mtype = db.get_goodbye_msgtype()
    parse_words = ["first", "last", "fullname", "id", "username", "mention", "chatname"]

    user = m.left_chat_member or m.from_user

    hmm = await escape_mentions_using_curly_brackets_wl(user, m, oo, parse_words)
    
    tek, button = await parse_button(hmm)
    button = await build_keyboard(button)
    button = ikb(button) if button else None

    if "%%%" in tek:
        filter_reply = tek.split("%%%")
        teks = choice(filter_reply)
    else:
        teks = tek

    if not teks:
        teks = f"Goodbye {user.mention}!"

    # Clean previous goodbye
    ifff = db.get_current_cleangoodbye_id()
    iii = db.get_current_cleangoodbye_settings()
    if ifff and iii:
        try:
            await c.delete_messages(m.chat.id, int(ifff))
        except:
            pass
    
    try:
        ooo = (
            await (await send_cmd(c, mtype))(
                m.chat.id,
                UwU,
                caption=teks,
                reply_markup=button,
            ) if UwU else await c.send_message(
                m.chat.id,
                text=teks,
                reply_markup=button,
                disable_web_page_preview=True,
            )
        )
        if ooo:
            db.set_cleangoodbye_id(int(ooo.id))
    except:
        pass


@app.on_message(filters.command("welcome", config.COMMAND_PREFIXES))
@chatadmin
async def welcome(c: Client, m: Message):
    db = Greetings(m.chat.id)
    status = db.get_welcome_status()
    oo = db.get_welcome_text()
    args = m.text.split(" ", 1)

    if m and not m.from_user:
        return

    if len(args) >= 2:
        if args[1].lower() == "noformat":
            await m.reply_text(
                f"""Current welcome settings:-
Welcome : {status}
Clean Welcome: {db.get_current_cleanwelcome_settings()}
Cleaning service: {db.get_current_cleanservice_settings()}
Welcome text in no formatting:
""",
            )
            await c.send_message(
                m.chat.id, text=oo, parse_mode=enums.ParseMode.DISABLED
            )
            return
        if args[1].lower() == "on":
            db.set_current_welcome_settings(True)
            await m.reply_text("I will greet newly joined member from now on.")
            return
        if args[1].lower() == "off":
            db.set_current_welcome_settings(False)
            await m.reply_text("I will stay quiet when someone joins.")
            return
        await m.reply_text("what are you trying to do ??")
        return
    
    await m.reply_text(
        f"""Current welcome settings:-
Welcome : {status}
Clean Welcome: {db.get_current_cleanwelcome_settings()}
Cleaning service: {db.get_current_cleanservice_settings()}
Welcome text:
""",
    )
    
    UwU = db.get_welcome_media()
    mtype = db.get_welcome_msgtype()
    tek, button = await parse_button(oo)
    button = await build_keyboard(button)
    button = ikb(button) if button else None
    
    if not UwU:
        await c.send_message(
            m.chat.id,
            text=tek,
            reply_markup=button,
            disable_web_page_preview=True,
        )
    else:
        await (await send_cmd(c, mtype))(
            m.chat.id,
            UwU,
            caption=tek,
            reply_markup=button,
        )
    return


@app.on_message(filters.command("goodbye", config.COMMAND_PREFIXES))
@chatadmin
async def goodbye(c: Client, m: Message):
    db = Greetings(m.chat.id)
    status = db.get_goodbye_status()
    oo = db.get_goodbye_text()
    args = m.text.split(" ", 1)
    
    if m and not m.from_user:
        return
    
    if len(args) >= 2:
        if args[1].lower() == "noformat":
            await m.reply_text(
                f"""Current goodbye settings:-
Goodbye : {status}
Clean Goodbye: {db.get_current_cleangoodbye_settings()}
Cleaning service: {db.get_current_cleanservice_settings()}
Goodbye text in no formatting:
""",
            )
            await c.send_message(
                m.chat.id, text=oo, parse_mode=enums.ParseMode.DISABLED
            )
            return
        if args[1].lower() == "on":
            db.set_current_goodbye_settings(True)
            await m.reply_text("I don't want but I will say goodbye to the fugitives")
            return
        if args[1].lower() == "off":
            db.set_current_goodbye_settings(False)
            await m.reply_text("I will stay quiet for fugitives")
            return
        await m.reply_text("what are you trying to do ??")
        return
    
    await m.reply_text(
        f"""Current Goodbye settings:-
Goodbye : {status}
Clean Goodbye: {db.get_current_cleangoodbye_settings()}
Cleaning service: {db.get_current_cleanservice_settings()}
Goodbye text:
""",
    )
    
    UwU = db.get_goodbye_media()
    mtype = db.get_goodbye_msgtype()
    tek, button = await parse_button(oo)
    button = await build_keyboard(button)
    button = ikb(button) if button else None
    
    if not UwU:
        await c.send_message(
            m.chat.id,
            text=tek,
            reply_markup=button,
            disable_web_page_preview=True,
        )
    else:
        await (await send_cmd(c, mtype))(
            m.chat.id,
            UwU,
            caption=tek,
            reply_markup=button,
        )
    return


__module__ = "Greetings_v2"

__help__ = """**Customize Welcome/Goodbye Messages (V2):**

**Professional Welcome Cards**: Automatically generates beautiful welcome cards with user profile pictures!

**Customize Messages:**
  /setwelcome <reply> - Sets custom welcome (disables welcome card)
  /setgoodbye <reply> - Sets custom goodbye
  /resetwelcome - Resets to default (enables welcome card)
  /resetgoodbye - Resets to default goodbye

**Enable/Disable:**
  /welcome <on/off> - Enable/disable welcome
  /goodbye <on/off> - Enable/disable goodbye

**Clean Messages:**
  /cleanwelcome <on/off> - Auto-delete previous welcome
  /cleangoodbye <on/off> - Auto-delete previous goodbye

**Notes:**
  - Works in both public and private groups!
  - Works when users join via invite link or are manually added
  - Automatically generates welcome cards with profile pictures
  - Using /setwelcome switches to custom message mode
  - Yumeko must be an admin to greet users
"""
