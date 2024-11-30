import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from groq import Groq

GROQ_API_KEY = "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"
TELEGRAM_BOT_TOKEN = "7769614636:AAEkdMwsfQjlyXEPjPbd3ZLPs_fe3mUKrx4"  # Make sure to use your actual token

client = Groq(api_key=GROQ_API_KEY)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello! I am EmpathAI - your online therapist. I am here to help you")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    fixed_prompt = "1. Respond with empathy and validate the user’s emotions without judgment. 2. Use open-ended questions to encourage the user to express their feelings and thoughts. 3. Provide general suggestions for self-care, coping strategies, or mindfulness practices when appropriate. 4. Do not offer medical, legal, or diagnostic advice. Redirect users to seek professional help if needed.5. If a user mentions self-harm or distressing thoughts, respond with care and suggest they contact a trusted person or professional helpline.  6. Avoid making assumptions and focus on understanding the user’s perspective. 7. Remind users that you are not a substitute for professional counseling but are here to support them. "
    completion = client.chat.completions.create(
        model="llama-3.1-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": fixed_prompt
            },
            {
                "role": "user",
                "content": user_message
            }
        ],
        temperature=0.7,
        max_tokens=150,
        top_p=1,
        stop=None
    )
    
    answer = completion.choices[0].message.content
    await update.message.reply_text(f"Answer: {answer}")

def main():
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    application.run_polling()

if __name__ == '__main__':
    main()
