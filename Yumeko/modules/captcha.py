import asyncio
import random
import time
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, ChatPermissions
from pyrogram.enums import ChatMemberStatus
from Yumeko import app
from Yumeko.database import db
import config

# Captcha storage
captcha_data = {}
pending_users = {}

# Captcha types
CAPTCHA_TYPES = {
    "math": "Math Question",
    "button": "Button Click",
    "emoji": "Emoji Selection"
}

async def is_admin(client: Client, chat_id: int, user_id: int) -> bool:
    """Check if user is admin or owner"""
    try:
        member = await client.get_chat_member(chat_id, user_id)
        return member.status in [ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR]
    except:
        return False

async def get_captcha_settings(chat_id: int):
    """Get captcha settings for a chat"""
    data = await db.captcha.find_one({"chat_id": chat_id})
    if not data:
        return {
            "enabled": False,
            "type": "button",
            "timeout": 120,
            "action": "kick"
        }
    return data

async def save_captcha_settings(chat_id: int, settings: dict):
    """Save captcha settings"""
    await db.captcha.update_one(
        {"chat_id": chat_id},
        {"$set": settings},
        upsert=True
    )

def generate_math_captcha():
    """Generate a simple math question"""
    num1 = random.randint(1, 20)
    num2 = random.randint(1, 20)
    operations = ['+', '-', '×']
    op = random.choice(operations)
    
    if op == '+':
        answer = num1 + num2
        question = f"{num1} + {num2}"
    elif op == '-':
        # Ensure positive result
        if num1 < num2:
            num1, num2 = num2, num1
        answer = num1 - num2
        question = f"{num1} - {num2}"
    else:  # multiplication
        num1 = random.randint(1, 10)
        num2 = random.randint(1, 10)
        answer = num1 * num2
        question = f"{num1} × {num2}"
    
    # Generate wrong answers
    wrong_answers = set()
    while len(wrong_answers) < 3:
        wrong = answer + random.randint(-5, 5)
        if wrong != answer and wrong >= 0:
            wrong_answers.add(wrong)
    
    answers = list(wrong_answers) + [answer]
    random.shuffle(answers)
    
    return question, answer, answers

def generate_emoji_captcha():
    """Generate emoji selection captcha"""
    emojis = ["🍎", "🚗", "⚽", "🎸", "🌟", "🎨", "🔥", "💎", "🌺", "🎭", 
              "🦁", "🎪", "🚀", "🏆", "🎯", "🌈", "⚡", "🎁", "🌊", "🎵"]
    
    target_emoji = random.choice(emojis)
    
    # Create options with target and decoys
    options = [target_emoji]
    while len(options) < 4:
        emoji = random.choice(emojis)
        if emoji not in options:
            options.append(emoji)
    
    random.shuffle(options)
    
    return target_emoji, options

@app.on_message(filters.command("captcha", prefixes=config.config.COMMAND_PREFIXES) & filters.group)
async def captcha_cmd(client: Client, message: Message):
    """Enable/disable captcha or show settings"""
    chat_id = message.chat.id
    
    if not await is_admin(client, chat_id, message.from_user.id):
        await message.reply_text("**❌ Only admins can use this command!**")
        return
    
    if len(message.command) < 2:
        # Show current settings
        settings = await get_captcha_settings(chat_id)
        status = "✅ Enabled" if settings["enabled"] else "❌ Disabled"
        captcha_type = CAPTCHA_TYPES.get(settings["type"], "Button Click")
        timeout = settings["timeout"]
        action = settings["action"].upper()
        
        text = f"""
**🛡️ Captcha Settings**

**Status:** {status}
**Type:** {captcha_type}
**Timeout:** {timeout} seconds
**Action:** {action}

**Commands:**
• `/captcha on` - Enable captcha
• `/captcha off` - Disable captcha
• `/captcha type` - Change captcha type
• `/captcha timeout <seconds>` - Set timeout
• `/captcha action <kick/ban>` - Set action
"""
        await message.reply_text(text)
        return
    
    action = message.command[1].lower()
    
    if action == "on":
        settings = await get_captcha_settings(chat_id)
        settings["enabled"] = True
        settings["chat_id"] = chat_id
        await save_captcha_settings(chat_id, settings)
        await message.reply_text("**✅ Captcha verification enabled!**\n\nNew members will need to verify before chatting.")
    
    elif action == "off":
        settings = await get_captcha_settings(chat_id)
        settings["enabled"] = False
        settings["chat_id"] = chat_id
        await save_captcha_settings(chat_id, settings)
        await message.reply_text("**❌ Captcha verification disabled!**")
    
    elif action == "type":
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🔢 Math", callback_data=f"captcha_type_math_{chat_id}"),
                InlineKeyboardButton("🔘 Button", callback_data=f"captcha_type_button_{chat_id}")
            ],
            [
                InlineKeyboardButton("😊 Emoji", callback_data=f"captcha_type_emoji_{chat_id}")
            ]
        ])
        await message.reply_text("**🛡️ Select Captcha Type:**", reply_markup=keyboard)
    
    elif action == "timeout":
        if len(message.command) < 3:
            await message.reply_text("**❌ Please specify timeout in seconds!**\nExample: `/captcha timeout 120`")
            return
        
        try:
            timeout = int(message.command[2])
            if timeout < 30 or timeout > 300:
                await message.reply_text("**❌ Timeout must be between 30 and 300 seconds!**")
                return
            
            settings = await get_captcha_settings(chat_id)
            settings["timeout"] = timeout
            settings["chat_id"] = chat_id
            await save_captcha_settings(chat_id, settings)
            await message.reply_text(f"**✅ Captcha timeout set to {timeout} seconds!**")
        except ValueError:
            await message.reply_text("**❌ Invalid timeout value!**")
    
    elif action == "action":
        if len(message.command) < 3:
            await message.reply_text("**❌ Please specify action (kick/ban)!**\nExample: `/captcha action kick`")
            return
        
        action_type = message.command[2].lower()
        if action_type not in ["kick", "ban"]:
            await message.reply_text("**❌ Invalid action! Use: kick or ban**")
            return
        
        settings = await get_captcha_settings(chat_id)
        settings["action"] = action_type
        settings["chat_id"] = chat_id
        await save_captcha_settings(chat_id, settings)
        await message.reply_text(f"**✅ Failed captcha action set to {action_type.upper()}!**")
    
    else:
        await message.reply_text("**❌ Invalid command!**\n\nUse: `/captcha on/off/type/timeout/action`")

