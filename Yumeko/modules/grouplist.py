"""
Module to track and list all chats where bot is present
Uses database to track joins/leaves since bots can't use get_dialogs()
"""

from pyrogram import filters, Client, enums
from pyrogram.types import Message, ChatMemberUpdated
from Yumeko import app
from Yumeko.database import MongoDB
from Yumeko.decorator.chatadmin import chatadmin
from config import config
from io import BytesIO
from datetime import datetime
from threading import RLock

ChatType = enums.ChatType
INSERTION_LOCK = RLock()


class ChatTracker(MongoDB):
    """Track all chats where bot is present"""
    
    db_name = "bot_chats"
    
    def __init__(self):
        super().__init__(self.db_name)
    
    def add_chat(self, chat_id: int, chat_data: dict):
        """Add or update chat in database"""
        with INSERTION_LOCK:
            existing = self.find_one({"_id": chat_id})
            if existing:
                # Update existing
                self.update({"_id": chat_id}, chat_data)
            else:
                # Add new
                chat_data["_id"] = chat_id
                chat_data["joined_date"] = datetime.now().isoformat()
                self.insert_one(chat_data)
            print(f"[CHAT_TRACKER] Added/Updated chat: {chat_id}")
    
    def remove_chat(self, chat_id: int):
        """Remove chat from database"""
        with INSERTION_LOCK:
            result = self.delete_one({"_id": chat_id})
            print(f"[CHAT_TRACKER] Removed chat: {chat_id}")
            return result
    
    def get_all_chats(self):
        """Get all tracked chats"""
        with INSERTION_LOCK:
            chats = list(self.find_all())
            print(f"[CHAT_TRACKER] Retrieved {len(chats)} chats from database")
            return chats
    
    def get_chat(self, chat_id: int):
        """Get specific chat"""
        with INSERTION_LOCK:
            return self.find_one({"_id": chat_id})
    
    def count_by_type(self, chat_type: str):
        """Count chats by type"""
        with INSERTION_LOCK:
            return self.count({"type": chat_type})


# Initialize tracker
tracker = ChatTracker()


async def track_chat_info(c: Client, chat_id: int):
    """Get and save chat information"""
    try:
        print(f"[CHAT_TRACKER] Fetching info for chat {chat_id}")
        
        # Get chat info
        chat = await c.get_chat(chat_id)
        
        # Get member count
        member_count = "N/A"
        try:
            member_count = await c.get_chat_members_count(chat_id)
        except Exception as e:
            print(f"[CHAT_TRACKER] Could not get member count: {e}")
        
        # Prepare chat data
        chat_data = {
            "name": chat.title if hasattr(chat, 'title') else "Unknown",
            "type": str(chat.type).replace('ChatType.', ''),
            "username": chat.username if hasattr(chat, 'username') and chat.username else None,
            "members": member_count,
            "last_updated": datetime.now().isoformat()
        }
        
        # Save to database
        tracker.add_chat(chat_id, chat_data)
        
        print(f"[CHAT_TRACKER] Tracked: {chat_data['name']} ({chat_data['type']})")
        
    except Exception as e:
        print(f"[CHAT_TRACKER] Error tracking chat {chat_id}: {e}")


# Track when bot is added to a chat
@app.on_message(filters.new_chat_members)
async def on_bot_added_to_chat(c: Client, m: Message):
    """Track when bot is added to a new chat"""
    
    # Check if bot was added
    for user in m.new_chat_members:
        if user.id == c.me.id:
            print(f"\n[CHAT_TRACKER] ========== BOT ADDED TO CHAT ==========")
            print(f"[CHAT_TRACKER] Chat ID: {m.chat.id}")
            print(f"[CHAT_TRACKER] Chat Name: {m.chat.title}")
            print(f"[CHAT_TRACKER] Chat Type: {m.chat.type}")
            
            await track_chat_info(c, m.chat.id)
            
            print(f"[CHAT_TRACKER] ========== END ==========\n")
            break


# Track via chat_member_updated (for when bot joins via link)
@app.on_chat_member_updated()
async def on_bot_member_updated(c: Client, update: ChatMemberUpdated):
    """Track when bot joins via invite link"""
    
    # Check if it's the bot
    if update.new_chat_member and update.new_chat_member.user.id == c.me.id:
        
        # Check if bot just joined
        if not update.old_chat_member:
            print(f"\n[CHAT_TRACKER] ========== BOT JOINED VIA LINK ==========")
            print(f"[CHAT_TRACKER] Chat ID: {update.chat.id}")
            print(f"[CHAT_TRACKER] Chat Type: {update.chat.type}")
            
            await track_chat_info(c, update.chat.id)
            
            print(f"[CHAT_TRACKER] ========== END ==========\n")


