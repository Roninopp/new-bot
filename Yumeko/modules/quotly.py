import os
import random
import textwrap
import urllib.request
import json
from io import BytesIO

import emoji
from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFont, ImageOps
from pyrogram import Client, filters
from pyrogram.types import Message
from Yumeko import app
import config

# Color palette for profile pictures
COLORS = [
    "#F07975",
    "#F49F69",
    "#F9C84A",
    "#8CC56E",
    "#6CC7DC",
    "#80C1FA",
    "#BCB3F9",
    "#E181AC",
]

# Ensure resources folder exists
def ensure_resources():
    if not os.path.isdir("resources"):
        os.mkdir("resources", 0o755)
        fonts = {
            "Roboto-Regular.ttf": "https://github.com/erenmetesar/modules-repo/raw/master/Roboto-Regular.ttf",
            "Quivira.otf": "https://github.com/erenmetesar/modules-repo/raw/master/Quivira.otf",
            "Roboto-Medium.ttf": "https://github.com/erenmetesar/modules-repo/raw/master/Roboto-Medium.ttf",
            "DroidSansMono.ttf": "https://github.com/erenmetesar/modules-repo/raw/master/DroidSansMono.ttf",
            "Roboto-Italic.ttf": "https://github.com/erenmetesar/modules-repo/raw/master/Roboto-Italic.ttf",
        }
        for font_name, url in fonts.items():
            urllib.request.urlretrieve(url, f"resources/{font_name}")

async def fontTest(letter):
    """Check if a letter is supported by the font"""
    try:
        test = TTFont("resources/Roboto-Medium.ttf")
        for table in test["cmap"].tables:
            if ord(letter) in table.cmap.keys():
                return True
    except:
        pass
    return False

async def drawer(width, height):
    """Draw the background template"""
    # Top part
    top = Image.new("RGBA", (width, 20), (0, 0, 0, 0))
    draw = ImageDraw.Draw(top)
    draw.line((10, 0, top.width - 20, 0), fill=(29, 29, 29, 255), width=50)
    draw.pieslice((0, 0, 30, 50), 180, 270, fill=(29, 29, 29, 255))
    draw.pieslice((top.width - 75, 0, top.width, 50), 270, 360, fill=(29, 29, 29, 255))

    # Middle part
    middle = Image.new("RGBA", (top.width, height + 75), (29, 29, 29, 255))

    # Bottom part
    bottom = ImageOps.flip(top)

    return top, middle, bottom

async def no_photo(user, tot):
    """Generate a profile picture with first letter if no photo"""
    pfp = Image.new("RGBA", (105, 105), (0, 0, 0, 0))
    pen = ImageDraw.Draw(pfp)
    color = random.choice(COLORS)
    pen.ellipse((0, 0, 105, 105), fill=color)
    letter = "" if not tot else tot[0]
    font = ImageFont.truetype("resources/Roboto-Regular.ttf", 60)
    pen.text((32, 17), letter, font=font, fill="white")
    return pfp, color

async def emoji_fetch(emoji_char):
    """Fetch emoji image"""
    try:
        emojis = json.loads(
            urllib.request.urlopen(
                "https://github.com/erenmetesar/modules-repo/raw/master/emojis.txt"
            )
            .read()
            .decode()
        )
        if emoji_char in emojis:
            img = emojis[emoji_char]
        else:
            img = emojis["🖤"]
        
        emoji_path = "resources/emoji.png"
        urllib.request.urlretrieve(img, emoji_path)
        return await transparent(emoji_path)
    except:
        # Fallback emoji
        emoji_img = Image.new("RGBA", (40, 40), (0, 0, 0, 0))
        mask = Image.new("L", (40, 40), 0)
        return emoji_img, mask

async def transparent(emoji_path):
    """Make emoji transparent"""
    emoji_img = Image.open(emoji_path).convert("RGBA")
    emoji_img.thumbnail((40, 40))

    # Mask
    mask = Image.new("L", (40, 40), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, 40, 40), fill=255)
    return emoji_img, mask

