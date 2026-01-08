"""
Module to list all chats where bot is present
Shows groups, supergroups, and channels
"""

from pyrogram import filters, Client, enums
from pyrogram.types import Message
from Yumeko import app
from Yumeko.decorator.chatadmin import chatadmin
from config import config
from io import BytesIO
from datetime import datetime

ChatType = enums.ChatType


@app.on_message(filters.command("groups", config.COMMAND_PREFIXES))
@chatadmin
async def list_all_groups(c: Client, m: Message):
    """
    List all groups/supergroups/channels where bot is present
    Exports as groups.txt file
    """
    
    print(f"\n[CHATLIST] ========== /groups command triggered ==========")
    print(f"[CHATLIST] User: {m.from_user.first_name} (ID: {m.from_user.id})")
    print(f"[CHATLIST] Chat: {m.chat.id}")
    
    # Send processing message
    status_msg = await m.reply_text("🔄 Fetching all chats... Please wait...")
    
    # Counters
    total_groups = 0
    total_supergroups = 0
    total_channels = 0
    total_private = 0
    failed_count = 0
    
    # Lists to store chat data
    groups_list = []
    supergroups_list = []
    channels_list = []
    
    print(f"[CHATLIST] Starting to fetch dialogs...")
    
    try:
        # Fetch all dialogs (chats)
        dialog_count = 0
        async for dialog in c.get_dialogs():
            dialog_count += 1
            
            # Get chat info
            chat = dialog.chat
            chat_type = chat.type
            chat_id = chat.id
            chat_title = chat.title if hasattr(chat, 'title') and chat.title else "Unknown"
            
            print(f"[CHATLIST] Processing dialog {dialog_count}: {chat_title} (ID: {chat_id}, Type: {chat_type})")
            
            # Skip private chats (1-on-1 DMs)
            if chat_type == ChatType.PRIVATE:
                total_private += 1
                print(f"[CHATLIST] Skipping private chat")
                continue
            
            # Get member count (if possible)
            member_count = "Unknown"
            try:
                member_count = await c.get_chat_members_count(chat_id)
                print(f"[CHATLIST] Member count: {member_count}")
            except Exception as e:
                print(f"[CHATLIST] Could not get member count: {e}")
                member_count = "N/A"
            
            # Prepare chat info
            chat_info = {
                'name': chat_title,
                'id': chat_id,
                'type': str(chat_type).replace('ChatType.', ''),
                'members': member_count,
                'username': f"@{chat.username}" if hasattr(chat, 'username') and chat.username else "No username"
            }
            
            # Categorize by type
            if chat_type == ChatType.GROUP:
                total_groups += 1
                groups_list.append(chat_info)
                print(f"[CHATLIST] Added to groups list")
                
            elif chat_type == ChatType.SUPERGROUP:
                total_supergroups += 1
                supergroups_list.append(chat_info)
                print(f"[CHATLIST] Added to supergroups list")
                
            elif chat_type == ChatType.CHANNEL:
                total_channels += 1
                channels_list.append(chat_info)
                print(f"[CHATLIST] Added to channels list")
        
        print(f"\n[CHATLIST] Finished fetching dialogs. Total processed: {dialog_count}")
        print(f"[CHATLIST] Groups: {total_groups}, Supergroups: {total_supergroups}, Channels: {total_channels}")
        
        # Update status message
        await status_msg.edit_text(f"✅ Found {total_groups + total_supergroups + total_channels} chats!\n🔄 Generating file...")
        
        # Calculate totals
        total_chats = total_groups + total_supergroups + total_channels
        
        if total_chats == 0:
            await status_msg.edit_text("❌ Bot is not in any groups/channels yet!")
            return
        
        # Generate text file content
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
        
        # Add basic groups
        if groups_list:
            output += "\n\n" + "="*50 + "\n"
            output += "👥 BASIC GROUPS\n"
            output += "="*50 + "\n\n"
            
            for idx, group in enumerate(groups_list, 1):
                output += f"{idx}. {group['name']}\n"
                output += f"   📍 ID: {group['id']}\n"
                output += f"   👤 Members: {group['members']}\n"
                output += f"   🔗 Username: {group['username']}\n"
                output += f"   {'─' * 45}\n\n"
        
        # Add supergroups
        if supergroups_list:
            output += "\n" + "="*50 + "\n"
            output += "🏢 SUPERGROUPS\n"
            output += "="*50 + "\n\n"
            
            for idx, group in enumerate(supergroups_list, 1):
                output += f"{idx}. {group['name']}\n"
                output += f"   📍 ID: {group['id']}\n"
                output += f"   👤 Members: {group['members']}\n"
                output += f"   🔗 Username: {group['username']}\n"
                output += f"   {'─' * 45}\n\n"
        
        # Add channels
        if channels_list:
            output += "\n" + "="*50 + "\n"
            output += "📢 CHANNELS\n"
            output += "="*50 + "\n\n"
            
            for idx, channel in enumerate(channels_list, 1):
                output += f"{idx}. {channel['name']}\n"
                output += f"   📍 ID: {channel['id']}\n"
                output += f"   👤 Subscribers: {channel['members']}\n"
                output += f"   🔗 Username: {channel['username']}\n"
                output += f"   {'─' * 45}\n\n"
        
        # Add footer
        output += "\n" + "="*50 + "\n"
        output += "        END OF LIST\n"
        output += "="*50 + "\n"
        
        print(f"[CHATLIST] Generated file content ({len(output)} characters)")
        
        # Create BytesIO object with the content
        file_content = BytesIO(output.encode('utf-8'))
        file_content.name = f"groups_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        # Send the file
        print(f"[CHATLIST] Sending file...")
        await m.reply_document(
            document=file_content,
            caption=f"""
📊 **Bot Chat Statistics**

👥 Basic Groups: `{total_groups}`
🏢 Supergroups: `{total_supergroups}`
📢 Channels: `{total_channels}`

🎯 **Total Chats: `{total_chats}`**

✅ File generated successfully!
""",
            file_name=file_content.name
        )
        
        # Delete status message
        await status_msg.delete()
        
        print(f"[CHATLIST] ✓ File sent successfully!")
        print(f"[CHATLIST] ========== END ==========\n")
        
    except Exception as e:
        print(f"[CHATLIST] ❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        
        await status_msg.edit_text(f"❌ Error fetching chats:\n`{str(e)}`")


@app.on_message(filters.command("groupstats", config.COMMAND_PREFIXES))
@chatadmin
async def group_stats(c: Client, m: Message):
    """
    Quick statistics about groups/channels (no file)
    """
    
    print(f"\n[CHATLIST] /groupstats command triggered")
    
    status_msg = await m.reply_text("🔄 Counting chats...")
    
    # Counters
    total_groups = 0
    total_supergroups = 0
    total_channels = 0
    total_members = 0
    
    try:
        async for dialog in c.get_dialogs():
            chat = dialog.chat
            chat_type = chat.type
            
            # Skip private chats
            if chat_type == ChatType.PRIVATE:
                continue
            
            # Count by type
            if chat_type == ChatType.GROUP:
                total_groups += 1
            elif chat_type == ChatType.SUPERGROUP:
                total_supergroups += 1
            elif chat_type == ChatType.CHANNEL:
                total_channels += 1
            
            # Try to get member count
            try:
                count = await c.get_chat_members_count(chat.id)
                total_members += count
            except:
                pass
        
        total_chats = total_groups + total_supergroups + total_channels
        
        # Send statistics
        stats_text = f"""
📊 **Bot Chat Statistics**

👥 **Basic Groups:** `{total_groups}`
🏢 **Supergroups:** `{total_supergroups}`
📢 **Channels:** `{total_channels}`

━━━━━━━━━━━━━━━━━━━━━━
🎯 **Total Chats:** `{total_chats}`
👤 **Total Members:** `{total_members:,}`
━━━━━━━━━━━━━━━━━━━━━━

💡 Use `/groups` to get detailed list with file
"""
        
        await status_msg.edit_text(stats_text)
        
        print(f"[CHATLIST] Stats sent: {total_chats} chats, {total_members} members")
        
    except Exception as e:
        print(f"[CHATLIST] Error: {e}")
        await status_msg.edit_text(f"❌ Error: `{str(e)}`")


__module__ = "Chat List"

__help__ = """**Bot Chat List Module:**

View all groups and channels where the bot is present.

**Commands:**

  /groups - Get detailed list of all chats
  • Generates a text file with all groups/channels
  • Shows chat name, ID, type, member count
  • Categorized by type (Groups, Supergroups, Channels)
  
  /groupstats - Quick statistics
  • Shows count of groups, supergroups, channels
  • Shows total member count across all chats
  • No file generated (quick view)

**Features:**
  ✅ Lists ALL chats (won't miss any!)
  ✅ Shows member count for each chat
  ✅ Shows chat username if available
  ✅ Categorized output (Groups/Supergroups/Channels)
  ✅ Exports as downloadable .txt file
  ✅ Admin only command (secure)

**Note:** Bot must be admin in chats to see member counts.
"""
