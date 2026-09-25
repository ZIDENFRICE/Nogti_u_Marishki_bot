from aiogram.fsm.state import State, StatesGroup


class BookingSG(StatesGroup):
    choosing_service = State()
    choosing_slot = State()
    entering_name = State()
    entering_phone = State()
    entering_note = State()      # новое: пожелания
    confirming = State()


class AdminSG(StatesGroup):
    # услуги
    add_service_title = State()
    add_service_desc = State()
    add_service_price = State()
    add_service_duration = State()

    # слоты
    add_slot_datetime = State()
    add_slot_bulk = State()

    # рассылка
    broadcast_content = State()

    # поиск клиента
    search_client = State()


class ReviewSG(StatesGroup):
    rating = State()
    text = State()
    photo = State()      # ← НОВОЕ

