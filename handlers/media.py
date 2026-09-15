import os
import uuid
from pathlib import Path
from aiogram import Router, types, Bot, F
from aiogram.types import FSInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import DOWNLOADS_DIR
from services.downloader import DownloaderService
from services.video_converter import convert_to_video_note

router = Router()

import html
from aiogram.enums import ParseMode

from database import add_user

@router.message(F.text.regexp(r'https?://[^\s]+'))
async def handle_url(message: types.Message, bot: Bot):
    if message.from_user:
        add_user(message.from_user.id, message.from_user.username, message.from_user.first_name)

    urls = DownloaderService.extract_urls(message.text or "")
    if not urls:
        return

    url = urls[0]
    status_msg = await message.reply("⏳ Video yuklanmoqda, iltimos kuting...")

    video_path = None
    audio_path = None

    try:
        data = await DownloaderService.download_media(url)
        video_path = data.get("video_path")
        audio_path = data.get("audio_path")
        title = data.get("title", "Yuklangan video")

        if not video_path or not Path(video_path).exists():
            raise RuntimeError("Videoni yuklab bo'lmadi. Havola to'g'ri ekanligini yoki ommaviy (public) post ekanligini tekshiring.")

        # Tugmalar: Musiqasini olish va Dumaloq qilish
        builder = InlineKeyboardBuilder()
        builder.button(text="🎵 Musiqasini olish", callback_data="ext_audio")
        builder.button(text="⚪ Dumaloq video qilish", callback_data="ext_round")
        builder.adjust(2)

        safe_title = html.escape(title[:100])
        caption = f"🎬 <b>{safe_title}</b>\n\n🤖 @Instadanmusiqavdyukla_bot"
        
        await message.reply_video(
            video=FSInputFile(video_path),
            caption=caption,
            parse_mode=ParseMode.HTML,
            reply_markup=builder.as_markup()
        )

        # Agar TikTok orqali musiqasi ham birdaniga kelgan bo'lsa, uni ham alohida berish mumkin
        if audio_path and Path(audio_path).exists():
            try:
                await message.reply_audio(
                    audio=FSInputFile(audio_path),
                    title=title[:50],
                    performer="TikTok Musiqa"
                )
            except Exception:
                pass

        await status_msg.delete()

    except Exception as e:
        safe_err = html.escape(str(e))
        await status_msg.edit_text(f"❌ Yuklashda xatolik yuz berdi: {safe_err}\n\nIltimos, havola to'g'riligini va post ochiq (public) ekanligini tekshiring.", parse_mode=ParseMode.HTML)

    finally:
        # Fayllarni tozalash
        if video_path and Path(video_path).exists():
            try: os.remove(video_path)
            except Exception: pass
        if audio_path and Path(audio_path).exists():
            try: os.remove(audio_path)
            except Exception: pass

@router.callback_query(lambda c: c.data == "ext_round")
async def cb_extract_round(callback: types.CallbackQuery, bot: Bot):
    target_video = callback.message.video
    if not target_video:
        await callback.answer("Video topilmadi!", show_alert=True)
        return

    await callback.answer("Dumaloq video tayyorlanmoqda...")
    status = await callback.message.reply("⏳ Dumaloq video (Video Note) tayyorlanmoqda...")

    temp_video = DOWNLOADS_DIR / f"temp_{uuid.uuid4().hex[:8]}.mp4"
    note_path = None
    try:
        file = await bot.get_file(target_video.file_id)
        await bot.download_file(file.file_path, destination=temp_video)

        note_path = await convert_to_video_note(temp_video)
        await callback.message.reply_video_note(video_note=FSInputFile(note_path))
        await status.delete()
    except Exception as e:
        await status.edit_text(f"❌ Xatolik yuz berdi: {e}")
    finally:
        if temp_video.exists():
            try: os.remove(temp_video)
            except Exception: pass
        if note_path and Path(note_path).exists():
            try: os.remove(note_path)
            except Exception: pass

@router.callback_query(lambda c: c.data == "ext_audio")
async def cb_extract_audio(callback: types.CallbackQuery, bot: Bot):
    target_video = callback.message.video
    if not target_video:
        await callback.answer("Video topilmadi!", show_alert=True)
        return

    await callback.answer("Musiqa ajratilmoqda...")
    status = await callback.message.reply("⏳ Musiqasi ajratib olinmoqda...")

    temp_video = DOWNLOADS_DIR / f"temp_{uuid.uuid4().hex[:8]}.mp4"
    audio_path = None
    try:
        file = await bot.get_file(target_video.file_id)
        await bot.download_file(file.file_path, destination=temp_video)

        audio_path = await DownloaderService.extract_audio_from_video(temp_video)
        await callback.message.reply_audio(
            audio=FSInputFile(audio_path),
            title="Ajratilgan musiqa",
            performer="Instadanmusiqavdyukla_bot"
        )
        await status.delete()
    except Exception as e:
        await status.edit_text(f"❌ Xatolik yuz berdi: {e}")
    finally:
        if temp_video.exists():
            try: os.remove(temp_video)
            except Exception: pass
        if audio_path and Path(audio_path).exists():
            try: os.remove(audio_path)
            except Exception: pass
