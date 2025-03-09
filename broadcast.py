import logging
import asyncio
from telegram import Update
from telegram.ext import CallbackContext, CommandHandler
from telegram.error import TelegramError, RetryAfter
from pymongo import MongoClient
import config

# Logging setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# MongoDB Connection
client = MongoClient(config.MONGO_URI)
db = client[config.DB_NAME]
users_collection = db["users"]
groups_collection = db["active_groups"]

# Owner and Sudo Users
OWNER_ID = config.OWNER_ID
SUDO_USERS = config.SUDO_ID if isinstance(config.SUDO_ID, list) else [config.SUDO_ID]

# Functions to fetch users and groups
def get_all_users():
    return users_collection.find({}, {"user_id": 1, "_id": 0})

def get_all_groups():
    return groups_collection.find({}, {"group_id": 1, "_id": 0})

def get_sudo_users():
    sudo_users_from_db = [user["user_id"] for user in users_collection.find()]
    return list(set(sudo_users_from_db + SUDO_USERS))

# ============================
# Broadcast Function (FORWARDED / COPIED)
# ============================
async def broadcast_message(update: Update, context: CallbackContext, copy=True):
    user = update.effective_user
    sudo_users = get_sudo_users()

    if user.id != OWNER_ID and user.id not in sudo_users:
        return await update.message.reply_text("🚫 You do not have permission to broadcast.")

    reply = update.message.reply_to_message
    if not reply:
        return await update.message.reply_text("❗ Please reply to a message you want to broadcast.")

    send_to_users = send_to_groups = True

    # Optional args (like -group)
    args = context.args
    if args and args[0] == "-group":
        send_to_users = False
        send_to_groups = True
        args.pop(0)

    # Fetch lists
    users = list(get_all_users()) if send_to_users else []
    groups = list(get_all_groups()) if send_to_groups else []

    recipients = users + groups
    total_recipients = len(recipients)
    if total_recipients == 0:
        return await update.message.reply_text("❗ No users or groups found to broadcast.")

    users_sent = groups_sent = 0
    failed = 0

    status_message = await update.message.reply_text(f"🔄 Starting broadcast to {total_recipients} recipients...")

    # Loop through recipients
    for idx, recipient in enumerate(recipients, 1):
        chat_id = recipient.get("user_id") or recipient.get("group_id")

        try:
            # Copy message (clean) or forward (with sender info)
            if copy:
                await context.bot.copy_message(
                    chat_id=chat_id,
                    from_chat_id=reply.chat_id,
                    message_id=reply.message_id
                )
            else:
                await context.bot.forward_message(
                    chat_id=chat_id,
                    from_chat_id=reply.chat_id,
                    message_id=reply.message_id
                )

            # Count where the message was sent
            if "user_id" in recipient:
                users_sent += 1
            else:
                groups_sent += 1

        except RetryAfter as e:
            logger.warning(f"Flood wait for {e.retry_after} seconds on {chat_id}. Sleeping...")
            await asyncio.sleep(e.retry_after)
            continue

        except TelegramError as e:
            logger.error(f"Failed to send to {chat_id}: {e}")
            failed += 1
            continue

        # Update status every 20 messages
        if idx % 20 == 0:
            await status_message.edit_text(
                f"📤 Broadcasting...\n✅ Users: {users_sent}\n✅ Groups: {groups_sent}\n❌ Failed: {failed}\nProgress: {idx}/{total_recipients}"
            )

    # Final message
    await status_message.edit_text(
        f"✅ Broadcast completed!\n\n👤 Users sent: {users_sent}\n👥 Groups sent: {groups_sent}\n❌ Failed: {failed}"
    )

# ============================
# Text Broadcast (non-reply)
# ============================
async def broadcast_text(update: Update, context: CallbackContext):
    user = update.effective_user
    sudo_users = get_sudo_users()

    if user.id != OWNER_ID and user.id not in sudo_users:
        return await update.message.reply_text("🚫 You do not have permission to broadcast.")

    args = context.args
    if not args:
        return await update.message.reply_text("❗ Usage: `/broadcast [message]`\nOr reply to a message to broadcast.", parse_mode="Markdown")

    send_to_users = send_to_groups = True
    if args[0] == "-group":
        send_to_users = False
        send_to_groups = True
        args.pop(0)

    message_content = " ".join(args)

    # Fetch lists
    users = list(get_all_users()) if send_to_users else []
    groups = list(get_all_groups()) if send_to_groups else []

    recipients = users + groups
    total_recipients = len(recipients)

    if total_recipients == 0:
        return await update.message.reply_text("❗ No users or groups found to broadcast.")

    users_sent = groups_sent = 0
    failed = 0

    status_message = await update.message.reply_text(f"🔄 Starting text broadcast to {total_recipients} recipients...")

    # Loop through recipients
    for idx, recipient in enumerate(recipients, 1):
        chat_id = recipient.get("user_id") or recipient.get("group_id")

        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=message_content,
                parse_mode="Markdown",
                disable_web_page_preview=True
            )

            if "user_id" in recipient:
                users_sent += 1
            else:
                groups_sent += 1

        except RetryAfter as e:
            logger.warning(f"Flood wait for {e.retry_after} seconds on {chat_id}. Sleeping...")
            await asyncio.sleep(e.retry_after)
            continue

        except TelegramError as e:
            logger.error(f"Failed to send message to {chat_id}: {e}")
            failed += 1
            continue

        if idx % 20 == 0:
            await status_message.edit_text(
                f"📤 Broadcasting...\n✅ Users: {users_sent}\n✅ Groups: {groups_sent}\n❌ Failed: {failed}\nProgress: {idx}/{total_recipients}"
            )

    await status_message.edit_text(
        f"✅ Text Broadcast completed!\n\n👤 Users sent: {users_sent}\n👥 Groups sent: {groups_sent}\n❌ Failed: {failed}"
    )
