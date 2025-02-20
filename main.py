import html
import logging
import re
import os
import asyncio
import time
import pymongo
from random import choice
from interstellar import *
from telegram import Update, Bot
from pyrogram import Client, filters
from pyrogram.types import Message
from telegram.utils.helpers import escape_markdown, mention_html
from telegram.utils.helpers import mention_markdown
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, ParseMode
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from pymongo import MongoClient
from broadcast import broadcast_command, reply_broadcast_command
from pymongo.errors import DuplicateKeyError
from config import LOGGER, MONGO_URI, DB_NAME, TELEGRAM_TOKEN, OWNER_ID, SUDO_ID, BOT_NAME, SUPPORT_ID, API_ID, API_HASH

app = Client("AutoDelete", bot_token=TELEGRAM_TOKEN, api_id=API_ID, api_hash=API_HASH)
print("INFO: ʙɪʟʟᴀ ɢᴜᴀʀᴅɪᴀɴ ɪs ᴏɴ ᴡᴀʏ")
app.start()
bot = app
# Initialize your Pyrogram Client your bot's ID
# Define the text variables
texts = {
    "sudo_5": "Current Sudo Users:\n",
    "sudo_6": "Other Sudo Users:\n",
    "sudo_7": "No sudo users found."
}

# Initialize logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Define StartTime at the beginning of the script
StartTime = time.time()

# MongoDB initialization
client = MongoClient(MONGO_URI)
db = client[DB_NAME]
users_collection = db['users']
active_groups_collection = db['active_groups']

# Define a list to store sudo user IDs
sudo_users = SUDO_ID.copy()  # Copy initial SUDO_ID list
sudo_users.append(OWNER_ID)  # Add owner to sudo users list initially

def get_readable_time(seconds: int) -> str:
    count = 0
    ping_time = ""
    time_list = []
    time_suffix_list = ["s", "m", "h", "days"]

    while count < 4:
        count += 1
        remainder, result = divmod(seconds, 60) if count < 3 else divmod(seconds, 24)
        if seconds == 0 and remainder == 0:
            break
        time_list.append(int(result))
        seconds = int(remainder)

    for x in range(len(time_list)):
        time_list[x] = str(time_list[x]) + time_suffix_list[x]
    if len(time_list) == 4:
        ping_time += time_list.pop() + ", "

    time_list.reverse()
    ping_time += ":".join(time_list)

    return ping_time

def help(update, context):
    user = update.effective_user
    mention = f"<a href='tg://user?id={user.id}'>{user.first_name}</a>"
    update.message.reply_text(f"ʙᴜᴅᴅʏ, {mention}! ᴘʟᴇᴀsᴇ ᴄʜᴇᴄᴋᴏᴜᴛ sᴜᴘᴘᴏʀᴛ ɢʀᴜᴘ ɴᴏᴡ", parse_mode='HTML')

