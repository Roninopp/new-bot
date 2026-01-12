"""
Mini Games Module for Music Bot
Features: Tic Tac Toe (AI & 1v1) + Rock Paper Scissors (AI & 1v1)
"""

import random
from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from Yumeko import app
from config import config

# ==========================================
# 🎮 GAME STORAGE
# ==========================================
tictactoe_games = {}  # {msg_id: {board, player1, player2, turn, mode}}
rps_games = {}  # {msg_id: {player1, player2, mode}}
waiting_for_opponent = {}  # {chat_id: {game_type, message_id, player1}}

# ==========================================
# 🎯 TIC TAC TOE - AI LOGIC
# ==========================================
def check_winner(board):
    """Check if there's a winner. Returns 'X', 'O', 'Draw', or None"""
    # Check rows, columns, diagonals
    lines = [
        [board[0], board[1], board[2]],
        [board[3], board[4], board[5]],
        [board[6], board[7], board[8]],
        [board[0], board[3], board[6]],
        [board[1], board[4], board[7]],
        [board[2], board[5], board[8]],
        [board[0], board[4], board[8]],
        [board[2], board[4], board[6]]
    ]
    
    for line in lines:
        if line[0] == line[1] == line[2] and line[0] != '⬜':
            return line[0]
    
    if '⬜' not in board:
        return 'Draw'
    return None

def ai_move(board):
    """Smart AI that tries to win or block"""
    # Try to win
    for i in range(9):
        if board[i] == '⬜':
            board[i] = '⭕'
            if check_winner(board) == '⭕':
                board[i] = '⬜'
                return i
            board[i] = '⬜'
    
    # Try to block player
    for i in range(9):
        if board[i] == '⬜':
            board[i] = '❌'
            if check_winner(board) == '❌':
                board[i] = '⬜'
                return i
            board[i] = '⬜'
    
    # Take center if available
    if board[4] == '⬜':
        return 4
    
    # Take corners
    corners = [0, 2, 6, 8]
    random.shuffle(corners)
    for i in corners:
        if board[i] == '⬜':
            return i
    
    # Take any available
    available = [i for i in range(9) if board[i] == '⬜']
    return random.choice(available) if available else None

def create_ttt_keyboard(board, game_id):
    """Create Tic Tac Toe keyboard"""
    keyboard = []
    for row in range(3):
        keyboard.append([
            InlineKeyboardButton(
                board[row*3 + col], 
                callback_data=f"ttt_{game_id}_{row*3 + col}"
            ) for col in range(3)
        ])
    keyboard.append([InlineKeyboardButton("🔄 New Game", callback_data=f"ttt_new_{game_id}")])
    return InlineKeyboardMarkup(keyboard)

# ==========================================
# 🎮 TIC TAC TOE - BUTTON CALLBACK (AI MODE)
# ==========================================
@app.on_callback_query(filters.regex(r"^game_tictactoe"))
async def start_ttt_ai(_, query: CallbackQuery):
    """Start AI vs Player Tic Tac Toe"""
    msg_id = query.message.id
    user_id = query.from_user.id
    user_name = query.from_user.first_name
    
    # Initialize game
    board = ['⬜'] * 9
    tictactoe_games[msg_id] = {
        'board': board,
        'player1': user_id,
        'player1_name': user_name,
        'mode': 'ai',
        'turn': '❌'
    }
    
    text = (
        f"🎮 **Tic Tac Toe - AI Mode**\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 {user_name} (❌) vs 🤖 AI (⭕)\n"
        f"Your turn! Tap any square."
    )
    
    await query.message.edit_text(
        text, 
        reply_markup=create_ttt_keyboard(board, msg_id)
    )
    await query.answer("Game started! You're ❌")

