from aiogram.fsm.state import StatesGroup, State

class FormStates(StatesGroup):
    waiting_for_phone = State()
    waiting_for_email = State()

class LoanStates(StatesGroup):
    choose_loan_type = State()
    enter_amount = State()
    enter_term = State()
    confirm_loan = State()

class PaymentStates(StatesGroup):
    choose_loan = State()      
    enter_amount = State()   
    confirm_payment = State()