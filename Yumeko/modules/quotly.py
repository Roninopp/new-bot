import os
import random
import textwrap
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
from pyrogram import Client, filters
from pyrogram.types import Message
from Yumeko import app
import config

# Premium color schemes
COLOR_SCHEMES = [
    {"accent": "#FF6B9D", "bg": "#1a1625", "gradient": "#2d1f3d"},
    {"accent": "#00D9FF", "bg": "#0a1929", "gradient": "#1a2942"},
    {"accent": "#F8B500", "bg": "#1f1810", "gradient": "#3d2f1f"},
    {"accent": "#38E54D", "bg": "#0f1f12", "gradient": "#1f3d25"},
    {"accent": "#7F5AF0", "bg": "#1a1333", "gradient": "#2d2252"},
    {"accent": "#FF5757", "bg": "#2d1414", "gradient": "#4a2323"},
    {"accent": "#2EC4B6", "bg": "#0e1f1d", "gradient": "#1d3d37"},
    {"accent": "#FFA41B", "bg": "#1f1608", "gradient": "#3d2d18"},
]

def ensure_font():
    """Download premium fonts"""
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

def create_gradient_background(width, height, color_scheme):
    """Create a beautiful gradient background"""
    img = Image.new('RGB', (width, height), color_scheme["bg"])
    draw = ImageDraw.Draw(img)
    
    # Gradient from top to bottom
    r1, g1, b1 = tuple(int(color_scheme["bg"][i:i+2], 16) for i in (1, 3, 5))
    r2, g2, b2 = tuple(int(color_scheme["gradient"][i:i+2], 16) for i in (1, 3, 5))
    
    for y in range(height):
        ratio = y / height
        r = int(r1 + (r2 - r1) * ratio)
        g = int(g1 + (g2 - g1) * ratio)
        b = int(b1 + (b2 - b1) * ratio)
        draw.line([(0, y), (width, y)], fill=(r, g, b))
    
    return img

def add_glow_effect(img, draw, x, y, size, color):
    """Add glow effect to profile picture"""
    glow_radius = 8
    for i in range(glow_radius, 0, -1):
        alpha = int(30 * (glow_radius - i) / glow_radius)
        glow_color = tuple(list(color) + [alpha])
        offset = i * 2
        draw.ellipse(
            [(x - offset, y - offset), (x + size + offset, y + size + offset)],
            outline=color + (alpha,),
            width=2
        )

def calculate_optimal_sizes(text_length):
    """AI-like feature: Calculate optimal sizes based on text length"""
    # Short messages get zoomed in (larger elements)
    # Long messages get zoomed out (smaller elements)
    
    if text_length < 50:
        # Very short - zoom in
        return {
            "profile_size": 90,
            "name_font_size": 42,
            "text_font_size": 34,
            "padding": 35,
            "line_spacing": 48,
            "wrap_width": 35,
            "max_lines": 8
        }
    elif text_length < 150:
        # Short to medium
        return {
            "profile_size": 80,
            "name_font_size": 38,
            "text_font_size": 30,
            "padding": 30,
            "line_spacing": 42,
            "wrap_width": 40,
            "max_lines": 10
        }
    elif text_length < 300:
        # Medium to long
        return {
            "profile_size": 70,
            "name_font_size": 34,
            "text_font_size": 26,
            "padding": 25,
            "line_spacing": 36,
            "wrap_width": 48,
            "max_lines": 14
        }
    else:
        # Very long - zoom out
        return {
            "profile_size": 60,
            "name_font_size": 30,
            "text_font_size": 22,
            "padding": 20,
            "line_spacing": 30,
            "wrap_width": 55,
            "max_lines": 18
        }

