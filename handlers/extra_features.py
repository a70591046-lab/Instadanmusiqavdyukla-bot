import os
import uuid
from pathlib import Path
from aiogram import Router, types, Bot, F
from aiogram.filters import Command
from aiogram.types import FSInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import DOWNLOADS_DIR
from services.effect_4k import apply_4k_effect
from services.downloader import DownloaderService

router = Router()

@router.message(Command("4k"))
async def cmd_4k(message: types.Message, bot: Bot):
    # 1. Videoga reply qilingan bo'lsa
    reply = message.reply_to_message
    if reply and (reply.video or reply.animation or (reply.document and reply.document.mime_type and "video" in reply.document.mime_type)):
        target_media = reply.video or reply.animation or reply.document
        if target_media.file_size and target_media.file_size > 30 * 1024 * 1024:
            await message.reply("⚠️ Video hajmi juda katta (maksimal 30 MB gacha bo'lishi kerak).")
            return

        status_msg = await message.reply("⏳ Video 4K HDR sifatga ishlanmoqda (tiniqlashtirish va ranglar boyitilmoqda)...")
        temp_input = DOWNLOADS_DIR / f"input_4k_{uuid.uuid4().hex[:8]}.mp4"
        out_4k = None

        try:
            file = await bot.get_file(target_media.file_id)
            await bot.download_file(file.file_path, destination=temp_input)

            out_4k = await apply_4k_effect(temp_input)
            await message.reply_video(
                video=FSInputFile(out_4k),
                caption="✨ <b>4K / HDR effekti berildi!</b>\n\n🤖 @Instadanmusiqavdyukla_bot"
            )
            await status_msg.delete()
        except Exception as e:
            await status_msg.edit_text(f"❌ Xatolik yuz berdi: {e}")
        finally:
            if temp_input.exists():
                try: os.remove(temp_input)
                except Exception: pass
            if out_4k and Path(out_4k).exists():
                try: os.remove(out_4k)
                except Exception: pass
        return

    # 2. /4k <url> ko'rinishida yuborilgan bo'lsa
    urls = DownloaderService.extract_urls(message.text or "")
    if urls:
        url = urls[0]
        status_msg = await message.reply("⏳ Video yuklanmoqda va 4K effekt berilmoqda...")
        video_path = None
        out_4k = None
        try:
            data = await DownloaderService.download_media(url)
            video_path = data.get("video_path")
            if not video_path or not Path(video_path).exists():
                raise RuntimeError("Video yuklab olinmadi.")

            out_4k = await apply_4k_effect(video_path)
            await message.reply_video(
                video=FSInputFile(out_4k),
                caption="✨ <b>4K / HDR effekti berildi!</b>\n\n🤖 @Instadanmusiqavdyukla_bot"
            )
            await status_msg.delete()
        except Exception as e:
            await status_msg.edit_text(f"❌ Xatolik yuz berdi: {e}")
        finally:
            if video_path and Path(video_path).exists():
                try: os.remove(video_path)
                except Exception: pass
            if out_4k and Path(out_4k).exists():
                try: os.remove(out_4k)
                except Exception: pass
        return

    # 3. Yordam
    await message.reply(
        "✨ <b>4K Effekt berish uchun:</b>\n\n"
        "1. Botdagi istalgan videoga <b>Reply</b> (javob) qilib <code>/4k</code> deb yozing.\n"
        "2. Yoki <code>/4k &lt;video havolasi&gt;</code> shaklida yuboring.\n"
        "3. Bot videoni tiniqlashtirib, HDR rang berib qaytaradi!"
    )

@router.message(Command("musiqa"))
async def cmd_musiqa(message: types.Message):
    await message.reply(
        "🎵 <b>Musiqa qidirish va yuklash:</b>\n\n"
        "Hech qanday maxsus buyruq shart emas! Shunchaki istalgan qo'shiq nomi yoki xonanda ismini yozing:\n\n"
        "Masalan:\n"
        "• <code>Jahongir Otajonov</code>\n"
        "• <code>Yulduz Usmonova</code>\n"
        "• <code>Xamdam Sobirov</code>\n\n"
        "Bot darhol topib, MP3 formatida sizga yuboradi! 🎧"
    )

@router.message(Command("konsert"))
async def cmd_konsert(message: types.Message):
    builder = InlineKeyboardBuilder()
    builder.button(text="🏟️ Yulduz Usmonova Konsert", callback_data="search_konsert:Yulduz Usmonova Konsert")
    builder.button(text="🏟️ Tohir Sodiqov Konsert", callback_data="search_konsert:Tohir Sodiqov Konsert")
    builder.button(text="🏟️ Ozodbek Nazarbekov Konsert", callback_data="search_konsert:Ozodbek Nazarbekov Konsert")
    builder.adjust(1)

    await message.reply(
        "🏟️ <b>Konsert va Jonli Ijro Musiqalari:</b>\n\n"
        "Quyidagi mashhur konsertlardan birini tanlang yoki qidiruvga <code>[Xonanda ismi] konsert</code> deb yozing:",
        reply_markup=builder.as_markup()
    )

@router.callback_query(lambda c: c.data.startswith("search_konsert:"))
async def cb_konsert_search(callback: types.CallbackQuery):
    query = callback.data.split(":", 1)[1]
    await callback.answer()
    from handlers.music import handle_music_search_query
    await handle_music_search_query(callback.message, query)
