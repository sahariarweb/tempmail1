import os
import imaplib
import email
import re
import random
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# GitHub Secrets থেকে ডাটা পড়া
BOT_TOKEN = os.getenv("BOT_TOKEN")
GMAIL_USER = os.getenv("GMAIL_USER")
GMAIL_PASS = os.getenv("GMAIL_PASS")

bot = telebot.TeleBot(BOT_TOKEN)
user_sessions = {}

def create_case_variation(email_address):
    try:
        name, domain = email_address.split('@')
        varied_name = ''.join(random.choice([c.upper(), c.lower()]) for c in name)
        return f"{varied_name}@{domain}"
    except Exception as e:
        print(f"Error: {e}")
        return email_address

def get_latest_otp():
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(GMAIL_USER, GMAIL_PASS)
        mail.select("inbox")

        status, messages = mail.search(None, 'ALL')
        mail_ids = messages[0].split()

        if not mail_ids:
            mail.logout()
            return None

        latest_id = mail_ids[-1]
        status, data = mail.fetch(latest_id, '(RFC822)')

        for response_part in data:
            if isinstance(response_part, tuple):
                msg = email.message_from_bytes(response_part[1])
                
                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            body = part.get_payload(decode=True).decode(errors="ignore")
                            break
                else:
                    body = msg.get_payload(decode=True).decode(errors="ignore")

                otp_match = re.search(r'\b\d{4,8}\b', body)
                mail.logout()
                
                otp_code = otp_match.group(0) if otp_match else "Not explicitly detected"
                return otp_code, body[:300]
                
        mail.logout()
        return None
    except Exception as e:
        print(f"IMAP Error: {e}")
        return None

@bot.message_handler(commands=['start', 'new_email'])
def send_varied_email(message):
    chat_id = message.chat.id
    
    varied_email = create_case_variation(GMAIL_USER)
    user_sessions[chat_id] = varied_email

    markup = InlineKeyboardMarkup()
    refresh_btn = InlineKeyboardButton("🔄 Refresh / Get OTP", callback_data="check_otp")
    new_btn = InlineKeyboardButton("➕ Get Another Variation", callback_data="new_mail")
    markup.add(refresh_btn, new_btn)

    msg_text = (
        f"✨ **Your Custom Gmail Address:**\n"
        f"`{varied_email}`\n\n"
        f"📩 _Use this email for registration. Click **Refresh / Get OTP** to fetch verification codes._"
    )
    bot.send_message(chat_id, msg_text, parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    chat_id = call.message.chat.id

    if call.data == "new_mail":
        send_varied_email(call.message)

    elif call.data == "check_otp":
        if chat_id not in user_sessions:
            bot.answer_callback_query(call.id, "No active session! Click /start", show_alert=True)
            return

        bot.answer_callback_query(call.id, "Checking Gmail inbox...")

        result = get_latest_otp()

        if result:
            otp, snippet = result
            text = (
                f"🔑 **Latest OTP Code:** `{otp}`\n\n"
                f"📝 **Email Content Preview:**\n```{snippet}```"
            )
            bot.send_message(chat_id, text, parse_mode="Markdown")
        else:
            bot.send_message(chat_id, "❌ No mail received yet in your Gmail inbox.")

if __name__ == "__main__":
    print("Bot starting...")
    bot.infinity_polling()
