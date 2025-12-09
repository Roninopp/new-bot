from Yumeko.database import aura_db
from pyrogram import Client, filters
from pyrogram.types import Message
from Yumeko import app
import config
import random

# Fun aura level descriptions
def get_aura_level(aura_points):
    if aura_points >= 1000:
        return "💫 Legendary Aura"
    elif aura_points >= 500:
        return "✨ Godlike Aura"
    elif aura_points >= 250:
        return "🌟 Supreme Aura"
    elif aura_points >= 100:
        return "⚡ Elite Aura"
    elif aura_points >= 50:
        return "🔥 Strong Aura"
    elif aura_points >= 20:
        return "💪 Rising Aura"
    elif aura_points >= 0:
        return "🌱 Growing Aura"
    else:
        return "💀 Negative Aura"

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
    top_users = await aura_db.top_aura(chat_id)
    if not top_users:
        await message.reply_text("🌑 No aura data available for this group yet. Start spreading positive vibes!")
        return

    # Create fancy leaderboard with medals
    medals = ["🥇", "🥈", "🥉"]
    leaderboard_lines = []
    
    for i, user in enumerate(top_users):
        medal = medals[i] if i < 3 else f"**{i + 1}.**"
        aura_level = get_aura_level(user['aura'])
        leaderboard_lines.append(
            f"{medal} **{user['user_name']}** • {user['aura']} ✨\n   ┗━ {aura_level}"
        )
    
    leaderboard = "\n\n".join(leaderboard_lines)
    await message.reply_text(
        f"🏆 **TOP AURA LEADERBOARD** 🏆\n\n{leaderboard}\n\n"
        f"━━━━━━━━━━━━━━━━\n💫 Keep spreading positive vibes!"
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
