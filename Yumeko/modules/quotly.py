import os
import random
import textwrap
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
from pyrogram import Client, filters
from pyrogram.types import Message
from Yumeko import app
import config

# Telegram-style color schemes for chat bubbles
CHAT_THEMES = [
    {"bubble": "#8774E1", "bg": "#0E0E0E", "pattern": "#1a1a1a"},  # Purple
    {"bubble": "#3390EC", "bg": "#0E0E0E", "pattern": "#1a1a1a"},  # Blue
    {"bubble": "#40A7E3", "bg": "#0E0E0E", "pattern": "#1a1a1a"},  # Light Blue
    {"bubble": "#33C659", "bg": "#0E0E0E", "pattern": "#1a1a1a"},  # Green
    {"bubble": "#E8733B", "bg": "#0E0E0E", "pattern": "#1a1a1a"},  # Orange
    {"bubble": "#E8457C", "bg": "#0E0E0E", "pattern": "#1a1a1a"},  # Pink
    {"bubble": "#C95DD7", "bg": "#0E0E0E", "pattern": "#1a1a1a"},  # Magenta
]

def ensure_font():
    """Download fonts with better emoji support"""
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
    """Convert hex to RGB tuple"""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def create_telegram_pattern(width, height, pattern_color):
    """Create Telegram-style background pattern"""
    img = Image.new('RGBA', (width, height), pattern_color + (255,))
    draw = ImageDraw.Draw(img)
    
    # Draw subtle pattern elements (circles, stars, etc.)
    pattern_rgb = pattern_color + (30,)
    for i in range(0, width, 100):
        for j in range(0, height, 100):
            # Random shapes
            shape = random.choice(['circle', 'star', 'heart'])
            if shape == 'circle':
                draw.ellipse([(i, j), (i+40, j+40)], outline=pattern_rgb, width=1)
            elif shape == 'star':
                # Simple star approximation
                points = [(i+20, j), (i+25, j+15), (i+40, j+15), (i+28, j+25), 
                         (i+32, j+40), (i+20, j+30), (i+8, j+40), (i+12, j+25), 
                         (i, j+15), (i+15, j+15)]
                draw.polygon(points, outline=pattern_rgb)
    
    return img

def calculate_bubble_size(text_length):
    """Calculate optimal bubble size based on text length - QuotLy style"""
    if text_length < 30:
        # Very short - big bubble
        return {
            "profile_size": 100,
            "name_font": 36,
            "text_font": 32,
            "padding": 25,
            "bubble_padding": 20,
            "line_height": 42,
            "wrap_width": 30,
            "max_lines": 5
        }
    elif text_length < 100:
        # Short
        return {
            "profile_size": 90,
            "name_font": 34,
            "text_font": 30,
            "padding": 22,
            "bubble_padding": 18,
            "line_height": 38,
            "wrap_width": 35,
            "max_lines": 8
        }
    elif text_length < 200:
        # Medium
        return {
            "profile_size": 80,
            "name_font": 32,
            "text_font": 27,
            "padding": 20,
            "bubble_padding": 16,
            "line_height": 35,
            "wrap_width": 40,
            "max_lines": 12
        }
    else:
        # Long - smaller bubble
        return {
            "profile_size": 70,
            "name_font": 28,
            "text_font": 24,
            "padding": 18,
            "bubble_padding": 14,
            "line_height": 31,
            "wrap_width": 48,
            "max_lines": 16
        }

def draw_rounded_rectangle(draw, coords, radius, fill):
    """Draw a rounded rectangle (for chat bubble)"""
    x1, y1, x2, y2 = coords
    
    # Draw rectangles
    draw.rectangle([x1 + radius, y1, x2 - radius, y2], fill=fill)
    draw.rectangle([x1, y1 + radius, x2, y2 - radius], fill=fill)
    
    # Draw corners
    draw.pieslice([x1, y1, x1 + radius * 2, y1 + radius * 2], 180, 270, fill=fill)
    draw.pieslice([x2 - radius * 2, y1, x2, y1 + radius * 2], 270, 360, fill=fill)
    draw.pieslice([x1, y2 - radius * 2, x1 + radius * 2, y2], 90, 180, fill=fill)
    draw.pieslice([x2 - radius * 2, y2 - radius * 2, x2, y2], 0, 90, fill=fill)

