import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import pytz
import asyncio
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from apscheduler.schedulers.background import BackgroundScheduler

from curriculum import CURRICULUM
from tracker import get_progress, update_progress
from ai_service import get_kana_reading, chat_kaiwa

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TARGET_CHAT_ID = os.getenv("TELEGRAM_USER_ID")
TIMEZONE = os.getenv("TIMEZONE", "Asia/Jakarta")
PORT = int(os.environ.get("PORT", 8080))

# Web Server minimalis untuk health check Render
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Nihongo Bot is active and running!")
        
    def log_message(self, format, *args):
        return

def run_health_server():
    server = HTTPServer(("0.0.0.0", PORT), HealthCheckHandler)
    server.serve_forever()

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_chat.id
    msg = (
        f"🤖 **Nihongo Engineering Assistant Aktif!**\n"
        f"ID Telegram Anda: `{user_id}`\n\n"
        "Perintah yang dapat digunakan:\n"
        "• `/materi` — Pelajari teori partikel/konjugasi unit aktif\n"
        "• `/drill` — Mulai latihan soal pemahaman\n"
        "• `/baca` — Minta teks latihan membaca kana instan\n"
        "• Kirim pesan teks langsung untuk latihan percakapan `/kaiwa` bersama Senpai."
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

async def materi_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prog = get_progress()
    unit_id = prog["current_unit"]
    unit_data = CURRICULUM.get(unit_id)
    if not unit_data:
        await update.message.reply_text("Semua unit kurikulum telah selesai dipelajari!")
        return
    await update.message.reply_text(unit_data["explanation"], parse_mode="Markdown")

async def drill_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prog = get_progress()
    unit_id = prog["current_unit"]
    idx = prog["drill_index"]
    unit_data = CURRICULUM.get(unit_id)

    if not unit_data or idx >= len(unit_data["drills"]):
        unit_id += 1
        idx = 0
        update_progress(unit=unit_id, drill_idx=idx, waiting=False)
        unit_data = CURRICULUM.get(unit_id)
        if not unit_data:
            await update.message.reply_text("🎉 Selamat, seluruh latihan yang tersedia telah tuntas!")
            return
        await update.message.reply_text(f"Maju ke {unit_data['title']}!")

    drill = unit_data["drills"][idx]
    update_progress(waiting=True)

    text = (
        f"🎯 **Drill {unit_data['title']} (Soal {idx + 1}/{len(unit_data['drills'])})**\n\n"
        f"{drill['question']}\n\n"
        f"{drill['options']}\n\n"
        "Ketik pilihan jawaban Anda (a / b / c):"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

async def baca_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Menyiapkan teks kana...")
    kana_text = get_kana_reading("keseharian kantor dan komunikasi teknis")
    pesan = (
        "📖 **Latihan Membaca Kana**\n"
        "────────────────────\n\n"
        f"{kana_text}\n\n"
        "────────────────────\n"
        "Bacalah perlahan per frasa untuk melatih kelancaran pelafalan Anda."
    )
    await update.message.reply_text(pesan, parse_mode="Markdown")

async def message_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prog = get_progress()
    user_text = update.message.text.strip()

    # Cek apakah sedang menjawab soal drill
    if prog.get("waiting_answer"):
        unit_data = CURRICULUM.get(prog["current_unit"])
        current_drill = unit_data["drills"][prog["drill_index"]]
        
        jawaban_user = user_text.lower()
        if jawaban_user in ["a", "b", "c"]:
            if jawaban_user == current_drill["answer"]:
                status = "✅ **Tepat sekali!**\n"
            else:
                status = f"❌ **Kurang tepat.** (Jawaban benar: {current_drill['answer']})\n"

            evaluasi = f"{status}\n💡 *Catatan:* {current_drill['note']}\n\nKetik `/drill` untuk lanjut ke soal berikutnya."
            update_progress(drill_idx=prog["drill_index"] + 1, waiting=False)
            await update.message.reply_text(evaluasi, parse_mode="Markdown")
            return

    # Sesi Kaiwa / Chatting percakapan
    await update.message.reply_text("Senpai sedang menyusun balasan...")
    reply = chat_kaiwa(user_text)
    await update.message.reply_text(reply)

# Fungsi pembungkus pengiriman jadwal otomatis via Background thread
def scheduled_push_sync(app, topic: str):
    target = os.getenv("TELEGRAM_USER_ID")
    if not target or target == "2005":
        return
    kana_text = get_kana_reading(topic)
    pesan = (
        "📖 **Sesi Membaca Kana Terjadwal**\n"
        "────────────────────\n\n"
        f"{kana_text}\n\n"
        "────────────────────\n"
        "Luangkan waktu membaca teks kana di atas sejenak."
    )
    try:
        # Jalankan coroutine kirim pesan ke event loop Telegram
        loop = app.loop if hasattr(app, "loop") else asyncio.get_event_loop()
        asyncio.run_coroutine_threadsafe(
            app.bot.send_message(chat_id=int(target), text=pesan, parse_mode="Markdown"),
            loop
        )
    except Exception as e:
        print(f"Gagal mengirim pesan terjadwal: {e}")

def main():
    if not TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN belum diset di environment variable!")

    # Jalankan server HTTP dummy di background thread
    threading.Thread(target=run_health_server, daemon=True).start()

    app = ApplicationBuilder().token(TOKEN).build()

    # Menggunakan BackgroundScheduler agar aman di Python 3.14
    scheduler = BackgroundScheduler(timezone=pytz.timezone(TIMEZONE))
    scheduler.add_job(scheduled_push_sync, "cron", hour=12, minute=0, args=[app, "kegiatan kantor dan jam istirahat"])
    scheduler.add_job(scheduled_push_sync, "cron", hour=20, minute=0, args=[app, "pengujian kode, bug software, dan sensor"])
    scheduler.start()

    # Daftarkan command handlers
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("materi", materi_handler))
    app.add_handler(CommandHandler("drill", drill_handler))
    app.add_handler(CommandHandler("baca", baca_handler))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), message_router))

    print(f"Bot aktif. Web server berjalan di port {PORT}...")
    app.run_polling()

if __name__ == "__main__":
    main()
