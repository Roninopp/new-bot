from html import escape
from secrets import choice
from typing import List
from io import BytesIO
import os
import requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from pyrogram import emoji, enums, filters, Client
from pyrogram.errors import ChannelPrivate, ChatAdminRequired, RPCError, UserNotParticipant
from pyrogram.types import Message, User
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
    m: Message,
    text: str,
    parse_words: list,
) -> str:
    teks = await escape_invalid_curly_brackets(text, parse_words)
    if teks:
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
            chatname=escape(m.chat.title)
            if m.chat.type != ChatType.PRIVATE
            else escape(user.first_name),
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


@app.on_message(filters.new_chat_members)
async def member_has_joined(c: Client, m: Message):
    # Debug logging
    print(f"[WELCOME DEBUG] ========== NEW MEMBER EVENT ==========")
    print(f"[WELCOME DEBUG] Chat ID: {m.chat.id}")
    print(f"[WELCOME DEBUG] Chat Type: {m.chat.type}")
    print(f"[WELCOME DEBUG] Chat Title: {m.chat.title}")
    print(f"[WELCOME DEBUG] Message from user: {m.from_user.first_name if m.from_user else 'None'}")
    
    # Check if it's a private chat (skip)
    if m.chat.type == ChatType.PRIVATE:
        print(f"[WELCOME DEBUG] Skipping - private chat")
        return
    
    # Check bot permissions
    try:
        bot_member = await c.get_chat_member(m.chat.id, c.me.id)
        print(f"[WELCOME DEBUG] Bot status in chat: {bot_member.status}")
        print(f"[WELCOME DEBUG] Bot can send messages: {bot_member.privileges.can_post_messages if bot_member.privileges else 'N/A'}")
    except Exception as e:
        print(f"[WELCOME DEBUG] Error checking bot permissions: {e}")
    
    users: List[User] = m.new_chat_members
    db = Greetings(m.chat.id)
    
    print(f"[WELCOME DEBUG] Processing {len(users)} new members")
    
    for user in users:
        try:
            print(f"[WELCOME DEBUG] Processing user: {user.first_name} (ID: {user.id}, is_bot: {user.is_bot})")
            
            if user.id == c.me.id:
                print(f"[WELCOME DEBUG] Skipping - it's me (bot)")
                continue
            if user.is_bot:
                print(f"[WELCOME DEBUG] Skipping - user is a bot")
                continue  # ignore bots
        except ChatAdminRequired:
            print(f"[WELCOME DEBUG] ChatAdminRequired error")
            continue
        except Exception as e:
            print(f"[WELCOME DEBUG] Error checking user: {e}")
            continue
        
        status = db.get_welcome_status()
        print(f"[WELCOME DEBUG] Welcome status from DB: {status}")
        
        if not status:
            print(f"[WELCOME DEBUG] Welcome is disabled for this chat")
            continue
        
        oo = db.get_welcome_text()
        UwU = db.get_welcome_media()
        mtype = db.get_welcome_msgtype()
        
        print(f"[WELCOME DEBUG] DB values - text: {oo[:50] if oo else None}, media: {UwU}, mtype: {mtype}")
        
        # Check if user has set custom welcome (not default)
        is_custom_welcome = (mtype is not None and mtype is not False) or (UwU is not None and UwU is not False)
        
        print(f"[WELCOME DEBUG] Is custom welcome: {is_custom_welcome}")
        
        parse_words = [
            "first",
            "last",
            "fullname",
            "username",
            "mention",
            "id",
            "chatname",
        ]
        
        # Get member count
        try:
            member_count = await c.get_chat_members_count(m.chat.id)
            print(f"[WELCOME DEBUG] Member count: {member_count}")
        except Exception as e:
            print(f"[WELCOME DEBUG] Error getting member count: {e}")
            member_count = 0
        
        # If custom welcome is set, use old method
        if is_custom_welcome:
            print(f"[WELCOME DEBUG] Using custom welcome message")
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
                teks = f"A wild {user.mention} appeared in {m.chat.title}! Everyone be aware."

            ifff = db.get_current_cleanwelcome_id()
            gg = db.get_current_cleanwelcome_settings()
            if ifff and gg:
                try:
                    await c.delete_messages(m.chat.id, int(ifff))
                except RPCError:
                    pass
            
            try:
                print(f"[WELCOME DEBUG] Attempting to send custom message...")
                if not UwU:
                    jj = await c.send_message(
                        m.chat.id,
                        text=teks,
                        reply_markup=button,
                        disable_web_page_preview=True,
                    )
                else:
                    jj = await (await send_cmd(c, mtype))(
                        m.chat.id,
                        UwU,
                        caption=teks,
                        reply_markup=button,
                    )

                if jj:
                    db.set_cleanwlcm_id(int(jj.id))
                print(f"[WELCOME DEBUG] ✓ Custom welcome sent successfully!")
            except ChannelPrivate as e:
                print(f"[WELCOME DEBUG] ✗ ChannelPrivate error: {e}")
                continue
            except RPCError as e:
                print(f"[WELCOME DEBUG] ✗ RPCError: {e}")
                continue
            except Exception as e:
                print(f"[WELCOME DEBUG] ✗ Unexpected error: {e}")
                import traceback
                traceback.print_exc()
                continue
        else:
            # Use new welcome card system
            print(f"[WELCOME DEBUG] Using welcome card system")
            try:
                # Download profile picture
                print(f"[WELCOME DEBUG] Downloading profile picture...")
                profile_pic_path = await download_profile_pic(user, c)
                print(f"[WELCOME DEBUG] Profile pic path: {profile_pic_path}")
                
                # Create welcome card
                print(f"[WELCOME DEBUG] Creating welcome card...")
                chat_title = m.chat.title if m.chat.title else "this group"
                welcome_card = await create_welcome_card(user, chat_title, member_count, profile_pic_path)
                
                if welcome_card:
                    print(f"[WELCOME DEBUG] Welcome card created successfully")
                    # Delete previous welcome if clean welcome is on
                    ifff = db.get_current_cleanwelcome_id()
                    gg = db.get_current_cleanwelcome_settings()
                    if ifff and gg:
                        try:
                            await c.delete_messages(m.chat.id, int(ifff))
                            print(f"[WELCOME DEBUG] Deleted previous welcome message")
                        except RPCError as e:
                            print(f"[WELCOME DEBUG] Could not delete previous message: {e}")
                    
                    # Send welcome card
                    print(f"[WELCOME DEBUG] Attempting to send welcome card...")
                    caption = f"Welcome to {chat_title}, {user.mention}! 🎉"
                    jj = await c.send_photo(
                        m.chat.id,
                        photo=welcome_card,
                        caption=caption
                    )
                    
                    if jj:
                        db.set_cleanwlcm_id(int(jj.id))
                    print(f"[WELCOME DEBUG] ✓ Welcome card sent successfully!")
                else:
                    print(f"[WELCOME DEBUG] Welcome card generation failed, using fallback")
                    # Fallback to text if card generation fails
                    teks = f"Welcome {user.mention} to {m.chat.title}! 🎉\nYou are member #{member_count}"
                    jj = await c.send_message(m.chat.id, text=teks)
                    if jj:
                        db.set_cleanwlcm_id(int(jj.id))
                    print(f"[WELCOME DEBUG] ✓ Fallback text sent!")
                        
            except ChannelPrivate as e:
                print(f"[WELCOME DEBUG] ✗ ChannelPrivate error in welcome card: {e}")
                continue
            except Exception as e:
                print(f"[WELCOME DEBUG] ✗ Error in welcome card: {e}")
                import traceback
                traceback.print_exc()
                # Fallback to simple text
                try:
                    print(f"[WELCOME DEBUG] Trying final fallback...")
                    teks = f"Welcome {user.mention} to {m.chat.title}! 🎉"
                    await c.send_message(m.chat.id, text=teks)
                    print(f"[WELCOME DEBUG] ✓ Final fallback sent!")
                except Exception as e2:
                    print(f"[WELCOME DEBUG] ✗ Final fallback also failed: {e2}")
    
    print(f"[WELCOME DEBUG] ========== END OF WELCOME HANDLER ==========\n")


