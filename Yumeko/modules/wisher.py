from pyrogram import Client, filters
from pyrogram.types import Message
from Yumeko import app
import random

# Help text for the module
__help__ = """
**🌅 Auto Wisher - Spread Good Vibes! 🌅**

**How it works:**
The bot automatically responds when you greet the group!

**Triggers:**
• Good Morning, GM, Gm, Morning
• Good Night, GN, Gn, Night
• Good Evening, GE, Ge, Evening

**Response:**
Bot will mention you and reply with a random inspirational quote!

**Note:** Just say these greetings naturally in chat and bot will respond! ✨
"""

__module__ = "Wisher"

# Good Morning Quotes (20+)
GOOD_MORNING_QUOTES = [
    "🌅 Good morning! May your day be filled with positive vibes and endless possibilities! ✨",
    "☀️ Good morning! Wake up with determination, go to bed with satisfaction! 💪",
    "🌞 Good morning! Today is a new beginning, make it amazing! 🚀",
    "🌄 Good morning! Every sunrise is an invitation for us to arise and brighten someone's day! 🌟",
    "☕ Good morning! A cup of coffee and a positive mindset - that's all you need today! 💫",
    "🌅 Good morning! Believe in yourself and all that you are. Know that there is something inside you that is greater than any obstacle! 🔥",
    "🌞 Good morning! Today's goal: Be so positive that negative people don't want to be around you! 😄",
    "☀️ Good morning! Rise up, start fresh, see the bright opportunity in each new day! ⚡",
    "🌄 Good morning! Don't count the days, make the days count! 🎯",
    "🌅 Good morning! Your only limit is you. Be brave and fearless! 💪",
    "☕ Good morning! Wake up and be awesome! The world needs your energy today! ✨",
    "🌞 Good morning! Success is not final, failure is not fatal. It's the courage to continue that counts! 🏆",
    "🌄 Good morning! Start each day with a grateful heart and watch the magic happen! 💖",
    "☀️ Good morning! Life is 10% what happens to you and 90% how you react to it! 🌟",
    "🌅 Good morning! Dream big, work hard, stay focused, and surround yourself with good people! 🚀",
    "🌞 Good morning! The secret to getting ahead is getting started. Let's go! 💫",
    "☕ Good morning! Today is your opportunity to build the tomorrow you want! 🏗️",
    "🌄 Good morning! Be the energy you want to attract! Positive vibes only! ⚡",
    "☀️ Good morning! Every accomplishment starts with the decision to try! You got this! 💪",
    "🌅 Good morning! Make today so awesome that yesterday gets jealous! 😎",
    "🌞 Good morning! Opportunities don't happen, you create them! 🎯",
    "☕ Good morning! Your vibe attracts your tribe. Keep shining! ✨",
]

# Good Night Quotes (20+)
GOOD_NIGHT_QUOTES = [
    "🌙 Good night! May your dreams be as sweet as you are! Sleep tight! ✨",
    "⭐ Good night! End the day with gratitude and start tomorrow with hope! 💫",
    "🌃 Good night! Sleep is the best meditation. Rest well, warrior! 😴",
    "🌙 Good night! Close your eyes and let the stars guide you to peaceful dreams! 🌟",
    "⭐ Good night! Tomorrow is a new day with new opportunities. Recharge yourself! 🔋",
    "🌃 Good night! May your pillow be soft, your dreams be sweet, and your rest be deep! 💤",
    "🌙 Good night! Don't count sheep, count blessings! Sleep peacefully! 🐑",
    "⭐ Good night! Let go of today's stress, tomorrow is a fresh start! 🌅",
    "🌃 Good night! Dream big, sleep well, and wake up ready to conquer! 🏆",
    "🌙 Good night! The night is more than the day. It is time to reflect and recharge! 💭",
    "⭐ Good night! May the angels protect you through the night! Sweet dreams! 👼",
    "🌃 Good night! Sleep away your worries, wake up with solutions! 💡",
    "🌙 Good night! End your day with a smile and start your sleep with peace! 😊",
    "⭐ Good night! Rest your mind, body, and soul. You've earned it! 🧘",
    "🌃 Good night! Stars can't shine without darkness. Rest and glow tomorrow! ✨",
    "🌙 Good night! May your night be filled with beautiful dreams and peaceful sleep! 🌈",
    "⭐ Good night! Sleep tight, don't let the bedbugs bite! 🛏️",
    "🌃 Good night! Tomorrow is another chance to be amazing! Sleep well! 🚀",
    "🌙 Good night! Let your dreams be your wings tonight! Fly high! 🦋",
    "⭐ Good night! The best bridge between despair and hope is a good night's sleep! 🌉",
    "🌃 Good night! Close your eyes, clear your mind, and drift into peaceful slumber! 😴",
    "🌙 Good night! May the moonlight guide you to a world of sweet dreams! 🌙",
]