@app.on_callback_query(filters.regex(r"^ttt_(\d+)_(\d+)"))
async def ttt_move(_, query: CallbackQuery):
    """Handle Tic Tac Toe moves"""
    data = query.data.split('_')
    msg_id = int(data[1])
    position = int(data[2])
    user_id = query.from_user.id
    
    if msg_id not in tictactoe_games:
        await query.answer("Game expired!", show_alert=True)
        return
    
    game = tictactoe_games[msg_id]
    board = game['board']
    
    # Check if it's player's turn and valid move
    if game['mode'] == 'ai':
        if user_id != game['player1']:
            await query.answer("Not your game!", show_alert=True)
            return
        
        if board[position] != '⬜':
            await query.answer("Square taken!", show_alert=True)
            return
        
        # Player move
        board[position] = '❌'
        winner = check_winner(board)
        
        if winner:
            await handle_ttt_end(query, game, winner)
            return
        
        # AI move
        ai_pos = ai_move(board)
        if ai_pos is not None:
            board[ai_pos] = '⭕'
            winner = check_winner(board)
            
            if winner:
                await handle_ttt_end(query, game, winner)
                return
        
        # Update board
        text = (
            f"🎮 **Tic Tac Toe - AI Mode**\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 {game['player1_name']} (❌) vs 🤖 AI (⭕)\n"
            f"Your turn!"
        )
        await query.message.edit_text(
            text, 
            reply_markup=create_ttt_keyboard(board, msg_id)
        )
        await query.answer()
    
    elif game['mode'] == '1v1':
        # Check whose turn
        current_player = game['player1'] if game['turn'] == '❌' else game['player2']
        if user_id != current_player:
            await query.answer("Not your turn!", show_alert=True)
            return
        
        if board[position] != '⬜':
            await query.answer("Square taken!", show_alert=True)
            return
        
        # Make move
        board[position] = game['turn']
        winner = check_winner(board)
        
        if winner:
            await handle_ttt_end(query, game, winner)
            return
        
        # Switch turn
        game['turn'] = '⭕' if game['turn'] == '❌' else '❌'
        next_player = game['player1_name'] if game['turn'] == '❌' else game['player2_name']
        
        text = (
            f"🎮 **Tic Tac Toe - 1v1**\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 {game['player1_name']} (❌) vs {game['player2_name']} (⭕)\n"
            f"Turn: {next_player} ({game['turn']})"
        )
        await query.message.edit_text(
            text,
            reply_markup=create_ttt_keyboard(board, msg_id)
        )
        await query.answer()

async def handle_ttt_end(query, game, winner):
    """Handle game end"""
    msg_id = query.message.id
    board = game['board']
    
    if winner == 'Draw':
        result = "🤝 **It's a Draw!**"
    elif winner == '❌':
        result = f"🎉 **{game['player1_name']} Wins!**" if game['mode'] == 'ai' else f"🎉 **{game['player1_name']} Wins!**"
    else:
        result = "🤖 **AI Wins!**" if game['mode'] == 'ai' else f"🎉 **{game['player2_name']} Wins!**"
    
    text = (
        f"🎮 **Tic Tac Toe - Game Over**\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{result}"
    )
    
    # Create final board (no callbacks)
    keyboard = []
    for row in range(3):
        keyboard.append([
            InlineKeyboardButton(board[row*3 + col], callback_data="ttt_end") 
            for col in range(3)
        ])
    keyboard.append([InlineKeyboardButton("🔄 New Game", callback_data=f"ttt_new_{msg_id}")])
    
    await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    del tictactoe_games[msg_id]
    await query.answer(result)

@app.on_callback_query(filters.regex(r"^ttt_new_"))
async def restart_ttt(_, query: CallbackQuery):
    """Restart Tic Tac Toe"""
    await start_ttt_ai(_, query)

# ==========================================
# ✊ ROCK PAPER SCISSORS - AI MODE
# ==========================================
@app.on_callback_query(filters.regex(r"^game_rps"))
async def start_rps_ai(_, query: CallbackQuery):
    """Start Rock Paper Scissors AI mode"""
    msg_id = query.message.id
    user_name = query.from_user.first_name
    
    text = (
        f"✊✋✌️ **Rock Paper Scissors**\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 {user_name} vs 🤖 AI\n"
        f"Make your choice!"
    )
    
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🪨 Rock", callback_data=f"rps_{msg_id}_rock"),
            InlineKeyboardButton("📄 Paper", callback_data=f"rps_{msg_id}_paper"),
            InlineKeyboardButton("✂️ Scissors", callback_data=f"rps_{msg_id}_scissors")
        ]
    ])
    
    await query.message.edit_text(text, reply_markup=keyboard)
    await query.answer("Choose your weapon!")

