"""
Telegram Bot for counting invitations in chat
Telegram çatda çagyryşlary hasaplaýan bot
Author: Your Name
Version: 2.0 - Fixed permissions
"""

import logging
import sqlite3
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ChatMemberHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters
from telegram.constants import ParseMode

# ==================== CONFIGURATION ====================
BOT_TOKEN = "8655710933:AAE_Dxtc-6wXd20De6STHVvqtBjuFhAnoHA"  # Replace with your bot token
CHAT_ID = -1003877320935  # Replace with your chat ID

# Logging configuration
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==================== DATABASE ====================
class Database:
    def __init__(self):
        self.conn = sqlite3.connect('invite_stats.db', check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.create_tables()
    
    def create_tables(self):
        # Table for inviters statistics
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS inviters (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                invite_count INTEGER DEFAULT 0,
                last_invite_date TIMESTAMP
            )
        ''')
        # Table for invited users (prevents double counting)
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS invited_users (
                user_id INTEGER PRIMARY KEY,
                invited_by INTEGER,
                invite_date TIMESTAMP,
                FOREIGN KEY (invited_by) REFERENCES inviters (user_id)
            )
        ''')
        self.conn.commit()
    
    def add_invite(self, inviter_id, new_user_id, inviter_data):
        """Add new invitation to stats"""
        # Check if user was already invited
        self.cursor.execute('SELECT user_id FROM invited_users WHERE user_id = ?', (new_user_id,))
        if self.cursor.fetchone():
            return False
        
        # Save invited user
        self.cursor.execute('''
            INSERT INTO invited_users (user_id, invited_by, invite_date)
            VALUES (?, ?, ?)
        ''', (new_user_id, inviter_id, datetime.now()))
        
        # Update inviter's count
        self.cursor.execute('''
            INSERT INTO inviters (user_id, username, first_name, last_name, invite_count, last_invite_date)
            VALUES (?, ?, ?, ?, 1, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username = excluded.username,
                first_name = excluded.first_name,
                last_name = excluded.last_name,
                invite_count = invite_count + 1,
                last_invite_date = excluded.last_invite_date
        ''', (
            inviter_id,
            inviter_data.get('username', ''),
            inviter_data.get('first_name', ''),
            inviter_data.get('last_name', ''),
            datetime.now()
        ))
        
        self.conn.commit()
        return True
    
    def get_top_inviters(self, limit=10):
        """Get top inviters"""
        self.cursor.execute('''
            SELECT user_id, username, first_name, last_name, invite_count
            FROM inviters
            ORDER BY invite_count DESC
            LIMIT ?
        ''', (limit,))
        return self.cursor.fetchall()
    
    def get_user_stats(self, user_id):
        """Get stats for specific user"""
        self.cursor.execute('''
            SELECT invite_count FROM inviters WHERE user_id = ?
        ''', (user_id,))
        result = self.cursor.fetchone()
        return result[0] if result else 0
    
    def reset_stats(self):
        """Reset all statistics (admins only)"""
        self.cursor.execute('DELETE FROM invited_users')
        self.cursor.execute('DELETE FROM inviters')
        self.conn.commit()

# Initialize database
db = Database()

# ==================== PERMISSION CHECK ====================

