import logging
from telegram import Bot, Update, ParseMode
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
user_collection = db["users"]  # Collection for users who started the bot
group_collection = db["groups"]  # Collection for groups where bot is present

# Fetch OWNER_ID and SUDO_ID from config.py
OWNER_ID = config.OWNER_ID
SUDO_USERS = config.SUDO_ID  # Can be a list or set, for multiple sudo users

# Function to fetch all users who started the bot
def get_all_users():
    return user_collection.find()  # Fetches all users who have started the bot

# Function to fetch all groups where the bot is active
def get_all_groups():
    return group_collection.find()  # Fetches all group chats

# Function to fetch all sudo users from MongoDB and config.py
def get_sudo_users():
    # Sudo users from MongoDB
    sudo_users_from_db = [user["user_id"] for user in user_collection.find()]
    # Adding sudo users from config.py to the list
    sudo_users = set(sudo_users_from_db + SUDO_USERS)
    return sudo_users

# Function to get the message content from a reply (whether it is text, audio, video, or emoji)
def get_reply_content(update: Update):
    reply = update.message.reply_to_message
    if not reply:
        return None, "No message to reply to."

    # Extract content based on the message type
    if reply.text:
        return reply.text, "text"
    elif reply.audio:
        return reply.audio, "audio"
    elif reply.video:
        return reply.video, "video"
    elif reply.sticker:
        return reply.sticker, "sticker"
    elif reply.document:
        return reply.document, "document"
    elif reply.emoji:
        return reply.text, "emoji"  # For emoji, the content is just text
    return None, "Unsupported message type"

# Broadcasting function
def broadcast_message(bot: Bot, message_content: str, send_to_users=True, send_to_groups=True):
    # Fetch users and groups from MongoDB
    users = get_all_users() if send_to_users else []
    groups = get_all_groups() if send_to_groups else []

    users_sent, groups_sent = 0, 0

    # Broadcasting to users
    for user in users:
        try:
            bot.send_message(user["chat_id"], message_content, parse_mode=ParseMode.MARKDOWN)
            users_sent += 1
        except TelegramError as e:
            logger.error(f"Failed to send message to user {user['chat_id']}: {e}")

    # Broadcasting to groups
    for group in groups:
        try:
            bot.send_message(group["chat_id"], message_content, parse_mode=ParseMode.MARKDOWN)
            groups_sent += 1
        except TelegramError as e:
            logger.error(f"Failed to send message to group {group['chat_id']}: {e}")

    return users_sent, groups_sent

# Command to broadcast (can be triggered by sudo users)
def broadcast_command(update: Update, context):
    user = update.effective_user

    # Fetch the list of sudo users
    sudo_users = get_sudo_users()

    # Check if the user is the owner or a sudo user
    if user.id != OWNER_ID and user.id not in sudo_users:
        update.message.reply_text("You do not have permission to broadcast messages.")
        return

    # Check for user-only broadcast
    send_to_users = False
    send_to_groups = True
    if len(context.args) > 0 and context.args[0] == "-user":
        send_to_users = True
        send_to_groups = False
        context.args = context.args[1:]

    # Ensure we have the message content
    if len(context.args) < 1:
        update.message.reply_text("Usage: /broadcast [optional -user] <message_content>")
        return

    message_content = " ".join(context.args)
    # Send the broadcast
    users_sent, groups_sent = broadcast_message(update.message.bot, message_content, send_to_users, send_to_groups)
    
    # Reply back with success info
    if send_to_users and not send_to_groups:
        update.message.reply_text(f"Message broadcasted to {users_sent} users.")
    elif not send_to_users and send_to_groups:
        update.message.reply_text(f"Message broadcasted to {users_sent} users and {groups_sent} groups.")
    elif send_to_users and send_to_groups:
        update.message.reply_text(f"Message broadcasted to {users_sent} users and {groups_sent} groups.")

# Command to broadcast by replying to a message
def reply_broadcast_command(update: Update, context):
    user = update.effective_user

    # Fetch the list of sudo users
    sudo_users = get_sudo_users()

    # Check if the user is the owner or a sudo user
    if user.id != OWNER_ID and user.id not in sudo_users:
        update.message.reply_text("You do not have permission to broadcast messages.")
        return

    # Get reply content
    message_content, message_type = get_reply_content(update)

    if message_content is None:
        update.message.reply_text("No supported content found in the replied message.")
        return

    # Check for user-only broadcast
    send_to_users = False
    send_to_groups = True
    if len(context.args) > 0 and context.args[0] == "-user":
        send_to_users = True
        send_to_groups = False
        context.args = context.args[1:]

    # Send the broadcast
    users_sent, groups_sent = broadcast_message(update.message.bot, message_content, send_to_users, send_to_groups)

    # Reply back with success info
    if send_to_users and not send_to_groups:
        update.message.reply_text(f"Message broadcasted to {users_sent} users.")
    elif not send_to_users and send_to_groups:
        update.message.reply_text(f"Message broadcasted to {users_sent} users and {groups_sent} groups.")
    elif send_to_users and send_to_groups:
        update.message.reply_text(f"Message broadcasted to {users_sent} users and {groups_sent} groups.")