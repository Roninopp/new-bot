from Yumeko.database import aura_db
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from Yumeko import app
import config
import random

# Help text for the module
__help__ = """
**✨ Aura System - Spread Positivity! ✨**

**What is Aura?**
Aura points represent your positive energy in the group! Earn aura by being helpful, kind, and awesome. Lose aura by being negative.

**How to Give/Remove Aura:**
Reply to someone's message with:

**Positive Words (Gain +1 Aura):**
• `+`, `++`, `+1` - Quick aura boost
• `nice`, `good`, `great`, `amazing`, `perfect`
• `awesome`, `excellent`, `cool`, `pro`, `legend`
• `thanks`, `thank you`, `ty`, `thx`
• `agree`, `right`, `true`, `facts`
• Emojis: 👍 🔥 💯 ✨ ⚡ 💪 👑

**Negative Words (Lose -1 Aura):**
• `-`, `--`, `-1` - Aura decrease
• `bad`, `worst`, `terrible`, `trash`
• `disagree`, `wrong`, `cringe`
• Emojis: 👎 💀 😭

**Commands:**
• `/aura` - Check your current aura status
• `/topaura` - View top aura users in the group

**Aura Levels:**
🌱 Growing (0-19) → 💪 Rising (20-49) → 🔥 Strong (50-99)
⚡ Elite (100-249) → 🌟 Supreme (250-499) → ✨ Godlike (500-999)
💫 Legendary (1000+)

**Note:** You can't boost your own aura! Keep it fair and fun! 😊
"""

__module__ = "Aura"

# Fun aura level descriptions
def get_aura_level(aura_points):
    if aura_points >= 1000:
        return "💫 Legendary"
    elif aura_points >= 500:
        return "✨ Godlike"
    elif aura_points >= 250:
        return "🌟 Supreme"
    elif aura_points >= 100:
        return "⚡ Elite"
    elif aura_points >= 50:
        return "🔥 Strong"
    elif aura_points >= 20:
        return "💪 Rising"
    elif aura_points >= 0:
        return "🌱 Growing"
    else:
        return "💀 Negative"

# Random positive emojis for variety
POSITIVE_EMOJIS = ["✨", "⚡", "🔥", "💫", "🌟", "⭐", "🎯", "👑", "💎", "🚀"]
NEGATIVE_EMOJIS = ["💀", "😭", "📉", "❌", "⚠️", "💔", "👎", "⛔"]

@app.on_message(filters.command("aura", prefixes=config.config.COMMAND_PREFIXES) & filters.group)
async def show_aura(client: Client, message: Message):
    """Show the aura points of a user."""
    user_id = message.from_user.id
    chat_id = message.chat.id

    # Get the user's aura points
    user_aura = await aura_db.get_aura(user_id, chat_id)
    aura_level = get_aura_level(user_aura)
    
    await message.reply_text(
        f"🌈 **{message.from_user.mention}'s Aura Status**\n\n"
        f"**Aura Points:** {user_aura} ✨\n"
        f"**Level:** {aura_level}"
    )

@app.on_message(filters.command("topaura", prefixes=config.config.COMMAND_PREFIXES) & filters.group)
async def show_top_aura(client: Client, message: Message):
    """Show the top users with the highest aura in the group."""
    chat_id = message.chat.id

    # Get the top aura users
    top_users = await aura_db.top_aura(chat_id, limit=10)
    if not top_users:
        await message.reply_text("🌑 No aura data available for this group yet. Start spreading positive vibes!")
        return

    # Show first 5 users
    medals = ["🥇", "🥈", "🥉", "4.", "5."]
    leaderboard_lines = []
    
    for i in range(min(5, len(top_users))):
        user = top_users[i]
        medal = medals[i]
        aura_level = get_aura_level(user['aura'])
        leaderboard_lines.append(f"{medal} **{user['user_name']}** • {user['aura']} ✨ • {aura_level}")
    
    leaderboard = "\n".join(leaderboard_lines)
    
    # Add button if there are more than 5 users
    keyboard = None
    if len(top_users) > 5:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📊 View More", callback_data=f"aura_more_{chat_id}")]
        ])
    
    await message.reply_text(
        f"🏆 **TOP AURA LEADERBOARD** 🏆\n\n{leaderboard}\n\n"
        f"━━━━━━━━━━━━━━━━\n💫 Keep spreading positive vibes!",
        reply_markup=keyboard
    )

@app.on_callback_query(filters.regex(r"^aura_more_"))
async def show_more_aura(client: Client, callback_query: CallbackQuery):
    """Show remaining top aura users."""
    chat_id = int(callback_query.data.split("_")[2])
    
    # Get the top aura users
    top_users = await aura_db.top_aura(chat_id, limit=10)
    
    # Show users 6-10
    leaderboard_lines = []
    for i in range(5, len(top_users)):
        user = top_users[i]
        aura_level = get_aura_level(user['aura'])
        leaderboard_lines.append(f"{i+1}. **{user['user_name']}** • {user['aura']} ✨ • {aura_level}")
    
    leaderboard = "\n".join(leaderboard_lines)
    
    # Add back button
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Back to Top 5", callback_data=f"aura_back_{chat_id}")]
    ])
    
    await callback_query.message.edit_text(
        f"🏆 **TOP AURA LEADERBOARD** 🏆\n\n{leaderboard}\n\n"
        f"━━━━━━━━━━━━━━━━\n💫 Keep spreading positive vibes!",
        reply_markup=keyboard
    )

