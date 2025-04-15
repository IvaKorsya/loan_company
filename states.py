from aiogram.fsm.state import StatesGroup, State

class FormStates(StatesGroup):
    waiting_for_phone = State()
    waiting_for_email = State()