# Track users when they start the bot
def start(update: Update, context: CallbackContext):
    user = update.effective_user
    user_data = {"user_id": user.id, "first_name": user.first_name}

    # Insert user into MongoDB if they are not already stored
    if not users_collection.find_one({"user_id": user.id}):
        users_collection.insert_one(user_data)

    update.message.reply_text("ʜᴏʟᴀ ᴀᴍɪɢᴏ!ᴋᴀɪsᴇ ʜᴏ ᴛʜɪᴋ ʜᴏ?,ʙɪʟʟᴀ ɪs ᴀᴄᴛɪᴠᴇ.")

    if update.effective_chat.type == "private":
        if len(args) >= 1:
            if args[0].lower() == "help":
                send_help(update.effective_chat.id, HELP_STRINGS)
            elif args[0].lower().startswith("ghelp_"):
                mod = args[0].lower().split("_", 1)[1]
                if not HELPABLE.get(mod, False):
                    return
                send_help(
                    update.effective_chat.id,
                    HELPABLE[mod].__help__,
                    InlineKeyboardMarkup(
                        [[InlineKeyboardButton(text="Back", callback_data="help_back")]]
                    ),
                )

            elif args[0].lower().startswith("stngs_"):
                match = re.match("stngs_(.*)", args[0].lower())
                chat = dispatcher.bot.getChat(match.group(1))

                if is_user_admin(chat, update.effective_user.id):
                    send_settings(match.group(1), update.effective_user.id, False)
                else:
                    send_settings(match.group(1), update.effective_user.id, True)

            elif args[0][1:].isdigit() and "rules" in IMPORTED:
                IMPORTED["rules"].send_rules(update, args[0], from_pm=True)

        else:
            first_name = update.effective_user.first_name
            update.effective_message.reply_text(
                PM_START_TEXT.format(escape_markdown(first_name), (PM_START_IMG), BOT_NAME),                              
                reply_markup=InlineKeyboardMarkup(buttons),
                parse_mode=ParseMode.MARKDOWN,
                timeout=60,
            )
    else:
        update.effective_message.reply_photo(
            PM_START_IMG,
            reply_markup=InlineKeyboardMarkup(buttons),
            caption="ʙɪʟʟᴀ ᴇᴅɪᴛ ɢᴜᴀʀᴅɪᴀɴ ɪs ᴀʟɪᴠᴇ ʙᴀʙʏ!\n<b>ᴜᴘᴛɪᴍᴇ :</b> <code>{}</code>".format(
                uptime
            ),
            parse_mode=ParseMode.HTML,
        )

def get_user_id(update: Update, context: CallbackContext):
    if len(context.args) != 1:
        update.message.reply_text("Usᴀɢᴇ: /id <ᴜsᴇʀɴᴀᴍᴇ>")
        return

    username = context.args[0]
    if not username.startswith('@'):
        update.message.reply_text("ᴘʟᴇᴀsᴡ ᴘʀᴏᴠɪᴅᴇ ᴀ ᴠᴀʟɪᴅ ᴜsᴇʀɴᴀᴍᴇ sᴛᴀʀᴛɪɴɢ ᴡɪᴛʜ '@'.")
        return
    try:
        user = context.bot.get_chat(username)
        user_id = user.id
        update.message.reply_text(f"Usᴇʀ Iᴅ ᴏғ {username} ɪs {user_id}.")
    except Exception as e:
        update.message.reply_text(f"ғᴀɪʟᴅᴇ ᴛᴏ ɢᴇᴛ ᴜsᴇʀ Iᴅ: {e}")
        logger.error(f"get_user_id error: {e}")

# Track groups where the bot is active
def track_groups(update: Update, context: CallbackContext):
    chat = update.effective_chat

    if chat.type in ["group", "supergroup"]:
        group_data = {"group_id": chat.id, "group_name": chat.title, "invite_link": "No invite link available"}

        if not active_groups_collection.find_one({"group_id": chat.id}):
            active_groups_collection.insert_one(group_data)

# Establish a MongoDB client connection using MONGO_URI
mongo_client = MongoClient(MONGO_URI)  # Use MONGO_URI from config.py

# Select the collection without specifying the database
authorized_users_collection = mongo_client["your_database_name"]["authorized_users"]  # Replace with your collection name

def check_edit(update, context):
    bot = context.bot

    # Check if the update is an edited message
    if update.edited_message:
        edited_message = update.edited_message
        
        # Get the chat ID and message ID
        chat_id = edited_message.chat_id
        message_id = edited_message.message_id
        
        # Get the user who edited the message
        user_id = edited_message.from_user.id
        
        # Create the mention for the user
        user_mention = f"<a href='tg://user?id={user_id}'>{html.escape(edited_message.from_user.first_name)}</a>"
        
        # Check if the user is authorized or admin (check against sudo users and MongoDB authorized users)
        if user_id not in sudo_users and authorized_users_collection.find_one({"user_id": user_id}) is None:
            # Ensure user is not an admin
            chat_member = bot.get_chat_member(chat_id, user_id)
            if chat_member.status not in ['administrator', 'creator']:  # Only delete if the user is not an admin
                # Delete the message if the user is neither authorized nor an admin
                bot.delete_message(chat_id=chat_id, message_id=message_id)
                
                # Send a message notifying about the deletion
                bot.send_message(chat_id=chat_id, text=f"{user_mention} Jᴜsᴛ ᴇᴅɪᴛᴇᴅ ᴀ ᴍᴇssᴀɢᴇ, ɪ ʜᴀᴠᴇ ᴅᴇʟᴇᴛᴇᴅ ᴛʜᴇʀɪ ᴇᴅɪᴛɪᴇᴅ ᴍᴇssᴀɢᴇ.", parse_mode='HTML')