@app.on_callback_query(filters.regex(r"^aura_back_"))
async def show_back_aura(client: Client, callback_query: CallbackQuery):
    """Go back to top 5 aura users."""
    chat_id = int(callback_query.data.split("_")[2])
    
    # Get the top aura users
    top_users = await aura_db.top_aura(chat_id, limit=10)
    
    # Show first 5 users
    medals = ["🥇", "🥈", "🥉", "4.", "5."]
    leaderboard_lines = []
    
    for i in range(min(5, len(top_users))):
        user = top_users[i]
        medal = medals[i]
        aura_level = get_aura_level(user['aura'])
        leaderboard_lines.append(f"{medal} **{user['user_name']}** • {user['aura']} ✨ • {aura_level}")
    
    leaderboard = "\n".join(leaderboard_lines)
    
    # Add button if there are more than 5 users
    keyboard = None
    if len(top_users) > 5:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📊 View More", callback_data=f"aura_more_{chat_id}")]
        ])
    
    await callback_query.message.edit_text(
        f"🏆 **TOP AURA LEADERBOARD** 🏆\n\n{leaderboard}\n\n"
        f"━━━━━━━━━━━━━━━━\n💫 Keep spreading positive vibes!",
        reply_markup=keyboard
    )

@app.on_message(
    filters.regex(
        r"^(?i)(\+|\+\+|\+1|nice|good|great|amazing|perfect|awesome|excellent|"
        r"wonderful|fantastic|brilliant|outstanding|superb|incredible|wow|"
        r"cool|pro|legend|king|queen|boss|fire|lit|based|gigachad|"
        r"thx|tnx|ty|tq|thank you|thanks|thanx|appreciate|"
        r"agree|right|true|facts|real|makasih|"
        r"love it|love this|loved it|beautiful|"
        r"👍|🔥|💯|✨|⚡|💪|👑|🎯|💎|😍|🤩|"
        r"\+\+ .+)$"
    ) & filters.group & filters.reply
)
async def increase_aura_handler(client: Client, message: Message):
    """Increase aura when someone replies with positive words."""
    target_user = message.reply_to_message.from_user
    target_user_id = target_user.id
    sender_id = message.from_user.id
    chat_id = message.chat.id
    name = target_user.first_name

    # Prevent self-aura boosting
    if target_user_id == sender_id:
        await message.reply_text("🤨 Nice try! You can't boost your own aura!")
        return

    # Increase the target user's aura points
    await aura_db.increase_aura(target_user_id, name, chat_id)
    
    # Get updated aura
    new_aura = await aura_db.get_aura(target_user_id, chat_id)
    emoji = random.choice(POSITIVE_EMOJIS)
    
    # Special messages for milestones
    milestone_msg = ""
    if new_aura in [10, 25, 50, 100, 250, 500, 1000]:
        milestone_msg = f"\n🎉 **MILESTONE REACHED!** 🎉"
    
    await message.reply_text(
        f"{emoji} **Aura Increased!** {emoji}\n\n"
        f"**User:** {target_user.mention}\n"
        f"**Aura:** +1 ✨\n"
        f"**Total Aura:** {new_aura} ⚡"
        f"{milestone_msg}"
    )

@app.on_message(
    filters.regex(
        r"^(?i)(-|--|-1|bad|worst|terrible|awful|horrible|trash|cringe|"
        r"disagree|wrong|false|cap|lame|weak|"
        r"not cool|not good|no way|nope|"
        r"👎|💀|😭|🤡|"
        r"-- .+)$"
    ) & filters.group & filters.reply
)
async def decrease_aura_handler(client: Client, message: Message):
    """Decrease aura when someone replies with negative words."""
    target_user = message.reply_to_message.from_user
    target_user_id = target_user.id
    sender_id = message.from_user.id
    chat_id = message.chat.id
    name = target_user.first_name

    # Prevent self-aura sabotage (though why would anyone do this lol)
    if target_user_id == sender_id:
        await message.reply_text("🤔 Destroying your own aura? That's bold!")
        return

    # Decrease the target user's aura points
    await aura_db.decrease_aura(target_user_id, name, chat_id)
    
    # Get updated aura
    new_aura = await aura_db.get_aura(target_user_id, chat_id)
    emoji = random.choice(NEGATIVE_EMOJIS)
    
    await message.reply_text(
        f"{emoji} **Aura Decreased!** {emoji}\n\n"
        f"**User:** {target_user.mention}\n"
        f"**Aura:** -1 📉\n"
        f"**Total Aura:** {new_aura} 💔"
    )
