import asyncio
import random
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, ChatPermissions
from pyrogram.enums import ChatMemberStatus, ChatType
from Yumeko import app
import config

# Store pending verifications
pending_verifications = {}

async def is_admin(client: Client, chat_id: int, user_id: int) -> bool:
    """Check if user is admin or owner"""
    try:
        member = await client.get_chat_member(chat_id, user_id)
        return member.status in [ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR]
    except:
        return False

# Simple in-memory storage for captcha status
captcha_enabled_chats = set()

@app.on_message(filters.command("captcha", prefixes=config.config.COMMAND_PREFIXES) & filters.group)
async def captcha_toggle(client: Client, message: Message):
    """Enable or disable captcha verification"""
    chat_id = message.chat.id
    
    if not await is_admin(client, chat_id, message.from_user.id):
        await message.reply_text("**❌ Only admins can use this command!**")
        return
    
    if len(message.command) < 2:
        status = "✅ Enabled" if chat_id in captcha_enabled_chats else "❌ Disabled"
        await message.reply_text(f"**🛡️ Captcha Status:** {status}\n\nUse `/captcha on` or `/captcha off`")
        return
    
    action = message.command[1].lower()
    
    if action == "on":
        captcha_enabled_chats.add(chat_id)
        await message.reply_text(
            "**✅ Captcha Verification Enabled!**\n\n"
            "New members will be muted and need to verify in DM.\n"
            "⏱️ Timeout: 10 minutes"
        )
    elif action == "off":
        if chat_id in captcha_enabled_chats:
            captcha_enabled_chats.remove(chat_id)
        await message.reply_text("**❌ Captcha Verification Disabled!**")
    else:
        await message.reply_text("**❌ Use:** `/captcha on` or `/captcha off`")

def generate_math_question():
    """Generate a simple math question"""
    num1 = random.randint(1, 10)
    num2 = random.randint(1, 10)
    operations = [('+', num1 + num2), ('-', num1 - num2 if num1 > num2 else num2 - num1), ('×', num1 * num2)]
    op, answer = random.choice(operations)
    
    if op == '-' and num1 < num2:
        num1, num2 = num2, num1
    
    question = f"{num1} {op} {num2}"
    
    # Generate wrong answers
    wrong_answers = set()
    while len(wrong_answers) < 3:
        wrong = answer + random.randint(-5, 5)
        if wrong != answer and wrong >= 0:
            wrong_answers.add(wrong)
    
    options = list(wrong_answers) + [answer]
    random.shuffle(options)
    
    return question, answer, options

@app.on_chat_member_updated()
async def handle_new_member(client: Client, update):
    """Handle new members joining"""
    chat = update.chat
    
    # Only process group chats
    if chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
        return
    
    chat_id = chat.id
    
    # Check if captcha is enabled
    if chat_id not in captcha_enabled_chats:
        return
    
    # Check if this is a new member join
    new_member = update.new_chat_member
    old_member = update.old_chat_member
    
    if not new_member:
        return
    
    # Check if user just joined
    if old_member and old_member.status not in [None, "left", "kicked"]:
        return
    
    if new_member.status not in ["member", "restricted"]:
        return
    
    user = new_member.user
    
    # Ignore bots
    if user.is_bot:
        return
    
    user_id = user.id
    user_mention = user.mention
    
    # Mute the user immediately
    try:
        await client.restrict_chat_member(
            chat_id,
            user_id,
            ChatPermissions(can_send_messages=False)
        )
    except Exception as e:
        print(f"Failed to mute user: {e}")
        return
    
    # Generate math question
    question, correct_answer, options = generate_math_question()
    
    # Create verification button
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Complete Verification", url=f"https://t.me/{(await client.get_me()).username}?start=verify_{chat_id}_{user_id}")]
    ])
    
    # Send message in group
    welcome_msg = await client.send_message(
        chat_id,
        f"**👋 Welcome {user_mention}!**\n\n"
        f"**🔒 You have been muted for security.**\n\n"
        f"Click the button below to verify in DM.\n"
        f"⏱️ You have **10 minutes** to complete verification.\n\n"
        f"❌ Failure to verify will result in removal.",
        reply_markup=keyboard
    )
    
    # Store verification data
    pending_verifications[f"{chat_id}_{user_id}"] = {
        "chat_id": chat_id,
        "user_id": user_id,
        "question": question,
        "answer": correct_answer,
        "options": options,
        "welcome_msg_id": welcome_msg.id,
        "user_mention": user_mention
    }
    
    # Schedule timeout (10 minutes)
    asyncio.create_task(handle_verification_timeout(client, chat_id, user_id, welcome_msg.id))