# MongoDB collection for sudo users
sudo_users_collection = db['sudo_users']

def add_sudo(update: Update, context: CallbackContext):
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    # Check if the user is the owner
    if user.id != OWNER_ID:
        update.message.reply_text("Yᴏᴜ ᴅᴏɴ'ᴛ ʜᴀᴠᴇ ᴘᴇʀᴍɪssɪᴏɴ ᴛᴏ ᴜsᴇ ᴛʜɪs ᴄᴏᴍᴍᴀɴᴅ.")
        return
    
    # Check if a username or user ID is provided
    if len(context.args) != 1:
        update.message.reply_text("Usᴀɢᴇ: /addsudo <ᴜsᴇʀɴᴀᴍᴇ ᴏʀ ᴜsᴇʀ Iᴅ>")
        return
    
    sudo_user = context.args[0]
    
    # Resolve the user ID from username if provided
    try:
        sudo_user_obj = context.bot.get_chat_member(chat_id=chat_id, user_id=sudo_user)
        sudo_user_id = sudo_user_obj.user.id
    except Exception as e:
        update.message.reply_text(f"Fᴀɪʟᴇᴅ ᴛᴏ ʀᴇsᴏʟᴠᴇ ᴜsᴇʀ: {e}")
        return
    
    # Add sudo user ID to the database if not already present
    if sudo_users_collection.find_one({"user_id": sudo_user_id}):
        update.message.reply_text(f"{sudo_user_obj.user.username} ɪs ᴀʟʀᴇᴀᴅʏ ᴀ sᴜᴅᴏ ᴜsᴇʀ.")
        return
    
    # Add sudo user to the database
    try:
        sudo_users_collection.insert_one({
            "user_id": sudo_user_id,
            "username": sudo_user_obj.user.username,
            "first_name": sudo_user_obj.user.first_name
        })
        update.message.reply_text(f"ᴀᴅᴅᴇᴅ {sudo_user_obj.user.username} ᴀs ᴀ sᴜᴅᴏ ᴜsᴇʀ.")
    except Exception as e:
        update.message.reply_text(f"Fᴀɪʟᴇᴅ ʏᴏ ᴀᴅᴅ sᴜᴘᴇʀ ᴜsᴇʀ: {e}")