@app.on_callback_query(filters.regex(r"^rps_(\d+)_(rock|paper|scissors)"))
async def rps_play(_, query: CallbackQuery):
    """Handle RPS game"""
    data = query.data.split('_')
    player_choice = data[2]
    user_name = query.from_user.first_name
    
    choices = ['rock', 'paper', 'scissors']
    ai_choice = random.choice(choices)
    
    emojis = {'rock': '🪨', 'paper': '📄', 'scissors': '✂️'}
    
    # Determine winner
    if player_choice == ai_choice:
        result = "🤝 **It's a Tie!**"
    elif (player_choice == 'rock' and ai_choice == 'scissors') or \
         (player_choice == 'paper' and ai_choice == 'rock') or \
         (player_choice == 'scissors' and ai_choice == 'paper'):
        result = f"🎉 **{user_name} Wins!**"
    else:
        result = "🤖 **AI Wins!**"
    
    text = (
        f"✊✋✌️ **Rock Paper Scissors**\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 You: {emojis[player_choice]}\n"
        f"🤖 AI: {emojis[ai_choice]}\n\n"
        f"{result}"
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Play Again", callback_data="game_rps")]
    ])
    
    await query.message.edit_text(text, reply_markup=keyboard)
    await query.answer(result)

# ==========================================
# 🎮 MANUAL COMMANDS - 1v1 MODE
# ==========================================
@app.on_message(filters.command("tic", config.COMMAND_PREFIXES) & filters.group)
async def manual_ttt(_, message):
    """Start 1v1 Tic Tac Toe"""
    chat_id = message.chat.id
    player1 = message.from_user.id
    player1_name = message.from_user.first_name
    
    text = (
        f"🎮 **Tic Tac Toe - 1v1 Mode**\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 {player1_name} is waiting for opponent!\n"
        f"Tap 'Join Game' to play!"
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎯 Join Game", callback_data=f"ttt_join_{player1}")]
    ])
    
    msg = await message.reply(text, reply_markup=keyboard)
    waiting_for_opponent[chat_id] = {
        'game_type': 'ttt',
        'message_id': msg.id,
        'player1': player1,
        'player1_name': player1_name
    }

@app.on_callback_query(filters.regex(r"^ttt_join_"))
async def join_ttt(_, query: CallbackQuery):
    """Join 1v1 Tic Tac Toe"""
    player1_id = int(query.data.split('_')[2])
    player2 = query.from_user.id
    player2_name = query.from_user.first_name
    chat_id = query.message.chat.id
    
    if player2 == player1_id:
        await query.answer("You can't play with yourself!", show_alert=True)
        return
    
    if chat_id not in waiting_for_opponent:
        await query.answer("Game expired!", show_alert=True)
        return
    
    waiting = waiting_for_opponent[chat_id]
    msg_id = query.message.id
    
    # Start game
    board = ['⬜'] * 9
    tictactoe_games[msg_id] = {
        'board': board,
        'player1': player1_id,
        'player1_name': waiting['player1_name'],
        'player2': player2,
        'player2_name': player2_name,
        'mode': '1v1',
        'turn': '❌'
    }
    
    text = (
        f"🎮 **Tic Tac Toe - 1v1**\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 {waiting['player1_name']} (❌) vs {player2_name} (⭕)\n"
        f"Turn: {waiting['player1_name']} (❌)"
    )
    
    await query.message.edit_text(text, reply_markup=create_ttt_keyboard(board, msg_id))
    del waiting_for_opponent[chat_id]
    await query.answer("Game started!")

