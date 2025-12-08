import os
import random
import textwrap
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
from pyrogram import Client, filters
from pyrogram.types import Message
from Yumeko import app
import config

# Bright Telegram-style colors (like QuotLy - VIBRANT!)
BUBBLE_COLORS = [
    "#8B7FF8",  # Purple - bright!
    "#3D9AFF",  # Blue - bright!
    "#4DD4AC",  # Teal - bright!
    "#F7C244",  # Yellow - bright!
    "#FF8066",  # Orange-red - bright!
    "#E85D95",  # Pink - bright!
    "#7EE5A8",  # Green - bright!
]

def ensure_font():
    """Download fonts"""
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

def hex_to_rgb(hex_color):
    """Convert hex to RGB"""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def clean_text(text):
    """Remove problematic characters but keep emojis"""
    # This keeps most unicode including emojis
    return text

def calculate_bubble_size(text_length):
    """Smart sizing based on text length"""
    if text_length < 30:
        return {
            "profile_size": 100,
            "name_font": 34,
            "text_font": 30,
            "padding": 24,
            "bubble_pad": 18,
            "line_height": 40,
            "wrap_width": 28,
            "max_lines": 5
        }
    elif text_length < 100:
        return {
            "profile_size": 90,
            "name_font": 32,
            "text_font": 28,
            "padding": 22,
            "bubble_pad": 16,
            "line_height": 37,
            "wrap_width": 33,
            "max_lines": 8
        }
    elif text_length < 200:
        return {
            "profile_size": 80,
            "name_font": 30,
            "text_font": 26,
            "padding": 20,
            "bubble_pad": 15,
            "line_height": 34,
            "wrap_width": 38,
            "max_lines": 12
        }
    else:
        return {
            "profile_size": 70,
            "name_font": 28,
            "text_font": 23,
            "padding": 18,
            "bubble_pad": 13,
            "line_height": 30,
            "wrap_width": 45,
            "max_lines": 16
        }

def draw_rounded_rectangle(draw, coords, radius, fill):
    """Draw rounded rectangle for bubble"""
    x1, y1, x2, y2 = coords
    
    # Main rectangles
    draw.rectangle([x1 + radius, y1, x2 - radius, y2], fill=fill)
    draw.rectangle([x1, y1 + radius, x2, y2 - radius], fill=fill)
    
    # Corners
    draw.pieslice([x1, y1, x1 + radius * 2, y1 + radius * 2], 180, 270, fill=fill)
    draw.pieslice([x2 - radius * 2, y1, x2, y1 + radius * 2], 270, 360, fill=fill)
    draw.pieslice([x1, y2 - radius * 2, x1 + radius * 2, y2], 90, 180, fill=fill)
    draw.pieslice([x2 - radius * 2, y2 - radius * 2, x2, y2], 0, 90, fill=fill)

