from aiogram import Router, F
from aiogram.types import Message, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove, PhotoSize
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from states.quiz import QuizStates
from data.questions import questions
from config import config
import sqlite3
from datetime import datetime

router = Router()

# /start komandası
@router.message(F.text == "/start")
async def cmd_start(message: Message, state: FSMContext):
    data = await state.get_data()
    user_approved = data.get("user_approved", False)
    attempt_count = data.get("attempt_count", 0)

    try:
        conn = sqlite3.connect("quiz_users.db")
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                full_name TEXT,
                joined_at TEXT
            )
        """)
        user_id = message.from_user.id
        full_name = f"{message.from_user.first_name or ''} {message.from_user.last_name or ''}".strip()
        joined_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.execute("INSERT OR IGNORE INTO users (user_id, full_name, joined_at) VALUES (?, ?, ?)",
                  (user_id, full_name, joined_at))
        conn.commit()
        conn.close()
    except Exception as e:
        print("DB error:", e)

    if not user_approved:
        if attempt_count == 0:
            await message.answer("📥 İmtahana başlamaq üçün zəhmət olmasa ad və soyadınızı yazın.")
            await state.set_state(QuizStates.waiting_for_name)
        else:
            await message.answer(
                "📌 Diqqət! Bu imtahanda yalnız bir dəfə pulsuz iştirak etmək mümkündür.\n\n"
                "🔁 Təkrar iştirak üçün aşağıdakı rekvizitə 1.30 AZN məbləğində ödəniş etməlisiniz:\n\n"
                "💳 Kart nömrəsi: 4127 2141 2489 5464\n\n"
                "📸 Ödənişi etdikdən sonra qəbzin şəklini bu mesaja cavab olaraq göndərin.\n"
                "🛡️ Administrator tərəfindən təsdiqləndikdən sonra imtahana giriş hüququ əldə edəcəksiniz."
            )
            await state.set_state(QuizStates.waiting_for_receipt)
        return

    await message.answer("📥 İmtahana başlamaq üçün ad və soyadınızı yazın.")
    await state.set_state(QuizStates.waiting_for_name)

@router.message(QuizStates.waiting_for_name)
async def get_name(message: Message, state: FSMContext):
    await state.update_data(full_name=message.text, score=0, current_question=0)
    await message.answer("✅ Təşəkkür edirik. İmtahan başlayır.")
    await ask_next_question(message, state)

async def ask_next_question(message: Message, state: FSMContext):
    data = await state.get_data()
    q_index = data["current_question"]

    if q_index >= len(questions):
        user = message.from_user
        score = data['score']
        full_name = data['full_name']

        if score < 15:
            result_msg = "❌ Təəssüf! Siz imtahandan keçə bilmədiniz."
        elif score in [15, 16]:
            result_msg = "🥉 Siz III dərəcəli sertifikata layiq görüldünüz."
        elif score in [17, 18]:
            result_msg = "🥈 Təbriklər! Siz II dərəcəli sertifikat qazandınız."
        elif score in [19, 20]:
            result_msg = "🏆 Təbriklər! Siz ən yüksək nəticə ilə I dərəcəli sertifikata layiq görüldünüz."
        else:
            result_msg = "✔️ İmtahan tamamlandı."

        result = (
            f"📊 İmtahan tamamlandı.\n"
            f"🔢 Nəticə: {score} / {len(questions)}\n\n"
            f"{result_msg}\n\n"
            "📢 Təkrar imtahan üçün /start yazın."
        )

        await message.answer(result, reply_markup=ReplyKeyboardRemove())

        await message.bot.send_message(
            config.admin_id,
            f"📋 Yeni iştirakçı imtahanı bitirdi:\n"
            f"👤 Ad: {full_name}\n"
            f"🆔 Telegram ID: {user.id}\n"
            f"✅ Nəticə: {score} / {len(questions)}"
        )

        await state.update_data(user_approved=False, attempt_count=1)
        await state.set_state(QuizStates.waiting_for_receipt)
        return

    q = questions[q_index]
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=opt)] for opt in q["options"]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    sent = await message.answer(f"{q_index + 1}) {q['question']}", reply_markup=keyboard)
    await state.update_data(last_question_msg_id=sent.message_id)
    await state.set_state(QuizStates.asking_question)

@router.message(QuizStates.asking_question)
async def handle_answer(message: Message, state: FSMContext):
    try:
        await message.delete()
    except:
        pass

    data = await state.get_data()
    q_index = data["current_question"]
    q = questions[q_index]

    score = data["score"]
    if message.text == q["correct"]:
        score += 1

    last_question_msg_id = data.get("last_question_msg_id")
    if last_question_msg_id:
        try:
            await message.bot.delete_message(chat_id=message.chat.id, message_id=last_question_msg_id)
        except:
            pass

    await state.update_data(score=score, current_question=q_index + 1)
    await ask_next_question(message, state)

@router.message(QuizStates.waiting_for_receipt, F.photo)
async def handle_receipt_photo(message: Message, state: FSMContext):
    data = await state.get_data()
    user = message.from_user
    photo: PhotoSize = message.photo[-1]

    await message.bot.send_photo(
        config.admin_id,
        photo.file_id,
        caption=(
            f"📥 Yeni ödəniş sorğusu:\n"
            f"👤 Ad: {data.get('full_name', 'Naməlum')}\n"
            f"🆔 Telegram ID: {user.id}\n"
            f"💳 Status: Yoxlanma gözləyir\n\n"
            f"🔐 Təsdiq üçün: /approve_{user.id}"
        )
    )

    await message.answer(
        "📤 Təşəkkür edirik! Ödəniş qəbziniz uğurla alındı və yoxlanış üçün administratora yönləndirildi.\n\n"
        "⏳ Zəhmət olmasa, təsdiq üçün növbəti mesajımı gözləyin.\n"
        "✅ Narahat olmayın, təsdiqləndikdən sonra imtahana yenidən başlaya biləcəksiniz."
    )
    await state.clear()

@router.message(QuizStates.waiting_for_receipt)
async def receipt_invalid(message: Message):
    await message.answer("Təkrar imtahanda iştirak etmək üçün 1.30 AZN məbləğində ödənişi \n"
                         "4127 2141 2489 5464 - nömrəli kart hesabına köçürüb,\n"
                         "📸 ödəniş qəbzinin şəklini göndərin.\n"
                         "Administrator tərəfindən təsdiqləndikdən sonra imtahana yenidən başlaya biləcəksiniz.\n\n"
                         "Xahiş olunur, yalnız qəbz şəklini göndərin.")

@router.message(F.text.startswith("/approve_"))
async def approve_user(message: Message, state: FSMContext):
    if message.from_user.id != config.admin_id:
        await message.answer("❌ Bu əmri yalnız administrator icra edə bilər.")
        return

    try:
        user_id_str = message.text.split("_")[1]
        user_id = int(user_id_str.strip())
    except (IndexError, ValueError):
        await message.answer("❌ Yanlış format! /approve_123456789 şəklində yazın.")
        return

    bot_id = message.bot.id
    storage_key = StorageKey(chat_id=user_id, user_id=user_id, bot_id=bot_id)
    user_context = FSMContext(storage=state.storage, key=storage_key)

    await user_context.update_data(user_approved=True, attempt_count=0)
    await user_context.set_state(None)

    await message.bot.send_message(
        user_id,
        "✅ Ödənişiniz administrator tərəfindən təsdiqləndi!\n"
        "📚 İndi /start -toxunub, imtahana yenidən başlaya bilərsiniz.\n\n"
        "Uğurlar!"
    )

    await message.answer(f"👍 İstifadəçi {user_id} uğurla təsdiqləndi.")

@router.message(F.text == "/qebul_olunanlar")
async def list_approved_users(message: Message):
    if message.from_user.id != config.admin_id:
        return

    try:
        conn = sqlite3.connect("quiz_users.db")
        c = conn.cursor()
        c.execute("SELECT full_name, user_id, joined_at FROM users")
        rows = c.fetchall()
        conn.close()

        if not rows:
            await message.answer("📭 Heç bir iştirakçı qeyd olunmayıb.")
            return

        msg = "📋 Qeydiyyatdan keçmiş iştirakçılar:\n\n"
        for name, uid, joined in rows:
            msg += f"👤 {name}\n🆔 {uid}\n📅 Tarix: {joined}\n\n"

        await message.answer(msg)

    except Exception as e:
        await message.answer("❌ Məlumatlar oxunarkən xəta baş verdi.")
        print("DB read error:", e)
