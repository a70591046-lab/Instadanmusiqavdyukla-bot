import os
import uuid
from pathlib import Path

import html
from aiogram import Router, types, F
from aiogram.enums import ParseMode
from aiogram.types import FSInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database import add_user
from services.downloader import DownloaderService

router = Router()

# {session_id -> {"query": str, "results": list, "page": int}}
SEARCH_SESSIONS: dict = {}
# {video_id -> track_info_dict}
TRACK_CACHE: dict = {}

PER_PAGE = 5


def _build_page(query: str, results: list, page: int, session_id: str):
    """Natijalar xabarini va tugmalarni yaratish"""
    start = page * PER_PAGE
    end = start + PER_PAGE
    page_results = results[start:end]
    total_pages = (len(results) + PER_PAGE - 1) // PER_PAGE

    text = f"🎶 <b>\"{html.escape(query)}\" bo'yicha topilgan natijalar:</b>\n\n"
    builder = InlineKeyboardBuilder()

    for local_i, item in enumerate(page_results, start=1):
        global_num = start + local_i
        dur_total = item["duration"]
        dur_min = dur_total // 60
        dur_sec = dur_total % 60
        artist = html.escape(item.get("artist", ""))
        title = html.escape(item.get("title", "Noma'lum"))
        if artist:
            text += f"{global_num}. <b>{artist}</b> — {title} <code>({dur_min}:{dur_sec:02d})</code>\n"
        else:
            text += f"{global_num}. {title} <code>({dur_min}:{dur_sec:02d})</code>\n"
        builder.button(text=f"⬇️ {global_num}", callback_data=f"dl_track:{item['id']}")

    builder.adjust(PER_PAGE)

    nav = []
    if page > 0:
        nav.append(("⬅️ Oldingi", f"music_page:{session_id}:{page - 1}"))
    if page < total_pages - 1:
        nav.append(("➡️ Keyingi", f"music_page:{session_id}:{page + 1}"))
    for btn_text, cb_data in nav:
        builder.button(text=btn_text, callback_data=cb_data)
    if nav:
        builder.adjust(PER_PAGE, len(nav))

    text += "\n⬇️ Yuklab olish uchun raqamni bosing."
    if total_pages > 1:
        text += f"\n📄 Sahifa {page + 1}/{total_pages} (jami {len(results)} ta natija)"

    return text, builder.as_markup()


# ─── Message handler ─────────────────────────────────────────────────────────

@router.message(F.text & ~F.text.startswith("/") & ~F.text.regexp(r"https?://[^\s]+"))
async def handle_music_search(message: types.Message):
    if message.from_user:
        add_user(message.from_user.id, message.from_user.username, message.from_user.first_name)

    query = message.text.strip()
    if len(query) < 2:
        return

    status = await message.reply(
        f"🔍 <b>\"{html.escape(query)}\"</b> qidirilmoqda...",
        parse_mode=ParseMode.HTML,
    )

    try:
        results = await DownloaderService.search_music_youtube(query, limit=25)
        if not results:
            await status.edit_text(
                f"😔 <b>\"{html.escape(query)}\"</b> bo'yicha hech narsa topilmadi.\n"
                "Boshqacha yozing yoki YouTube/Instagram URL ulashing.",
                parse_mode=ParseMode.HTML,
            )
            return

        session_id = uuid.uuid4().hex[:8]
        SEARCH_SESSIONS[session_id] = {"query": query, "results": results, "page": 0}
        for item in results:
            TRACK_CACHE[item["id"]] = item

        text, markup = _build_page(query, results, 0, session_id)
        await status.delete()
        await message.reply(text, parse_mode=ParseMode.HTML, reply_markup=markup)

    except Exception as e:
        await status.edit_text(f"❌ Qidiruvda xatolik yuz berdi: {html.escape(str(e))}")


# ─── Pagination callback ──────────────────────────────────────────────────────

@router.callback_query(lambda c: c.data and c.data.startswith("music_page:"))
async def cb_music_page(callback: types.CallbackQuery):
    parts = callback.data.split(":")
    session_id = parts[1]
    page = int(parts[2])

    session = SEARCH_SESSIONS.get(session_id)
    if not session:
        await callback.answer("Sessiya eskirgan. Qaytadan qidiring.", show_alert=True)
        return

    SEARCH_SESSIONS[session_id]["page"] = page
    text, markup = _build_page(session["query"], session["results"], page, session_id)
    await callback.answer()
    try:
        await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=markup)
    except Exception:
        pass


# ─── Download callback ────────────────────────────────────────────────────────

@router.callback_query(lambda c: c.data and c.data.startswith("dl_track:"))
async def cb_download_track(callback: types.CallbackQuery):
    video_id = callback.data.split(":", 1)[1]
    track_info = TRACK_CACHE.get(video_id)

    if not track_info:
        await callback.answer("Ma'lumot topilmadi. Qaytadan qidiring.", show_alert=True)
        return

    await callback.answer("Yuklanmoqda... ⏳")
    title_esc = html.escape(track_info.get("title", "Noma'lum"))
    status = await callback.message.reply(
        f"⏳ <b>{title_esc}</b> to'liq versiyasi yuklanmoqda...",
        parse_mode=ParseMode.HTML,
    )

    audio_path = None
    try:
        url = track_info.get("url", "")
        if not url:
            raise RuntimeError("URL topilmadi")

        audio_path = await DownloaderService.download_audio_by_url(url)

        safe_artist = html.escape(track_info.get("artist", ""))
        safe_title = html.escape(track_info.get("title", "Noma'lum"))
        if safe_artist:
            caption = f"🎵 <b>{safe_artist} — {safe_title}</b>\n🤖 @Instadanmusiqavdyukla_bot"
        else:
            caption = f"🎵 <b>{safe_title}</b>\n🤖 @Instadanmusiqavdyukla_bot"

        await callback.message.reply_audio(
            audio=FSInputFile(audio_path),
            title=track_info.get("title", ""),
            performer=track_info.get("artist", ""),
            caption=caption,
            parse_mode=ParseMode.HTML,
        )
        await status.delete()

    except Exception as e:
        await status.edit_text(f"❌ Yuklashda xatolik: {html.escape(str(e))}")
    finally:
        if audio_path and Path(audio_path).exists():
            try:
                os.remove(audio_path)
            except Exception:
                pass
