import html
from aiogram import Router, types
from aiogram.filters import CommandStart, Command
from aiogram.enums import ParseMode
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database import add_user

router = Router()

@router.message(CommandStart())
async def cmd_start(message: types.Message):
    if message.from_user:
        add_user(message.from_user.id, message.from_user.username, message.from_user.first_name)

    first_name_safe = html.escape(message.from_user.first_name or "")

    text = (
        f"Assalomu alaykum, {first_name_safe}! 👋\n\n"
        "🤖 <b>Instadanmusiqavdyukla</b> botiga xush kelibsiz!\n\n"
        "Men quyidagi vazifalarni bajara olaman:\n"
        "📥 <b>Instagram, TikTok, YouTube</b> videolarini yuklab berish\n"
        "🎵 <b>Musiqa qidirish va yuklash</b> (shunchaki nomini yozing)\n"
        "🔵 <b>/dumaloq</b> — videoni Telegram dumaloq video (krujochek) qilish\n"
        "✨ <b>/4k</b> — videoga 4K / HDR tiniqlik effekti berish\n"
        "🏟️ <b>/konsert</b> — jonli ijro va konsert musiqalari\n"
        "👑 <b>/ega</b> — Admin panel (@Muhammadali00010)\n\n"
        "📌 <b>Qanday ishlatiladi?</b>\n"
        "• Video havolasini yuboring (Instagram, TikTok, YouTube)\n"
        "• Qo'shiq nomini yozing (masalan: <code>Yulduz Usmonova</code>)\n"
        "• Videoni dumaloq qilish uchun videoga reply qilib <code>/dumaloq</code> deb yozing!"
    )
    
    builder = InlineKeyboardBuilder()
    builder.button(text="ℹ️ Yordam / Qo'llanma", callback_data="help_info")
    builder.button(text="👑 Bot Egasi", url="https://t.me/Muhammadali00010")
    builder.adjust(1, 1)
    
    await message.answer(text, parse_mode=ParseMode.HTML, reply_markup=builder.as_markup())

@router.message(Command("help"))
async def cmd_help(message: types.Message):
    text = (
        "📖 <b>Botdan foydalanish qo'llanmasi:</b>\n\n"
        "1️⃣ <b>Video yuklash:</b>\n"
        "Instagram, TikTok yoki YouTube havolasini botga yuboring. Bot videoni yuklab beradi.\n\n"
        "2️⃣ <b>Dumaloq video (Video Note):</b>\n"
        "• Videoga javob tariqasida <code>/dumaloq</code> deb yozing.\n"
        "• Yoki to'g'ridan-to'g'ri video yuboring va chiqadigan tugmani bosing.\n\n"
        "3️⃣ <b>4K Effekt:</b>\n"
        "• Videoga javob qilib <code>/4k</code> deb yozing.\n\n"
        "4️⃣ <b>Musiqa topish:</b>\n"
        "Qo'shiq yoki ijrochi nomini shunchaki yozib yuboring.\n\n"
        "👑 <b>Admin:</b> @Muhammadali00010"
    )
    await message.answer(text, parse_mode=ParseMode.HTML)

@router.callback_query(lambda c: c.data == "help_info")
async def cb_help_info(callback: types.CallbackQuery):
    text = (
        "💡 <b>Tezkor maslahatlar:</b>\n\n"
        "• Havolani to'liq nusxalab yuboring.\n"
        "• Dumaloq videolar 1:1 kvadratga keltirilib, maksimal 60 soniya bo'ladi.\n"
        "• Har qanday videodan musiqani MP3 qilib olishingiz mumkin.\n"
        "• Admin bilan bog'lanish: @Muhammadali00010"
    )
    await callback.message.answer(text, parse_mode=ParseMode.HTML)
    await callback.answer()

