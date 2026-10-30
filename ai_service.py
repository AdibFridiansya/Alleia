import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

MODEL_NAME = "gemini-2.5-flash"

def get_client():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY belum disetel!")
    return genai.Client(api_key=api_key.strip())

def generate_kana_reading(topic: str = "keseharian kantor dan teknologi") -> str:
    prompt = f"""
Buat 1 paragraf pendek (3-4 kalimat ringkas level N4) tentang topik: {topic}.
SYARAT MUTLAK:
- Tulis HANYA dalam HIRAGANA dan KATAKANA dengan pemisahan spasi antar frasa/kata agar mudah dibaca pemula.
- JANGAN gunakan Kanji sama sekali.
- JANGAN sertakan terjemahan, salam pembuka, atau penutup. Langsung teks kananya saja.
"""
    try:
        client = get_client()
        res = client.models.generate_content(model=MODEL_NAME, contents=prompt)
        return res.text.strip()
    except Exception as e:
        return f"Gagal membuat bacaan kana: {str(e)}"

def evaluate_translation(target_id: str, user_jp: str) -> str:
    prompt = f"""
Pengguna diminta menerjemahkan kalimat Bahasa Indonesia ini ke Bahasa Jepang:
"{target_id}"

Jawaban Bahasa Jepang Pengguna:
"{user_jp}"

Instruksi Evaluasi:
1. Periksa apakah partikel, konjugasi kerja/sifat, dan kosakatanya tepat dan wajar untuk situasi kerja/sehari-hari.
2. Berikan penilaian ramah:
   - Evaluasi singkat (Benar / Kurang Tepat beserta alasannya).
   - Kalimat alami versi standar (disertai romaji dan arti).
   - Opsi formal/sopan jika ada perbedaan konteks.
Gunakan format ringkas, jelas, dan memotivasi.
"""
    try:
        client = get_client()
        res = client.models.generate_content(model=MODEL_NAME, contents=prompt)
        return res.text.strip()
    except Exception as e:
        return f"Gagal mengevaluasi: {str(e)}"

def generate_drill_prompt() -> str:
    prompt = """
Buat TEPAT SATU kalimat Bahasa Indonesia sederhana yang relevan untuk situasi kerja kantor atau rekayasa software/hardware (tingkat N4/N3 dasar).
Tujuannya adalah pengguna akan menerjemahkannya ke Bahasa Jepang.
Keluarkan HANYA kalimat Bahasa Indonesia tersebut tanpa tanda kutip, tanpa nomor, tanpa pembuka/penutup.
Contoh:
Saya sedang memperbaiki bug pada modul sensor.
"""
    try:
        client = get_client()
        res = client.models.generate_content(model=MODEL_NAME, contents=prompt)
        return res.text.strip()
    except Exception:
        return "Saya sedang memeriksa laporan pengujian sistem bersama senior."

def chat_kaiwa_with_history(history_list: list, user_message: str) -> str:
    system_instruction = (
        "Anda adalah rekan kerja senior (Senpai) ramah asal Jepang. "
        "ATURAN MUTLAK:
"
        "1. JANGAN PERNAH MENGGUNAKAN HURUF KANA ATAU KANJI DALAM BALASAN ANDA.
"
        "2. Tulis balasan HANYA DALAM DUA BAGIAN:
"
        "   - Bagian 1: Bahasa Jepang dalam format ROMAJI saja.
"
        "   - Bagian 2: Terjemahan Bahasa Indonesia di bawahnya.
"
        "3. Selalu tanyakan kabar atau perkembangan aktivitas/rutinitas harian pengguna.
"
        "4. Ingat dan tanggapi konteks riwayat percakapan sebelumnya.
"
        "Contoh format balasan:
"
        "Kyou wa dou deshita ka? Oshigoto wa junchou desu ka?
"
        "(Bagaimana hari Anda hari ini? Apakah pekerjaan berjalan lancar?)"
    )

    contents = []
    for msg in history_list[-8:]:
        role = "user" if msg["role"] == "user" else "model"
        contents.append(types.Content(role=role, parts=[types.Part.from_text(text=msg["text"])]))
    
    contents.append(types.Content(role="user", parts=[types.Part.from_text(text=user_message)]))

    try:
        client = get_client()
        res = client.models.generate_content(
            model=MODEL_NAME,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.7
            )
        )
        return res.text.strip()
    except Exception as e:
        return f"Gomen ne, sistem sedang sibuk: {str(e)}"
