from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.enums import ParseMode
from aiogram.types import Message, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from datetime import datetime, timedelta
from decimal import Decimal
from services.phone_validation import validate_phone_number
from sqlalchemy import select, func, and_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload
import logging

from utils.database import async_session
from models.user import Client, Loan, Payment, CreditHistory
from models.base import LoanType, LoanStatus
from config import Config
from states import FormStates, LoanStates
from utils.calculations import *
from utils.auxiliary_funcs import *
from utils.generate_files import *

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

#Далее кредиты и платежи

@router.message(Command("my_loans"))
async def show_client_loans(message: types.Message):
    """Показывает все кредиты клиента"""
    async with async_session() as session:
        client = await session.execute(
            select(Client)
            .where(Client.telegram_id == message.from_user.id)
        )
        client = client.scalar()

        if not client:
            return await message.answer("ℹ Вы не зарегистрированы. Используйте /register")

        loans = await session.execute(
            select(Loan)
            .where(Loan.client_id == client.clientID)
            .order_by(Loan.issue_date.desc())
        )
        loans = loans.scalars().all()

        if not loans:
            return await message.answer("У вас нет активных кредитов")
            
        response = ["📋 <b>Ваши кредиты:</b>"]
        
        for loan in loans:
            status_emoji = "🟢" if loan.status == LoanStatus.ACTIVE else "🔴"
            response.append(
                f"{status_emoji} <b>Кредит #{loan.loan_id}</b>\n"
                f"Сумма: {loan.amount} руб.\n"
                f"Статус: {loan.status.value}\n"
                f"Остаток: {loan.remaining_amount} руб."
            )

        await message.answer(
            "\n\n".join(response),
            parse_mode=ParseMode.HTML
        )

