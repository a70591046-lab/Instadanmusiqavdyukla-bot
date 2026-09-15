import os
from pathlib import Path
from aiogram import Router, types, Bot, F
from aiogram.types import FSInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder

from services.downloader import DownloaderService

router = Router()

# Qidiruv natijalarini qisqa vaqt saqlash uchun kesh
SEARCH_CACHE = {}

import html
from database import add_user

async def handle_music_search_query(message: types.Message, query: str):
    status = await message.reply(f"🔍 \"{html.escape(query)}\" bo'yicha musiqa qidirilmoqda...")

    try:
        results = await DownloaderService.search_music_deezer(query, limit=5)
        if not results:
            await status.edit_text(f"😔 Kechirasiz, \"{html.escape(query)}\" bo'yicha musiqa topilmadi.\nIltimos, nomini boshqacharoq yozib ko'ring.")
            return

        text = f"🎶 <b>\"{html.escape(query)}\" bo'yicha topilgan natijalar:</b>\n\n"
        builder = InlineKeyboardBuilder()

        for idx, item in enumerate(results, start=1):
            dur_min = item['duration'] // 60
            dur_sec = item['duration'] % 60
            artist_safe = html.escape(item['artist'])
            title_safe = html.escape(item['title'])
            text += f"{idx}. <b>{artist_safe}</b> — {title_safe} <code>({dur_min}:{dur_sec:02d})</code>\n"

            # Keshga saqlash
            track_key = f"{item['id']}"
            SEARCH_CACHE[track_key] = item

            builder.button(text=f"⬇️ {idx}", callback_data=f"dl_music:{track_key}")

        builder.adjust(5)
        text += "\nYuklab olish uchun pastdagi raqamli tugmalardan birini bosing:"

        await status.edit_text(text, parse_mode="HTML", reply_markup=builder.as_markup())

    except Exception as e:
        safe_err = html.escape(str(e))
        await status.edit_text(f"❌ Qidiruvda xatolik yuz berdi: {safe_err}")

@router.message(F.text & ~F.text.startswith("/") & ~F.text.regexp(r'https?://[^\s]+'))
async def handle_music_search(message: types.Message):
    if message.from_user:
        add_user(message.from_user.id, message.from_user.username, message.from_user.first_name)
    query = message.text.strip()
    if len(query) < 2:
        return
    await handle_music_search_query(message, query)


@router.callback_query(lambda c: c.data.startswith("dl_music:"))
async def cb_download_music(callback: types.CallbackQuery):
    track_key = callback.data.split(":", 1)[1]
    track_info = SEARCH_CACHE.get(track_key)

    if not track_info:
        try:
            track_info = await DownloaderService.get_deezer_track(track_key)
            if track_info:
                SEARCH_CACHE[track_key] = track_info
        except Exception:
            pass

    if not track_info:
        await callback.answer("Musiqa ma'lumotlari topilmadi. Qaytadan qidiring.", show_alert=True)
        return

    preview_url = track_info.get("preview")
    if not preview_url:
        await callback.answer("Ushbu musiqani yuklab bo'lmadi.", show_alert=True)
        return

    await callback.answer("Musiqa yuklanmoqda...")
    status = await callback.message.reply(f"⏳ \"{track_info['title']}\" to'liq formatda yuklanmoqda...")

    audio_path = None
    is_full = False
    try:
        import html
        from aiogram.enums import ParseMode

        # 1. Avval YouTube yoki SoundCloud orqali to'liq musiqani (Full MP3) yuklash
        try:
            audio_path = await DownloaderService.download_full_audio(track_info['artist'], track_info['title'])
            is_full = True
        except Exception as err:
            print(f"To'liq yuklash o'xshamadi, preview olinmoqda: {err}")
            # 2. Agar to'liq yuklab bo'lmasa, preview dan foydalanish
            audio_path = await DownloaderService.download_preview_audio(preview_url, track_info['title'])

        safe_artist = html.escape(track_info.get('artist', ''))
        safe_title = html.escape(track_info.get('title', ''))
        tag = " (To'liq versiya 🎧)" if is_full else " (Qisqa parcha)"
        await callback.message.reply_audio(
            audio=FSInputFile(audio_path),
            title=track_info['title'],
            performer=track_info['artist'],
            caption=f"🎵 <b>{safe_artist} — {safe_title}</b>{tag}\n\n🤖 @Instadanmusiqavdyukla_bot",
            parse_mode=ParseMode.HTML
        )
        await status.delete()


    except Exception as e:
        await status.edit_text(f"❌ Musiqani yuklashda xatolik: {e}")
    finally:
        if audio_path and Path(audio_path).exists():
            try: os.remove(audio_path)
            except Exception: pass
