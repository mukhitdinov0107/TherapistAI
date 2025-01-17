from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from groq import Groq
import os
import json
from datetime import datetime
from dotenv import load_dotenv
import asyncio

# Load environment variables
load_dotenv()

# Get API keys from environment variables
GROQ_API_KEY = os.getenv('GROQ_API_KEY')
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

if not GROQ_API_KEY or not TELEGRAM_BOT_TOKEN:
    raise ValueError("Missing required environment variables. Please check your .env file")

client = Groq(api_key=GROQ_API_KEY)

# File to store conversation history
HISTORY_FILE = 'conversation_history.json'

def load_conversation_history():
    try:
        with open(HISTORY_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_conversation_history(history):
    with open(HISTORY_FILE, 'w') as f:
        json.dump(history, f, indent=2)

# Load existing conversation history or create new one
conversation_history = load_conversation_history()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)  # Convert to string for JSON compatibility
    # Clear any existing conversation history
    conversation_history[user_id] = []
    save_conversation_history(conversation_history)
    
    await update.message.reply_text(
        "Hello! I am EmpathAI - your online therapist. I am here to help you. "
        "I'll remember our conversation to provide better support. "
        "Your chat history will be saved for continuity between sessions.\n\n"
        "Commands:\n"
        "/start - Start fresh conversation\n"
        "/reset - Clear conversation history"
    )

async def stream_response(message, completion):
    current_message = ""
    sent_message = await message.reply_text("...")
    buffer = ""
    update_threshold = 10  # Update every 10 characters
    
    try:
        for chunk in completion:
            if hasattr(chunk.choices[0], 'delta') and chunk.choices[0].delta.content:
                buffer += chunk.choices[0].delta.content
                # Update in larger chunks
                if len(buffer) >= update_threshold:
                    current_message += buffer
                    buffer = ""
                    try:
                        await sent_message.edit_text(current_message)
                    except Exception as e:
                        if "Message is not modified" not in str(e):
                            print(f"Error updating message: {e}")
        
        # Add any remaining buffer content
        if buffer:
            current_message += buffer
            try:
                await sent_message.edit_text(current_message)
            except Exception as e:
                if "Message is not modified" not in str(e):
                    print(f"Error in final update: {e}")
    
    except Exception as e:
        print(f"Error in streaming: {e}")
        if not current_message:
            current_message = "I apologize, but I encountered an error while generating the response. Please try again."
            await sent_message.edit_text(current_message)
    
    return current_message

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)  # Convert to string for JSON compatibility
    user_message = update.message.text
    current_time = datetime.now().isoformat()
    
    # Initialize conversation history for new users
    if user_id not in conversation_history:
        conversation_history[user_id] = []
    
    # Add user message to history with timestamp
    user_entry = {
        "role": "user",
        "content": user_message,
        "timestamp": current_time
    }
    conversation_history[user_id].append(user_entry)
    
    # Prepare conversation history for API
    messages = [
        {
            "role": "system",
            "content": """1. Respond with empathy and validate the user's emotions without judgment.
                        2. Use open-ended questions to encourage the user to express their feelings and thoughts.
                        3. Provide general suggestions for self-care, coping strategies, or mindfulness practices when appropriate.
                        4. Do not offer medical, legal, or diagnostic advice. Redirect users to seek professional help if needed.
                        5. If a user mentions self-harm or distressing thoughts, respond with care and suggest they contact a trusted person or professional helpline.
                        6. Avoid making assumptions and focus on understanding the user's perspective.
                        7. Remind users that you are not a substitute for professional counseling but are here to support them.
                        8. Use the conversation history to provide more contextual and personalized responses."""
        }
    ]
    
    # Add last 30 messages from history to maintain context
    history_messages = [
        {"role": msg["role"], "content": msg["content"]} 
        for msg in conversation_history[user_id][-30:]
    ]
    messages.extend(history_messages)
    
    try:
        # Create streaming completion
        completion = client.chat.completions.create(
            model="llama-3.1-70b-versatile",
            messages=messages,
            temperature=0.7,
            max_tokens=150,
            top_p=1,
            stream=True
        )
        
        # Stream the response and get the final message
        answer = await stream_response(update.message, completion)
        
        # Add assistant's response to history with timestamp
        assistant_entry = {
            "role": "assistant",
            "content": answer,
            "timestamp": datetime.now().isoformat()
        }
        conversation_history[user_id].append(assistant_entry)
        
        # Save updated history to file
        save_conversation_history(conversation_history)
    
    except Exception as e:
        print(f"Error in handle_text: {e}")
        await update.message.reply_text(
            "I apologize, but I encountered an error while processing your message. Please try again."
        )

async def reset_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    # Clear the user's conversation history
    conversation_history[user_id] = []
    save_conversation_history(conversation_history)
    await update.message.reply_text("Conversation history has been cleared. Starting fresh!")

def main():
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("reset", reset_conversation))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    # Ensure the conversation history file exists
    if not os.path.exists(HISTORY_FILE):
        save_conversation_history({})
    
    application.run_polling()

if __name__ == '__main__':
    main()
