# Nihongo Engineering Bot (Gemini Engine)

Bot Telegram untuk latihan percakapan bahasa Jepang kerja (*kaiwa*), pemahaman tata bahasa/partikel, dan latihan membaca kana terjadwal.

## Panduan Deploy ke Render.com
1. Buat repositori baru di GitHub (bisa Private atau Public), lalu push seluruh isi folder ini ke repositori tersebut.
2. Buka dashboard Render.com dan pilih **New + > Web Service**.
3. Hubungkan repositori GitHub yang baru dibuat.
4. Konfigurasi Service:
   - **Runtime:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python main.py`
   - **Instance Type:** Free
5. Masukkan **Environment Variables**:
   - `TELEGRAM_BOT_TOKEN`: Token bot Telegram dari BotFather
   - `GEMINI_API_KEY`: API Key dari Google AI Studio
   - `TELEGRAM_USER_ID`: Angka chat ID akun Telegram Anda (didapat saat kirim `/start` ke bot)
   - `TIMEZONE`: `Asia/Jakarta`
   - `PORT`: `8080`
6. Klik **Create Web Service**. Bot akan langsung aktif 24/7 di server cloud.