# Add the /rmsudo command to remove a sudo user
def rmsudo(update: Update, context: CallbackContext):
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    # Check if the user is the owner
    if user.id != OWNER_ID:
        update.message.reply_text("Yᴏᴜ ᴅᴏɴ'ᴛ ʜᴀᴠᴇ ᴘᴇʀᴍɪssɪᴏɴ ᴛᴏ ᴜsᴇ ᴛʜɪs ᴄᴏᴍᴍᴀɴᴅ.")
        return
    
    # Check if a username or user ID is provided
    if len(context.args) != 1:
        update.message.reply_text("Usᴀɢᴇ: /rmsudo <ᴜsᴇʀɴᴀᴍᴇ ᴏʀ ᴜsᴇʀ ɪᴅ>")
        return
    
    sudo_user = context.args[0]
    
    try:
        # Check if a username is provided (starts with '@')
        if sudo_user.startswith('@'):  # Username provided
            username = sudo_user.lstrip('@')
            
            # Resolve username to user_id (this will work only if the user is in the group)
            chat_member = context.bot.get_chat_member(chat_id, username=username)
            sudo_user_id = chat_member.user.id
        else:  # Direct user ID provided
            sudo_user_id = int(sudo_user)

        # Ensure the user is in the chat (use user_id)
        sudo_user_obj = context.bot.get_chat_member(chat_id, sudo_user_id)
        
    except Exception as e:
        update.message.reply_text(f"Fᴀɪʟᴇᴅ ᴛᴏ ʀᴇsᴏʟʙᴇ ᴜsᴇʀ: {e}")
        return
    
    # Now let's handle the removal of the sudo user from both the list and MongoDB
    if sudo_user_id in sudo_users:
        sudo_users.remove(sudo_user_id)

        # Try removing the sudo user from the MongoDB collection
        try:
            result = db.sudo_users.delete_one({"user_id": sudo_user_id})
            
            if result.deleted_count > 0:
                # Success: send confirmation with username (if exists) or ID
                if sudo_user_obj.user.username:
                    update.message.reply_text(f"Rᴇᴍᴘᴠᴇᴅ @{sudo_user_obj.user.username} ᴀs ᴀ sᴜᴘᴇʀ ᴜsᴇʀ.")
                else:
                    update.message.reply_text(f"Rᴇᴍᴏᴠᴇᴅ ᴜsᴇʀ ᴡɪᴛʜ Iᴅ {sudo_user_id} ᴀs ᴀ sᴜᴅᴏ ᴜsᴇʀ.")
            else:
                update.message.reply_text(f"Fᴀɪʟᴇᴅ ᴛᴏ ғɪɴᴅ ᴜsᴇʀ ᴡɪᴛʜ Iᴅ {sudo_user_id} ɪɴ ᴛʜᴇ Dʙ.")
                
        except Exception as e:
            update.message.reply_text(f"Fᴀɪʟᴇᴅ ᴛᴏ ʀᴇᴍᴏᴠᴇ ғʀᴏᴍ Mᴏɴɢᴏᴅʙ: {e}")
    else:
        if sudo_user_obj.user.username:
            update.message.reply_text(f"@{sudo_user_obj.user.username} ɪs ɴᴏᴛ ᴀ sᴜᴅᴏ ᴜsᴇʀ.")
        else:
            update.message.reply_text(f"User with ID {sudo_user_id} ɪs ɴᴏᴛ ᴀ sᴜᴅᴏ ᴜsᴇʀ.")


def sudo_list(update: Update, context: CallbackContext):
    # Check if the user is the owner
    if update.effective_user.id != OWNER_ID:
        update.message.reply_text("Yᴏᴜ ᴅᴏɴ'ᴛ ʜᴀᴠᴇ ᴘᴇʀᴍɪssɪᴏɴ ᴛᴏ ᴜsᴇ ᴛʜɪs ᴄᴏᴍᴍᴀɴᴅ.")
        return

    # Prepare the response message with SUDO_ID users
    text = "ʟɪsᴛ ᴏғ sᴜᴅᴏ ᴜsᴇʀs:\n"
    count = 1

    # Fetch sudo users from MongoDB
    sudo_users_cursor = sudo_users_collection.find({})
    
    for user_data in sudo_users_cursor:
        try:
            user_mention = mention_markdown(user_data["user_id"], user_data["first_name"])
            text += f"{count}. {user_mention}\n"
            count += 1
        except Exception as e:
            update.message.reply_text(f"Fᴀɪʟᴇᴅ ᴛᴏ ғᴇᴛᴄʜ sᴜᴘᴇʀ ᴜsᴇʀ ᴅᴇᴛᴀɪʟs: {e}")
            return

    if not text.strip():
        update.message.reply_text("Nᴏ sᴜᴘᴇʀ ᴜsᴇʀs ғᴏᴜɴᴅ.")
    else:
        update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
# MongoDB collection for authorized users
authorized_users_collection = db['authorized_users']

