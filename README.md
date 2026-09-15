# Instadanmusiqavdyukla - Telegram Bot

Ushbu bot Instagram, TikTok, YouTube tarmoqlaridan media yuklash, musiqalarni qidirish va videolarni dumaloq video ("krujochek") formatiga aylantirish uchun mo'ljallangan.

## Asosiy Imkoniyatlar
1. **Video yuklash**: Instagram Reels/Post, TikTok (suv belgisiz), YouTube.
2. **Audio/MP3 ajratish**: Har qanday videodan musiqa ajratib berish.
3. **Musiqa qidirish**: Shunchaki qo'shiq nomi yoki ijrochini yozing.
4. **Dumaloq video (/dumaloq)**:
   - Videoga reply qilib `/dumaloq` deb yozilsa
   - Yoki `/dumaloq <havola>` yuborilsa
   - Yoki video yuborilgandagi tugma bosilsa, FFmpeg orqali 1:1 formatdagi Telegram Video Note yaratiladi.

## O'rnatish va Ishga tushirish
1. Kutubxonalarni o'rnatish:
   ```bash
   pip install -r requirements.txt
   ```
2. Ishga tushirish:
   - `run_bot.bat` faylini ikki marta bosing, yoki:
   ```bash
   python main.py
   ```

## Sozlamalar
`.env` faylida:
- `BOT_TOKEN` — Telegram Bot tokeni
- `PROXY` (ixtiyoriy) — Agar serverda proksi kerak bo'lsa (masalan `http://127.0.0.1:1080`)
