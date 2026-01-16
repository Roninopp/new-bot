"""
Module to unban all banned users in a group
"""

from pyrogram import filters, Client, enums
from pyrogram.types import Message
from pyrogram.errors import FloodWait, UserAdminInvalid, ChatAdminRequired
from Yumeko import app
from Yumeko.decorator.chatadmin import chatadmin
from config import config
import asyncio

ChatType = enums.ChatType


@app.on_message(filters.command("unbanall", config.COMMAND_PREFIXES))
@chatadmin
async def unban_all_users(c: Client, m: Message):
    """
    Unban all banned users in the group
    Requires bot and user to be admin
    """
    
    print(f"\n[UNBANALL] ========== /unbanall command triggered ==========")
    print(f"[UNBANALL] User: {m.from_user.first_name} (ID: {m.from_user.id})")
    print(f"[UNBANALL] Chat: {m.chat.title} (ID: {m.chat.id})")
    
    # Check if in a group
    if m.chat.type == ChatType.PRIVATE:
        await m.reply_text("❌ This command only works in groups!")
        return
    
    # Check if user is admin
    try:
        user_member = await c.get_chat_member(m.chat.id, m.from_user.id)
        if user_member.status not in ["creator", "administrator"]:
            await m.reply_text("❌ You need to be an admin to use this command!")
            return
        
        # Check if user has ban permissions
        if user_member.status == "administrator":
            if not user_member.privileges or not user_member.privileges.can_restrict_members:
                await m.reply_text("❌ You don't have permission to restrict members!")
                return
    except Exception as e:
        print(f"[UNBANALL] Error checking user permissions: {e}")
        await m.reply_text(f"❌ Error checking permissions: `{e}`")
        return
    
    # Check if bot is admin
    try:
        bot_member = await c.get_chat_member(m.chat.id, c.me.id)
        if bot_member.status not in ["creator", "administrator"]:
            await m.reply_text("❌ I need to be an admin to unban users!")
            return
        
        # Check if bot has ban permissions
        if bot_member.status == "administrator":
            if not bot_member.privileges or not bot_member.privileges.can_restrict_members:
                await m.reply_text("❌ I don't have permission to restrict members!")
                return
    except Exception as e:
        print(f"[UNBANALL] Error checking bot permissions: {e}")
        await m.reply_text(f"❌ Error checking my permissions: `{e}`")
        return
    
    # Confirmation message
    confirm_msg = await m.reply_text(
        "⚠️ **WARNING**\n\n"
        "This will unban **ALL** banned users in this group!\n\n"
        "Are you sure you want to continue?\n\n"
        "Reply with `/confirm` within 30 seconds to proceed."
    )
    
    print(f"[UNBANALL] Waiting for confirmation...")
    
    # Wait for confirmation
    def check_confirm(_, __, message):
        return (
            message.from_user 
            and message.from_user.id == m.from_user.id 
            and message.chat.id == m.chat.id
            and message.text 
            and message.text.lower().startswith("/confirm")
        )
    
    try:
        confirmation = await c.listen(
            m.chat.id,
            filters=filters.create(check_confirm),
            timeout=30
        )
        print(f"[UNBANALL] ✓ Confirmation received!")
    except asyncio.TimeoutError:
        print(f"[UNBANALL] ✗ Timeout - no confirmation")
        await confirm_msg.edit_text("❌ **Cancelled!**\n\nNo confirmation received within 30 seconds.")
        return
    
    # Start unbanning
    status_msg = await m.reply_text("🔄 **Starting to unban users...**\n\nThis may take a while...")
    
    print(f"[UNBANALL] Starting to fetch banned users...")
    
    unbanned_count = 0
    failed_count = 0
    banned_users = []
    
    try:
        # Get all banned users
        print(f"[UNBANALL] Fetching banned users list...")
        async for member in c.get_chat_members(m.chat.id, filter=enums.ChatMembersFilter.BANNED):
            banned_users.append(member.user)
        
        total_banned = len(banned_users)
        print(f"[UNBANALL] Found {total_banned} banned users")
        
        if total_banned == 0:
            await status_msg.edit_text("✅ **No banned users found!**\n\nThe group has no banned users.")
            return
        
        # Update status
        await status_msg.edit_text(
            f"🔄 **Found {total_banned} banned users!**\n\n"
            f"Starting to unban them..."
        )
        
        # Unban each user
        for idx, user in enumerate(banned_users, 1):
            try:
                print(f"[UNBANALL] Unbanning {idx}/{total_banned}: {user.first_name} (ID: {user.id})")
                
                # Unban the user
                await c.unban_chat_member(m.chat.id, user.id)
                unbanned_count += 1
                
                # Update status every 10 users
                if idx % 10 == 0 or idx == total_banned:
                    await status_msg.edit_text(
                        f"🔄 **Unbanning in progress...**\n\n"
                        f"Progress: {idx}/{total_banned}\n"
                        f"✅ Unbanned: {unbanned_count}\n"
                        f"❌ Failed: {failed_count}"
                    )
                
                # Small delay to avoid flood
                await asyncio.sleep(0.5)
                
            except FloodWait as e:
                print(f"[UNBANALL] FloodWait: waiting {e.value} seconds")
                await status_msg.edit_text(
                    f"⏳ **Rate limit hit!**\n\n"
                    f"Waiting {e.value} seconds...\n\n"
                    f"Progress: {idx}/{total_banned}\n"
                    f"✅ Unbanned: {unbanned_count}\n"
                    f"❌ Failed: {failed_count}"
                )
                await asyncio.sleep(e.value)
                
                # Retry the user after waiting
                try:
                    await c.unban_chat_member(m.chat.id, user.id)
                    unbanned_count += 1
                except Exception as retry_error:
                    print(f"[UNBANALL] Retry failed for {user.id}: {retry_error}")
                    failed_count += 1
                    
            except UserAdminInvalid:
                print(f"[UNBANALL] Cannot unban admin: {user.id}")
                failed_count += 1
                
            except Exception as e:
                print(f"[UNBANALL] Error unbanning {user.id}: {e}")
                failed_count += 1
        
        # Final status
        print(f"[UNBANALL] Completed! Unbanned: {unbanned_count}, Failed: {failed_count}")
        
        await status_msg.edit_text(
            f"✅ **Unban All Completed!**\n\n"
            f"📊 **Statistics:**\n"
            f"👥 Total banned users: {total_banned}\n"
            f"✅ Successfully unbanned: {unbanned_count}\n"
            f"❌ Failed to unban: {failed_count}\n\n"
            f"🎉 All done!"
        )
        
        print(f"[UNBANALL] ========== END ==========\n")
        
    except ChatAdminRequired:
        print(f"[UNBANALL] Error: Bot needs admin rights")
        await status_msg.edit_text(
            "❌ **Error!**\n\n"
            "I need admin rights with 'Restrict Members' permission to unban users!"
        )
        
    except Exception as e:
        print(f"[UNBANALL] Critical error: {e}")
        import traceback
        traceback.print_exc()
        
        await status_msg.edit_text(
            f"❌ **Error occurred!**\n\n"
            f"Unbanned so far: {unbanned_count}\n"
            f"Failed: {failed_count}\n\n"
            f"Error: `{str(e)[:200]}`"
        )