# Add the /auth command to authorize a user
def auth(update: Update, context: CallbackContext):
    user = update.effective_user
    chat_id = update.effective_chat.id
    reply_message = update.message.reply_to_message
    username = context.args[0] if len(context.args) > 0 else None
    
    if not username and not reply_message:
        update.message.reply_text("Usᴀɢᴇ: /auth <@ᴜsᴇʀɴᴀᴍᴇ> ᴏʀ ʀᴇᴘʟʏ ᴛᴏ ʜɪs/ʜᴇʀ ᴍᴇssᴀɢᴇ.")
        return
    
    if reply_message:
        user_to_auth = reply_message.from_user
    elif username:
        # Try to resolve the username to a user_id
        try:
            # Get chat member details using the username
            user_to_auth = context.bot.get_chat_member(chat_id=chat_id, user_id=username)
        except Exception as e:
            update.message.reply_text(f"Fᴀɪʟᴇᴅ ᴛᴏ ғɪɴᴅ ᴜsᴇʀ ᴛʜᴇʀᴇ {username}: {e}")
            return

    user_id = user_to_auth.id

    # Check if the user is already authorized
    if authorized_users_collection.find_one({"user_id": user_id}):
        update.message.reply_text(f"{user_to_auth.first_name} ɪs ᴀʟʀᴇᴀᴅʏ ᴀᴜᴛʜᴏʀɪᴢᴇᴅ.")
        return

    # Add to the database
    try:
        authorized_users_collection.insert_one({
            "user_id": user_id,
            "username": user_to_auth.username,
            "first_name": user_to_auth.first_name
        })
        update.message.reply_text(f"{user_to_auth.first_name} ʜᴀs ʙᴇᴇɴ ᴀᴜᴛʜᴏʀɪᴢᴇᴅ.")
    except DuplicateKeyError:
        update.message.reply_text(f"{user_to_auth.first_name} ɪs ᴀʟʀᴇᴀᴅʏ ɪɴ ʙɪʟʟᴀ's ᴍɪɴᴅ.")

# Add the /unauth command to unauthorize a user
def unauth(update: Update, context: CallbackContext):
    user = update.effective_user
    chat_id = update.effective_chat.id
    reply_message = update.message.reply_to_message
    username = context.args[0] if len(context.args) > 0 else None
    
    if not username and not reply_message:
        update.message.reply_text("Usᴀɢᴇ: /unauth <@ᴜsᴇʀɴᴀᴍᴇ> ᴏʀ ʀᴇᴘʟʏ ᴛᴏ ʜɪs/ʜᴇʀ ᴍᴇssᴀɢᴇ.")
        return
    
    if reply_message:
        user_to_unauth = reply_message.from_user
    elif username:
        try:
            user_to_unauth = context.bot.get_chat(username)
        except Exception as e:
            update.message.reply_text(f"Fᴀɪʟᴇᴅ ᴛᴏ ғɪɴᴅ ᴜsᴇʀ {username}: {e}")
            return

    user_id = user_to_unauth.id

    # Check if the user is authorized
    if not authorized_users_collection.find_one({"user_id": user_id}):
        update.message.reply_text(f"{user_to_unauth.first_name} ɪs ɴᴏᴛ ᴀᴜᴛʜᴏʀɪᴢᴇᴅ.")
        return

    # Remove from the database
    authorized_users_collection.delete_one({"user_id": user_id})
    update.message.reply_text(f"{user_to_unauth.first_name} ʜᴀs ʙᴇᴇɴ ᴜɴᴀᴜᴛʜᴏʀɪᴢᴇᴅ.")
    