@app.on_message(filters.command("paper", config.COMMAND_PREFIXES) & filters.group)
async def manual_rps(_, message):
    """Start 1v1 Rock Paper Scissors"""
    chat_id = message.chat.id
    player1 = message.from_user.id
    player1_name = message.from_user.first_name
    
    text = (
        f"✊✋✌️ **Rock Paper Scissors - 1v1**\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 {player1_name} is waiting!\n"
        f"Tap 'Join Game' to play!"
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎯 Join Game", callback_data=f"rps_join_{player1}")]
    ])
    
    msg = await message.reply(text, reply_markup=keyboard)
    rps_games[msg.id] = {
        'player1': player1,
        'player1_name': player1_name,
        'player1_choice': None,
        'player2': None,
        'player2_name': None,
        'player2_choice': None,
        'waiting': True
    }

@app.on_callback_query(filters.regex(r"^rps_join_"))
async def join_rps(_, query: CallbackQuery):
    """Join 1v1 RPS"""
    player1_id = int(query.data.split('_')[2])
    player2 = query.from_user.id
    player2_name = query.from_user.first_name
    msg_id = query.message.id
    
    if player2 == player1_id:
        await query.answer("You can't play with yourself!", show_alert=True)
        return
    
    if msg_id not in rps_games:
        await query.answer("Game expired!", show_alert=True)
        return
    
    game = rps_games[msg_id]
    game['player2'] = player2
    game['player2_name'] = player2_name
    game['waiting'] = False
    
    text = (
        f"✊✋✌️ **Rock Paper Scissors - 1v1**\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 {game['player1_name']} vs {player2_name}\n"
        f"Both players make your choice!"
    )
    
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🪨", callback_data=f"rps1v1_{msg_id}_rock"),
            InlineKeyboardButton("📄", callback_data=f"rps1v1_{msg_id}_paper"),
            InlineKeyboardButton("✂️", callback_data=f"rps1v1_{msg_id}_scissors")
        ]
    ])
    
    await query.message.edit_text(text, reply_markup=keyboard)
    await query.answer("Game started! Make your choice!")

@app.on_callback_query(filters.regex(r"^rps1v1_(\d+)_(rock|paper|scissors)"))
async def rps_1v1_choice(_, query: CallbackQuery):
    """Handle 1v1 RPS choices"""
    data = query.data.split('_')
    msg_id = int(data[1])
    choice = data[2]
    user_id = query.from_user.id
    
    if msg_id not in rps_games:
        await query.answer("Game expired!", show_alert=True)
        return
    
    game = rps_games[msg_id]
    
    # Record choice
    if user_id == game['player1']:
        if game['player1_choice']:
            await query.answer("You already chose!", show_alert=True)
            return
        game['player1_choice'] = choice
        await query.answer(f"You chose {choice}! ✅", show_alert=False)
    elif user_id == game['player2']:
        if game['player2_choice']:
            await query.answer("You already chose!", show_alert=True)
            return
        game['player2_choice'] = choice
        await query.answer(f"You chose {choice}! ✅", show_alert=False)
    else:
        await query.answer("Not your game!", show_alert=True)
        return
    
    # Check if both chose
    if game['player1_choice'] and game['player2_choice']:
        p1_choice = game['player1_choice']
        p2_choice = game['player2_choice']
        emojis = {'rock': '🪨', 'paper': '📄', 'scissors': '✂️'}
        
        # Determine winner
        if p1_choice == p2_choice:
            result = "🤝 **It's a Tie!**"
        elif (p1_choice == 'rock' and p2_choice == 'scissors') or \
             (p1_choice == 'paper' and p2_choice == 'rock') or \
             (p1_choice == 'scissors' and p2_choice == 'paper'):
            result = f"🎉 **{game['player1_name']} Wins!**"
        else:
            result = f"🎉 **{game['player2_name']} Wins!**"
        
        text = (
            f"✊✋✌️ **Rock Paper Scissors**\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 {game['player1_name']}: {emojis[p1_choice]}\n"
            f"👤 {game['player2_name']}: {emojis[p2_choice]}\n\n"
            f"{result}"
        )
        
        await query.message.edit_text(text)
        del rps_games[msg_id]

# ==========================================
# ℹ️ MODULE INFO
# ==========================================
print("✅ MINI-GAMES MODULE LOADED (Tic Tac Toe + RPS)")
