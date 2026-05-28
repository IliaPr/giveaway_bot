from aiogram.fsm.state import State, StatesGroup


class RegistrationForm(StatesGroup):
    full_name = State()
    phone = State()
    company = State()
    position = State()