def send_stats(update: Update, context: CallbackContext):
    user = update.effective_user
    
    if user.id != OWNER_ID:
        update.message.reply_text("Yᴏᴜ ᴅᴏɴ'ᴛ ʜᴀᴠᴇ ᴘᴇʀᴍɪssɪᴏɴ ᴛᴏ ᴜsᴇ ᴛʜɪs ᴄᴏᴍᴍᴀɴᴅ.")
        return
    
    try:
        users_count = users_collection.count_documents({})
        chat_count = active_groups_collection.count_documents({})  # Use correct collection
        
        stats_msg = f"Tᴏᴛᴀʟ Usᴇʀs: {users_count}\nTᴏᴛᴀʟ Gʀᴏᴜᴘs: {chat_count}\n"
        update.message.reply_text(stats_msg)
    except Exception as e:
        logger.error(f"ᴇʀʀᴏʀ ɪɴ send_stats ғᴜɴᴄᴛɪᴏɴ: {e}")
        update.message.reply_text("Fᴀɪʟᴇᴅ ᴛᴏ ғᴇᴛᴄʜ sᴛᴀs.")


def fetch_active_groups_from_db():
    try:
        active_groups = list(active_groups_collection.find({}, {"group_id": 1, "group_name": 1, "invite_link": 1, "_id": 0}))
        return active_groups
    except Exception as e:
        print(f"Fᴀɪʟᴇᴅ ᴛᴏ ᴄᴏɴɴᴇᴄᴛ ᴛᴏ MᴏɴɢᴏDB: {e}")
        return None

# Handler for /activegroups command
def list_active_groups(update: Update, context: CallbackContext):
    if update.message.from_user.id != OWNER_ID:
        update.message.reply_text("You don't have permission to use this command.")
        return

    active_groups_from_db = fetch_active_groups_from_db()

    if not active_groups_from_db:
        update.message.reply_text("Tʜᴇ ʙɪʟʟᴀ ᴇɢ ɪs ɴᴏᴛ ᴀᴄᴛɪᴠᴇ ɪɴ ᴀɴʏ ɢʀᴏᴜᴘs ᴏʀ ғᴀɪʟᴇᴅ ᴛᴏ ᴄᴏᴍɴᴇᴄᴛ ᴛᴏ MᴏɴɢᴏDB.")
        return

    group_list_msg = "Aᴄᴛɪᴠᴇ ɢʀᴏᴜᴘ ᴡʜᴇʀᴇ ᴛʜᴇ ʙɪʟʟᴀ ɪs ᴄᴜʀʀᴇɴᴛʟʏ ᴀᴄᴛɪᴠᴇ:\n"
    for group in active_groups_from_db:
        group_name = group.get("group_name", "Unknown Group")
        invite_link = group.get("invite_link", "Nᴏ ɪɴᴠɪᴛᴀᴛɪᴏɴ ᴀᴠᴀɪʟᴀʙʟᴅ")

        if invite_link != "ɪɴᴠɪᴛᴀᴛᴀᴛɪᴏɴ ᴀᴠᴀɪʟᴀʙʟᴇ":
            group_list_msg += f"- <a href='{invite_link}'>[{group_name}]</a>\n"
        else:
            group_list_msg += f"- {group_name}\n"

    update.message.reply_text(group_list_msg, parse_mode="HTML")

# Global list to store active cloned bots
active_cloned_bots = []

