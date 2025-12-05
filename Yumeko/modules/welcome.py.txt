import os
from html import escape
from secrets import choice
from typing import List
from PIL import Image, ImageDraw, ImageFont, ImageOps
import io

from Yumeko.helper.welcome_helper import *
from pyrogram import emoji, enums, filters, Client
from pyrogram.errors import ChannelPrivate, ChatAdminRequired, RPCError
from pyrogram.types import Message, User
from Yumeko import app
from Yumeko.database.welcome_db import Greetings
from Yumeko.decorator.chatadmin import can_change_info, chatadmin
from config import config 

ChatType = enums.ChatType

# --- CONFIG FOR WELCOME CARD ---
BG_PATH = "Yumeko/resources/welcome_bg.jpg"
FONT_PATH = "Yumeko/resources/bold_font.ttf"
DEFAULT_WELCOME = "Hey {first}, welcome to {chatname}!"

# --- CARD GENERATOR FUNCTION ---
async def generate_welcome_card(user: User, chat_title: str):
    try:
        # 1. Load Background
        if not os.path.exists(BG_PATH):
            return None # Fallback if file missing
            
        background = Image.open(BG_PATH).convert("RGBA")
        background = background.resize((1024, 500)) # Standard Size

        # 2. Draw Text (Name & Chat)
        draw = ImageDraw.Draw(background)
        
        # Load Font
        try:
            font_large = ImageFont.truetype(FONT_PATH, 60)
            font_small = ImageFont.truetype(FONT_PATH, 40)
        except:
            font_large = ImageFont.load_default()
            font_small = ImageFont.load_default()

        # Text Positions
        draw.text((360, 250), f"Welcome {user.first_name}!", fill="white", font=font_large, stroke_width=2, stroke_fill="black")
        draw.text((360, 330), f"To: {chat_title}", fill="white", font=font_small, stroke_width=1, stroke_fill="black")

        # 3. Handle Profile Picture (PFP)
        pfp_path = f"pfp_{user.id}.jpg"
        try:
            # Download PFP
            photo = await app.download_media(user.photo.big_file_id, file_name=pfp_path)
            if photo:
                img = Image.open(photo).convert("RGBA")
                img = img.resize((250, 250))
                
                # Make it Circle
                mask = Image.new("L", (250, 250), 0)
                draw_mask = ImageDraw.Draw(mask)
                draw_mask.ellipse((0, 0, 250, 250), fill=255)
                
                # Paste PFP onto background
                img = ImageOps.fit(img, mask.size, centering=(0.5, 0.5))
                img.putalpha(mask)
                
                # Paste at specific location (Left side)
                background.alpha_composite(img, (50, 125))
                
                # Cleanup PFP file
                os.remove(photo)
        except Exception:
            pass # Use background without PFP if download fails

        # 4. Save to Memory
        final_image = io.BytesIO()
        background = background.convert("RGB")
        background.save(final_image, format="JPEG")
        final_image.seek(0)
        return final_image

    except Exception as e:
        print(f"Card Gen Error: {e}")
        return None

# --- HELPER: FORMATTING ---
async def escape_mentions_using_curly_brackets_wl(user: User, m: Message, text: str, parse_words: list) -> str:
    teks = await escape_invalid_curly_brackets(text, parse_words)
    if teks:
        chat_title = m.chat.title if m.chat.title else "this group"
        teks = teks.format(
            first=escape(user.first_name),
            last=escape(user.last_name or user.first_name),
            fullname=" ".join([escape(user.first_name), escape(user.last_name)]) if user.last_name else escape(user.first_name),
            username=("@" + (await escape_markdown(escape(user.username)))) if user.username else (await (mention_html(escape(user.first_name), user.id))),
            mention=await (mention_html(escape(user.first_name), user.id)),
            chatname=escape(chat_title),
            id=user.id,
        )
    else:
        teks = ""
    return teks

# --- MAIN JOIN HANDLER ---
@app.on_message(filters.group & filters.new_chat_members, group=69)
async def member_has_joined(c: Client, m: Message):
    users: List[User] = m.new_chat_members
    db = Greetings(m.chat.id)
    
    for user in users:
        try:
            if user.id == c.me.id or user.is_bot:
                continue

            status = db.get_welcome_status()
            if not status:
                continue

            # Get DB Settings
            oo = db.get_welcome_text()
            UwU = db.get_welcome_media()
            mtype = db.get_welcome_msgtype()

            # --- THE NEW LOGIC ---
            # Check if current text is the Default one. If yes -> Send Card.
            # If no (user changed it) -> Send custom message.
            
            is_default = (oo == DEFAULT_WELCOME)
            
            # Clean old messages
            ifff = db.get_current_cleanwelcome_id()
            if ifff and db.get_current_cleanwelcome_settings():
                try: await c.delete_messages(m.chat.id, int(ifff))
                except: pass

            sent_msg = None

            if is_default and not UwU:
                # >> SEND WELCOME CARD <<
                card = await generate_welcome_card(user, m.chat.title or "Group")
                caption = f"Hey {user.mention}, Welcome to **{m.chat.title}**! ❄️"
                
                if card:
                    sent_msg = await c.send_photo(
                        m.chat.id, 
                        photo=card, 
                        caption=caption
                    )
                else:
                    # Fallback to text if card fails
                    sent_msg = await c.send_message(m.chat.id, caption)

            else:
                # >> SEND CUSTOM MESSAGE <<
                parse_words = ["first", "last", "fullname", "username", "mention", "id", "chatname"]
                hmm = await escape_mentions_using_curly_brackets_wl(user, m, oo, parse_words)
                tek, button = await parse_button(hmm)
                button = ikb(await build_keyboard(button)) if button else None
                
                if not teks: teks = f"Welcome {user.mention}"

                if not UwU:
                    sent_msg = await c.send_message(m.chat.id, text=tek, reply_markup=button, disable_web_page_preview=True)
                else:
                    sent_msg = await (await send_cmd(c, mtype))(m.chat.id, UwU, caption=tek, reply_markup=button)

            # Save ID for auto-clean
            if sent_msg:
                db.set_cleanwlcm_id(int(sent_msg.id))

        except (ChannelPrivate, ChatAdminRequired):
            continue
        except Exception as e:
            print(f"Welcome Error: {e}")
            continue

# --- COMMANDS (Set/Reset) ---

@app.on_message(filters.command("setwelcome", config.COMMAND_PREFIXES))
@chatadmin
async def save_wlcm(_, m: Message):
    db = Greetings(m.chat.id)
    text, msgtype, file = await get_wlcm_type(m)
    
    if not text and not file:
        await m.reply_text("Please provide text or media!")
        return

    db.set_welcome_text(text, msgtype, file)
    await m.reply_text("✅ **Custom Welcome Saved!**\nThe Welcome Card will now be disabled for this group.")

@app.on_message(filters.command("resetwelcome", config.COMMAND_PREFIXES))
@chatadmin
async def resetwlcm(_, m: Message):
    db = Greetings(m.chat.id)
    # Resetting to default string triggers the Card Logic again
    db.set_welcome_text(DEFAULT_WELCOME, None)
    await m.reply_text("✅ **Reset to Default!**\nWelcome Card is back ON.")

# (Keep cleanwelcome, cleangoodbye, setgoodbye, resetgoodbye as they were)
# I have shortened them here to fit, but you can keep the previous ones for those commands 
# or copy the full file if you want me to write the ENTIRE thing out (it's long).
# The logic above is the key change.
