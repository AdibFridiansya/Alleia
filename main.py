import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import pytz
import asyncio
from dotenv import load_dotenv

from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)
from apscheduler.schedulers.background import BackgroundScheduler

from memory_manager import get_user_session, save_user_session, append_kaiwa_history
from partikel_data import PARTIKEL_DRILLS
from ai_service import (
    generate_kana_reading,
    evaluate_translation,
    generate_drill_prompt,
    chat_kaiwa_with_history
)

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TARGET_CHAT_ID = os.getenv("TELEGRAM_USER_ID")
TIMEZONE = os.getenv("TIMEZONE", "Asia/Jakarta")
PORT = int(os.environ.get("PORT", 8080))

# Web server port binding untuk Render health check
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Bot is alive!")
        
    def log_message(self, format, *args):
        return

def run_health_server():
    server = HTTPServer(("0.0.0.0", PORT), HealthCheckHandler)
    server.serve_forever()

def get_main_keyboard():
    keyboard = [
        ["🎯 Drill Partikel (Rumpang)", "✍️ Drill Terjemah (ID -> JP)"],
        ["💬 Kaiwa (Chat Romaji)", "🛑 Selesai / Menu Utama (/end)"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_chat.id
    sess = get_user_session(user_id)
    sess["mode"] = "IDLE"
    save_user_session(user_id, sess)

    msg = (
        f"Konnichiwa! Bot Asisten Bahasa Jepang siap menemani belajar.\n"
        f"ID Telegram Anda: `{user_id}`\n\n"
        "Silakan pilih menu langsung menggunakan tombol di bawah:\n"
        "• 🎯 **Drill Partikel**: Latihan mengisi partikel kalimat rumpang (Otomatis Next)\n"
        "• ✍️ **Drill Terjemah**: Menerjemahkan kalimat ID ke JP (Otomatis Next)\n"
        "• 💬 **Kaiwa**: Ngobrol santai format Romaji + arti (Senpai mengingat obrolan Anda)\n"
        "• Ketik `/end` kapan saja untuk keluar ke menu utama."
    )
    await update.message.reply_text(msg, reply_markup=get_main_keyboard(), parse_mode="Markdown")

async def end_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_chat.id
    sess = get_user_session(user_id)
    sess["mode"] = "IDLE"
    sess["drill_target"] = ""
    save_user_session(user_id, sess)

    await update.message.reply_text(
        "Sesi selesai. Kembali ke menu utama. Silakan pilih menu di bawah:",
        reply_markup=get_main_keyboard()
    )

# --- Sub-fitur 1: Drill Partikel Rumpang ---
async def send_next_partikel(update: Update, user_id: int):
    sess = get_user_session(user_id)
    idx = sess.get("partikel_idx", 0)
    
    if idx >= len(PARTIKEL_DRILLS):
        sess["partikel_idx"] = 0
        idx = 0

    q = PARTIKEL_DRILLS[idx]
    keyboard = [[opt] for opt in q["options"]]
    keyboard.append(["🛑 Selesai / Menu Utama (/end)"])
    markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    text = (
        f"🎯 **Drill Partikel (Soal {idx + 1}/{len(PARTIKEL_DRILLS)})**\n\n"
        f"Kalimat:\n`{q['sentence']}`\n\n"
        f"{q['question']}\n"
        "Pilih tombol jawaban di bawah:"
    )
    await update.message.reply_text(text, reply_markup=markup, parse_mode="Markdown")

# --- Sub-fitur 2: Drill Terjemah ID -> JP ---
async def send_next_drill_translation(update: Update, user_id: int):
    await update.message.reply_text("Menyiapkan kalimat latihan berikutnya...")
    kalimat_id = generate_drill_prompt()
    sess = get_user_session(user_id)
    sess["drill_target"] = kalimat_id
    save_user_session(user_id, sess)

    keyboard = [["🛑 Selesai / Menu Utama (/end)"]]
    markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    text = (
        "✍️ **Drill Terjemahan (ID -> JP)**\n\n"
        "Terjemahkan ke Bahasa Jepang:\n"
        f"👉 **'{kalimat_id}'**\n\n"
        "*(Boleh tulis menggunakan Romaji, Hiragana, atau Kanji)*"
    )
    await update.message.reply_text(text, reply_markup=markup, parse_mode="Markdown")

# --- Central Message Handler ---
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_chat.id
    text = update.message.text.strip()
    sess = get_user_session(user_id)
    mode = sess.get("mode", "IDLE")

    # Deteksi tombol kembali
    if text in ["🛑 Selesai / Menu Utama (/end)", "/end"]:
        await end_handler(update, context)
        return

    # Pemilihan Menu Awal
    if text == "🎯 Drill Partikel (Rumpang)":
        sess["mode"] = "PARTIKEL"
        save_user_session(user_id, sess)
        await send_next_partikel(update, user_id)
        return

    elif text == "✍️ Drill Terjemah (ID -> JP)":
        sess["mode"] = "DRILL"
        save_user_session(user_id, sess)
        await send_next_drill_translation(update, user_id)
        return

    elif text == "💬 Kaiwa (Chat Romaji)":
        sess["mode"] = "KAIWA"
        save_user_session(user_id, sess)
        
        keyboard = [["🛑 Selesai / Menu Utama (/end)"]]
        markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        greeting = (
            "Konnichiwa! Kyou wa dou deshita ka? Genki desu ka?\n"
            "(Halo! Bagaimana hari Anda hari ini? Apakah sehat?)\n\n"
            "Silakan ketik balasan Anda santai saja. Ketik /end jika ingin selesai."
        )
        append_kaiwa_history(user_id, "model", greeting)
        await update.message.reply_text(greeting, reply_markup=markup)
        return

    # Proses Sesuai Mode Aktif
    if mode == "PARTIKEL":
        idx = sess.get("partikel_idx", 0)
        current_q = PARTIKEL_DRILLS[idx]

        if text == current_q["answer"]:
            hasil = "✅ **Benar sekali!**\n\n"
        else:
            hasil = f"❌ **Kurang tepat.** Jawaban benar: `{current_q['answer']}`\n\n"

        penjelasan = f"{hasil}💡 **Catatan:**\n{current_q['explanation']}"
        await update.message.reply_text(penjelasan, parse_mode="Markdown")

        sess["partikel_idx"] = (idx + 1) % len(PARTIKEL_DRILLS)
        save_user_session(user_id, sess)
        await send_next_partikel(update, user_id)

    elif mode == "DRILL":
        target_id = sess.get("drill_target", "")
        if not target_id:
            await send_next_drill_translation(update, user_id)
            return

        await update.message.reply_text("Sedang mengevaluasi terjemahan Anda...")
        evaluasi = evaluate_translation(target_id, text)
        await update.message.reply_text(evaluasi, parse_mode="Markdown")

        await send_next_drill_translation(update, user_id)

    elif mode == "KAIWA":
        await update.message.reply_text("Senpai sedang mengetik...")
        history = sess.get("kaiwa_history", [])
        
        reply = chat_kaiwa_with_history(history, text)
        
        append_kaiwa_history(user_id, "user", text)
        append_kaiwa_history(user_id, "model", reply)

        keyboard = [["🛑 Selesai / Menu Utama (/end)"]]
        markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text(reply, reply_markup=markup)

    else:
        await update.message.reply_text(
            "Silakan pilih menu latihan pada tombol di bawah:",
            reply_markup=get_main_keyboard()
        )

# Pengiriman Terjadwal Otomatis (Reminder Bacaan Kana Jam 12.00 dan 20.00)
def auto_send_kana(app, topic: str):
    target = os.getenv("TELEGRAM_USER_ID")
    if not target or target == "2005":
        return
    kana_text = generate_kana_reading(topic)
    pesan = (
        "⏰ **Pengingat Bacaan Kana Hari Ini**\n"
        "────────────────────\n\n"
        f"{kana_text}\n\n"
        "────────────────────\n"
        "Luangkan waktu 1 menit untuk membaca teks kana di atas dengan tenang."
    )
    try:
        loop = app.loop if hasattr(app, "loop") else asyncio.get_event_loop()
        asyncio.run_coroutine_threadsafe(
            app.bot.send_message(chat_id=int(target), text=pesan, parse_mode="Markdown"),
            loop
        )
    except Exception as e:
        print(f"Gagal push bacaan: {e}")

def main():
    if not TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN belum diset di environment variables!")

    threading.Thread(target=run_health_server, daemon=True).start()

    app = ApplicationBuilder().token(TOKEN).build()

    scheduler = BackgroundScheduler(timezone=pytz.timezone(TIMEZONE))
    scheduler.add_job(auto_send_kana, "cron", hour=12, minute=0, args=[app, "kegiatan kantor dan jam istirahat"])
    scheduler.add_job(auto_send_kana, "cron", hour=20, minute=0, args=[app, "pengujian software, bug, dan hardware"])
    scheduler.start()

    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("end", end_handler))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), message_handler))

    print(f"Bot revisi aktif. Server listening port {PORT}...")
    app.run_polling()

if __name__ == "__main__":
    main()