def create_telegram_quote(text: str, username: str, profile_pic=None):
    """Create realistic Telegram-style quote like QuotLy"""
    
    font_path, bold_path = ensure_font()
    
    # Calculate sizes based on text length
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
    
    # Choose theme
    theme = random.choice(CHAT_THEMES)
    bg_rgb = hex_to_rgb(theme["bg"])
    pattern_rgb = hex_to_rgb(theme["pattern"])
    bubble_rgb = hex_to_rgb(theme["bubble"])
    
    # Smart text wrapping
    wrapped_lines = []
    for line in text.split('\n'):
        if len(line) > sizes["wrap_width"]:
            wrapped_lines.extend(textwrap.wrap(line, sizes["wrap_width"], break_long_words=False, break_on_hyphens=False))
        else:
            wrapped_lines.append(line if line else " ")
    
    # Limit lines
    if len(wrapped_lines) > sizes["max_lines"]:
        wrapped_lines = wrapped_lines[:sizes["max_lines"]]
        if len(wrapped_lines[-1]) > sizes["wrap_width"] - 3:
            wrapped_lines[-1] = wrapped_lines[-1][:sizes["wrap_width"]-3] + "..."
    
    # Calculate dimensions
    profile_size = sizes["profile_size"]
    padding = sizes["padding"]
    bubble_pad = sizes["bubble_padding"]
    line_height = sizes["line_height"]
    
    # Calculate text dimensions
    max_text_width = 0
    for line in wrapped_lines:
        bbox = text_font.getbbox(line)
        text_width = bbox[2] - bbox[0]
        max_text_width = max(max_text_width, text_width)
    
    # Bubble dimensions
    bubble_width = max(max_text_width + bubble_pad * 2, 250)
    bubble_height = len(wrapped_lines) * line_height + bubble_pad * 2
    
    # Total image size
    img_width = 512
    total_height = profile_size + padding * 2 + bubble_height + padding * 2
    img_height = min(total_height, 512)
    
    # Create base with pattern
    img = create_telegram_pattern(img_width, img_height, pattern_rgb)
    
    # Darken background
    dark_overlay = Image.new('RGBA', (img_width, img_height), bg_rgb + (220,))
    img = Image.alpha_composite(img, dark_overlay)
    
    draw = ImageDraw.Draw(img)
    
    # Profile picture area
    profile_x = padding
    profile_y = padding
    
    # Draw profile picture
    if profile_pic:
        try:
            profile_pic = profile_pic.convert('RGB')
            profile_pic = profile_pic.resize((profile_size, profile_size), Image.Resampling.LANCZOS)
            
            # Enhance
            enhancer = ImageEnhance.Sharpness(profile_pic)
            profile_pic = enhancer.enhance(1.3)
            
            # Circular mask
            mask = Image.new('L', (profile_size, profile_size), 0)
            mask_draw = ImageDraw.Draw(mask)
            mask_draw.ellipse((0, 0, profile_size, profile_size), fill=255)
            
            # Apply mask
            profile_pic = profile_pic.convert('RGBA')
            output = Image.new('RGBA', (profile_size, profile_size), (0, 0, 0, 0))
            output.paste(profile_pic, (0, 0))
            output.putalpha(mask)
            
            img.paste(output, (profile_x, profile_y), output)
            
        except:
            # Fallback circle
            draw.ellipse(
                [(profile_x, profile_y), (profile_x + profile_size, profile_y + profile_size)],
                fill=bubble_rgb
            )
            letter = username[0].upper() if username else "?"
            try:
                bbox = name_font.getbbox(letter)
                w = bbox[2] - bbox[0]
                h = bbox[3] - bbox[1]
                text_x = profile_x + (profile_size - w) // 2
                text_y = profile_y + (profile_size - h) // 2 - 2
                draw.text((text_x, text_y), letter, fill='white', font=name_font)
            except:
                draw.text((profile_x + profile_size // 3, profile_y + profile_size // 3), 
                         letter, fill='white', font=name_font)
    else:
        # Draw colored circle
        draw.ellipse(
            [(profile_x, profile_y), (profile_x + profile_size, profile_y + profile_size)],
            fill=bubble_rgb
        )
        letter = username[0].upper() if username else "?"
        try:
            bbox = name_font.getbbox(letter)
            w = bbox[2] - bbox[0]
            h = bbox[3] - bbox[1]
            text_x = profile_x + (profile_size - w) // 2
            text_y = profile_y + (profile_size - h) // 2 - 2
            draw.text((text_x, text_y), letter, fill='white', font=name_font)
        except:
            draw.text((profile_x + profile_size // 3, profile_y + profile_size // 3), 
                     letter, fill='white', font=name_font)
    
    # Username position (above bubble)
    name_x = profile_x + profile_size + padding
    name_y = profile_y + 8
    
    # Truncate long names
    display_name = username if len(username) <= 25 else username[:22] + "..."
    
    # Draw username
    draw.text((name_x, name_y), display_name, fill='white', font=name_font)
    
    # Chat bubble position
    bubble_x = name_x
    bubble_y = name_y + sizes["name_font"] + 10
    
    # Draw realistic Telegram chat bubble with shadow
    shadow_offset = 3
    draw_rounded_rectangle(
        draw,
        [bubble_x + shadow_offset, bubble_y + shadow_offset, 
         bubble_x + bubble_width + shadow_offset, bubble_y + bubble_height + shadow_offset],
        15,
        (0, 0, 0, 60)
    )
    
    # Main bubble
    draw_rounded_rectangle(
        draw,
        [bubble_x, bubble_y, bubble_x + bubble_width, bubble_y + bubble_height],
        15,
        bubble_rgb
    )
    
    # Draw bubble tail (Telegram-style pointer)
    tail_points = [
        (bubble_x, bubble_y + 15),
        (bubble_x - 8, bubble_y + 20),
        (bubble_x, bubble_y + 25)
    ]
    draw.polygon(tail_points, fill=bubble_rgb)
    
    # Draw text inside bubble
    text_x = bubble_x + bubble_pad
    text_y = bubble_y + bubble_pad
    
    for line in wrapped_lines:
        # Draw text with slight shadow for depth
        draw.text((text_x + 1, text_y + 1), line, fill=(0, 0, 0, 40), font=text_font)
        draw.text((text_x, text_y), line, fill='white', font=text_font)
        text_y += line_height
    
    return img

@app.on_message(filters.command("q", prefixes=config.config.COMMAND_PREFIXES))
async def telegram_quote(client: Client, message: Message):
    """Generate realistic Telegram quote like QuotLy"""
    
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
    
    username = user.first_name or "User"
    if user.last_name:
        username += f" {user.last_name}"
    
    processing_msg = await message.reply_text("**💬 Creating Telegram quote...**")
    
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
        
        # Generate Telegram-style quote
        quote_img = create_telegram_quote(text, username, profile_pic)
        
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
**💬 Telegram Quote Module:**

Create realistic Telegram-style quotes like @QuotLyBot!

**Commands:**
• `/q` - Reply to any message to create a quote

**Premium Features:**
• 💬 Realistic Telegram chat bubbles
• 🎨 7 authentic Telegram color themes
• 🔍 Smart sizing (short = bigger, long = compact)
• 📱 Perfect chat screenshot look
• 👤 Clear profile pictures
• ✨ Bubble shadows & tails
• 🎯 Clean, readable text

**Smart Sizing:**
• < 30 chars: Large bubble (32px text)
• 30-100: Medium (30px text)
• 100-200: Compact (27px text)
• 200+: Ultra compact (24px text)

**Usage:**
Reply to message → `/q` → Perfect Telegram quote! 💬

Looks exactly like real Telegram chat screenshots!
"""

__module__ = "Quote"