@app.on_message(filters.command("listbanned", config.COMMAND_PREFIXES))
@chatadmin
async def list_banned_users(c: Client, m: Message):
    """
    List all currently banned users in the group
    """
    
    print(f"\n[LISTBANNED] Command triggered by {m.from_user.first_name}")
    
    # Check if in a group
    if m.chat.type == ChatType.PRIVATE:
        await m.reply_text("❌ This command only works in groups!")
        return
    
    status_msg = await m.reply_text("🔄 **Fetching banned users...**")
    
    try:
        banned_users = []
        async for member in c.get_chat_members(m.chat.id, filter=enums.ChatMembersFilter.BANNED):
            banned_users.append(member.user)
        
        total_banned = len(banned_users)
        
        if total_banned == 0:
            await status_msg.edit_text("✅ **No banned users!**\n\nThis group has no banned users.")
            return
        
        # Create list text
        text = f"🚫 **Banned Users ({total_banned})**\n\n"
        
        for idx, user in enumerate(banned_users[:50], 1):  # Show max 50
            username = f"@{user.username}" if user.username else "No username"
            text += f"{idx}. {user.first_name} | {username}\n    ID: `{user.id}`\n\n"
        
        if total_banned > 50:
            text += f"\n... and {total_banned - 50} more users.\n\n"
        
        text += f"💡 Use `/unbanall` to unban all users."
        
        await status_msg.edit_text(text)
        
        print(f"[LISTBANNED] Listed {total_banned} banned users")
        
    except Exception as e:
        print(f"[LISTBANNED] Error: {e}")
        await status_msg.edit_text(f"❌ Error: `{e}`")


__module__ = "Unban All"

__help__ = """**Unban All Module:**

Mass unban all banned users from the group.

**Commands:**

  /unbanall - Unban all banned users
  • Requires admin with ban permissions
  • Bot must be admin with ban permissions
  • Shows confirmation prompt
  • Displays progress while unbanning
  • Handles rate limits automatically
  
  /listbanned - List all banned users
  • Shows max 50 banned users
  • Displays username and user ID
  • Admin only command

**How to use /unbanall:**

1. Run `/unbanall` in the group
2. Bot will ask for confirmation
3. Reply with `/confirm` within 30 seconds
4. Bot will start unbanning all users
5. Progress will be shown in real-time

**Requirements:**
  • You must be admin with 'Ban Users' permission
  • Bot must be admin with 'Ban Users' permission

**Note:** Process can take time if there are many banned users.
Rate limits are handled automatically.
"""
