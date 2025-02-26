import logging
from telegram import Update, InputMediaPhoto, InputMediaVideo, InputMediaAnimation, InputMediaDocument
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

def broadcast_message(update: Update, message_content: str, send_to_users=True, send_to_groups=True, reply=None):
    users = list(get_all_users()) if send_to_users else []
    groups = list(get_all_groups()) if send_to_groups else []

    logger.info(f"Found {len(users)} users and {len(groups)} groups to broadcast.")

    users_sent, groups_sent = 0, 0

    for recipient in users + groups:
        chat_id = recipient.get("user_id") or recipient.get("group_id")
        try:
            # If the message is a reply (i.e., contains media)
            if reply:
                if reply.photo:
                    update.message.bot.send_photo(
                        chat_id, 
                        reply.photo[-1].file_id, 
                        caption=message_content, 
                        parse_mode="Markdown", 
                        disable_web_page_preview=False
                    )
                elif reply.video:
                    update.message.bot.send_video(
                        chat_id, 
                        reply.video.file_id, 
                        caption=message_content, 
                        parse_mode="Markdown", 
                        disable_web_page_preview=False
                    )
                elif reply.animation:  # GIF or Animated Emojis
                    update.message.bot.send_animation(
                        chat_id, 
                        reply.animation.file_id, 
                        caption=message_content, 
                        parse_mode="Markdown", 
                        disable_web_page_preview=False
                    )
                elif reply.document:
                    update.message.bot.send_document(
                        chat_id, 
                        reply.document.file_id, 
                        caption=message_content, 
                        parse_mode="Markdown", 
                        disable_web_page_preview=False
                    )
                else:
                    update.message.bot.send_message(
                        chat_id, 
                        message_content, 
                        parse_mode="Markdown", 
                        disable_web_page_preview=False
                    )
            else:
                update.message.bot.send_message(
                    chat_id, 
                    message_content, 
                    parse_mode="Markdown", 
                    disable_web_page_preview=False
                )
            
            if chat_id in [user["user_id"] for user in users]:
                users_sent += 1
            else:
                groups_sent += 1

        except TelegramError as e:
            logger.error(f"Failed to send message to {chat_id}: {e}")

    logger.info(f"Broadcast completed: {users_sent} users, {groups_sent} groups.")
    return users_sent, groups_sent
  
def broadcast_command(update: Update, context: CallbackContext):
    user = update.effective_user
    sudo_users = get_sudo_users()

    if user.id != OWNER_ID and user.id not in sudo_users:
        update.message.reply_text("Yᴏᴜ ᴅᴏ ɴᴏᴛ ʜᴀᴠᴇ ᴘᴇʀᴍɪssɪᴏɴ ᴛᴏ ʙʀᴏᴀᴅᴄᴀsᴛ.")
        return

    send_to_users, send_to_groups = True, True
    if len(context.args) > 0 and context.args[0] == "-group":
        send_to_users = False
        send_to_groups = True
        context.args = context.args[1:]

    if len(context.args) < 1:
        update.message.reply_text(ǫ"Usᴀɢᴇ: /broadcast [ᴏᴘᴛɪᴏɴᴀʟ -group] <ᴍᴇssᴀɢᴇ_ᴄᴏɴᴛᴇɴᴛ>")
        return

    message_content = " ".join(context.args)
    users_sent, groups_sent = broadcast_message(update, message_content, send_to_users, send_to_groups)
    update.message.reply_text(f"ᴍᴇssᴀɢᴇ ᴛʀᴜᴍᴘʜᴇᴅ ᴛᴏ {users_sent} Usᴇʀs ᴀɴᴅ {groups_sent} ɢʀᴏᴜᴘs.")


def reply_broadcast_command(update: Update, context: CallbackContext):
    user = update.effective_user
    sudo_users = get_sudo_users()

    if user.id != OWNER_ID and user.id not in sudo_users:
        update.message.reply_text("Yᴏᴜ ᴅᴏ ɴᴏᴛ ʜᴀᴠᴇ ᴘᴇʀᴍɪssɪᴏɴ ᴛᴏ ʙʀᴏᴀᴅᴄᴀsᴛ.")
        return

    reply = update.message.reply_to_message
    if not reply:
        update.message.reply_text("ʀᴇᴘʟʏ ᴛᴏ ᴀ ᴍᴇssᴀɢᴇ ᴛᴏ ʙʀᴏᴀᴅᴄᴀsᴛ.")
        return

    message_content = reply.text or reply.caption
    if not message_content:
        update.message.reply_text("Uɴsᴜᴘᴘᴏʀᴛᴇᴅ ᴍᴇssᴀɢᴇ ᴛʏᴘᴇ.")
        return

    send_to_users, send_to_groups = True, True
    if len(context.args) > 0 and context.args[0] == "-group":
        send_to_users = False
        send_to_groups = True
        context.args = context.args[1:]

    users_sent, groups_sent = broadcast_message(update, message_content, send_to_users, send_to_groups, reply)
    update.message.reply_text(f"ᴍᴇssᴀɢᴇ ᴛʀᴜᴍᴘʜᴇᴅ ᴛᴏ  {users_sent} ᴜsᴇʀs ᴀɴᴅ {groups_sent} ɢʀᴏᴜᴘs.")
