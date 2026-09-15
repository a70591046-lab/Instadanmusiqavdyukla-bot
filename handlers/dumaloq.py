import os
import uuid
from pathlib import Path
from aiogram import Router, types, Bot, F
from aiogram.filters import Command
from aiogram.types import FSInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import DOWNLOADS_DIR
from services.video_converter import convert_to_video_note
from services.downloader import DownloaderService

router = Router()

@router.message(Command("dumaloq", "krujok", "round"))
async def cmd_dumaloq(message: types.Message, bot: Bot):
    # 1-holat: Biror videoga reply qilib /dumaloq deb yozilgan bo'lsa
    reply = message.reply_to_message
    if reply and (reply.video or reply.animation or (reply.document and reply.document.mime_type and "video" in reply.document.mime_type)):
        target_media = reply.video or reply.animation or reply.document
        if target_media.file_size and target_media.file_size > 25 * 1024 * 1024:
            await message.reply("⚠️ Video hajmi juda katta (maksimal 25 MB gacha bo'lishi kerak).")
            return

        status_msg = await message.reply("⏳ Video dumaloq formatga o'tkazilmoqda...")
        temp_input = DOWNLOADS_DIR / f"input_{uuid.uuid4().hex[:8]}.mp4"
        note_path = None

        try:
            file = await bot.get_file(target_media.file_id)
            await bot.download_file(file.file_path, destination=temp_input)

            note_path = await convert_to_video_note(temp_input)
            await message.reply_video_note(video_note=FSInputFile(note_path))
            await status_msg.delete()
        except Exception as e:
            await status_msg.edit_text(f"❌ Xatolik yuz berdi: {e}")
        finally:
            if temp_input.exists():
                try: os.remove(temp_input)
                except Exception: pass
            if note_path and Path(note_path).exists():
                try: os.remove(note_path)
                except Exception: pass
        return

    # 2-holat: /dumaloq <link> ko'rinishida yuborilgan bo'lsa
    urls = DownloaderService.extract_urls(message.text or "")
    if urls:
        url = urls[0]
        status_msg = await message.reply("⏳ Havoladan video yuklanmoqda va dumaloq formatga aylantirilmoqda...")
        note_path = None
        video_path = None

        try:
            media_info = await DownloaderService.download_media(url)
            video_path = media_info.get("video_path")
            if not video_path or not Path(video_path).exists():
                raise RuntimeError("Video yuklab olinmadi.")

            note_path = await convert_to_video_note(video_path)
            await message.reply_video_note(video_note=FSInputFile(note_path))
            await status_msg.delete()
        except Exception as e:
            await status_msg.edit_text(f"❌ Xatolik yuz berdi: {e}")
        finally:
            if video_path and Path(video_path).exists():
                try: os.remove(video_path)
                except Exception: pass
            if note_path and Path(note_path).exists():
                try: os.remove(note_path)
                except Exception: pass
        return

    # 3-holat: Hech qanday video yoki havola ko'rsatilmagan
    await message.reply(
        "⚪ **Videoni dumaloq (Video Note) qilish uchun:**\n\n"
        "1. Botdagi yoki guruhdagi istalgan videoga **Reply** (javob) qilib `/dumaloq` deb yozing.\n"
        "2. Yoki `/dumaloq <havola>` shaklida yuboring.\n"
        "3. Yoki to'g'ridan-to'g'ri biror video yuboring va chiqadigan **⚪ Dumaloq qilish** tugmasini bosing!",
        parse_mode="Markdown"
    )

@router.message(F.video | F.animation)
async def handle_direct_video(message: types.Message):
    """Foydalanuvchi to'g'ridan-to'g'ri video yuborganida tugmalar chiqarish"""
    builder = InlineKeyboardBuilder()
    file_id = (message.video or message.animation).file_id
    builder.button(text="⚪ Dumaloq video qilish", callback_data=f"doround:{file_id[:30]}")
    builder.button(text="🎵 MP3 ga ajratish", callback_data=f"doaudio:{file_id[:30]}")
    builder.adjust(1, 1)

    await message.reply(
        "🎬 Video qabul qilindi. Nima qilmoqchisiz?",
        reply_markup=builder.as_markup()
    )

@router.callback_query(lambda c: c.data.startswith("doround:"))
async def cb_do_round(callback: types.CallbackQuery, bot: Bot):
    await callback.answer("Dumaloq video tayyorlanmoqda...")
    msg = callback.message.reply_to_message or callback.message
    target_media = msg.video or msg.animation

    if not target_media:
        await callback.message.answer("⚠️ Video topilmadi.")
        return

    temp_input = DOWNLOADS_DIR / f"input_{uuid.uuid4().hex[:8]}.mp4"
    note_path = None
    status = await callback.message.answer("⏳ Video qayta ishlanmoqda (dumaloq formatga keltirilmoqda)...")

    try:
        file = await bot.get_file(target_media.file_id)
        await bot.download_file(file.file_path, destination=temp_input)

        note_path = await convert_to_video_note(temp_input)
        await callback.message.answer_video_note(video_note=FSInputFile(note_path))
        await status.delete()
    except Exception as e:
        await status.edit_text(f"❌ Xatolik yuz berdi: {e}")
    finally:
        if temp_input.exists():
            try: os.remove(temp_input)
            except Exception: pass
        if note_path and Path(note_path).exists():
            try: os.remove(note_path)
            except Exception: pass

@router.callback_query(lambda c: c.data.startswith("doaudio:"))
async def cb_do_audio(callback: types.CallbackQuery, bot: Bot):
    await callback.answer("Audio ajratilmoqda...")
    msg = callback.message.reply_to_message or callback.message
    target_media = msg.video or msg.animation

    if not target_media:
        await callback.message.answer("⚠️ Video topilmadi.")
        return

    temp_input = DOWNLOADS_DIR / f"input_{uuid.uuid4().hex[:8]}.mp4"
    audio_path = None
    status = await callback.message.answer("⏳ Audiosi ajratib olinmoqda...")

    try:
        file = await bot.get_file(target_media.file_id)
        await bot.download_file(file.file_path, destination=temp_input)

        audio_path = await DownloaderService.extract_audio_from_video(temp_input)
        await callback.message.answer_audio(
            audio=FSInputFile(audio_path),
            title="Ajratilgan musiqa",
            performer="Instadanmusiqavdyukla_bot"
        )
        await status.delete()
    except Exception as e:
        await status.edit_text(f"❌ Xatolik yuz berdi: {e}")
    finally:
        if temp_input.exists():
            try: os.remove(temp_input)
            except Exception: pass
        if audio_path and Path(audio_path).exists():
            try: os.remove(audio_path)
            except Exception: pass
