import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import speech_recognition as sr
from pydub import AudioSegment
import g4f  # Open-source API-keyless AI client

# Setup logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends a welcome message."""
    await update.message.reply_text("Hi! I'm a completely free AI assistant. Text me or send a voice note, no API keys attached!")

async def ask_free_ai(prompt: str) -> str:
    """Queries a free, anonymous AI model without an API key."""
    try:
        response = g4f.ChatCompletion.create(
            model=g4f.models.gpt_4o, # Automatically routes to an available free provider
            messages=[{"role": "user", "content": prompt}],
        )
        return response
    except Exception as e:
        logger.error(f"AI Generation Error: {e}")
        return "I had trouble generating a response right now. Try again in a moment!"

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles text messages."""
    user_text = update.message.text
    await update.message.reply_chat_action(action="typing")
    
    ai_response = await ask_free_ai(user_text)
    await update.message.reply_text(ai_response)

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Downloads a voice note, converts it, transcribes it, and responds."""
    await update.message.reply_chat_action(action="typing")
    
    ogg_filename = f"{update.message.voice.file_id}.ogg"
    wav_filename = f"{update.message.voice.file_id}.wav"
    
    try:
        # 1. Download the Telegram voice note (.ogg format)
        voice_file = await context.bot.get_file(update.message.voice.file_id)
        await voice_file.download_to_drive(ogg_filename)
        
        # 2. Convert OGG to WAV using pydub
        audio = AudioSegment.from_file(ogg_filename, format="ogg")
        audio.export(wav_filename, format="wav")
        
        # 3. Transcribe audio using SpeechRecognition (Free Google Web Speech backend)
        recognizer = sr.Recognizer()
        with sr.AudioFile(wav_filename) as source:
            audio_data = recognizer.record(source)
            # Using the built-in free web search recognition API
            user_transcription = recognizer.recognize_google(audio_data)
        
        # 4. Feed transcription into our free AI brain
        ai_response = await ask_free_ai(user_transcription)
        
        # 5. Format and reply
        reply = f"🗣️ *You said:* {user_transcription}\n\n🤖 *AI:* {ai_response}"
        await update.message.reply_text(reply, parse_mode="Markdown")
        
    except sr.UnknownValueError:
        await update.message.reply_text("Sorry, I couldn't understand the audio clearly.")
    except Exception as e:
        logger.error(f"Voice Processing Error: {e}")
        await update.message.reply_text("An error occurred while handling your voice note.")
    finally:
        # Clean up temporary local files so your server doesn't run out of space
        if os.path.exists(ogg_filename):
            os.remove(ogg_filename)
        if os.path.exists(wav_filename):
            os.remove(wav_filename)

def main():
    # Only the Telegram Bot Token is required here!
    TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
    if not TELEGRAM_TOKEN:
        logger.error("TELEGRAM_TOKEN variable is missing!")
        return

    application = Application.builder().token(TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    application.add_handler(MessageHandler(filters.VOICE, handle_voice))

    application.run_polling()

if __name__ == '__main__':
    main()