@app.on_callback_query(filters.regex(r"^captcha_type_"))
async def captcha_type_callback(client: Client, callback: CallbackQuery):
    """Handle captcha type selection"""
    data = callback.data.split("_")
    captcha_type = data[2]
    chat_id = int(data[3])
    
    if not await is_admin(client, chat_id, callback.from_user.id):
        await callback.answer("❌ Only admins can change this!", show_alert=True)
        return
    
    settings = await get_captcha_settings(chat_id)
    settings["type"] = captcha_type
    settings["chat_id"] = chat_id
    await save_captcha_settings(chat_id, settings)
    
    type_name = CAPTCHA_TYPES.get(captcha_type, "Button Click")
    await callback.answer(f"✅ Captcha type set to {type_name}!", show_alert=True)
    await callback.message.edit_text(f"**✅ Captcha type changed to: {type_name}**")

@app.on_chat_member_updated(filters.group)
async def welcome_captcha(client: Client, update):
    """Handle new member joins"""
    chat_id = update.chat.id
    new_member = update.new_chat_member
    
    if not new_member or new_member.status not in ["member", "restricted"]:
        return
    
    user = new_member.user
    if user.is_bot:
        return
    
    # Check if captcha is enabled
    settings = await get_captcha_settings(chat_id)
    if not settings["enabled"]:
        return
    
    # Mute the user
    try:
        await client.restrict_chat_member(
            chat_id,
            user.id,
            ChatPermissions(can_send_messages=False)
        )
    except Exception as e:
        print(f"Error muting user: {e}")
        return
    
    # Generate captcha based on type
    captcha_type = settings["type"]
    timeout = settings["timeout"]
    
    if captcha_type == "math":
        question, answer, options = generate_math_captcha()
        text = f"**👋 Welcome {user.mention}!**\n\n**🔒 Please verify you're human:**\n\n**Solve:** `{question} = ?`\n\n⏱️ Time: {timeout} seconds"
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(str(options[0]), callback_data=f"verify_{chat_id}_{user.id}_{options[0]}"),
             InlineKeyboardButton(str(options[1]), callback_data=f"verify_{chat_id}_{user.id}_{options[1]}")],
            [InlineKeyboardButton(str(options[2]), callback_data=f"verify_{chat_id}_{user.id}_{options[2]}"),
             InlineKeyboardButton(str(options[3]), callback_data=f"verify_{chat_id}_{user.id}_{options[3]}")]
        ])
        
        captcha_data[f"{chat_id}_{user.id}"] = answer
    
    elif captcha_type == "emoji":
        target_emoji, options = generate_emoji_captcha()
        text = f"**👋 Welcome {user.mention}!**\n\n**🔒 Please verify you're human:**\n\n**Select:** {target_emoji}\n\n⏱️ Time: {timeout} seconds"
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(options[0], callback_data=f"verify_{chat_id}_{user.id}_{options[0]}"),
             InlineKeyboardButton(options[1], callback_data=f"verify_{chat_id}_{user.id}_{options[1]}")],
            [InlineKeyboardButton(options[2], callback_data=f"verify_{chat_id}_{user.id}_{options[2]}"),
             InlineKeyboardButton(options[3], callback_data=f"verify_{chat_id}_{user.id}_{options[3]}")]
        ])
        
        captcha_data[f"{chat_id}_{user.id}"] = target_emoji
    
    else:  # button type
        text = f"**👋 Welcome {user.mention}!**\n\n**🔒 Please verify you're human:**\n\nClick the button below to verify!\n\n⏱️ Time: {timeout} seconds"
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ I'm Human!", callback_data=f"verify_{chat_id}_{user.id}_human")]
        ])
        
        captcha_data[f"{chat_id}_{user.id}"] = "human"
    
    try:
        captcha_msg = await client.send_message(chat_id, text, reply_markup=keyboard)
        
        # Store for timeout handling
        pending_users[f"{chat_id}_{user.id}"] = {
            "msg_id": captcha_msg.id,
            "time": time.time(),
            "timeout": timeout
        }
        
        # Schedule timeout check
        asyncio.create_task(check_captcha_timeout(client, chat_id, user.id, captcha_msg.id, timeout, settings["action"]))
    
    except Exception as e:
        print(f"Error sending captcha: {e}")