# Good Evening Quotes (20+)
GOOD_EVENING_QUOTES = [
    "🌆 Good evening! May your evening be as beautiful as your smile! 😊",
    "🌇 Good evening! Time to relax and unwind. You've earned it today! ☕",
    "🌃 Good evening! Let the sunset take away all your stress and worries! 🌅",
    "🌆 Good evening! Evenings are life's way of saying you survived another day! 🎉",
    "🌇 Good evening! Take a deep breath, relax, and enjoy this beautiful evening! 💆",
    "🌃 Good evening! May this evening bring you peace, joy, and good vibes! ✨",
    "🌆 Good evening! The evening breeze is whispering your success stories! 🍃",
    "🌇 Good evening! Reflect on today's victories, no matter how small! 🏆",
    "🌃 Good evening! Time to switch off work mode and switch on relaxation mode! 😌",
    "🌆 Good evening! Every sunset is an opportunity to reset! 🔄",
    "🌇 Good evening! May your evening be filled with laughter and love! ❤️",
    "🌃 Good evening! The best is yet to come. Keep believing! 💫",
    "🌆 Good evening! Evenings are proof that endings can be beautiful too! 🌅",
    "🌇 Good evening! Take time to do what makes your soul happy this evening! 🎨",
    "🌃 Good evening! Let go of stress, embrace the calm of the evening! 🧘",
    "🌆 Good evening! May this evening bring you closer to your dreams! 🌟",
    "🌇 Good evening! Celebrate small wins, enjoy the peaceful moments! 🥂",
    "🌃 Good evening! The evening whispers what the morning couldn't shout! 💭",
    "🌆 Good evening! Time to recharge your batteries for tomorrow! 🔋",
    "🌇 Good evening! May your evening be as awesome as you are! 😎",
    "🌃 Good evening! Sunsets are proof that no matter what happens, every day can end beautifully! 🌄",
]

@app.on_message(
    filters.regex(
        r"^(?i)(good morning|gm|morning|gud morning|good mrng|mrng|suprabhat|subah|सुप्रभात)$"
    ) & filters.group
)
async def wish_good_morning(client: Client, message: Message):
    """Reply with a good morning quote when someone wishes good morning."""
    quote = random.choice(GOOD_MORNING_QUOTES)
    await message.reply_text(f"**{message.from_user.mention}**\n\n{quote}")

@app.on_message(
    filters.regex(
        r"^(?i)(good night|gn|night|gud night|good nite|nite|nyt|shubh ratri|शुभ रात्रि)$"
    ) & filters.group
)
async def wish_good_night(client: Client, message: Message):
    """Reply with a good night quote when someone wishes good night."""
    quote = random.choice(GOOD_NIGHT_QUOTES)
    await message.reply_text(f"**{message.from_user.mention}**\n\n{quote}")

@app.on_message(
    filters.regex(
        r"^(?i)(good evening|ge|evening|gud evening|good eve|eve|shubh sandhya|शुभ संध्या)$"
    ) & filters.group
)
async def wish_good_evening(client: Client, message: Message):
    """Reply with a good evening quote when someone wishes good evening."""
    quote = random.choice(GOOD_EVENING_QUOTES)
    await message.reply_text(f"**{message.from_user.mention}**\n\n{quote}")
