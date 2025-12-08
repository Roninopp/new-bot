import os
import random
import textwrap
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from pyrogram import Client, filters
from pyrogram.types import Message
from Yumeko import app
import config

# Color palette
COLORS = [
    "#FF6B6B", "#4ECDC4", "#45B7D1", "#FFA07A", 
    "#98D8C8", "#F7DC6F", "#BB8FCE", "#85C1E2"
]

def ensure_font():
    """Download a working font if not exists"""
    font_path = "resources/DejaVuSans.ttf"
    
    if not os.path.isdir("resources"):
        os.mkdir("resources", 0o755)
    
    if not os.path.exists(font_path):
        # Use a reliable CDN for DejaVu Sans
        import urllib.request
        try:
            url = "https://github.com/dejavu-fonts/dejavu-fonts/raw/master/ttf/DejaVuSans.ttf"
            urllib.request.urlretrieve(url, font_path)
        except:
            # If download fails, use PIL's default font
            return None
    
    return font_path

def create_quote_image(text: str, username: str, profile_pic=None):
    """Create a simple, clean quote image"""
    
    # Get font
    font_path = ensure_font()
    
    try:
        if font_path and os.path.exists(font_path):
            name_font = ImageFont.truetype(font_path, 36)
            text_font = ImageFont.truetype(font_path, 28)
        else:
            name_font = ImageFont.load_default()
            text_font = ImageFont.load_default()
    except:
        name_font = ImageFont.load_default()
        text_font = ImageFont.load_default()
    
    # Wrap text
    max_width = 50
    wrapped_lines = []
    for line in text.split('\n'):
        if len(line) > max_width:
            wrapped_lines.extend(textwrap.wrap(line, max_width))
        else:
            wrapped_lines.append(line)
    
    # Calculate dimensions
    padding = 40
    line_height = 40
    text_height = len(wrapped_lines) * line_height
    img_width = 600
    img_height = text_height + 180
    
    # Choose random color
    accent_color = random.choice(COLORS)
    
    # Create image with dark background
    img = Image.new('RGB', (img_width, img_height), color='#1a1a1a')
    draw = ImageDraw.Draw(img)
    
    # Draw accent bar on left
    draw.rectangle([(0, 0), (8, img_height)], fill=accent_color)
    
    # Draw profile circle placeholder
    profile_x = padding + 20
    profile_y = padding
    profile_size = 70
    
    if profile_pic:
        try:
            # Resize profile pic
            profile_pic = profile_pic.resize((profile_size, profile_size))
            
            # Create circular mask
            mask = Image.new('L', (profile_size, profile_size), 0)
            mask_draw = ImageDraw.Draw(mask)
            mask_draw.ellipse((0, 0, profile_size, profile_size), fill=255)
            
            # Create circular profile pic
            output = Image.new('RGBA', (profile_size, profile_size), (0, 0, 0, 0))
            output.paste(profile_pic, (0, 0))
            output.putalpha(mask)
            
            img.paste(output, (profile_x, profile_y), output)
        except:
            # Draw colored circle if profile pic fails
            draw.ellipse(
                [(profile_x, profile_y), 
                 (profile_x + profile_size, profile_y + profile_size)],
                fill=accent_color
            )
            # Draw first letter
            letter = username[0].upper() if username else "U"
            letter_bbox = draw.textbbox((0, 0), letter, font=name_font)
            letter_width = letter_bbox[2] - letter_bbox[0]
            letter_height = letter_bbox[3] - letter_bbox[1]
            draw.text(
                (profile_x + (profile_size - letter_width) // 2,
                 profile_y + (profile_size - letter_height) // 2 - 5),
                letter, fill='white', font=name_font
            )
    else:
        # Draw colored circle with first letter
        draw.ellipse(
            [(profile_x, profile_y), 
             (profile_x + profile_size, profile_y + profile_size)],
            fill=accent_color
        )
        letter = username[0].upper() if username else "U"
        letter_bbox = draw.textbbox((0, 0), letter, font=name_font)
        letter_width = letter_bbox[2] - letter_bbox[0]
        letter_height = letter_bbox[3] - letter_bbox[1]
        draw.text(
            (profile_x + (profile_size - letter_width) // 2,
             profile_y + (profile_size - letter_height) // 2 - 5),
            letter, fill='white', font=name_font
        )
    
    # Draw username
    name_x = profile_x + profile_size + 20
    name_y = profile_y + 20
    draw.text((name_x, name_y), username, fill=accent_color, font=name_font)
    
    # Draw message text
    text_y = profile_y + profile_size + 30
    for line in wrapped_lines:
        draw.text((padding + 20, text_y), line, fill='#FFFFFF', font=text_font)
        text_y += line_height
    
    return img

@app.on_message(filters.command("q", prefixes=config.config.COMMAND_PREFIXES))
async def quote_command(client: Client, message: Message):
    """Generate a quote image from replied message"""
    
    if not message.reply_to_message:
        await message.reply_text("**❌ Reply to a message to quote it!**")
        return

    reply = message.reply_to_message
    
    # Get text
    if reply.text:
        text = reply.text
    elif reply.caption:
        text = reply.caption
    else:
        await message.reply_text("**❌ Can only quote text messages!**")
        return
    
    # Get user
    user = reply.from_user
    if not user:
        await message.reply_text("**❌ Cannot quote this message!**")
        return
    
    # Limit text length
    if len(text) > 500:
        text = text[:497] + "..."
    
    username = user.first_name
    if user.last_name:
        username += f" {user.last_name}"
    
    # Processing message
    processing_msg = await message.reply_text("**🎨 Creating quote...**")
    
    output_path = None
    try:
        # Try to get profile photo
        profile_pic = None
        try:
            photos = [photo async for photo in client.get_chat_photos(user.id, limit=1)]
            if photos:
                pfp_file = await client.download_media(photos[0], in_memory=True)
                profile_pic = Image.open(BytesIO(pfp_file.getvalue()))
        except:
            pass
        
        # Generate quote image
        quote_img = create_quote_image(text, username, profile_pic)
        
        # Save as PNG (more reliable than WebP)
        output_path = f"quote_{message.id}.png"
        quote_img.save(output_path, "PNG")
        
        # Send as photo (more reliable than sticker)
        await message.reply_photo(photo=output_path)
        
        # Cleanup
        await processing_msg.delete()
        
    except Exception as e:
        await processing_msg.edit_text(f"**❌ Error:** `{str(e)}`")
    
    finally:
        # Cleanup file
        if output_path and os.path.exists(output_path):
            try:
                os.remove(output_path)
            except:
                pass

@app.on_message(filters.command("qq", prefixes=config.config.COMMAND_PREFIXES))
async def quote_sticker(client: Client, message: Message):
    """Generate a quote as sticker (WebP format)"""
    
    if not message.reply_to_message:
        await message.reply_text("**❌ Reply to a message to quote it!**")
        return

    reply = message.reply_to_message
    
    # Get text
    if reply.text:
        text = reply.text
    elif reply.caption:
        text = reply.caption
    else:
        await message.reply_text("**❌ Can only quote text messages!**")
        return
    
    user = reply.from_user
    if not user:
        await message.reply_text("**❌ Cannot quote this message!**")
        return
    
    if len(text) > 500:
        text = text[:497] + "..."
    
    username = user.first_name
    if user.last_name:
        username += f" {user.last_name}"
    
    processing_msg = await message.reply_text("**🎨 Creating quote sticker...**")
    
    output_path = None
    try:
        profile_pic = None
        try:
            photos = [photo async for photo in client.get_chat_photos(user.id, limit=1)]
            if photos:
                pfp_file = await client.download_media(photos[0], in_memory=True)
                profile_pic = Image.open(BytesIO(pfp_file.getvalue()))
        except:
            pass
        
        quote_img = create_quote_image(text, username, profile_pic)
        
        # Convert to RGBA for WebP with transparency
        quote_img = quote_img.convert('RGBA')
        
        output_path = f"quote_{message.id}.webp"
        quote_img.save(output_path, "WebP")
        
        await message.reply_sticker(sticker=output_path)
        await processing_msg.delete()
        
    except Exception as e:
        await processing_msg.edit_text(f"**❌ Error:** `{str(e)}`")
    
    finally:
        if output_path and os.path.exists(output_path):
            try:
                os.remove(output_path)
            except:
                pass

__help__ = """
**📝 Quote Module:**

Create beautiful quote images from messages!

**Commands:**
• `/q` - Reply to a message to create a quote image (PNG)
• `/qq` - Reply to a message to create a quote sticker (WebP)

**Features:**
• Clean, modern design
• Shows user profile picture
• Automatic text wrapping
• Random accent colors
• Works with long messages

**Usage:**
Simply reply to any text message with `/q` or `/qq`

**Note:** `/q` sends as photo (more reliable), `/qq` sends as sticker.
"""

__module__ = "Quote"
