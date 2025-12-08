import os
import random
import textwrap
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from pyrogram import Client, filters
from pyrogram.types import Message
from Yumeko import app
import config

# Color palette - vibrant colors
COLORS = [
    "#FF6B6B", "#4ECDC4", "#45B7D1", "#FFA07A", 
    "#98D8C8", "#F7DC6F", "#BB8FCE", "#85C1E2",
    "#FF85B3", "#74C0FC", "#FFD93D", "#6BCB77"
]

def ensure_font():
    """Download a working font if not exists"""
    font_path = "resources/DejaVuSans.ttf"
    
    if not os.path.isdir("resources"):
        os.mkdir("resources", 0o755)
    
    if not os.path.exists(font_path):
        import urllib.request
        try:
            url = "https://github.com/dejavu-fonts/dejavu-fonts/raw/master/ttf/DejaVuSans.ttf"
            urllib.request.urlretrieve(url, font_path)
        except:
            return None
    
    return font_path

def create_quote_sticker(text: str, username: str, profile_pic=None):
    """Create a Telegram-style quote sticker"""
    
    # Get font
    font_path = ensure_font()
    
    try:
        if font_path and os.path.exists(font_path):
            name_font = ImageFont.truetype(font_path, 40)
            text_font = ImageFont.truetype(font_path, 32)
        else:
            name_font = ImageFont.load_default()
            text_font = ImageFont.load_default()
    except:
        name_font = ImageFont.load_default()
        text_font = ImageFont.load_default()
    
    # Wrap text
    max_width = 45
    wrapped_lines = []
    for line in text.split('\n'):
        if len(line) > max_width:
            wrapped_lines.extend(textwrap.wrap(line, max_width))
        else:
            wrapped_lines.append(line if line else " ")
    
    # Calculate dimensions
    padding = 30
    line_height = 45
    text_height = len(wrapped_lines) * line_height
    img_width = 512  # Standard sticker width
    img_height = min(text_height + 200, 512)  # Standard sticker height (max 512)
    
    # Choose random vibrant color
    accent_color = random.choice(COLORS)
    
    # Create image with dark gradient background
    img = Image.new('RGB', (img_width, img_height), color='#1a1a2e')
    draw = ImageDraw.Draw(img)
    
    # Draw subtle gradient effect
    for i in range(img_height):
        shade = int(26 + (i / img_height) * 15)
        draw.line([(0, i), (img_width, i)], fill=f'#{shade:02x}{shade:02x}{shade+10:02x}')
    
    # Draw colorful accent bar on left
    draw.rectangle([(0, 0), (6, img_height)], fill=accent_color)
    
    # Profile section
    profile_x = padding + 10
    profile_y = padding
    profile_size = 80
    
    if profile_pic:
        try:
            # Resize and make circular
            profile_pic = profile_pic.resize((profile_size, profile_size))
            mask = Image.new('L', (profile_size, profile_size), 0)
            mask_draw = ImageDraw.Draw(mask)
            mask_draw.ellipse((0, 0, profile_size, profile_size), fill=255)
            
            output = Image.new('RGBA', (profile_size, profile_size), (0, 0, 0, 0))
            output.paste(profile_pic, (0, 0))
            output.putalpha(mask)
            
            # Add white border around profile pic
            draw.ellipse(
                [(profile_x - 3, profile_y - 3), 
                 (profile_x + profile_size + 3, profile_y + profile_size + 3)],
                outline='white', width=3
            )
            
            img.paste(output, (profile_x, profile_y), output)
        except:
            # Draw colored circle with white border
            draw.ellipse(
                [(profile_x - 3, profile_y - 3), 
                 (profile_x + profile_size + 3, profile_y + profile_size + 3)],
                outline='white', width=3
            )
            draw.ellipse(
                [(profile_x, profile_y), 
                 (profile_x + profile_size, profile_y + profile_size)],
                fill=accent_color
            )
            # Draw first letter
            letter = username[0].upper() if username else "U"
            try:
                letter_bbox = draw.textbbox((0, 0), letter, font=name_font)
                letter_width = letter_bbox[2] - letter_bbox[0]
                letter_height = letter_bbox[3] - letter_bbox[1]
                draw.text(
                    (profile_x + (profile_size - letter_width) // 2,
                     profile_y + (profile_size - letter_height) // 2 - 5),
                    letter, fill='white', font=name_font
                )
            except:
                draw.text((profile_x + 25, profile_y + 20), letter, fill='white', font=name_font)
    else:
        # Draw colored circle with white border
        draw.ellipse(
            [(profile_x - 3, profile_y - 3), 
             (profile_x + profile_size + 3, profile_y + profile_size + 3)],
            outline='white', width=3
        )
        draw.ellipse(
            [(profile_x, profile_y), 
             (profile_x + profile_size, profile_y + profile_size)],
            fill=accent_color
        )
        letter = username[0].upper() if username else "U"
        try:
            letter_bbox = draw.textbbox((0, 0), letter, font=name_font)
            letter_width = letter_bbox[2] - letter_bbox[0]
            letter_height = letter_bbox[3] - letter_bbox[1]
            draw.text(
                (profile_x + (profile_size - letter_width) // 2,
                 profile_y + (profile_size - letter_height) // 2 - 5),
                letter, fill='white', font=name_font
            )
        except:
            draw.text((profile_x + 25, profile_y + 20), letter, fill='white', font=name_font)
    
    # Draw username with glow effect
    name_x = profile_x + profile_size + 20
    name_y = profile_y + 25
    
    # Add shadow for depth
    draw.text((name_x + 2, name_y + 2), username, fill='#000000', font=name_font)
    draw.text((name_x, name_y), username, fill=accent_color, font=name_font)
    
    # Draw decorative line under username
    line_y = profile_y + profile_size + 15
    draw.line([(padding + 10, line_y), (img_width - padding - 10, line_y)], 
              fill=accent_color, width=2)
    
    # Draw message text with better spacing
    text_y = line_y + 25
    for line in wrapped_lines:
        # Add subtle shadow
        draw.text((padding + 12, text_y + 1), line, fill='#000000', font=text_font)
        draw.text((padding + 10, text_y), line, fill='#FFFFFF', font=text_font)
        text_y += line_height
    
    return img

@app.on_message(filters.command("q", prefixes=config.config.COMMAND_PREFIXES))
async def quote_command(client: Client, message: Message):
    """Generate a beautiful quote sticker from replied message"""
    
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
    if len(text) > 400:
        text = text[:397] + "..."
    
    username = user.first_name
    if user.last_name:
        username += f" {user.last_name}"
    
    # Limit username length
    if len(username) > 25:
        username = username[:22] + "..."
    
    # Processing message
    processing_msg = await message.reply_text("**🎨 Creating quote sticker...**")
    
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
        
        # Generate quote sticker
        quote_img = create_quote_sticker(text, username, profile_pic)
        
        # Convert to RGBA for transparency
        quote_img = quote_img.convert('RGBA')
        
        # Save as WebP (sticker format)
        output_path = f"quote_{message.id}.webp"
        quote_img.save(output_path, "WebP", quality=95)
        
        # Send as sticker
        await message.reply_sticker(sticker=output_path)
        
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

__help__ = """
**📝 Quote Module:**

Create beautiful quote stickers from messages!

**Commands:**
• `/q` - Reply to any message to create a quote sticker

**Features:**
• Beautiful Telegram-style design
• Colorful accent colors
• Shows profile picture
• Professional sticker format
• Auto text wrapping

**Usage:**
Simply reply to any text message with `/q`

**Example:**
Reply to someone's message → `/q` → Get a beautiful quote sticker! 🎨
"""

__module__ = "Quote"