async def process_quote(msg_text, user, client: Client):
    """Process the quote and generate image"""
    ensure_resources()

    # Load fonts
    font = ImageFont.truetype("resources/Roboto-Medium.ttf", 43, encoding="utf-16")
    font2 = ImageFont.truetype("resources/Roboto-Regular.ttf", 33, encoding="utf-16")
    fallback = ImageFont.truetype("resources/Quivira.otf", 43, encoding="utf-16")

    # Split text
    maxlength = 0
    width = 0
    text = []
    
    for line in msg_text.split("\n"):
        length = len(line)
        if length > 43:
            text += textwrap.wrap(line, 43)
            maxlength = 43
            if width < fallback.getsize(line[:43])[0]:
                width = fallback.getsize(line[:43])[0]
        else:
            text.append(line + "\n")
            if width < fallback.getsize(line)[0]:
                width = fallback.getsize(line)[0]
            if maxlength < length:
                maxlength = length

    # Get user name
    lname = "" if not user.last_name else user.last_name
    tot = user.first_name + " " + lname
    namewidth = fallback.getsize(tot)[0] + 10

    if namewidth > width:
        width = namewidth
    width += 60
    height = len(text) * 40

    # Profile Photo BG
    pfpbg = Image.new("RGBA", (125, 600), (0, 0, 0, 0))

    # Draw Template
    top, middle, bottom = await drawer(width, height)
    
    # Profile Photo
    color = random.choice(COLORS)
    try:
        photos = [photo async for photo in client.get_chat_photos(user.id, limit=1)]
        if photos:
            pfp_file = await client.download_media(photos[0], in_memory=True)
            paste = Image.open(BytesIO(pfp_file.getvalue()))
            paste.thumbnail((105, 105))

            # Create circular mask
            mask_im = Image.new("L", paste.size, 0)
            draw = ImageDraw.Draw(mask_im)
            draw.ellipse((0, 0, 105, 105), fill=255)

            pfpbg.paste(paste, (0, 0), mask_im)
        else:
            raise Exception("No photo")
    except:
        paste, color = await no_photo(user, tot)
        pfpbg.paste(paste, (0, 0))

    # Create canvas
    canvassize = (
        middle.width + pfpbg.width,
        top.height + middle.height + bottom.height,
    )
    canvas = Image.new("RGBA", canvassize)
    draw = ImageDraw.Draw(canvas)

    # Paste components
    canvas.paste(pfpbg, (0, 0))
    canvas.paste(top, (pfpbg.width, 0))
    canvas.paste(middle, (pfpbg.width, top.height))
    canvas.paste(bottom, (pfpbg.width, top.height + middle.height))

    # Write user name
    space = pfpbg.width + 30
    namefallback = ImageFont.truetype("resources/Quivira.otf", 43, encoding="utf-16")
    for letter in tot:
        if letter in emoji.UNICODE_EMOJI:
            try:
                newemoji, mask = await emoji_fetch(letter)
                canvas.paste(newemoji, (space, 24), mask)
                space += 40
            except:
                space += 10
        else:
            if not await fontTest(letter):
                draw.text((space, 20), letter, font=namefallback, fill=color)
                space += namefallback.getsize(letter)[0]
            else:
                draw.text((space, 20), letter, font=font, fill=color)
                space += font.getsize(letter)[0]

    # Write message text
    x = pfpbg.width + 30
    y = 85
    textfallback = ImageFont.truetype("resources/Quivira.otf", 33, encoding="utf-16")
    
    for line in text:
        for letter in line:
            if letter in emoji.UNICODE_EMOJI:
                try:
                    newemoji, mask = await emoji_fetch(letter)
                    canvas.paste(newemoji, (x, y - 2), mask)
                    x += 45
                except:
                    x += 10
            else:
                if not await fontTest(letter):
                    draw.text((x, y), letter, font=textfallback, fill="white")
                    x += textfallback.getsize(letter)[0]
                else:
                    draw.text((x, y), letter, font=font2, fill="white")
                    x += font2.getsize(letter)[0]
        y += 40
        x = pfpbg.width + 30

    return canvas

@app.on_message(filters.command("q", prefixes=config.COMMAND_PREFIXES))
async def quote_command(client: Client, message: Message):
    """Generate a quote sticker from replied message"""
    if not message.reply_to_message:
        await message.reply_text("**❌ Reply to a message to quote it!**")
        return

    reply = message.reply_to_message
    
    # Check if message has text
    if not reply.text and not reply.caption:
        await message.reply_text("**❌ Can only quote text messages!**")
        return

    msg_text = reply.text or reply.caption
    user = reply.from_user

    if not user:
        await message.reply_text("**❌ Cannot quote this message!**")
        return

    # Processing message
    processing_msg = await message.reply_text("**🎨 Creating quote sticker...**")

    try:
        # Generate quote image
        canvas = await process_quote(msg_text, user, client)
        
        # Save as webp
        output_path = f"quote_{message.id}.webp"
        canvas.save(output_path, "WebP")

        # Send as sticker
        await message.reply_sticker(sticker=output_path)
        
        # Cleanup
        await processing_msg.delete()
        if os.path.exists(output_path):
            os.remove(output_path)
            
    except Exception as e:
        await processing_msg.edit_text(f"**❌ Error creating quote:** `{str(e)}`")
        if os.path.exists(output_path):
            os.remove(output_path)

__help__ = """
**📝 Quote Module:**

Create beautiful quote stickers from messages!

**Usage:**
• `/q` - Reply to any text message to create a quote sticker

**Features:**
• Beautiful Telegram-style quote design
• Shows user profile picture and name
• Supports emojis and special characters
• Creates high-quality WebP stickers

**Example:**
Reply to someone's message with `/q` to turn it into a shareable quote sticker!
"""

__module__ = "Quote"