def create_advanced_quote(text: str, username: str, profile_pic=None):
    """Create high-quality quote sticker with intelligent sizing"""
    
    # Get fonts
    font_path, bold_path = ensure_font()
    
    # Calculate optimal sizes based on text length
    sizes = calculate_optimal_sizes(len(text))
    
    try:
        if font_path and os.path.exists(font_path):
            name_font = ImageFont.truetype(bold_path if os.path.exists(bold_path) else font_path, sizes["name_font_size"])
            text_font = ImageFont.truetype(font_path, sizes["text_font_size"])
        else:
            name_font = ImageFont.load_default()
            text_font = ImageFont.load_default()
    except:
        name_font = ImageFont.load_default()
        text_font = ImageFont.load_default()
    
    # Choose random color scheme
    scheme = random.choice(COLOR_SCHEMES)
    accent_rgb = tuple(int(scheme["accent"][i:i+2], 16) for i in (1, 3, 5))
    
    # Smart text wrapping
    wrapped_lines = []
    for line in text.split('\n'):
        if len(line) > sizes["wrap_width"]:
            wrapped_lines.extend(textwrap.wrap(line, sizes["wrap_width"], break_long_words=False))
        else:
            wrapped_lines.append(line if line else " ")
    
    # Limit lines
    if len(wrapped_lines) > sizes["max_lines"]:
        wrapped_lines = wrapped_lines[:sizes["max_lines"]]
        wrapped_lines[-1] = wrapped_lines[-1][:sizes["wrap_width"]-3] + "..."
    
    # Calculate dimensions
    profile_size = sizes["profile_size"]
    padding = sizes["padding"]
    line_spacing = sizes["line_spacing"]
    
    header_height = profile_size + padding * 3
    text_height = len(wrapped_lines) * line_spacing + padding
    
    img_width = 512
    img_height = min(header_height + text_height + padding * 2, 512)
    
    # Create gradient background
    img = create_gradient_background(img_width, img_height, scheme)
    img = img.convert('RGBA')
    
    # Add subtle noise for texture
    overlay = Image.new('RGBA', (img_width, img_height), (255, 255, 255, 0))
    noise_draw = ImageDraw.Draw(overlay)
    for _ in range(500):
        x = random.randint(0, img_width)
        y = random.randint(0, img_height)
        noise_draw.point((x, y), fill=(255, 255, 255, random.randint(5, 15)))
    img = Image.alpha_composite(img, overlay)
    
    draw = ImageDraw.Draw(img)
    
    # Draw accent elements
    # Top accent line
    draw.rectangle([(0, 0), (img_width, 4)], fill=accent_rgb)
    # Left accent stripe
    draw.rectangle([(0, 0), (6, img_height)], fill=accent_rgb)
    # Bottom accent line
    draw.rectangle([(0, img_height - 4), (img_width, img_height)], fill=accent_rgb)
    
    # Profile picture positioning
    profile_x = padding + 5
    profile_y = padding
    
    # Process and draw profile picture
    if profile_pic:
        try:
            # Resize with high quality
            profile_pic = profile_pic.convert('RGB')
            profile_pic = profile_pic.resize((profile_size, profile_size), Image.Resampling.LANCZOS)
            
            # Enhance profile picture
            enhancer = ImageEnhance.Sharpness(profile_pic)
            profile_pic = enhancer.enhance(1.2)
            
            # Create circular mask
            mask = Image.new('L', (profile_size, profile_size), 0)
            mask_draw = ImageDraw.Draw(mask)
            mask_draw.ellipse((0, 0, profile_size, profile_size), fill=255)
            
            # Add subtle border
            border_size = profile_size + 6
            border_img = Image.new('RGBA', (border_size, border_size), (0, 0, 0, 0))
            border_draw = ImageDraw.Draw(border_img)
            border_draw.ellipse([(0, 0), (border_size, border_size)], fill=accent_rgb + (100,))
            img.paste(border_img, (profile_x - 3, profile_y - 3), border_img)
            
            # Paste profile pic
            profile_pic = profile_pic.convert('RGBA')
            output = Image.new('RGBA', (profile_size, profile_size), (0, 0, 0, 0))
            output.paste(profile_pic, (0, 0))
            output.putalpha(mask)
            
            img.paste(output, (profile_x, profile_y), output)
            
        except Exception as e:
            print(f"Profile error: {e}")
            # Fallback to colored circle
            draw.ellipse(
                [(profile_x, profile_y), (profile_x + profile_size, profile_y + profile_size)],
                fill=accent_rgb
            )
            letter = username[0].upper() if username else "?"
            bbox = draw.textbbox((0, 0), letter, font=name_font)
            w = bbox[2] - bbox[0]
            h = bbox[3] - bbox[1]
            draw.text(
                (profile_x + (profile_size - w) // 2, profile_y + (profile_size - h) // 2 - 2),
                letter, fill='white', font=name_font
            )
    else:
        # Draw gradient circle with letter
        for i in range(profile_size // 2, 0, -2):
            alpha = int(255 * i / (profile_size // 2))
            color = accent_rgb + (alpha,)
            offset = (profile_size // 2) - i
            draw.ellipse(
                [(profile_x + offset, profile_y + offset), 
                 (profile_x + profile_size - offset, profile_y + profile_size - offset)],
                fill=color
            )
        
        letter = username[0].upper() if username else "?"
        bbox = draw.textbbox((0, 0), letter, font=name_font)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        draw.text(
            (profile_x + (profile_size - w) // 2, profile_y + (profile_size - h) // 2 - 2),
            letter, fill='white', font=name_font
        )
    
    # Draw username with shadow
    name_x = profile_x + profile_size + padding
    name_y = profile_y + (profile_size - sizes["name_font_size"]) // 2 + 5
    
    # Truncate long names
    display_name = username[:22] + "..." if len(username) > 22 else username
    
    # Text shadow
    draw.text((name_x + 2, name_y + 2), display_name, fill=(0, 0, 0, 100), font=name_font)
    # Main text
    draw.text((name_x, name_y), display_name, fill='white', font=name_font)
    
    # Add decorative accent dot
    dot_x = name_x - 8
    dot_y = name_y + sizes["name_font_size"] // 2
    draw.ellipse([(dot_x, dot_y), (dot_x + 4, dot_y + 4)], fill=accent_rgb)
    
    # Draw message text with better visibility
    text_x = padding + 10
    text_y = header_height
    
    for line in wrapped_lines:
        if line.strip():
            # Subtle text shadow for depth
            draw.text((text_x + 1, text_y + 1), line, fill=(0, 0, 0, 80), font=text_font)
            # Main text with perfect contrast
            draw.text((text_x, text_y), line, fill=(255, 255, 255, 255), font=text_font)
        text_y += line_spacing
    
    # Add subtle vignette effect
    vignette = Image.new('RGBA', (img_width, img_height), (0, 0, 0, 0))
    vignette_draw = ImageDraw.Draw(vignette)
    for i in range(40):
        alpha = int(i * 1.5)
        vignette_draw.rectangle(
            [(i, i), (img_width - i, img_height - i)],
            outline=(0, 0, 0, alpha)
        )
    img = Image.alpha_composite(img, vignette)
    
    return img

@app.on_message(filters.command("q", prefixes=config.config.COMMAND_PREFIXES))
async def advanced_quote(client: Client, message: Message):
    """Generate premium quality quote sticker"""
    
    if not message.reply_to_message:
        await message.reply_text("**❌ Reply to a message to create a quote!**")
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
    if len(text) > 800:
        text = text[:797] + "..."
    
    username = user.first_name
    if user.last_name:
        username += f" {user.last_name}"
    
    # Processing with style
    processing_msg = await message.reply_text("**✨ Crafting your premium quote...**")
    
    output_path = None
    try:
        # Try to get profile photo with better error handling
        profile_pic = None
        try:
            photos = [photo async for photo in client.get_chat_photos(user.id, limit=1)]
            if photos:
                pfp_file = await client.download_media(photos[0], in_memory=True)
                profile_pic = Image.open(BytesIO(pfp_file.getvalue()))
        except:
            pass  # Silently handle profile fetch errors
        
        # Generate premium quote
        quote_img = create_advanced_quote(text, username, profile_pic)
        
        # Save with maximum quality
        output_path = f"quote_{message.id}.webp"
        quote_img.save(output_path, "WebP", quality=100, method=6)
        
        # Send as sticker
        await message.reply_sticker(sticker=output_path)
        
        # Cleanup processing message
        await processing_msg.delete()
        
    except Exception as e:
        await processing_msg.edit_text(f"**❌ Error:**\n`{str(e)}`")
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
**✨ Advanced Quote Module:**

Create stunning, premium-quality quote stickers!

**Commands:**
• `/q` - Reply to any message to create a quote

**Premium Features:**
• 🎨 Beautiful gradient backgrounds
• 🔍 AI-like intelligent zoom (short = zoom in, long = zoom out)
• 💎 Crystal clear text rendering with shadows
• 🌈 8 stunning color schemes
• 🖼️ High-quality profile pictures with glow effects
• ⚡ Optimized for all message lengths
• 🎭 Professional sticker format

**How It Works:**
The module intelligently adjusts:
• Short messages (< 50 chars): Larger fonts, zoomed in view
• Medium messages: Balanced sizing
• Long messages (> 300 chars): Compact fonts, zoomed out view

**Usage:**
Reply to any message → `/q` → Premium quote sticker! ✨

**Quality:** Maximum WebP quality with perfect text visibility on all backgrounds!
"""

__module__ = "Quote"