# Track when bot is removed/leaves
@app.on_message(filters.left_chat_member)
async def on_bot_removed_from_chat(c: Client, m: Message):
    """Track when bot is removed or leaves chat"""
    
    # Check if bot left
    if m.left_chat_member and m.left_chat_member.id == c.me.id:
        print(f"\n[CHAT_TRACKER] ========== BOT LEFT CHAT ==========")
        print(f"[CHAT_TRACKER] Chat ID: {m.chat.id}")
        print(f"[CHAT_TRACKER] Removing from database...")
        
        tracker.remove_chat(m.chat.id)
        
        print(f"[CHAT_TRACKER] ========== END ==========\n")


@app.on_message(filters.command("groups", config.COMMAND_PREFIXES))
@chatadmin
async def list_all_groups(c: Client, m: Message):
    """
    List all tracked groups/supergroups/channels
    Exports as groups.txt file
    """
    
    print(f"\n[CHATLIST] ========== /groups command triggered ==========")
    print(f"[CHATLIST] User: {m.from_user.first_name} (ID: {m.from_user.id})")
    
    status_msg = await m.reply_text("🔄 Fetching chat list from database...")
    
    try:
        # Get all chats from database
        all_chats = tracker.get_all_chats()
        
        print(f"[CHATLIST] Found {len(all_chats)} chats in database")
        
        if not all_chats:
            await status_msg.edit_text(
                "❌ No chats found in database!\n\n"
                "💡 **Note:** The bot tracks chats automatically when:\n"
                "• Bot is added to a group\n"
                "• Someone joins a group where bot is present\n\n"
                "The database will populate over time."
            )
            return
        
        # Categorize chats
        groups_list = []
        supergroups_list = []
        channels_list = []
        
        for chat in all_chats:
            chat_type = chat.get('type', 'Unknown')
            
            if chat_type == 'GROUP':
                groups_list.append(chat)
            elif chat_type == 'SUPERGROUP':
                supergroups_list.append(chat)
            elif chat_type == 'CHANNEL':
                channels_list.append(chat)
        
        total_groups = len(groups_list)
        total_supergroups = len(supergroups_list)
        total_channels = len(channels_list)
        total_chats = total_groups + total_supergroups + total_channels
        
        print(f"[CHATLIST] Groups: {total_groups}, Supergroups: {total_supergroups}, Channels: {total_channels}")
        
        await status_msg.edit_text(f"✅ Found {total_chats} chats!\n🔄 Generating file...")
        
        # Generate text file
        output = f"""
╔══════════════════════════════════════╗
║     BOT GROUPS & CHANNELS LIST      ║
╚══════════════════════════════════════╝

📊 SUMMARY:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
👥 Basic Groups: {total_groups}
🏢 Supergroups: {total_supergroups}
📢 Channels: {total_channels}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 TOTAL CHATS: {total_chats}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

"""
        
        # Add groups
        if groups_list:
            output += "\n\n" + "="*50 + "\n"
            output += "👥 BASIC GROUPS\n"
            output += "="*50 + "\n\n"
            
            for idx, group in enumerate(groups_list, 1):
                output += f"{idx}. {group.get('name', 'Unknown')}\n"
                output += f"   📍 ID: {group.get('_id', 'Unknown')}\n"
                output += f"   👤 Members: {group.get('members', 'N/A')}\n"
                username = group.get('username')
                output += f"   🔗 Username: @{username}\n" if username else f"   🔗 Username: No username\n"
                joined = group.get('joined_date', 'Unknown')
                if joined != 'Unknown':
                    try:
                        joined_dt = datetime.fromisoformat(joined)
                        output += f"   📅 Added: {joined_dt.strftime('%Y-%m-%d %H:%M')}\n"
                    except:
                        pass
                output += f"   {'─' * 45}\n\n"
        
        # Add supergroups
        if supergroups_list:
            output += "\n" + "="*50 + "\n"
            output += "🏢 SUPERGROUPS\n"
            output += "="*50 + "\n\n"
            
            for idx, group in enumerate(supergroups_list, 1):
                output += f"{idx}. {group.get('name', 'Unknown')}\n"
                output += f"   📍 ID: {group.get('_id', 'Unknown')}\n"
                output += f"   👤 Members: {group.get('members', 'N/A')}\n"
                username = group.get('username')
                output += f"   🔗 Username: @{username}\n" if username else f"   🔗 Username: No username\n"
                joined = group.get('joined_date', 'Unknown')
                if joined != 'Unknown':
                    try:
                        joined_dt = datetime.fromisoformat(joined)
                        output += f"   📅 Added: {joined_dt.strftime('%Y-%m-%d %H:%M')}\n"
                    except:
                        pass
                output += f"   {'─' * 45}\n\n"
        
        # Add channels
        if channels_list:
            output += "\n" + "="*50 + "\n"
            output += "📢 CHANNELS\n"
            output += "="*50 + "\n\n"
            
            for idx, channel in enumerate(channels_list, 1):
                output += f"{idx}. {channel.get('name', 'Unknown')}\n"
                output += f"   📍 ID: {channel.get('_id', 'Unknown')}\n"
                output += f"   👤 Subscribers: {channel.get('members', 'N/A')}\n"
                username = channel.get('username')
                output += f"   🔗 Username: @{username}\n" if username else f"   🔗 Username: No username\n"
                joined = channel.get('joined_date', 'Unknown')
                if joined != 'Unknown':
                    try:
                        joined_dt = datetime.fromisoformat(joined)
                        output += f"   📅 Added: {joined_dt.strftime('%Y-%m-%d %H:%M')}\n"
                    except:
                        pass
                output += f"   {'─' * 45}\n\n"
        
        output += "\n" + "="*50 + "\n"
        output += "        END OF LIST\n"
        output += "="*50 + "\n"
        
        # Create file
        file_content = BytesIO(output.encode('utf-8'))
        file_content.name = f"groups_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        # Send file
        await m.reply_document(
            document=file_content,
            caption=f"""
📊 **Bot Chat Statistics**

👥 Basic Groups: `{total_groups}`
🏢 Supergroups: `{total_supergroups}`
📢 Channels: `{total_channels}`

🎯 **Total Chats: `{total_chats}`**

✅ File generated from database!
""",
            file_name=file_content.name
        )
        
        await status_msg.delete()
        
        print(f"[CHATLIST] ✓ File sent successfully!")
        print(f"[CHATLIST] ========== END ==========\n")
        
    except Exception as e:
        print(f"[CHATLIST] ❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        
        await status_msg.edit_text(f"❌ Error: `{str(e)}`")


@app.on_message(filters.command("groupstats", config.COMMAND_PREFIXES))
@chatadmin
async def group_stats(c: Client, m: Message):
    """Quick statistics from database"""
    
    print(f"\n[CHATLIST] /groupstats command triggered")
    
    status_msg = await m.reply_text("🔄 Getting stats...")
    
    try:
        all_chats = tracker.get_all_chats()
        
        if not all_chats:
            await status_msg.edit_text("❌ No chats tracked yet!")
            return
        
        # Count by type
        total_groups = 0
        total_supergroups = 0
        total_channels = 0
        total_members = 0
        
        for chat in all_chats:
            chat_type = chat.get('type', '')
            
            if chat_type == 'GROUP':
                total_groups += 1
            elif chat_type == 'SUPERGROUP':
                total_supergroups += 1
            elif chat_type == 'CHANNEL':
                total_channels += 1
            
            # Add members
            members = chat.get('members', 0)
            if isinstance(members, int):
                total_members += members
        
        total_chats = total_groups + total_supergroups + total_channels
        
        stats_text = f"""
📊 **Bot Chat Statistics**

👥 **Basic Groups:** `{total_groups}`
🏢 **Supergroups:** `{total_supergroups}`
📢 **Channels:** `{total_channels}`

━━━━━━━━━━━━━━━━━━━━━━
🎯 **Total Chats:** `{total_chats}`
👤 **Total Members:** `{total_members:,}`
━━━━━━━━━━━━━━━━━━━━━━

💡 Use `/groups` to get detailed list
"""
        
        await status_msg.edit_text(stats_text)
        
        print(f"[CHATLIST] Stats sent: {total_chats} chats")
        
    except Exception as e:
        print(f"[CHATLIST] Error: {e}")
        await status_msg.edit_text(f"❌ Error: `{str(e)}`")


@app.on_message(filters.command("updatechat", config.COMMAND_PREFIXES))
@chatadmin
async def update_current_chat(c: Client, m: Message):
    """Manually add/update current chat in database"""
    
    if m.chat.type == ChatType.PRIVATE:
        await m.reply_text("❌ This only works in groups/channels!")
        return
    
    status_msg = await m.reply_text("🔄 Updating chat info...")
    
    try:
        await track_chat_info(c, m.chat.id)
        await status_msg.edit_text(f"✅ Updated chat info for: {m.chat.title}")
    except Exception as e:
        await status_msg.edit_text(f"❌ Error: `{str(e)}`")


__module__ = "Chat List"

__help__ = """**Bot Chat List Module:**

**AUTO-TRACKING:** Bot automatically tracks chats when:
  • Bot is added to a group
  • Members join groups where bot is present
  • Bot joins via invite link

**Commands:**

  /groups - Get detailed list of all tracked chats
  • Generates text file with all groups/channels
  • Shows: name, ID, type, members, join date
  • Categorized by type
  
  /groupstats - Quick statistics
  • Count of groups, supergroups, channels
  • Total member count
  • Fast overview
  
  /updatechat - Manually update current chat
  • Updates info for the chat where command is used
  • Useful if data seems outdated

**How It Works:**
  🔹 Bot tracks chats in database automatically
  🔹 No need to manually add - happens when bot joins
  🔹 Removes chats when bot leaves/kicked
  🔹 Database method (works with bot limitations)

**Note:** Data updates automatically when bot joins/leaves chats.
Admin only commands for security.
"""