async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Check if user is admin in the chat"""
    try:
        chat_member = await context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
        return chat_member.status in ['administrator', 'creator']
    except:
        return False

# ==================== COMMAND HANDLERS ====================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command"""
    await update.message.reply_text(
        "🇹🇲 **Salam! Men çaga goşulanlary hasaplaýan bot**\n\n"
        "📊 **Hemmeler üçin buýruklar:**\n"
        "/top - iň köp çagyranlary görkez\n"
        "/men - meniň statistikam\n\n"
        "👑 **Adminler üçin:**\n"
        "/reset - statistika sifrlemek\n\n"
        "⚡️ Men çata kim näçe adam goşandygyny awtomatiki hasaplaýaryn!",
        parse_mode=ParseMode.MARKDOWN
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Help command"""
    await update.message.reply_text(
        "🔍 **Men nähili işleýärin?**\n"
        "Men her bir täze agzany yzarlaýaryn we ony kim goşandygyny ýazga alýaryn.\n\n"
        "📌 **Hemmeler üçin buýruklar:**\n"
        "/top - iň köp çagyranlaryň ilkinji 10-sy\n"
        "/men - sen näçe adam çagyrdyň\n\n"
        "👑 **Adminler üçin buýruklar:**\n"
        "/reset - statistika sifrlemek\n\n"
        "⚠️ **Bellik:**\n"
        "• Men diňe goşulandan soňky çagyryşlary hasaplaýaryn\n"
        "• Bot çatda admin bolmaly\n"
        "• Her bir ulanyjy diňe bir gezek hasaplanýar",
        parse_mode=ParseMode.MARKDOWN
    )

async def top_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show top inviters - доступно всем"""
    logger.info(f"Top command used by user {update.effective_user.id}")
    
    try:
        top_inviters = db.get_top_inviters(10)
        
        if not top_inviters:
            await update.message.reply_text("📊 Entek statistika ýok. Ilkinji bol!")
            return
        
        message = "🏆 **IŇ KÖP ÇAGYRANLAR** 🏆\n\n"
        
        for i, (user_id, username, first_name, last_name, count) in enumerate(top_inviters, 1):
            name = first_name or ""
            if last_name:
                name += f" {last_name}"
            if username:
                name += f" (@{username})"
            
            if i == 1:
                medal = "🥇"
            elif i == 2:
                medal = "🥈"
            elif i == 3:
                medal = "🥉"
            else:
                medal = "👤"
            
            message += f"{medal} **{i}.** {name}: {count} adam\n"
        
        # Добавляем кнопку обновления
        keyboard = [[InlineKeyboardButton("🔄 Täzele", callback_data="refresh_top")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            message, 
            parse_mode=ParseMode.MARKDOWN, 
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.error(f"Error in top command: {e}")
        await update.message.reply_text("❌ Bir näsazlyk ýüze çykdy. Täzeden synanyşyň.")

async def mystats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user's personal stats - доступно всем"""
    logger.info(f"Men command used by user {update.effective_user.id}")
    
    try:
        user = update.effective_user
        count = db.get_user_stats(user.id)
        
        message = (
            f"📊 **Seniň statistikanyň**\n\n"
            f"👤 {user.first_name}"
        )
        if user.username:
            message += f" (@{user.username})"
        
        message += f"\n\n✅ Çagyran adamlaryň: **{count}**"
        
        await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        logger.error(f"Error in men command: {e}")
        await update.message.reply_text("❌ Bir näsazlyk ýüze çykdy. Täzeden synanyşyň.")

async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reset statistics - только для админов"""
    logger.info(f"Reset command used by user {update.effective_user.id}")
    
    try:
        # Проверяем, админ ли пользователь
        if not await is_admin(update, context):
            await update.message.reply_text("❌ Bu buýruk diňe adminler üçin!")
            return
        
        # Сбрасываем статистику
        db.reset_stats()
        await update.message.reply_text("✅ Statistika üstünlikli sifrlendi!")
        
        # Отправляем уведомление в чат
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"👑 Admin {update.effective_user.first_name} statistika sifrledi!"
        )
    except Exception as e:
        logger.error(f"Error in reset command: {e}")
        await update.message.reply_text("❌ Bir näsazlyk ýüze çykdy. Täzeden synanyşyň.")

# ==================== EVENT HANDLERS ====================

async def track_new_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Track new members and count invitations"""
    
    if not update.chat_member:
        return
    
    try:
        old_status = update.chat_member.old_chat_member.status
        new_status = update.chat_member.new_chat_member.status
        
        # Only count when someone becomes a member
        if new_status == 'member' and old_status != 'member':
            inviter = update.chat_member.from_user
            new_member = update.chat_member.new_chat_member.user
            
            # Don't count bots
            if new_member.is_bot:
                return
            
            inviter_data = {
                'username': inviter.username,
                'first_name': inviter.first_name,
                'last_name': inviter.last_name
            }
            
            success = db.add_invite(inviter.id, new_member.id, inviter_data)
            
            if success:
                invite_count = db.get_user_stats(inviter.id)
                # Optional notification
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=f"🎉 {new_member.first_name} çata goşuldy! Ony {inviter.first_name} çagyrdy (indi {invite_count} adam)",
                    parse_mode=ParseMode.HTML
                )
    except Exception as e:
        logger.error(f"Error tracking new member: {e}")

# ==================== BUTTON HANDLER ====================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button presses"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "refresh_top":
        try:
            top_inviters = db.get_top_inviters(10)
            
            if not top_inviters:
                await query.edit_message_text("📊 Entek statistika ýok.")
                return
            
            message = "🏆 **IŇ KÖP ÇAGYRANLAR** 🏆\n\n"
            
            for i, (user_id, username, first_name, last_name, count) in enumerate(top_inviters, 1):
                name = first_name or ""
                if last_name:
                    name += f" {last_name}"
                if username:
                    name += f" (@{username})"
                
                if i == 1:
                    medal = "🥇"
                elif i == 2:
                    medal = "🥈"
                elif i == 3:
                    medal = "🥉"
                else:
                    medal = "👤"
                
                message += f"{medal} **{i}.** {name}: {count} adam\n"
            
            keyboard = [[InlineKeyboardButton("🔄 Täzele", callback_data="refresh_top")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                message, 
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
        except Exception as e:
            logger.error(f"Error refreshing top: {e}")
            await query.edit_message_text("❌ Bir näsazlyk ýüze çykdy.")

# ==================== MESSAGE HANDLER (для отладки) ====================

async def debug_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отлавливает все сообщения для отладки"""
    logger.info(f"Message received: {update.message.text} from {update.effective_user.id}")
    # Не отвечаем, просто логируем

# ==================== MAIN ====================

def main():
    """Start the bot"""
    # Create application
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Add command handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("komek", help_command))
    app.add_handler(CommandHandler("top", top_command))
    app.add_handler(CommandHandler("men", mystats_command))
    app.add_handler(CommandHandler("reset", reset_command))
    
    # Add event handlers
    app.add_handler(ChatMemberHandler(track_new_members, ChatMemberHandler.CHAT_MEMBER))
    
    # Add button handler
    app.add_handler(CallbackQueryHandler(button_handler))
    
    # Debug handler - ловит все сообщения (поможет понять, видит ли бот команды)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, debug_messages))
    
    # Start bot
    print("🤖 Bot işe başlady... (Bot started...)")
    print("📝 Logging all messages for debugging...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
