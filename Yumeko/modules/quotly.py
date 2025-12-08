import os
import random
import textwrap
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from pyrogram import Client, filters
from pyrogram.types import Message
from Yumeko import app
import config

# Vibrant accent colors (like QuotLy)
COLORS = [
    "#FF6B9D", "#C44569", "#F8B500", "#38E54D", 
    "#00D9FF", "#7F5AF0", "#FF5757", "#2EC4B6",
    "#E85D75", "#FFA41B", "#5F27CD", "#00B894"
]

def ensure_font():
    """Download a working font if not exists"""
    font_path = "resources/DejaVuSans.ttf"
    bold_path = "resources/DejaVuSans-Bold.ttf"
    
    if not os.path.isdir("resources"):
        os.mkdir("resources", 0o755)
    
    if not os.path.exists(font_path):
        import urllib.request
        try:
            url = "https://github.com/dejavu-fonts/dejavu-fonts/raw/master/ttf/DejaVuSans.ttf"
            urllib.request.urlretrieve(url, font_path)
        except:
            pass
    
    if not os.path.exists(bold_path):
        import urllib.request
        try:
            url = "https://github.com/dejavu-fonts/dejavu-fonts/raw/master/ttf/DejaVuSans-Bold.ttf"
            urllib.request.urlretrieve(url, bold_path)
        except:
            pass
    
    return font_path, bold_path

def create_quote_sticker(text: str, username: str, profile_pic=None):
    """Create a QuotLy-style quote sticker"""
    
    # Get fonts
    font_path, bold_path = ensure_font()
    
    try:
        if font_path and os.path.exists(font_path):
            name_font = ImageFont.truetype(bold_path if os.path.exists(bold_path) else font_path, 38)
            text_font = ImageFont.truetype(font_path, 30)
        else:
            name_font = ImageFont.load_default()
            text_font = ImageFont.load_default()
    except:
        name_font = ImageFont.load_default()
        text_font = ImageFont.load_default()
    
    # Wrap text (shorter lines for better readability)
    max_width = 40
    wrapped_lines = []
    for line in text.split('\n'):
        if len(line) > max_width:
            wrapped_lines.extend(textwrap.wrap(line, max_width))
        else:
            wrapped_lines.append(line if line else " ")
    
    # Limit to reasonable number of lines
    if len(wrapped_lines) > 12:
        wrapped_lines = wrapped_lines[:12]
        wrapped_lines[-1] = wrapped_lines[-1][:37] + "..."
    
    # Calculate dimensions
    line_height = 42
    top_padding = 30
    text_start_y = 140
    text_height = len(wrapped_lines) * line_height
    
    img_width = 512
    img_height = min(text_start_y + text_height + 40, 512)
    
    # Choose random accent color
    accent_color = random.choice(COLORS)
    
    # Create image with DARK background (like QuotLy)
    img = Image.new('RGBA', (img_width, img_height), (42, 43, 46, 255))
    draw = ImageDraw.Draw(img)
    
    # Draw accent stripe on the left (vertical bar)
    draw.rectangle([(0, 0), (5, img_height)], fill=accent_color)
    
    # Profile picture setup
    profile_size = 80
    profile_x = 30
    profile_y = 35
    
    # Draw profile picture or placeholder
    if profile_pic:
        try:
            # Resize profile pic
            profile_pic = profile_pic.resize((profile_size, profile_size), Image.Resampling.LANCZOS)
            
            # Create circular mask
            mask = Image.new('L', (profile_size, profile_size), 0)
            mask_draw = ImageDraw.Draw(mask)
            mask_draw.ellipse((0, 0, profile_size, profile_size), fill=255)
            
            # Convert profile pic to RGBA
            profile_pic = profile_pic.convert('RGBA')
            
            # Create output with transparency
            output = Image.new('RGBA', (profile_size, profile_size), (0, 0, 0, 0))
            output.paste(profile_pic, (0, 0))
            output.putalpha(mask)
            
            # Paste on main image
            img.paste(output, (profile_x, profile_y), output)
        except Exception as e:
            print(f"Profile pic error: {e}")
            # Draw colored circle if error
            draw.ellipse(
                [(profile_x, profile_y), (profile_x + profile_size, profile_y + profile_size)],
                fill=accent_color
            )
            # First letter
            letter = username[0].upper() if username else "?"
            try:
                bbox = draw.textbbox((0, 0), letter, font=name_font)
                w = bbox[2] - bbox[0]
                h = bbox[3] - bbox[1]
                draw.text((profile_x + (profile_size - w) // 2, profile_y + (profile_size - h) // 2 - 4),
                         letter, fill='white', font=name_font)
            except:
                draw.text((profile_x + 25, profile_y + 20), letter, fill='white', font=name_font)
    else:
        # Draw colored circle with first letter
        draw.ellipse(
            [(profile_x, profile_y), (profile_x + profile_size, profile_y + profile_size)],
            fill=accent_color
        )
        letter = username[0].upper() if username else "?"
        try:
            bbox = draw.textbbox((0, 0), letter, font=name_font)
            w = bbox[2] - bbox[0]
            h = bbox[3] - bbox[1]
            draw.text((profile_x + (profile_size - w) // 2, profile_y + (profile_size - h) // 2 - 4),
                     letter, fill='white', font=name_font)
        except:
            draw.text((profile_x + 25, profile_y + 20), letter, fill='white', font=name_font)
    
    # Draw username next to profile pic
    name_x = profile_x + profile_size + 20
    name_y = profile_y + 27
    
    # Truncate long names
    if len(username) > 20:
        username = username[:17] + "..."
    
    draw.text((name_x, name_y), username, fill='white', font=name_font)
    
    # Draw message text (with good contrast on dark background)
    text_x = 30
    text_y = text_start_y
    
    for line in wrapped_lines:
        draw.text((text_x, text_y), line, fill='white', font=text_font)
        text_y += line_height
    
    return img

@app.on_message(filters.command("q", prefixes=config.config.COMMAND_PREFIXES))
async def quote_command(client: Client, message: Message):
    """Generate a QuotLy-style quote sticker"""
    
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
        except Exception as e:
            print(f"Error fetching profile: {e}")
        
        # Generate quote sticker
        quote_img = create_quote_sticker(text, username, profile_pic)
        
        # Save as WebP sticker
        output_path = f"quote_{message.id}.webp"
        quote_img.save(output_path, "WebP", quality=95, method=6)
        
        # Send as sticker
        await message.reply_sticker(sticker=output_path)
        
        # Cleanup
        await processing_msg.delete()
        
    except Exception as e:
        await processing_msg.edit_text(f"**❌ Error creating quote:**\n`{str(e)}`")
        import traceback
        print(traceback.format_exc())
    
    finally:
        # Cleanup file
        if output_path and os.path.exists(output_path):
            try:
                os.remove(output_path)
            except:
                pass

__help__ = """
**📝 Quote Module:**

Create beautiful quote stickers like @QuotLyBot!

**Commands:**
• `/q` - Reply to any message to create a quote sticker

**Features:**
• Clean QuotLy-style design
• Dark background with colorful accents
• Shows profile picture clearly
• Username displayed prominently
• Perfect text visibility
• Professional sticker format

**Usage:**
Simply reply to any text message with `/q`

**Example:**
Reply to someone's message → `/q` → Beautiful quote sticker! 🎨
"""

__module__ = "Quote"
