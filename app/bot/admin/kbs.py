from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

def main_admin_kb() -> InlineKeyboardMarkup:
    """
    Creates a keyboard for the main menu of the admin panel.
    """
    kb = InlineKeyboardBuilder()
    kb.add(InlineKeyboardButton(text="📊 Статистика по пользователям", callback_data="admin_users_stats"))
    kb.add(InlineKeyboardButton(text="📈 Статистика по броням", callback_data="admin_bookings_stats"))
    kb.add(InlineKeyboardButton(text="🏠 На главную", callback_data="back_home"))
    kb.adjust(1)  # Располагаем кнопки в один столбец
    return kb.as_markup()

def admin_back_kb() -> InlineKeyboardMarkup:
    """
    Сreates a keyboard to return to the admin panel.
    """
    kb = InlineKeyboardBuilder()
    kb.add(InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_panel"))
    kb.add(InlineKeyboardButton(text="🏠 На главную", callback_data="back_home"))
    kb.adjust(1)
    return kb.as_markup()