def create_quotly_style(text: str, username: str, profile_pic=None):
    """Create QuotLy-style quote - EXACT replica"""
    
    font_path, bold_path = ensure_font()
    
    # Calculate sizes
    sizes = calculate_bubble_size(len(text))
    
    # Load fonts
    try:
        if font_path and os.path.exists(font_path):
            name_font = ImageFont.truetype(bold_path if os.path.exists(bold_path) else font_path, sizes["name_font"])
            text_font = ImageFont.truetype(font_path, sizes["text_font"])
        else:
            name_font = ImageFont.load_default()
            text_font = ImageFont.load_default()
    except:
        name_font = ImageFont.load_default()
        text_font = ImageFont.load_default()
    
    # Random BRIGHT bubble color
    bubble_color = random.choice(BUBBLE_COLORS)
    bubble_rgb = hex_to_rgb(bubble_color)
    
    # Dark background like Telegram
    bg_color = (14, 14, 14)  # #0E0E0E
    
    # Wrap text
    wrapped_lines = []
    for line in text.split('\n'):
        if len(line) > sizes["wrap_width"]:
            wrapped_lines.extend(textwrap.wrap(line, sizes["wrap_width"], break_long_words=False, break_on_hyphens=False))
        else:
            wrapped_lines.append(line if line.strip() else " ")
    
    # Limit lines
    if len(wrapped_lines) > sizes["max_lines"]:
        wrapped_lines = wrapped_lines[:sizes["max_lines"]]
        if len(wrapped_lines[-1]) > sizes["wrap_width"] - 3:
            wrapped_lines[-1] = wrapped_lines[-1][:sizes["wrap_width"]-3] + "..."
    
    # Dimensions
    profile_size = sizes["profile_size"]
    padding = sizes["padding"]
    bubble_pad = sizes["bubble_pad"]
    line_height = sizes["line_height"]
    
    # Calculate text width
    max_text_width = 0
    for line in wrapped_lines:
        try:
            bbox = text_font.getbbox(line)
            text_width = bbox[2] - bbox[0]
            max_text_width = max(max_text_width, text_width)
        except:
            max_text_width = max(max_text_width, len(line) * sizes["text_font"] * 0.6)
    
    # Bubble size
    bubble_width = max(max_text_width + bubble_pad * 2 + 10, 280)
    bubble_height = len(wrapped_lines) * line_height + bubble_pad * 2
    
    # Image size
    img_width = 512
    total_height = profile_size + padding * 2 + bubble_height + padding * 2
    img_height = min(total_height, 512)
    
    # Create dark background
    img = Image.new('RGB', (img_width, img_height), bg_color)
    draw = ImageDraw.Draw(img, 'RGBA')
    
    # Profile position
    profile_x = padding
    profile_y = padding
    
    # Draw profile picture
    if profile_pic:
        try:
            profile_pic = profile_pic.convert('RGB')
            profile_pic = profile_pic.resize((profile_size, profile_size), Image.Resampling.LANCZOS)
            
            # Enhance
            enhancer = ImageEnhance.Sharpness(profile_pic)
            profile_pic = enhancer.enhance(1.2)
            
            # Circular mask
            mask = Image.new('L', (profile_size, profile_size), 0)
            mask_draw = ImageDraw.Draw(mask)
            mask_draw.ellipse((0, 0, profile_size, profile_size), fill=255)
            
            # Convert to RGBA
            profile_rgba = Image.new('RGBA', (profile_size, profile_size), (0, 0, 0, 0))
            profile_rgba.paste(profile_pic, (0, 0))
            profile_rgba.putalpha(mask)
            
            # Paste to main image
            img.paste(profile_rgba, (profile_x, profile_y), profile_rgba)
            
        except Exception as e:
            print(f"Profile error: {e}")
            # Fallback circle
            draw.ellipse(
                [(profile_x, profile_y), (profile_x + profile_size, profile_y + profile_size)],
                fill=bubble_rgb
            )
            # Draw letter
            letter = username[0].upper() if username and len(username) > 0 else "?"
            try:
                # Try to handle unicode
                if ord(letter) > 127:
                    letter = username[1].upper() if len(username) > 1 else "?"
            except:
                letter = "?"
            
            try:
                bbox = name_font.getbbox(letter)
                w = bbox[2] - bbox[0]
                h = bbox[3] - bbox[1]
                draw.text(
                    (profile_x + (profile_size - w) // 2, profile_y + (profile_size - h) // 2 - 2),
                    letter, fill=(255, 255, 255), font=name_font
                )
            except:
                draw.text(
                    (profile_x + profile_size // 3, profile_y + profile_size // 3),
                    letter, fill=(255, 255, 255), font=name_font
                )
    else:
        # Draw circle with letter
        draw.ellipse(
            [(profile_x, profile_y), (profile_x + profile_size, profile_y + profile_size)],
            fill=bubble_rgb
        )
        letter = username[0].upper() if username and len(username) > 0 else "?"
        try:
            if ord(letter) > 127:
                letter = username[1].upper() if len(username) > 1 else "?"
        except:
            letter = "?"
        
        try:
            bbox = name_font.getbbox(letter)
            w = bbox[2] - bbox[0]
            h = bbox[3] - bbox[1]
            draw.text(
                (profile_x + (profile_size - w) // 2, profile_y + (profile_size - h) // 2 - 2),
                letter, fill=(255, 255, 255), font=name_font
            )
        except:
            draw.text(
                (profile_x + profile_size // 3, profile_y + profile_size // 3),
                letter, fill=(255, 255, 255), font=name_font
            )
    
    # Username position (above bubble)
    name_x = profile_x + profile_size + padding - 5
    name_y = profile_y + 5
    
    # Clean and truncate username
    display_name = username if len(username) <= 25 else username[:22] + "..."
    
    # Draw username in WHITE (like QuotLy)
    try:
        draw.text((name_x, name_y), display_name, fill=(255, 255, 255), font=name_font)
    except Exception as e:
        # Fallback if unicode fails
        try:
            safe_name = display_name.encode('ascii', 'ignore').decode('ascii')
            if not safe_name:
                safe_name = "User"
            draw.text((name_x, name_y), safe_name, fill=(255, 255, 255), font=name_font)
        except:
            draw.text((name_x, name_y), "User", fill=(255, 255, 255), font=name_font)
    
    # Bubble position
    bubble_x = name_x
    bubble_y = name_y + sizes["name_font"] + 12
    
    # Draw bubble shadow
    shadow_offset = 2
    draw_rounded_rectangle(
        draw,
        [bubble_x + shadow_offset, bubble_y + shadow_offset,
         bubble_x + bubble_width + shadow_offset, bubble_y + bubble_height + shadow_offset],
        12,
        (0, 0, 0, 80)
    )
    
    # Draw BRIGHT bubble (like QuotLy!)
    draw_rounded_rectangle(
        draw,
        [bubble_x, bubble_y, bubble_x + bubble_width, bubble_y + bubble_height],
        12,
        bubble_rgb
    )
    
    # Draw bubble tail
    tail_points = [
        (bubble_x, bubble_y + 12),
        (bubble_x - 7, bubble_y + 18),
        (bubble_x, bubble_y + 24)
    ]
    draw.polygon(tail_points, fill=bubble_rgb)
    
    # Draw text INSIDE bubble - PURE WHITE (like QuotLy!)
    text_x = bubble_x + bubble_pad
    text_y = bubble_y + bubble_pad
    
    for line in wrapped_lines:
        try:
            # PURE WHITE TEXT - NO SHADOW - CRYSTAL CLEAR!
            draw.text((text_x, text_y), line, fill=(255, 255, 255), font=text_font)
        except Exception as e:
            # Handle unicode errors
            try:
                safe_line = line.encode('utf-8', 'ignore').decode('utf-8')
                draw.text((text_x, text_y), safe_line, fill=(255, 255, 255), font=text_font)
            except:
                pass
        text_y += line_height
    
    return img

@app.on_message(filters.command("q", prefixes=config.config.COMMAND_PREFIXES))
async def quotly_quote(client: Client, message: Message):
    """Generate QuotLy-style quote"""
    
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
    
    # Limit text
    if len(text) > 1000:
        text = text[:997] + "..."
    
    # Get FULL username with emojis (like QuotLy!)
    username = user.first_name or "User"
    if user.last_name:
        username += f" {user.last_name}"
    
    processing_msg = await message.reply_text("**💬 Creating quote...**")
    
    output_path = None
    try:
        # Get profile photo
        profile_pic = None
        try:
            photos = [photo async for photo in client.get_chat_photos(user.id, limit=1)]
            if photos:
                pfp_file = await client.download_media(photos[0], in_memory=True)
                profile_pic = Image.open(BytesIO(pfp_file.getvalue()))
        except:
            pass
        
        # Generate QuotLy-style quote
        quote_img = create_quotly_style(text, username, profile_pic)
        
        # Save as high-quality WebP
        output_path = f"quote_{message.id}.webp"
        quote_img.save(output_path, "WebP", quality=100, method=6)
        
        # Send as sticker
        await message.reply_sticker(sticker=output_path)
        await processing_msg.delete()
        
    except Exception as e:
        await processing_msg.edit_text(f"**❌ Error:**\n`{str(e)}`")
        import traceback
        print(traceback.format_exc())
    
    finally:
        if output_path and os.path.exists(output_path):
            try:
                os.remove(output_path)
            except:
                pass

__help__ = """
**💬 QuotLy-Style Quote Module:**

Create beautiful quotes exactly like @QuotLyBot!

**Commands:**
• `/q` - Reply to any message to create a quote

**Features:**
• 💬 Realistic Telegram chat bubbles
• 🎨 Bright, vibrant colors (like QuotLy!)
• ⚪ Pure white text - crystal clear!
• 🔤 Full emoji & unicode support
• 👤 High-quality profile pictures
• 🔍 Smart sizing (auto zoom in/out)
• ✨ Clean bubble shadows & tails

**Smart Sizing:**
• < 30 chars: Large (30px text)
• 30-100: Medium (28px text)
• 100-200: Compact (26px text)
• 200+: Ultra compact (23px text)

**Usage:**
Reply to message → `/q` → Beautiful quote! 💬

Perfect replica of @QuotLyBot design! ✨
"""

__module__ = "Quote"
