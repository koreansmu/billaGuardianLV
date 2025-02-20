import logging
from telegram import Update
from telegram.ext import CallbackContext
from telegram.error import TelegramError
from pymongo import MongoClient
import config

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

# MongoDB Connection
client = MongoClient(config.MONGO_URI)
db = client[config.DB_NAME]
users_collection = db["users"]  # Collection for users who started the bot
active_groups_collection = db["active_groups"]  # Collection for active groups

# Fetch OWNER_ID and SUDO_ID from config.py
OWNER_ID = config.OWNER_ID
SUDO_USERS = config.SUDO_ID  # List of sudo users

def get_all_users():
    return users_collection.find({}, {"user_id": 1, "_id": 0})  # Fetch only user_id

def get_all_groups():
    return active_groups_collection.find({}, {"group_id": 1, "_id": 0})  # Fetch only group_id

def get_sudo_users():
    sudo_users_from_db = [user["user_id"] for user in users_collection.find()]
    sudo_users = set(sudo_users_from_db + SUDO_USERS)
    return sudo_users

def broadcast_message(update: Update, message_content: str, send_to_users=True, send_to_groups=True):
    users = list(get_all_users()) if send_to_users else []
    groups = list(get_all_groups()) if send_to_groups else []

    users_sent, groups_sent = 0, 0
    
    logger.info(f"ɴᴏᴛɪғʏɪɴɢ ᴛᴏ {len(users)} ᴜsᴇʀs ᴀɴᴅ {len(groups)} ɢʀᴏᴜᴘs.")

    for user in users:
        try:
            update.message.bot.send_message(user["user_id"], message_content, parse_mode="Markdown")
            users_sent += 1
        except TelegramError as e:
            logger.error(f"Fᴀɪʟᴇᴅ ᴛᴏ sᴇɴᴅ ᴍᴇssᴀɢᴇ ᴛᴏ ᴜsᴇʀ {user['user_id']}: {e}")

    for group in groups:
        try:
            update.message.bot.send_message(group["group_id"], message_content, parse_mode="Markdown")
            groups_sent += 1
        except TelegramError as e:
            logger.error(f"ғᴀɪʟᴇᴅ ᴛᴏ sᴇɴᴅ ᴍᴇssᴀɢᴇ ᴛᴏ ɢʀᴏᴜᴘ {group['group_id']}: {e}")

    return users_sent, groups_sent

def broadcast_command(update: Update, context: CallbackContext):
    user = update.effective_user
    sudo_users = get_sudo_users()

    if user.id != OWNER_ID and user.id not in sudo_users:
        update.message.reply_text("Yᴏᴜ ᴅᴏ ɴᴏᴛ ʜᴀᴠᴇ ᴘᴇʀᴍɪssɪᴏᴍ ᴛᴏ ʙʀᴏᴀᴅᴄᴀsᴛ ʙɪᴛᴄʜ.")
        return

    send_to_users, send_to_groups = False, True
    if len(context.args) > 0 and context.args[0] == "-user":
        send_to_users = True
        send_to_groups = False
        context.args = context.args[1:]

    if len(context.args) < 1:
        update.message.reply_text("Usage: /broadcast [optional -user] <message_content>")
        return

    message_content = " ".join(context.args)
    users_sent, groups_sent = broadcast_message(update, message_content, send_to_users, send_to_groups)
    update.message.reply_text(f"ᴍᴇssᴀɢᴇ ɴᴏᴛɪғʏɪᴇᴅ ᴛᴏ {users_sent} ᴜsᴇʀs ᴀɴᴅ {groups_sent} ɢʀᴏᴜᴘs.")

def reply_broadcast_command(update: Update, context: CallbackContext):
    user = update.effective_user
    sudo_users = get_sudo_users()

    if user.id != OWNER_ID and user.id not in sudo_users:
        update.message.reply_text("Yᴏᴜ ᴅᴏ ɴᴏᴛ ʜᴀᴠᴇ ᴘᴇʀᴍɪssɪᴏᴍ ᴛᴏ ʙʀᴏᴀᴅᴄᴀsᴛ ʙɪᴛᴄʜ.")
        return

    reply = update.message.reply_to_message
    if not reply:
        update.message.reply_text("ᴛᴀɢ ᴏʀ ʀᴇᴘʟʏ ᴛᴏ ᴀ ᴍᴇssᴀɢᴇ ᴛᴏ ʙʀᴏᴀᴅᴄᴀsᴛ.")
        return

    message_content = reply.text or reply.caption
    if not message_content:
        update.message.reply_text("ᴀʜʜ ᴋɪᴅᴅ ᴜɴsᴜᴘᴘᴏʀᴛᴇᴅ ᴍᴇssᴀɢᴇ ᴛʏᴘᴇ.")
        return

    send_to_users, send_to_groups = False, True
    if len(context.args) > 0 and context.args[0] == "-user":
        send_to_users = True
        send_to_groups = False
        context.args = context.args[1:]

    users_sent, groups_sent = broadcast_message(update, message_content, send_to_users, send_to_groups)
    update.message.reply_text(f"ᴛᴀɢɢᴇᴅ ᴍᴇssᴀɢᴇ ʙʀᴏᴀᴅᴄᴀsᴛᴇᴅ ᴛᴏ {users_sent} ᴜsᴇʀs ᴀɴᴅ {groups_sent} ɢʀᴏᴜᴘs.")
