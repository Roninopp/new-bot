from html import escape
from secrets import choice
from typing import List
from Yumeko.helper.welcome_helper import *
from pyrogram import emoji, enums, filters, Client
from pyrogram.errors import ChannelPrivate, ChatAdminRequired, RPCError
from pyrogram.types import Message, User
from Yumeko import app
from Yumeko.database.welcome_db import Greetings
from Yumeko.decorator.chatadmin import can_change_info, chatadmin
from config import config 

ChatType = enums.ChatType

# --- HELPER: SAFE FORMATTING ---
async def escape_mentions_using_curly_brackets_wl(
        user: User,
        m: Message,
        text: str,
        parse_words: list,
) -> str:
    teks = await escape_invalid_curly_brackets(text, parse_words)
    if teks:
        # Safe Chat Title (Fixes Private Group Crash)
        chat_title = m.chat.title if m.chat.title else "this group"

        teks = teks.format(
            first=escape(user.first_name),
            last=escape(user.last_name or user.first_name),
            fullname=" ".join(
                [
                    escape(user.first_name),
                    escape(user.last_name),
                ]
                if user.last_name
                else [escape(user.first_name)],
            ),
            username=(
                "@" + (await escape_markdown(escape(user.username)))
                if user.username
                else (await (mention_html(escape(user.first_name), user.id)))
            ),
            mention=await (mention_html(escape(user.first_name), user.id)),
            chatname=escape(chat_title),
            id=user.id,
        )
    else:
        teks = ""

    return teks

# --- COMMANDS ---

@app.on_message(filters.command("cleanwelcome", config.COMMAND_PREFIXES))
@can_change_info
async def cleanwlcm(_, m: Message):
    db = Greetings(m.chat.id)
    status = db.get_current_cleanwelcome_settings()
    args = m.text.split(" ", 1)

    if len(args) >= 2:
        if args[1].lower() == "on":
            db.set_current_cleanwelcome_settings(True)
            await m.reply_text("Turned on!")
            return
        if args[1].lower() == "off":
            db.set_current_cleanwelcome_settings(False)
            await m.reply_text("Turned off!")
            return
        await m.reply_text("Usage: /cleanwelcome on/off")
        return
    await m.reply_text(f"Current settings:- {status}")


@app.on_message(filters.command("cleangoodbye", config.COMMAND_PREFIXES))
@can_change_info
async def cleangdbye(_, m: Message):
    db = Greetings(m.chat.id)
    status = db.get_current_cleangoodbye_settings()
    args = m.text.split(" ", 1)

    if len(args) >= 2:
        if args[1].lower() == "on":
            db.set_current_cleangoodbye_settings(True)
            await m.reply_text("Turned on!")
            return
        if args[1].lower() == "off":
            db.set_current_cleangoodbye_settings(False)
            await m.reply_text("Turned off!")
            return
        await m.reply_text("Usage: /cleangoodbye on/off")
        return
    await m.reply_text(f"Current settings:- {status}")


@app.on_message(filters.command("setwelcome", config.COMMAND_PREFIXES))
@can_change_info
async def save_wlcm(_, m: Message):
    db = Greetings(m.chat.id)
    if m and not m.from_user:
        return
    
    # Validation logic
    text, msgtype, file = await get_wlcm_type(m)
    if not m.reply_to_message and msgtype == Types.TEXT and len(m.command) <= 1:
        await m.reply_text("Error: There is no data in here!")
        return

    if not text and not file:
        await m.reply_text("Please provide some data!")
        return

    db.set_welcome_text(text, msgtype, file)
    await m.reply_text("Saved welcome!")


@app.on_message(filters.command("setgoodbye", config.COMMAND_PREFIXES))
@can_change_info
async def save_gdbye(_, m: Message):
    db = Greetings(m.chat.id)
    if m and not m.from_user:
        return
    
    text, msgtype, file = await get_wlcm_type(m)

    if not m.reply_to_message and msgtype == Types.TEXT and len(m.command) <= 1:
        await m.reply_text("Error: There is no data in here!")
        return

    if not text and not file:
        await m.reply_text("Please provide some data!")
        return

    db.set_goodbye_text(text, msgtype, file)
    await m.reply_text("Saved goodbye!")


@app.on_message(filters.command("resetwelcome", config.COMMAND_PREFIXES))
@can_change_info
async def resetwlcm(_, m: Message):
    db = Greetings(m.chat.id)
    text = "Hey {first}, welcome to {chatname}!"
    db.set_welcome_text(text, None)
    await m.reply_text("Done!")


@app.on_message(filters.command("resetgoodbye", config.COMMAND_PREFIXES))
@can_change_info
async def resetgb(_, m: Message):
    db = Greetings(m.chat.id)
    text = "Sad to see you leaving {first}.\nTake Care!"
    db.set_goodbye_text(text, None)
    await m.reply_text("Ok Done!")