@router.message(Command("take_loan"))
async def start_loan_process(message: types.Message, state: FSMContext):
    """Начало процесса оформления кредита"""
    async with async_session() as session:
        # Проверяем регистрацию клиента
        client = await session.execute(
            select(Client)
            .where(Client.telegram_id == message.from_user.id)
        )
        client = client.scalar()

        if not client:
            return await message.answer("ℹ Вы не зарегистрированы. Используйте /register")

        # Проверяем активные кредиты
        active_loans = await session.execute(
            select(func.count(Loan.loan_id))
            .where(
                and_(
                    Loan.client_id == client.clientID,
                    Loan.status == LoanStatus.ACTIVE
                )
            )
        )
        
        if active_loans.scalar() > 0:
            return await message.answer(
                "❌ У вас есть непогашенные кредиты. "
                "Новый кредит не может быть оформлен."
            )

        # Получаем доступные типы кредитов
        loan_types = await session.execute(select(LoanType))
        loan_types = loan_types.scalars().all()

        if not loan_types:
            return await message.answer("⚠ В настоящее время кредитные продукты недоступны")

        # Создаем клавиатуру с типами кредитов
        keyboard = types.ReplyKeyboardMarkup(
            keyboard=[
                [types.KeyboardButton(text=f"{lt.name} ({lt.interest_rate}%)")] 
                for lt in loan_types
            ],
            resize_keyboard=True,
            one_time_keyboard=True
        )

        await message.answer(
            "💰 <b>Выберите тип кредита:</b>",
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
        await state.set_state(LoanStates.choose_loan_type)

@router.message(LoanStates.choose_loan_type)
async def process_loan_type(message: types.Message, state: FSMContext):
    """Обработка выбора типа кредита"""
    async with async_session() as session:
        try:
            # Получаем выбранный тип кредита
            loan_type_name = message.text.split('(')[0].strip()
            loan_type = await session.execute(
                select(LoanType)
                .where(LoanType.name == loan_type_name)
            )
            loan_type = loan_type.scalar()

            if not loan_type:
                await message.answer("❌ Неверный тип кредита. Попробуйте еще раз.")
                return

            # Сохраняем данные в состоянии
            await state.update_data({
                'loan_type_id': loan_type.type_id,
                'min_amount': loan_type.min_amount,
                'max_amount': loan_type.max_amount,
                'min_term': loan_type.min_term,
                'max_term': loan_type.max_term,
                'interest_rate': loan_type.interest_rate
            })
            
            # Запрашиваем сумму кредита
            await message.answer(
                f"💵 Введите сумму кредита (от {loan_type.min_amount} до {loan_type.max_amount} руб.):",
                reply_markup=ReplyKeyboardRemove()
            )
            await state.set_state(LoanStates.enter_amount)

        except Exception as e:
            logging.error(f"Ошибка выбора типа кредита: {e}")
            await message.answer("⚠ Произошла ошибка. Попробуйте позже.")
            await state.clear()

@router.message(LoanStates.enter_amount)
async def process_loan_amount(message: types.Message, state: FSMContext):
    """Обработка суммы кредита"""
    try:
        data = await state.get_data()
        amount = Decimal(message.text.replace(',', '.'))
        
        if amount < data['min_amount'] or amount > data['max_amount']:
            raise ValueError(
                f"Сумма должна быть от {data['min_amount']} до {data['max_amount']} руб."
            )

        # Рассчитываем максимально доступную сумму
        async with async_session() as session:
            client = await session.execute(
                select(Client)
                .where(Client.telegram_id == message.from_user.id)
            )
            client = client.scalar()

            max_allowed = await calculate_max_loan_amount(client.clientID, session)
            if amount > max_allowed:
                raise ValueError(
                    f"Ваш кредитный рейтинг позволяет взять максимум {max_allowed} руб."
                )

        await state.update_data({'amount': amount})
        
        # Запрашиваем срок кредита
        await message.answer(
            f"⏳ Введите срок кредита в месяцах (от {int(data['min_term'])} до {int(data['max_term'])}):"
        )
        await state.set_state(LoanStates.enter_term)

    except ValueError as e:
        await message.answer(f"❌ Ошибка: {str(e)}")
    except Exception as e:
        logging.error(f"Ошибка ввода суммы: {e}")
        await message.answer("⚠ Произошла ошибка. Попробуйте позже.")
        await state.clear()

@router.message(LoanStates.enter_term)
async def process_loan_term(message: types.Message, state: FSMContext):
    """Обработка срока кредита"""
    try:
        term = int(message.text)
        data = await state.get_data()
        
        if term < data['min_term'] or term > data['max_term']:
            raise ValueError(
                f"Срок должен быть от {data['min_term']} до {data['max_term']} месяцев"
            )

        await state.update_data({'term': term})
        
        # Рассчитываем примерный платеж
        monthly_payment = calculate_monthly_payment(
            data['amount'],
            term,
            data['interest_rate']
        )
        
        # Показываем подтверждение
        keyboard = types.ReplyKeyboardMarkup(
            keyboard=[
                [types.KeyboardButton(text="✅ Подтвердить")],
                [types.KeyboardButton(text="❌ Отменить")]
            ],
            resize_keyboard=True
        )
        
        await message.answer(
            f"📋 <b>Детали кредита:</b>\n\n"
            f"Тип: {message.text.split('(')[0].strip()}\n"
            f"Сумма: {data['amount']} руб.\n"
            f"Срок: {term} мес.\n"
            f"Процентная ставка: {data['interest_rate']}%\n"
            f"Примерный ежемесячный платеж: ~{monthly_payment:.2f} руб.\n\n"
            "Подтверждаете оформление кредита?",
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
        await state.set_state(LoanStates.confirm_loan)

    except ValueError as e:
        await message.answer(f"❌ Ошибка: {str(e)}")
    except Exception as e:
        logging.error(f"Ошибка ввода срока: {e}")
        await message.answer("⚠ Произошла ошибка. Попробуйте позже.")
        await state.clear()

@router.message(LoanStates.confirm_loan, F.text == "✅ Подтвердить")
async def confirm_loan(message: types.Message, state: FSMContext):
    """Финальное подтверждение и оформление кредита"""
    async with async_session() as session:
        try:
            # Получаем данные из состояния
            data = await state.get_data()
            
            # Получаем клиента
            client = await session.execute(
                select(Client)
                .where(Client.telegram_id == message.from_user.id)
            )
            client = client.scalar()

            if not client:
                await message.answer("❌ Клиент не найден")
                await state.clear()
                return

            # Создаем новый кредит
            new_loan = Loan(
                client_id=client.clientID,
                loan_type_id=data['loan_type_id'],
                issue_date=datetime.utcnow(),
                amount=Decimal(data['amount']),
                term=data['term'],
                status=LoanStatus.ACTIVE,
                total_paid=Decimal('0.00'),
                remaining_amount=Decimal(data['amount'])
            )
            
            session.add(new_loan)
            await session.flush()  # Получаем loan_id
            
            # Генерируем график платежей
            
            payments = await generate_payment_schedule(
                loan_id=new_loan.loan_id,
                amount=Decimal(data['amount']),
                term=data['term'],
                interest_rate=data['interest_rate'],
                start_date=datetime.utcnow().date(),
                session=session
            )   
            
            # Добавляем платежи в сессию
            if payments:
                for payment in payments:
                    session.add(payment)
            else:
                logging.error("Нет платежей для обработки")
            
            # Обновляем кредитный рейтинг клиента
            client.creditScore = min(1000, client.creditScore + 10)  # Небольшой бонус за взятие кредита
            
            await session.commit()
            
            # Рассчитываем точный ежемесячный платеж
            monthly_payment = calculate_monthly_payment(
                Decimal(data['amount']),
                data['term'],
                data['interest_rate']
            )
            
            # Создаем CSV файл с графиком платежей
            csv_file = generate_payments_csv(payments, new_loan.loan_id)

            
            # Отправляем сообщение с деталями кредита
            await message.answer(
                "✅ <b>Кредит успешно оформлен!</b>\n\n"
                f"🔹 Номер кредита: #{new_loan.loan_id}\n"
                f"🔹 Сумма: {data['amount']} руб.\n"
                f"🔹 Срок: {data['term']} мес.\n"
                f"🔹 Процентная ставка: {data['interest_rate']}%\n"
                f"🔹 Ежемесячный платеж: {monthly_payment:.2f} руб.\n\n"
                "В прикрепленном файле график платежей:",
                reply_markup=ReplyKeyboardRemove(),
                parse_mode=ParseMode.HTML
            )
            
            # Отправляем файл пользователю
            await message.answer_document(csv_file)
            
        except Exception as e:
            await session.rollback()
            logging.error(f"Ошибка оформления кредита: {e}", exc_info=True)
            await message.answer(
                "⚠ Произошла ошибка при оформлении кредита. Попробуйте позже.",
                reply_markup=ReplyKeyboardRemove()
            )
        finally:
            await state.clear()

@router.message(LoanStates.confirm_loan, F.text == "❌ Отменить")
async def cancel_loan(message: types.Message, state: FSMContext):
    """Отмена оформления кредита"""
    await message.answer(
        "❌ Оформление кредита отменено",
        reply_markup=ReplyKeyboardRemove()
    )
    await state.clear()

        