# Update the clone function to track active cloned bots
def clone(update: Update, context: CallbackContext):
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    # Check if the user is the owner
    if user.id != OWNER_ID:
        update.message.reply_text("ʏᴏᴜ ᴀʀᴇ ɴᴏᴛ ᴀᴜᴛʜᴏʀɪᴢᴇᴅ ᴛᴏ ᴜsᴇ ᴛʜɪs ᴄᴍᴅ.")
        return

    # Get the bot token from the command
    if len(context.args) != 1:
        update.message.reply_text("𝗨𝘀𝗮𝗴𝗲: /clone <ʏᴏᴜʀ ʙᴏᴛ ᴛᴏᴋᴇɴ (ᴄᴏɴᴛᴀᴄᴛ ᴅᴇᴠᴇ)>")
        return

    new_bot_token = context.args[0]

    try:
        # Create a new bot instance
        new_bot = Bot(token=new_bot_token)
        new_bot_info = new_bot.get_me()

        # Clone all handlers from the main bot to the new bot
        clone_updater = Updater(token=new_bot_token, use_context=True)
        clone_dispatcher = clone_updater.dispatcher

        # Add existing handlers to the cloned bot
        clone_dispatcher.add_handler(CommandHandler("start", start))
        clone_dispatcher.add_handler(MessageHandler(Filters.update.edited_message, check_edit))
        clone_dispatcher.add_handler(CommandHandler("addsudo", add_sudo))
        clone_dispatcher.add_handler(CommandHandler("sudolist", sudo_list))
        clone_dispatcher.add_handler(CommandHandler("stats", send_stats))
        clone_dispatcher.add_handler(CommandHandler("clone", clone))

        # Start the cloned bot
        clone_updater.start_polling()

        # Track the active cloned bot
        active_cloned_bots.append({
            "bot_username": new_bot_info.username,
            "bot_token": new_bot_token
        })

        update.message.reply_text(
            f"sᴜᴄᴄᴇssғᴜʟʟʏ ᴄʟᴏɴᴇᴅ ᴛʜᴇ ʙᴏᴛ {new_bot_info.username} ({new_bot_info.id})."
        )

    except Exception as e:
        update.message.reply_text(f"ғᴀɪʟᴇᴅ ᴛᴏ ᴄʟᴏɴᴇ ᴛʜᴇ ʙᴏᴛ: {e}")

# Command to list active cloned bots
def list_active_cloned_bots(update: Update, context: CallbackContext):
    if update.effective_user.id != OWNER_ID:
        update.message.reply_text("Yᴏᴜ ᴅᴏɴ'ᴛ ʜᴀᴠᴇ ᴘᴇʀᴍɪssɪᴏɴ ᴛᴏ ᴜsᴇ ᴛʜɪs ᴄᴏᴍᴍᴀɴᴅ.")
        return

    # Generate a list of active cloned bots
    if not active_cloned_bots:
        update.message.reply_text("Nᴏ ᴄʟᴏɴᴇs ᴀʀᴇ ᴀᴄᴛɪᴠᴇ ᴀᴛ ᴛʜᴇ ᴍᴏᴍᴇɴᴛ.")
        return

    active_bots_msg = "Aᴄᴛɪᴠᴇ Cʟᴏɴᴇᴅ Bɪʟʟᴀ:\n"
    for bot in active_cloned_bots:
        active_bots_msg += f"- @{bot['bot_username']}\n"

    update.message.reply_text(active_bots_msg)

# Command handler for /getid
def get_id(update: Update, context: CallbackContext):
    bot, args = context.bot, context.args
    message = update.effective_message
    chat = update.effective_chat
    msg = update.effective_message

    # Attempt to extract user ID from args (if available)
    user_id = None
    if len(args) >= 1:
        try:
            user_id = int(args[0])
        except ValueError:
            user_id = None  # In case the provided arg is not a valid ID
    # If no valid user ID found in args, check if it's a reply message
    if not user_id and msg.reply_to_message:
        user_id = msg.reply_to_message.from_user.id

    if user_id:
        if msg.reply_to_message and msg.reply_to_message.forward_from:
            user1 = message.reply_to_message.from_user
            user2 = message.reply_to_message.forward_from

            msg.reply_text(
                f"<b>ᴛᴇʟᴇɢʀᴀᴍ ɪᴅ:</b>,"
                f"• {html.escape(user2.first_name)} - <code>{user2.id}</code>.\n"
                f"• {html.escape(user1.first_name)} - <code>{user1.id}</code>.",
                parse_mode=ParseMode.HTML,
            )
        else:
            user = bot.get_chat(user_id)
            msg.reply_text(
                f"{html.escape(user.first_name)}'s ɪᴅ ɪs <code>{user.id}</code>.",
                parse_mode=ParseMode.HTML,
            )
    else:
        if chat.type == "private":
            msg.reply_text(
                f"ʏᴏᴜʀ ᴜsᴇʀ ɪᴅ ɪs <code>{chat.id}</code>.", parse_mode=ParseMode.HTML
            )
        else:
            msg.reply_text(
                f"ᴛʜɪs ɢʀᴏᴜᴩ's ɪᴅ ɪs <code>{chat.id}</code>.", parse_mode=ParseMode.HTML
            )

