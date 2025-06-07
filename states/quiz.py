from aiogram.fsm.state import StatesGroup, State

class QuizStates(StatesGroup):
    waiting_for_name = State()        # Ad-soyad istənir
    asking_question = State()         # Suallar verilir
    waiting_for_receipt = State()     # Testdən sonra çek şəkli gözlənir