async def check_captcha_timeout(client: Client, chat_id: int, user_id: int, msg_id: int, timeout: int, action: str):
    """Check if user completed captcha in time"""
    await asyncio.sleep(timeout)
    
    key = f"{chat_id}_{user_id}"
    
    # Check if user still pending
    if key in pending_users:
        try:
            # Delete captcha message
            await client.delete_messages(chat_id, msg_id)
            
            # Take action
            if action == "ban":
                await client.ban_chat_member(chat_id, user_id)
                action_text = "banned"
            else:
                await client.ban_chat_member(chat_id, user_id)
                await client.unban_chat_member(chat_id, user_id)
                action_text = "kicked"
            
            # Send notification
            await client.send_message(
                chat_id,
                f"**⏱️ Captcha Failed!**\n\nUser was {action_text} for not completing verification in time."
            )
            
            # Cleanup
            if key in captcha_data:
                del captcha_data[key]
            if key in pending_users:
                del pending_users[key]
        
        except Exception as e:
            print(f"Error in timeout handler: {e}")

@app.on_callback_query(filters.regex(r"^verify_"))
async def verify_callback(client: Client, callback: CallbackQuery):
    """Handle captcha verification"""
    data = callback.data.split("_")
    chat_id = int(data[1])
    user_id = int(data[2])
    user_answer = "_".join(data[3:])  # Handle emoji with underscores
    
    # Check if the person clicking is the new member
    if callback.from_user.id != user_id:
        await callback.answer("❌ This verification is not for you!", show_alert=True)
        return
    
    key = f"{chat_id}_{user_id}"
    
    if key not in captcha_data:
        await callback.answer("❌ Verification expired!", show_alert=True)
        return
    
    correct_answer = str(captcha_data[key])
    
    # Check answer
    if str(user_answer) == correct_answer:
        try:
            # Unmute user
            await client.restrict_chat_member(
                chat_id,
                user_id,
                ChatPermissions(
                    can_send_messages=True,
                    can_send_media_messages=True,
                    can_send_other_messages=True,
                    can_add_web_page_previews=True,
                    can_send_polls=True,
                    can_invite_users=True,
                    can_pin_messages=True,
                    can_change_info=True
                )
            )
            
            # Update message
            await callback.message.edit_text(
                f"**✅ Verification Successful!**\n\n{callback.from_user.mention} has been verified!\n\nWelcome to the group! 🎉"
            )
            
            await callback.answer("✅ Verified successfully! Welcome!", show_alert=True)
            
            # Cleanup
            if key in captcha_data:
                del captcha_data[key]
            if key in pending_users:
                del pending_users[key]
        
        except Exception as e:
            print(f"Error unmuting user: {e}")
            await callback.answer("❌ Error unmuting user!", show_alert=True)
    
    else:
        await callback.answer("❌ Wrong answer! Try again.", show_alert=True)

__help__ = """
**🛡️ Captcha Verification Module:**

Protect your group from bots and spam with automatic captcha verification!

**Admin Commands:**
• `/captcha` - Show current settings
• `/captcha on` - Enable captcha verification
• `/captcha off` - Disable captcha verification
• `/captcha type` - Change captcha type (Math/Button/Emoji)
• `/captcha timeout <seconds>` - Set timeout (30-300 seconds)
• `/captcha action <kick/ban>` - Set action for failed verification

**Captcha Types:**
• **Math** - Solve simple math questions
• **Button** - Click "I'm Human" button
• **Emoji** - Select the correct emoji

**Features:**
• ✅ Auto-mute new members until verified
• ⏱️ Customizable timeout
• 🚫 Auto-kick/ban on failure
• 🎨 Multiple captcha types
• 🤖 Bot protection
• 💾 Settings saved per group

**How it works:**
1. New member joins group
2. Bot mutes them automatically
3. Captcha message is sent
4. Member solves captcha
5. Bot unmutes on success
6. Kicks/bans on failure or timeout

**Note:** Only admins can configure captcha settings.
Bot needs admin permissions to restrict members!
"""

__module__ = "Captcha"
