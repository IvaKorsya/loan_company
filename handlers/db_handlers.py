from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.enums import ParseMode
from aiogram.types import Message, ReplyKeyboardRemove
from services.phone_validation import validate_phone_number
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from datetime import datetime
import logging

from utils.database import async_session
from models.user import Client
from config import Config
from states import FormStates

router = Router(name="client_handlers")

class ClientRegistrationForm:
    """Класс для многошаговой регистрации"""
    def __init__(self):
        self.fullName = None
        self.passport = None
        self.phone = None
        self.email = None

# Временное хранилище для форм (в продакшене используйте Redis)
temp_storage = {}



@router.message(Command("register"))
async def start_registration(message: types.Message):
    """Начало процесса регистрации"""
    form = ClientRegistrationForm()
    temp_storage[message.from_user.id] = form

    await message.answer(
        "📝 Регистрация в кредитной системе\n\n"
        "Введите ваше <b>полное ФИО</b>:",
        parse_mode=ParseMode.HTML
    )

@router.message(Command("me"))
async def view_personal_info(message: types.Message):
    """Просмотр личной информации с защитой данных"""
    async with async_session() as session:
        result = await session.execute(
            select(Client)
            .where(Client.telegram_id == message.from_user.id)
        )
        client = result.scalar()

        if not client:
            return await message.answer("ℹ Вы не зарегистрированы. Используйте /register")

        # Форматируем дату регистрации
        reg_date = client.registration_date.strftime("%d.%m.%Y")

        # Форматируем телефон (показываем только последние 4 цифры)
        masked_phone = client.phone_numbers[0][:-4] + "****" if client.phone_numbers else "Не указан"

        # Форматируем email (показываем только часть)
        email_parts = client.email.split("@") if client.email else []
        masked_email = f"{email_parts[0][:2]}****@{email_parts[1]}" if len(email_parts) == 2 else "Не указан"

        response = (
            "👤 <b>Ваш личный кабинет</b>\n\n"
            f"<b>ID клиента:</b> {client.clientID}\n"
            f"<b>ФИО:</b> {client.fullName}\n"
            f"<b>Телефон:</b> {masked_phone}\n"
            f"<b>Email:</b> {masked_email}\n"
            f"<b>Дата регистрации:</b> {reg_date}\n"
            f"<b>Кредитный рейтинг:</b> {client.creditScore}/1000\n\n"
            "🔒 <i>Конфиденциальные данные защищены</i>"
        )

        await message.answer(response, parse_mode=ParseMode.HTML)

@router.message(Command("credit_info"))
async def view_credit_info(message: types.Message):
    """
    Показывает детальную информацию о кредитном рейтинге пользователя
    с историей изменений и рекомендациями.
    """
    async with async_session() as session:
        try:
            # Получаем данные клиента
            client = await session.execute(
                select(Client)
                .where(Client.telegram_id == message.from_user.id)
            )
            client = client.scalar()

            if not client:
                return await message.answer(
                    "❌ Вы не зарегистрированы в системе.\n"
                    "Используйте /register для регистрации."
                )

            # Форматируем сообщение
            rating_emoji = "⭐️" * (client.creditScore // 200)
            reg_date = client.registration_date.strftime("%d.%m.%Y")

            msg = [
                f"<b>💳 Кредитный рейтинг:</b> {client.creditScore}/1000 {rating_emoji}",
                f"<b>📅 Дата регистрации:</b> {reg_date}",
                "",
                "<b>📊 Ваш статус:</b>",
                get_credit_status(client.creditScore),
                "",
                "<b>🔍 Рекомендации:</b>",
                get_credit_advice(client.creditScore)
            ]

            await message.answer(
                "\n".join(msg),
                parse_mode=ParseMode.HTML
            )

        except Exception as e:
            logging.error(f"Ошибка при запросе кредитного рейтинга: {e}")
            await message.answer(
                "⚠️ Не удалось получить информацию. Попробуйте позже."
            )

def get_credit_status(score: int) -> str:
    """Возвращает текстовый статус в зависимости от рейтинга"""
    if score >= 800:
        return "Отличный - высокий приоритет одобрения"
    elif score >= 600:
        return "Хороший - стандартные условия"
    elif score >= 400:
        return "Удовлетворительный - повышенные ставки"
    else:
        return "Низкий - требуется дополнительная проверка"

def get_credit_advice(score: int) -> str:
    """Генерирует рекомендации для улучшения рейтинга"""
    advice = []
    if score < 700:
        advice.append("- Своевременно погашайте кредиты")
    if score < 500:
        advice.append("- Увеличьте частоту использования сервиса")
    if score < 300:
        advice.append("- Обратитесь в отделение для консультации")

    return "\n".join(advice) if advice else "Ваш рейтинг оптимальный!"

@router.message(Command("update_contact"))
async def start_contact_update(message: types.Message):
    """Обновление контактных данных"""
    buttons = [
        [types.KeyboardButton(text="📱 Изменить телефон", )],
        [types.KeyboardButton(text="📧 Изменить email")],
        [types.KeyboardButton(text="❌ Отмена")]
    ]
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True,
        one_time_keyboard=True
    )

    await message.answer(
        "Какие данные вы хотите обновить?",
        reply_markup=keyboard
    )