@app.on_message(filters.command("id"))
async def userid(client, message):
    chat = message.chat
    your_id = message.from_user.id
    message_id = message.message_id
    reply = message.reply_to_message

    text = f"**Message ID:** `{message_id}`\n"
    text += f"**Your ID:** `{your_id}`\n"
    
    if not message.command:
        message.command = message.text.split()

    if len(message.command) == 2:
        try:
            split = message.text.split(None, 1)[1].strip()
            user_id = (await client.get_users(split)).id
            text += f"**User ID:** `{user_id}`\n"
        except Exception:
            return await eor(message, text="Tʜɪs ᴜsᴇʀ ᴅᴏᴇsɴ'ᴛ ᴇxɪsᴛᴀ ᴛʜᴇʀᴇ.")

    text += f"**Chat ID:** `{chat.id}`\n\n"
    if not getattr(reply, "empty", True):
        id_ = reply.from_user.id if reply.from_user else reply.sender_chat.id
        text += (
            f"**Replied Message ID:** `{reply.message_id}`\n"
        )
        text += f"**Replied User ID:** `{id_}`"

    await eor(
        message,
        text=text,
        disable_web_page_preview=True,
        parse_mode="md",
            )

# Function to send message to SUPPORT_ID group
def main():

    if SUPPORT_ID is not None and isinstance(SUPPORT_ID, str):
        try:
            dispatcher.bot.sendphoto(
                f"{SUPPORT_ID}",
                photo=PM_START_IMG,               
                caption=f"""
ʜᴇʟʟᴏ ɪ ᴀᴍ sᴛᴀʀᴛᴇᴅ ᴛᴏ ᴍᴀɴᴀɢᴇ ᴇᴅɪᴛᴇᴅ ᴍᴇssᴀɢᴇ𝘀 ! ɪ"ᴍ ᴅᴇᴠʟᴏᴘᴇᴅ ʙʏ @ifeelraam""",
                parse_mode=ParseMode.MARKDOWN,
            )
        except Unauthorized:
            LOGGER.warning(
                f"ʙɪʟʟᴀ ɪsɴ'ᴛ aᴀʙʟᴇ ᴛᴏ sᴇɴᴅ ᴍᴇssᴀɢᴇ ᴛᴏ {SUPPORT_ID}, ɢᴏ ᴀɴᴅ ᴄʜᴇᴄᴋ!"
            )
        except BadRequest as e:
            LOGGER.warning(e.message)    
    # Create the Updater and pass it your bot's token
    updater = Updater(token=TELEGRAM_TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    # Register handlers
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(MessageHandler(Filters.update.edited_message, check_edit))
    dispatcher.add_handler(MessageHandler(Filters.chat_type.groups, track_groups))
    dispatcher.add_handler(CommandHandler("addsudo", add_sudo))
    dispatcher.add_handler(CommandHandler("rmsudo", rmsudo))
    dispatcher.add_handler(CommandHandler("sudolist", sudo_list))
    dispatcher.add_handler(CommandHandler("activegroups", list_active_groups))
    dispatcher.add_handler(CommandHandler("clone", clone))
    dispatcher.add_handler(CommandHandler("listactiveclones", list_active_cloned_bots))
    dispatcher.add_handler(CommandHandler("auth", auth))
    dispatcher.add_handler(CommandHandler("unauth", unauth))
    dispatcher.add_handler(CommandHandler("stats", send_stats))
    dispatcher.add_handler(CommandHandler("broadcast", broadcast_command))
    dispatcher.add_handler(CommandHandler("replybroadcast", reply_broadcast_command))
    dispatcher.add_handler(CommandHandler("getid", get_id))
    dispatcher.add_handler(CommandHandler("id", get_user_id))
    dispatcher.add_handler(CommandHandler("help", help))
   
    # Start the Bot
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
    # Start the bot