async def handle_verification_timeout(client: Client, chat_id: int, user_id: int, msg_id: int):
    """Kick user after 10 minutes if not verified"""
    await asyncio.sleep(600)  # 10 minutes
    
    key = f"{chat_id}_{user_id}"
    
    if key in pending_verifications:
        try:
            # Kick the user
            await client.ban_chat_member(chat_id, user_id)
            await client.unban_chat_member(chat_id, user_id)
            
            # Delete welcome message
            try:
                await client.delete_messages(chat_id, msg_id)
            except:
                pass
            
            # Send timeout message
            await client.send_message(
                chat_id,
                f"**⏱️ Verification Timeout!**\n\n"
                f"User was removed for not completing verification within 10 minutes."
            )
            
            # Cleanup
            del pending_verifications[key]
        except Exception as e:
            print(f"Error in timeout: {e}")

@app.on_message(filters.command("start") & filters.private)
async def start_verification(client: Client, message: Message):
    """Handle verification in DM"""
    if len(message.command) < 2:
        await message.reply_text("👋 Hi! I'm a group management bot.")
        return
    
    # Check if this is a verification request
    if not message.command[1].startswith("verify_"):
        return
    
    try:
        parts = message.command[1].split("_")
        chat_id = int(parts[1])
        user_id = int(parts[2])
    except:
        await message.reply_text("❌ Invalid verification link!")
        return
    
    # Check if user is the correct person
    if message.from_user.id != user_id:
        await message.reply_text("❌ This verification is not for you!")
        return
    
    key = f"{chat_id}_{user_id}"
    
    # Check if verification exists
    if key not in pending_verifications:
        await message.reply_text("❌ Verification expired or already completed!")
        return
    
    verification = pending_verifications[key]
    question = verification["question"]
    options = verification["options"]
    
    # Create answer buttons
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(str(options[0]), callback_data=f"ans_{chat_id}_{user_id}_{options[0]}"),
            InlineKeyboardButton(str(options[1]), callback_data=f"ans_{chat_id}_{user_id}_{options[1]}")
        ],
        [
            InlineKeyboardButton(str(options[2]), callback_data=f"ans_{chat_id}_{user_id}_{options[2]}"),
            InlineKeyboardButton(str(options[3]), callback_data=f"ans_{chat_id}_{user_id}_{options[3]}")
        ]
    ])
    
    await message.reply_text(
        f"**🤖 Captcha Verification**\n\n"
        f"**Solve this math question:**\n\n"
        f"📝 **{question} = ?**\n\n"
        f"Select the correct answer:",
        reply_markup=keyboard
    )

@app.on_callback_query(filters.regex(r"^ans_"))
async def handle_answer(client: Client, callback: CallbackQuery):
    """Handle captcha answer"""
    try:
        parts = callback.data.split("_")
        chat_id = int(parts[1])
        user_id = int(parts[2])
        user_answer = int(parts[3])
    except:
        await callback.answer("❌ Error processing answer!", show_alert=True)
        return
    
    # Check if user is correct person
    if callback.from_user.id != user_id:
        await callback.answer("❌ This is not your verification!", show_alert=True)
        return
    
    key = f"{chat_id}_{user_id}"
    
    if key not in pending_verifications:
        await callback.answer("❌ Verification expired!", show_alert=True)
        return
    
    verification = pending_verifications[key]
    correct_answer = verification["answer"]
    user_mention = verification["user_mention"]
    welcome_msg_id = verification["welcome_msg_id"]
    
    if user_answer == correct_answer:
        # Correct answer!
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
                    can_pin_messages=False,
                    can_change_info=False
                )
            )
            
            # Update DM message
            await callback.message.edit_text(
                "**✅ Verification Successful!**\n\n"
                "You have been verified and can now chat in the group!\n"
                "Welcome! 🎉"
            )
            
            await callback.answer("✅ Verified! You can chat now.", show_alert=True)
            
            # Delete welcome message in group
            try:
                await client.delete_messages(chat_id, welcome_msg_id)
            except:
                pass
            
            # Send success message in group
            await client.send_message(
                chat_id,
                f"**✅ Verification Complete!**\n\n"
                f"{user_mention} has completed captcha verification.\n"
                f"Welcome to the group! You can chat now. 🎉"
            )
            
            # Cleanup
            del pending_verifications[key]
            
        except Exception as e:
            print(f"Error unmuting: {e}")
            await callback.answer("❌ Error completing verification!", show_alert=True)
    else:
        # Wrong answer
        await callback.answer(f"❌ Wrong answer! Correct answer: {correct_answer}\nTry again.", show_alert=True)

__help__ = """
**🛡️ Captcha Verification Module**

Protect your group from bots and spam!

**Commands:**
• `/captcha on` - Enable captcha verification
• `/captcha off` - Disable captcha verification
• `/captcha` - Check current status

**How it works:**
1. New member joins → Bot mutes them
2. Member gets verification button
3. Clicks button → Opens bot DM
4. Solves math question in DM
5. ✅ Correct → Unmuted & welcomed
6. ❌ No verification in 10 min → Kicked

**Features:**
• 🔒 Auto-mute on join
• 📩 Verification in DM
• 🔢 Random math questions
• ⏱️ 10-minute timeout
• 🚫 Auto-kick on timeout
• ✅ Welcome message on success

**Note:** 
- Only admins can enable/disable
- Bot needs admin permissions to restrict members
- Users must start the bot to verify
"""

__module__ = "Captcha"