# --- MAIN HANDLER: MEMBER JOIN ---
@app.on_message(filters.group & filters.new_chat_members, group=69)
async def member_has_joined(c: Client, m: Message):
    # This works in Public Groups automatically.
    # IMPORTANT: In Private Groups, Bot MUST be Admin to see this message!
    
    users: List[User] = m.new_chat_members
    db = Greetings(m.chat.id)
    
    for user in users:
        try:
            if user.id == c.me.id:
                continue
            if user.is_bot:
                continue

            status = db.get_welcome_status()
            if not status:
                continue

            # Get Data
            oo = db.get_welcome_text()
            UwU = db.get_welcome_media()
            mtype = db.get_welcome_msgtype()
            parse_words = ["first", "last", "fullname", "username", "mention", "id", "chatname"]
            
            # Format Text
            hmm = await escape_mentions_using_curly_brackets_wl(user, m, oo, parse_words)
            tek, button = await parse_button(hmm)
            button = await build_keyboard(button)
            button = ikb(button) if button else None

            # Random Text Logic
            if "%%%" in tek:
                filter_reply = tek.split("%%%")
                teks = choice(filter_reply)
            else:
                teks = tek

            if not teks:
                teks = f"Hey {user.mention}, welcome to {m.chat.title}!"

            # Clean Previous Welcome Logic
            ifff = db.get_current_cleanwelcome_id()
            gg = db.get_current_cleanwelcome_settings()
            if ifff and gg:
                try:
                    await c.delete_messages(m.chat.id, int(ifff))
                except RPCError:
                    pass

            # Send Message
            if not UwU:
                # Text Welcome
                jj = await c.send_message(
                    m.chat.id,
                    text=teks,
                    reply_markup=button,
                    disable_web_page_preview=True
                )
            else:
                # Media Welcome
                jj = await (await send_cmd(c, mtype))(
                    m.chat.id,
                    UwU,
                    caption=teks,
                    reply_markup=button,
                )

            if jj:
                db.set_cleanwlcm_id(int(jj.id))
        
        except (ChannelPrivate, ChatAdminRequired):
            # Bot doesn't have permission to write
            continue
        except Exception as e:
            # Prevents crash on unexpected errors
            print(f"Welcome Error: {e}")
            continue


# --- MAIN HANDLER: MEMBER LEAVE ---
@app.on_message(filters.group & filters.left_chat_member, group=99)
async def member_has_left(c: Client, m: Message):
    db = Greetings(m.chat.id)
    status = db.get_goodbye_status()
    if not status:
        return

    user = m.left_chat_member or m.from_user
    oo = db.get_goodbye_text()
    UwU = db.get_goodbye_media()
    mtype = db.get_goodbye_msgtype()
    parse_words = ["first", "last", "fullname", "id", "username", "mention", "chatname"]

    try:
        hmm = await escape_mentions_using_curly_brackets_wl(user, m, oo, parse_words)
        tek, button = await parse_button(hmm)
        button = await build_keyboard(button)
        button = ikb(button) if button else None

        if "%%%" in tek:
            filter_reply = tek.split("%%%")
            teks = choice(filter_reply)
        else:
            teks = tek

        if not teks:
            teks = f"Goodbye {user.mention}!"

        # Clean Previous Goodbye
        ifff = db.get_current_cleangoodbye_id()
        iii = db.get_current_cleangoodbye_settings()
        if ifff and iii:
            try:
                await c.delete_messages(m.chat.id, int(ifff))
            except RPCError:
                pass

        # Send Goodbye
        if UwU:
            ooo = await (await send_cmd(c, mtype))(
                m.chat.id,
                UwU,
                caption=teks,
                reply_markup=button,
            )
        else:
            ooo = await c.send_message(
                m.chat.id,
                text=teks,
                reply_markup=button,
                disable_web_page_preview=True,
            )
            
        if ooo:
            db.set_cleangoodbye_id(int(ooo.id))

    except (ChannelPrivate, ChatAdminRequired):
        return
    except Exception:
        pass


@app.on_message(filters.command("welcome", config.COMMAND_PREFIXES))
@chatadmin
async def welcome(c: Client, m: Message):
    db = Greetings(m.chat.id)
    status = db.get_welcome_status()
    oo = db.get_welcome_text()
    args = m.text.split(" ", 1)

    if len(args) >= 2:
        if args[1].lower() == "on":
            db.set_current_welcome_settings(True)
            await m.reply_text("I will greet newly joined member from now on.")
            return
        if args[1].lower() == "off":
            db.set_current_welcome_settings(False)
            await m.reply_text("I will stay quiet when someone joins.")
            return
    
    await m.reply_text(
        f"**Welcome Settings:**\nWelcome: {status}\nClean Welcome: {db.get_current_cleanwelcome_settings()}"
    )


@app.on_message(filters.command("goodbye", config.COMMAND_PREFIXES))
@chatadmin
async def goodbye(c: Client, m: Message):
    db = Greetings(m.chat.id)
    status = db.get_goodbye_status()
    oo = db.get_goodbye_text()
    args = m.text.split(" ", 1)

    if len(args) >= 2:
        if args[1].lower() == "on":
            db.set_current_goodbye_settings(True)
            await m.reply_text("Goodbye messages enabled.")
            return
        if args[1].lower() == "off":
            db.set_current_goodbye_settings(False)
            await m.reply_text("Goodbye messages disabled.")
            return
    
    await m.reply_text(
        f"**Goodbye Settings:**\nGoodbye: {status}\nClean Goodbye: {db.get_current_cleangoodbye_settings()}"
    )

__module__ = "Greetings"
__help__ = """
**👋 Greetings Module**

Customize Welcome and Goodbye messages!

/setwelcome [Reply] - Set custom welcome
/setgoodbye [Reply] - Set custom goodbye
/welcome on/off - Enable or disable
/goodbye on/off - Enable or disable
/cleanwelcome on/off - Delete old welcome messages
"""
