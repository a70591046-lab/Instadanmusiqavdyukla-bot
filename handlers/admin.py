import asyncio
import os
from aiogram import Router, types, Bot, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database import get_users_count, get_all_users

router = Router()

ADMIN_USERNAME = "Muhammadali00010"

class AdminState(StatesGroup):
    waiting_for_broadcast = State()

def is_admin(user: types.User) -> bool:
    if user.username and user.username.lower() == ADMIN_USERNAME.lower():
        return True
    admin_id = os.getenv("ADMIN_ID", "").strip()
    if admin_id and str(user.id) == admin_id:
        return True
    return False

@router.message(Command("ega", "admin"))
async def cmd_ega(message: types.Message):
    if is_admin(message.from_user):
        users_count = get_users_count()
        text = (
            f"👑 <b>Xush kelibsiz, Bosh Admin (@{ADMIN_USERNAME})!</b>\n\n"
            f"📊 <b>Bot foydalanuvchilari soni:</b> {users_count} ta\n\n"
            "Quyidagi boshqaruv menyusidan kerakli amalni tanlang:"
        )

        builder = InlineKeyboardBuilder()
        builder.button(text="📊 Statistika", callback_data="admin_stats")
        builder.button(text="📢 Xabar tarqatish", callback_data="admin_broadcast")
        builder.adjust(1, 1)

        await message.reply(text, reply_markup=builder.as_markup())
    else:
        text = (
            "👑 <b>Bot Egasi / Administrator:</b>\n\n"
            f"👤 Admin: @{ADMIN_USERNAME}\n"
            "Savol, taklif yoki reklama masalalari bo'yicha adminga murojaat qilishingiz mumkin!"
        )
        builder = InlineKeyboardBuilder()
        builder.button(text="✉️ Adminga yozish", url=f"https://t.me/{ADMIN_USERNAME}")
        await message.reply(text, reply_markup=builder.as_markup())

@router.callback_query(lambda c: c.data == "admin_stats")
async def cb_admin_stats(callback: types.CallbackQuery):
    if not is_admin(callback.from_user):
        await callback.answer("Siz admin emassiz!", show_alert=True)
        return

    count = get_users_count()
    await callback.answer(f"Jami foydalanuvchilar: {count} ta", show_alert=True)

@router.callback_query(lambda c: c.data == "admin_broadcast")
async def cb_admin_broadcast(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user):
        await callback.answer("Siz admin emassiz!", show_alert=True)
        return

    await state.set_state(AdminState.waiting_for_broadcast)
    await callback.message.reply(
        "📝 <b>Barcha foydalanuvchilarga yubormoqchi bo'lgan xabaringizni yuboring:</b>\n\n"
        "(Matn, rasm, video yoki audio yuborishingiz mumkin. Bekor qilish uchun /cancel deb yozing)"
    )
    await callback.answer()

@router.message(Command("cancel"))
async def cmd_cancel(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state:
        await state.clear()
        await message.reply("❌ Amal bekor qilindi.")

@router.message(AdminState.waiting_for_broadcast)
async def process_broadcast(message: types.Message, bot: Bot, state: FSMContext):
    if not is_admin(message.from_user):
        await state.clear()
        return

    users = get_all_users()
    await message.reply(f"🚀 Xabar {len(users)} ta foydalanuvchiga yuborilmoqda...")

    success = 0
    failed = 0

    for user_id in users:
        try:
            await message.copy_to(chat_id=user_id)
            success += 1
            await asyncio.sleep(0.05) # Telegram limitlariga tushmaslik uchun
        except Exception:
            failed += 1

    await state.clear()
    await message.reply(
        f"✅ <b>Xabar tarqatish yakunlandi!</b>\n\n"
        f"• Muvaffaqiyatli: {success} ta\n"
        f"• Yetib bormadi (bloklagan): {failed} ta"
    )
