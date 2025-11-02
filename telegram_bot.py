# telegram_ai_quiz_bot_buttons.py
import os
from dotenv import load_dotenv
from openai import OpenAI
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import TelegramError
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters, ConversationHandler
)
import re
import httpx
from flask import Flask
import threading

# Define conversation states
GET_WORD = range(1)

# ---------------- WEB SERVER FOR RENDER ----------------
app = Flask(__name__)

@app.route('/')
def index():
    return "Bot is running!"

def run_flask_app():
    # Render provides the PORT environment variable.
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

# ---------------- LOAD ENV ----------------
load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")
HF_TOKEN = os.getenv("HF_TOKEN")

if not TOKEN or not HF_TOKEN:
    raise ValueError("TELEGRAM_TOKEN or HF_TOKEN is missing in your .env file!")

# ---------------- OPENAI CLIENT ----------------
client = OpenAI(
    base_url="https://router.huggingface.co/v1",
    api_key=HF_TOKEN
)

# ---------------- AI FUNCTION ----------------
def generate_ai_question():
    """
    Generates a multiple-choice English question using AI.
    Returns a tuple: (question_text, options_list, correct_answer)
    """
    try:
        completion = client.chat.completions.create(
            model="MiniMaxAI/MiniMax-M2:novita",
            messages=[
                {
                    "role": "user",
                    "content": (
                        "You are an English teacher bot that creates short multiple-choice questions.\n\n"
                        "Your task:\n"
                        "1️⃣ Create **ONE** English grammar or vocabulary question.\n"
                        "2️⃣ Provide exactly **three options**, labeled clearly as:\n"
                        "A) ...\nB) ...\nC) ...\n"
                        "3️⃣ At the end, write the correct answer on a new line as:\nAnswer: A\n\n"
                        "⚠️ Formatting rules (strict):\n"
                        "- Use capital letters A), B), C) exactly — no lowercase, no bullets.\n"
                        "- Do NOT include explanations or extra text.\n"
                        "- Keep the question short (1–2 lines).\n"
                        "- Example format:\n"
                        "Question: Choose the correct word.\nA) go\nB) goes\nC) going\nAnswer: B"
                    )
                }
            ],
            timeout=15.0,  # Add a 15-second timeout
        )
        message = completion.choices[0].message.content.strip()

        # Extract the correct answer
        match = re.search(r"Answer[:\s]*([A-C])", message, re.IGNORECASE)
        answer = match.group(1).upper() if match else None

        # Remove the answer from the question text
        question_text = re.sub(r"Answer[:\s]*[A-C]", "", message, flags=re.IGNORECASE).strip()

        # Extract options (assuming format "A) text", "B) text", "C) text")
        options = re.findall(r"([A-C])\)\s*(.+)", question_text)
        if options:
            options_dict = {opt[0]: opt[1] for opt in options}
        else:
            # fallback if AI didn't format nicely
            options_dict = {"A": "Option A", "B": "Option B", "C": "Option C"}

        # Remove option letters from question text
        question_text = re.sub(r"[A-C]\)\s*.+", "", question_text).strip()

        return question_text, options_dict, answer
    except Exception as e:
        print("Error generating AI question:", e)
        return "⚠️ Could not generate a question right now.", {"A": "A", "B": "B", "C": "C"}, None

# ---------------- DICTIONARY FUNCTION ----------------
async def get_word_definition(word: str):
    """
    Fetches the definition of a word from the DictionaryAPI.
    Returns a formatted string with the definition or an error message.
    """
    url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()  # Raise an exception for bad status codes
            data = response.json()

            # Format the response
            definition_text = f"📖 **{data[0]['word']}**\n\n"
            for meaning in data[0]['meanings']:
                definition_text += f"*{meaning['partOfSpeech']}*\n"
                for i, definition in enumerate(meaning['definitions'][:2]):  # Max 2 definitions per part of speech
                    definition_text += f"{i+1}. {definition['definition']}\n"
                    if 'example' in definition:
                        definition_text += f"   _Example: {definition['example']}_\n"
                definition_text += "\n"
            return definition_text

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return f"😕 Sorry, I couldn't find a definition for **{word}**."
        else:
            return "⚠️ An error occurred while fetching the definition."
    except Exception:
        return "⚠️ An error occurred. Please try again."