@router.message(F.text == "📱 Изменить телефон")
async def start_phone_update(message: Message, state: FSMContext):
    """Запуск процесса изменения телефона"""
    await message.answer(
        "Введите новый номер телефона в формате +7XXXYYYYYYY:",
        reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(FormStates.waiting_for_phone)

@router.message(FormStates.waiting_for_phone)
async def process_new_phone(message: Message, state: FSMContext):
    """Обработка нового номера телефона"""
    try:
        # Валидация номера
        phone = validate_phone_number(message.text)

        async with async_session() as session:
            # Обновляем номер в БД
            client = await session.execute(
                select(Client)
                .where(Client.telegram_id == message.from_user.id)
            )
            client = client.scalar()

            if not client:
                await message.answer("❌ Профиль не найден")
                return

            client.phone_numbers = [phone]
            await session.commit()

        await message.answer("✅ Номер телефона успешно обновлен!")
        await state.clear()

    except ValueError as e:
        await message.answer(f"❌ Ошибка: {e}\nПопробуйте еще раз:")
    except Exception as e:
        logging.error(f"Phone update error: {e}")
        await message.answer("⚠️ Произошла ошибка. Попробуйте позже.")
        await state.clear()

@router.message(F.text, lambda msg: msg.from_user.id in temp_storage and not temp_storage[msg.from_user.id].fullName)
async def process_full_name(message: types.Message):
    """Обработка ФИО"""
    form = temp_storage[message.from_user.id]
    form.fullName = message.text

    await message.answer(
        "🔐 Введите <b>серию и номер паспорта</b> (10 цифр):\n"
        "<i>Пример: 4510123456</i>",
        parse_mode=ParseMode.HTML
    )

@router.message(F.text, lambda msg: msg.from_user.id in temp_storage and not temp_storage[msg.from_user.id].passport)
async def process_passport(message: types.Message):
    """Обработка паспортных данных"""
    if not message.text.isdigit() or len(message.text) != 10:
        return await message.answer("❌ Неверный формат паспорта. Введите 10 цифр.")

    form = temp_storage[message.from_user.id]
    form.passport = message.text

    await message.answer(
        "📱 Введите <b>номер телефона</b> (с кодом страны):\n"
        "<i>Пример: +79161234567</i>",
        parse_mode=ParseMode.HTML
    )

@router.message(F.text, lambda msg: msg.from_user.id in temp_storage and not temp_storage[msg.from_user.id].phone)
async def process_phone(message: types.Message):
    """Обработка телефона"""
    try:
        form = temp_storage[message.from_user.id]
        form.phone = Client.validate_phone(message.text)

        await message.answer(
            "📧 Введите <b>email</b> (необязательно):\n"
            "<i>Пропустите, если не хотите указывать</i>",
            parse_mode=ParseMode.HTML
        )
    except ValueError as e:
        await message.answer(f"❌ Ошибка: {str(e)}")

@router.message(F.text, lambda msg: msg.from_user.id in temp_storage and not temp_storage[msg.from_user.id].email)
async def process_email(message: types.Message):
    """Обработка email и финальное сохранение"""
    form = temp_storage.pop(message.from_user.id)
    email = message.text if "@" in message.text else None

    async with async_session() as session:
        try:
            # Проверяем существующего пользователя
            existing = await session.execute(
                select(Client).where(
                    (Client.telegram_id == message.from_user.id) |
                    (Client.passport == form.passport)
                )
            )

            if existing.scalar():
                return await message.answer("⚠ Вы уже зарегистрированы!")

            # Создаем нового клиента
            client = Client(
                fullName=form.fullName,
                passport=form.passport,
                telegram_id=message.from_user.id,
                phone_numbers=[form.phone],
                email=email,
                creditScore=300  # Начальный кредитный рейтинг
            )

            session.add(client)
            await session.commit()

            await message.answer(
                "✅ Регистрация завершена!\n\n"
                f"<b>Ваш ID:</b> {client.clientID}\n"
                f"<b>Кредитный рейтинг:</b> {client.creditScore}",
                parse_mode=ParseMode.HTML
            )

        except IntegrityError:
            await session.rollback()
            await message.answer("❌ Ошибка регистрации. Пожалуйста, обратитесь в поддержку.")

@router.message(Command("my_profile"))
async def show_profile(message: types.Message):
    """Показывает профиль клиента"""
    async with async_session() as session:
        client = await session.execute(
            select(Client)
            .where(Client.telegram_id == message.from_user.id)
        )
        client = client.scalar()

        if not client:
            return await message.answer("ℹ Вы не зарегистрированы. Используйте /register")

        safe_data = client.to_safe_schema()

        await message.answer(
            "👤 <b>Ваш профиль</b>\n\n"
            f"<b>ID:</b> {safe_data.clientID}\n"
            f"<b>ФИО:</b> {safe_data.fullName}\n"
            f"<b>Дата регистрации:</b> {safe_data.registration_date.strftime('%d.%m.%Y')}\n"
            f"<b>Кредитный рейтинг:</b> {safe_data.creditScore}",
            parse_mode=ParseMode.HTML
        )