@app.on_message(filters.left_chat_member, group=99)
async def member_has_left(c: Client, m: Message):
    # Debug logging
    print(f"[GOODBYE DEBUG] Left member event detected!")
    print(f"[GOODBYE DEBUG] Chat ID: {m.chat.id}")
    print(f"[GOODBYE DEBUG] Chat Type: {m.chat.type}")
    
    # Skip if not a group/supergroup/channel
    if m.chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP, ChatType.CHANNEL]:
        print(f"[GOODBYE DEBUG] Skipping - not a group")
        return
    
    db = Greetings(m.chat.id)
    status = db.get_goodbye_status()
    oo = db.get_goodbye_text()
    UwU = db.get_goodbye_media()
    mtype = db.get_goodbye_msgtype()
    parse_words = [
        "first",
        "last",
        "fullname",
        "id",
        "username",
        "mention",
        "chatname",
    ]

    user = m.left_chat_member or m.from_user

    hmm = await escape_mentions_using_curly_brackets_wl(user, m, oo, parse_words)
    if not status:
        return
    
    tek, button = await parse_button(hmm)
    button = await build_keyboard(button)
    button = ikb(button) if button else None

    if "%%%" in tek:
        filter_reply = tek.split("%%%")
        teks = choice(filter_reply)
    else:
        teks = tek

    if not teks:
        teks = f"Thanks for being part of this group {user.mention}. But I don't like your arrogance and leaving the group {emoji.EYES}"

    ifff = db.get_current_cleangoodbye_id()
    iii = db.get_current_cleangoodbye_settings()
    if ifff and iii:
        try:
            await c.delete_messages(m.chat.id, int(ifff))
        except RPCError:
            pass
    
    if not teks:
        teks = "Sad to see you leaving {first}\nTake Care!"
    
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
        return
    except ChannelPrivate:
        pass
    except RPCError as e:
        return


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
  - Automatically generates welcome cards with profile pictures
  - Using /setwelcome switches to custom message mode
  - Yumeko must be an admin to greet users
"""