# ---------------- COMMAND HANDLERS ----------------
async def dictionary_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the dictionary conversation and asks for a word."""
    await update.message.reply_text("Please send me the word you'd like to define.")
    return GET_WORD

async def get_definition_from_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Fetches the definition for the word provided by the user."""
    word = update.message.text
    await update.message.reply_text(f"⏳ Searching for the definition of **{word}**...", parse_mode='Markdown')
    
    definition = await get_word_definition(word)
    await update.message.reply_text(definition, parse_mode='Markdown')
    
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels and ends the conversation."""
    await update.message.reply_text("Operation cancelled.")
    return ConversationHandler.END



async def _send_question(update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    question, options, answer = generate_ai_question()
    if answer is None:
        await context.bot.send_message(chat_id=chat_id, text=question)
        return

    context.user_data["current_question"] = question
    context.user_data["current_answer"] = answer

    keyboard = [
        [InlineKeyboardButton(f"{key}: {value}", callback_data=key)] for key, value in options.items()
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await context.bot.send_message(chat_id=chat_id, text=question, reply_markup=reply_markup)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Hello! Ready to learn English? Type /learn to start the quiz! /stop to stop it and /dictionary to learn the meaning of the word.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "💡 I am your AI English teacher! Use /learn to get a question, /stop to stop the quiz. /dictionary to learn the meaning of the word."
    )

async def learn_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ Generating your English question...")
    await _send_question(update, context, update.message.chat_id)


async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("current_question", None)
    context.user_data.pop("current_answer", None)
    await update.message.reply_text("🛑 Quiz stopped. Type /learn to start again.")

# ---------------- CALLBACK QUERY HANDLER ----------------
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    selected = query.data
    correct = context.user_data.get("current_answer")

    if not correct:
        await query.edit_message_text("⚠️ No active question. Type /learn to start a quiz.")
        return

    if selected == correct:
        await query.message.reply_text("✅ Correct! Well done!")
    else:
        await query.message.reply_text(f"❌ Not quite. The correct answer was {correct}.")

    context.user_data.pop("current_question", None)
    context.user_data.pop("current_answer", None)

    # Generate next question
    await query.message.reply_text("⏳ Generating your next English question...")
    try:
        await _send_question(update, context, query.message.chat_id)
    except TelegramError as e:
        print(f"Error sending next question: {e}")
        await query.message.reply_text("⚠️ Could not generate the next question right now. Please try /learn again.")

# ---------------- ERROR HANDLER ----------------
async def error(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"Update {update} caused the following error: {context.error}")

# ---------------- MAIN ----------------
if __name__ == "__main__":
    # Start the Flask app in a separate thread
    flask_thread = threading.Thread(target=run_flask_app)
    flask_thread.daemon = True
    flask_thread.start()

    print("Starting AI English quiz bot with buttons...")
    app = Application.builder().token(TOKEN).build()

    # Set up the conversation handler for the dictionary
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("dictionary", dictionary_start)],
        states={
            GET_WORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_definition_from_user)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv_handler)

    # Other command handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("learn", learn_command))
    app.add_handler(CommandHandler("stop", stop_command))

    # Callback query handler for button clicks
    app.add_handler(CallbackQueryHandler(button_handler))

    # Message handler for fallback text
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, lambda u, c: u.message.reply_text(
        "🤔 I didn't understand. Use the buttons or /learn to start."
    )))

    # Error handler
    app.add_error_handler(error)

    print("Polling...")
    app.run_polling(poll_interval=3)
