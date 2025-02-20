from datetime import date
from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.kbd import Button
from app.bot.booking.schemas import SCapacity, SNewBooking
from app.bot.user.kbs import main_user_kb
from app.DAO.dao import BookingDAO, TimeSlotUserDAO, TableDAO
from app.config import broker

async def cancel_logic(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
    await callback.answer("Сценарий бронирования отменен!")
    await callback.message.answer("Вы отменили сценарий бронирования.",
                                  reply_markup=main_user_kb(callback.from_user.id))


async def process_add_count_capacity(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
    """Handler for selecting the number of guests."""
    session = dialog_manager.middleware_data.get("session_without_commit")
    selected_capacity = int(button.widget_id)
    dialog_manager.dialog_data["capacity"] = selected_capacity
    dialog_manager.dialog_data['tables'] = await TableDAO(session).find_all(SCapacity(capacity=selected_capacity))
    await callback.answer(f"Выбрано {selected_capacity} гостей")
    await dialog_manager.next()

async def on_table_selected(callback: CallbackQuery, widget, dialog_manager: DialogManager, item_id: str):
    """Handler for selecting the table."""
    session = dialog_manager.middleware_data.get("session_without_commit")
    table_id = int(item_id)
    selected_table = await TableDAO(session).find_one_or_none_by_id(table_id)
    dialog_manager.dialog_data["selected_table"] = selected_table
    await callback.answer(f"Выбран стол №{table_id} на {selected_table.capacity} мест")
    await dialog_manager.next()

async def process_date_selected(callback: CallbackQuery, widget, dialog_manager: DialogManager, selected_date: date):
    """Handler for selecting the date."""
    dialog_manager.dialog_data["booking_date"] = selected_date
    session = dialog_manager.middleware_data.get("session_without_commit")
    selected_table = dialog_manager.dialog_data["selected_table"]
    slots = await BookingDAO(session).get_available_time_slots(table_id=selected_table.id, booking_date=selected_date)
    if slots:
        await callback.answer(f"Выбрана дата: {selected_date}")
        dialog_manager.dialog_data["slots"] = slots
        await dialog_manager.next()
    else:
        await callback.answer(f"Нет мест на {selected_date} для стола №{selected_table.id}!")
        await dialog_manager.back()


async def process_slots_selected(callback: CallbackQuery, widget, dialog_manager: DialogManager, item_id: str):
    """Handler for selecting the time slot."""
    session = dialog_manager.middleware_data.get("session_without_commit")
    slot_id = int(item_id)
    selected_slot = await TimeSlotUserDAO(session).find_one_or_none_by_id(slot_id)
    await callback.answer(f"Выбрано время с {selected_slot.start_time} до {selected_slot.end_time}")
    dialog_manager.dialog_data['selected_slot'] = selected_slot
    await dialog_manager.next()

async def on_confirmation(callback: CallbackQuery, widget, dialog_manager: DialogManager, **kwargs):
    """Handler for confirming the booking."""
    session = dialog_manager.middleware_data.get("session_with_commit")

    # Getting selected data
    selected_table = dialog_manager.dialog_data['selected_table']
    selected_slot = dialog_manager.dialog_data['selected_slot']
    booking_date = dialog_manager.dialog_data['booking_date']
    user_id = callback.from_user.id
    check = await BookingDAO(session).check_available_bookings(table_id=selected_table.id,
                                                              time_slot_id=selected_slot.id,
                                                              booking_date=booking_date)
    if check:
        await callback.answer("Приступаю к сохранению")
        add_model = SNewBooking(
            user_id=user_id, table_id=selected_table.id,
            time_slot_id=selected_slot.id, date=booking_date, status="booked"
        )
        await BookingDAO(session).add(add_model)
        await callback.answer(f"Бронирование успешно создано!")

        text = "Бронь успешно сохранена🔢🍴 Со списком своих броней можно ознакомиться в меню 'МОИ БРОНИ'"
        await callback.message.answer(text, reply_markup=main_user_kb(user_id))

        admin_text = (f"Внимание! Пользователь с ID {callback.from_user.id} забронировал столик №{selected_table.id} "
                     f"на {booking_date}. Время брони с {selected_slot.start_time} до {selected_slot.end_time}")
        await broker.publish(admin_text, "admin_msg")
        await broker.publish(callback.from_user.id, "noti_user")
        await dialog_manager.done()
    else:
        await callback.answer("Места на этот слот уже заняты!")
        await dialog_manager.back()