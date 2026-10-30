import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)
MODEL_NAME = "gemini-2.5-flash"

def get_kana_reading(topic: str = "situasi kantor dan teknologi") -> str:
    prompt = f"""
Buat 1 paragraf pendek (3-4 kalimat ringkas level N4) tentang topik: {topic}.
SYARAT MUTLAK:
- Tulis HANYA dalam HIRAGANA dan KATAKANA dengan pemisahan spasi antar frasa/kata agar mudah dibaca pemula.
- JANGAN gunakan Kanji sama sekali.
- JANGAN sertakan terjemahan, salam pembuka, atau penutup. Langsung berikan teks kananya saja.
"""
    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt
        )
        return response.text.strip()
    except Exception as e:
        return f"Gagal membuat bacaan kana: {str(e)}"

def chat_kaiwa(user_text: str) -> str:
    system_instruction = (
        "Anda adalah rekan kerja senior (Senpai) software/hardware engineer di Tokyo, Jepang. "
        "Tanggapi pesan pengguna dalam bahasa Jepang Teineigo (sopan kerja) yang wajar (tingkat N4-N3). "
        "Setelah respons percakapan bahasa Jepang selesai, buat garis pembatas '---' dan berikan evaluasi singkat dalam Bahasa Indonesia: "
        "1. Koreksi kesalahan partikel atau konjugasi jika ada. "
        "2. Rekomendasi kosakata teknis/kantor yang lebih lazim digunakan di lingkungan kerja Jepang."
    )
    
    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=user_text,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.7
            )
        )
        return response.text.strip()
    except Exception as e:
        return f"Maaf, terjadi kendala saat memproses jawaban: {str(e)}"
