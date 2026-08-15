import os
import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)
from google import genai

logging.basicConfig(level=logging.INFO)

# ============================================================
# DO NOT PUT YOUR ACTUAL KEYS HERE
# These names connect the code to Render Environment Variables.
# ============================================================

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
ADMIN_USER_ID = int(os.environ["ADMIN_USER_ID"])

# Add CHANNEL_ID later after we find it.
CHANNEL_ID = os.environ.get("CHANNEL_ID")

gemini = genai.Client(api_key=GEMINI_API_KEY)

pending_posts = {}


def is_admin(user_id):
    return user_id == ADMIN_USER_ID


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    await update.message.reply_text(
        "🤖 OPG Post Designer\n\n"
        "Commands:\n"
        "/design - Create a post\n"
        "/getid - Get chat/channel ID\n"
        "/start - Show menu"
    )


async def getid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user and not is_admin(update.effective_user.id):
        return

    chat = update.effective_chat

    if not chat:
        return

    await update.message.reply_text(
        f"📌 CHAT INFORMATION\n\n"
        f"Title: {chat.title or 'Private Chat'}\n"
        f"Type: {chat.type}\n"
        f"Chat ID: {chat.id}"
    )


async def design(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    text = update.message.text.replace("/design", "", 1).strip()

    if not text:
        await update.message.reply_text(
            "Example:\n\n"
            "/design\n"
            "App: YouTube\n"
            "Version: 8.6.80.137\n"
            "Size: 29.3 MB\n"
            "Features: No Ads, Stable"
        )
        return

    prompt = f"""
You are a professional Telegram post designer.

Turn the user's information into a premium Telegram channel post.

STYLE:
- Clean professional Telegram update style
- Attractive headings
- Good spacing
- Useful emojis
- Separators
- Easy to read on mobile
- Premium APK/app update channel appearance
- Similar structure to the user's preferred reference style
- Do not copy another channel's exact wording

RULES:
- Do not invent information.
- Do not invent download links.
- Do not invent features.
- Do not invent versions or prices.
- Keep the user's information accurate.
- Return only the finished post.
- No explanations.
- No code fences.

USER INFORMATION:
{text}
"""

    try:
        response = await gemini.aio.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )

        result = response.text.strip()

        pending_posts[update.effective_user.id] = result

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "✅ POST TO CHANNEL",
                    callback_data="post"
                ),
                InlineKeyboardButton(
                    "❌ CANCEL",
                    callback_data="cancel"
                ),
            ]
        ])

        await update.message.reply_text(
            "✨ PREVIEW\n\n" + result,
            reply_markup=keyboard
        )

    except Exception:
        logging.exception("Gemini error")

        await update.message.reply_text(
            "❌ Gemini could not generate the post."
        )


async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not is_admin(query.from_user.id):
        return

    user_id = query.from_user.id

    if query.data == "cancel":
        pending_posts.pop(user_id, None)

        await query.edit_message_text(
            "❌ Post cancelled."
        )
        return

    if query.data == "post":

        post = pending_posts.get(user_id)

        if not post:
            await query.edit_message_text(
                "❌ Preview expired. Create the post again."
            )
            return

        if not CHANNEL_ID:
            await query.edit_message_text(
                "❌ CHANNEL_ID is not configured yet.\n\n"
                "Use /getid inside your channel first."
            )
            return

        try:
            await context.bot.send_message(
                chat_id=CHANNEL_ID,
                text=post
            )

            pending_posts.pop(user_id, None)

            await query.edit_message_text(
                "✅ Successfully posted to your channel!"
            )

        except Exception:
            logging.exception("Channel posting error")

            await query.edit_message_text(
                "❌ Could not post to the channel.\n\n"
                "Check that OPG Post Designer is an administrator "
                "with permission to post messages."
            )


def main():

    app = (
        Application.builder()
        .token(TELEGRAM_BOT_TOKEN)
        .build()
    )

    app.add_handler(
        CommandHandler("start", start)
    )

    app.add_handler(
        CommandHandler("getid", getid)
    )

    app.add_handler(
        CommandHandler("design", design)
    )

    app.add_handler(
        CallbackQueryHandler(button)
    )

    print("OPG Post Designer is running...")

    app.run_polling()


if __name__ == "__main__":
    main()
