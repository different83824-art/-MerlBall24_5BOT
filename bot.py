import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import speech_recognition as sr
from pydub import AudioSegment
from duckduckgo_search import DDGS  # Reliable, free AI backend

# Setup logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends a welcome message."""
    await update.message.reply_text("Hi! I'm your free AI assistant. Text me or send a voice note, and I will answer you!")

def ask_free_ai(prompt: str) -> str:
    """Queries DuckDuckGo's free AI chat tool."""
    try:
        with DDGS() as ddgs:
            # Using the stable meta-llama model provided freely by DuckDuckGo
            response = ddgs.ai_chat(keywords=prompt, model="meta-llama-3.1-70b")
            return response
    except Exception as e:
        logger.error(f"DuckDuckGo AI Error: {e}")
        return "I encountered an issue processing your request. Please try asking again!"

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles incoming text messages."""
    user_text = update.message.text
    await update.message.reply_chat_action(action="typing")
    
    # Get response from the reliable free AI
    ai_response = ask_free_ai(user_text)
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
            user_transcription = recognizer.recognize_google(audio_data)
        
        # 4. Feed transcription into our free AI brain
        ai_response = ask_free_ai(user_transcription)
        
        # 5. Format and reply
        reply = f"🗣️ *You said:* {user_transcription}\n\n🤖 *AI:* {ai_response}"
        await update.message.reply_text(reply, parse_mode="Markdown")
        
    except sr.UnknownValueError:
        await update.message.reply_text("Sorry, I couldn't hear the audio clearly. Please try speaking closer to the mic!")
    except Exception as e:
        logger.error(f"Voice Processing Error: {e}")
        await update.message.reply_text("An error occurred while handling your voice note.")
    finally:
        # Clean up temporary local files
        if os.path.exists(ogg_filename):
            os.remove(ogg_filename)
        if os.path.exists(wav_filename):
            os.remove(wav_filename)

def main():
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
