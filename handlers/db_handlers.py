from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.enums import ParseMode
from aiogram.types import Message, ReplyKeyboardRemove
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_DOWN
from sqlalchemy import select, func, and_, delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload
import logging
import math

from utils.database import async_session
from models import LoanType, Client, Loan, Payment
from config import Config
from states import *
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
        client = await check_client_registered(message, session)
        if not client:
            return
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
            client = await check_client_registered(message, session)
            if not client:
                return

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
        phone = Client.validate_phone(message.text)

        async with async_session() as session:
            # Обновляем номер в БД
            client = await check_client_registered(message, session)
            if not client:
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
        client = await check_client_registered(message, session)
        if not client:
            return

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

#ПРОСМОТР ПЛАНА ПЛАТЕЖЕЙ С ВЫБОРОМ КРЕДИТА 
@router.message(Command("payments_plan"))
async def choose_loan_for_schedule(message: Message):
    """Команда для выбора кредита и просмотра графика платежей"""
    try:
        async with async_session() as session:
            # Сначала находим клиента по telegram_id
            client = await check_client_registered(message, session)
            if not client:
                return

            # Ищем активные кредиты только этого клиента
            active_loans = await session.scalars(
                select(Loan)
                .where(
                    (Loan.client_id == client.clientID) &
                    (Loan.status.in_([LoanStatus.ACTIVE, LoanStatus.OVERDUE]))
                )
                .order_by(Loan.loan_id.asc())
            )
            active_loans = active_loans.all()
        
        if not active_loans:
            await message.answer("ℹ У вас нет активных кредитов.")
            return
        
        # Формируем клавиатуру
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=f"Кредит #{loan.loan_id} на {loan.amount:.2f} руб.",
                        callback_data=f"show_schedule_{loan.loan_id}"
                    )
                ]
                for loan in active_loans
            ]
        )
        
        await message.answer(
            "🔹 Выберите кредит, чтобы посмотреть график платежей:",
            reply_markup=keyboard
        )
        
    except Exception as e:
        logging.error(f"Ошибка при выборе кредита для графика: {e}", exc_info=True)
        await message.answer("⚠ Произошла ошибка при получении списка кредитов.")

@router.callback_query(F.data.startswith("show_schedule_"))
async def show_schedule_handler(callback: CallbackQuery, state: FSMContext):
    """Выводит график платежей по выбранному кредиту"""
    try:
        # Открываем сессию
        async with async_session() as session:
            loan_id_str = callback.data.replace("show_schedule_", "")
            if not loan_id_str.isdigit():
                await callback.message.answer("❌ Некорректный идентификатор кредита")
                return

            loan_id = int(loan_id_str)

            # Вызываем функцию для отображения графика сессией
            success = await show_payment_schedule(callback.message, loan_id, session)

            if success:
                await callback.answer()
            else:
                await callback.answer("Не удалось получить график", show_alert=True)

    except Exception as e:
        logging.error(f"Ошибка в show_schedule_handler: {e}", exc_info=True)
        await callback.message.answer("⚠ Произошла ошибка при обработке запроса.")
        await callback.answer("Ошибка", show_alert=True)

#ПРОСМОТР КРЕДИТОВ
@router.message(Command("my_loans"))
async def show_client_loans(message: types.Message):
    """Показывает все кредиты клиента"""
    async with async_session() as session:
        client = await check_client_registered(message, session)
        if not client:
            return

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
                f"Остаток без процентов: {loan.remaining_amount} руб."
            )

        await message.answer(
            "\n\n".join(response),
            parse_mode=ParseMode.HTML
        )

#ВЫДАЧА КРЕДИТОВ
@router.message(Command("take_loan"))
async def start_loan_process(message: types.Message, state: FSMContext):
    """Начало процесса оформления кредита"""
    async with async_session() as session:
        # Проверяем регистрацию клиента
        client = await check_client_registered(message, session)
        if not client:
            return

        # Проверяем активные кредиты
        active_loans = await session.execute(
            select(func.count(Loan.loan_id))
            .where(
                and_(
                    Loan.client_id == client.clientID,
                    Loan.status.in_([LoanStatus.ACTIVE, LoanStatus.OVERDUE])
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
            client = await check_client_registered(message, session)
            if not client:
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

#ВНЕСЕНИЕ ПЛАТЕЖА С ПЕРЕРАСЧЕТОМ ПЛАТЕЖЕЙ ПРИ СУММЕ БОЛЬШЕЙ, ЧЕМ НУЖНО 
@router.message(Command("make_payment"))
async def start_payment_process(message: types.Message, state: FSMContext):
    """Более компактная версия с проверками"""
    async with async_session() as session:
        client = await check_client_registered(message, session)
        if not client:
            return

        loans = await session.scalars(
            select(Loan)
            .where(Loan.client_id == client.clientID)
            .where(Loan.status.in_([LoanStatus.ACTIVE, LoanStatus.OVERDUE])
        ))
        loans = loans.all()  # Получаем все записи
        
        if not loans:
            return await message.answer("У вас нет активных кредитов для погашения")

        # Логируем количество найденных кредитов для отладки
        print(f"Found {len(loans)} active loans for client {client.clientID}")

        await state.update_data(loans={loan.loan_id: loan for loan in loans})
        
        # Создаем кнопки для кредитов (максимум 10 чтобы не перегружать интерфейс)
        loan_buttons = [
            [types.KeyboardButton(text=f"Кредит #{l.loan_id} - {l.amount:,.2f}₽")] 
            for l in loans[:10]  # Ограничиваем количество
        ]
        
        # Добавляем кнопку отмены
        loan_buttons.append([types.KeyboardButton(text="❌ Отмена")])
        
        kb = types.ReplyKeyboardMarkup(
            keyboard=loan_buttons,
            resize_keyboard=True,
            one_time_keyboard=True
        )
        
        await message.answer(
            f"Выберите кредит (доступно {len(loans)}):",
            reply_markup=kb
        )
        await state.set_state(PaymentStates.choose_loan)

@router.message(PaymentStates.choose_loan, F.text.regexp(r'Кредит #\d+'))
async def choose_loan_for_payment(message: types.Message, state: FSMContext):
    """Обработка выбора кредита с использованием существующих платежей из БД"""
    try:
        loan_id = int(message.text.split('#')[1].split()[0])
        
        async with async_session() as session:
            # Получаем данные по кредиту
            loan = await session.get(Loan, loan_id)
            if not loan:
                await message.answer("❌ Кредит не найден")
                await state.clear()
                return
            
            # Получаем все платежи по кредиту из БД
            payments = await session.scalars(
                select(Payment)
                .where(Payment.loan_id == loan_id)
                .order_by(Payment.payment_date_plan)
            )
            payments = payments.all()

            # Рассчитываем общую сумму оплаченных платежей
            total_paid = sum(
                Decimal(str(p.actual_amount)) 
                for p in payments 
                if p.actual_amount is not None
            )
            
            # Обновляем остаток долга
            loan.remaining_amount = loan.amount - total_paid

            # Находим следующий платеж (первый неоплаченный)
            next_payment = await session.scalar(
                select(Payment)
                .where(Payment.loan_id == loan_id)
                .where(Payment.payment_date_fact.is_(None))
                .order_by(Payment.payment_date_plan.asc())
                .limit(1)
            )

            # Находим просроченные платежи
            today = date.today()
            overdue_payments = await session.scalars(
                select(Payment)
                .where(Payment.loan_id == loan_id)
                .where(Payment.payment_date_plan < today)
                .where(Payment.payment_date_fact.is_(None))
                .order_by(Payment.payment_date_plan.asc())
            )
            overdue_payments = overdue_payments.all()

            # Рассчитываем пени (если есть просрочки)
            penalty_amount = Decimal('0')
            if overdue_payments:
                for payment in overdue_payments:
                    days_overdue = (today - payment.payment_date_plan).days
                    penalty_rate = Decimal('0.01')  # 1% в день
                    penalty = Decimal(str(payment.planned_amount)) * penalty_rate * days_overdue
                    penalty_amount += penalty

                    # Добавляем запись о пени, если ее еще нет
                    existing_penalty = await session.scalar(
                        select(Payment)
                        .where(Payment.loan_id == loan_id)
                        .where(Payment.penalty_date == today)
                        .where(Payment.payment_date_plan == payment.payment_date_plan)
                    )
                    
                    if not existing_penalty:
                        penalty_payment = Payment(
                            loan_id=loan_id,
                            payment_date_plan=payment.payment_date_plan,
                            planned_amount=payment.planned_amount,
                            payment_date_fact=None,
                            actual_amount=0,
                            penalty_date=today,
                            penalty_amount=float(penalty)
                        )
                        session.add(penalty_payment)
                
                await session.commit()

            # Сохраняем данные для следующего шага
            await state.update_data(
                loan_id=loan_id,
                current_loan=loan,
                penalty_amount=float(penalty_amount),
                next_payment_date=next_payment.payment_date_plan if next_payment else None,
                next_payment_amount=Decimal(str(next_payment.planned_amount)) if next_payment else None
            )

            # Формируем информационное сообщение
            msg = [
                f"<b>Кредит #{loan_id}</b>",
                f"🔹 Сумма: {loan.amount:.2f} руб.",
                f"🔹 Срок: {loan.term} мес.",
                f"🔹 Погашено: {total_paid:.2f} руб.",
                f"🔹 Остаток: {loan.remaining_amount:.2f} руб."
            ]

            if next_payment:
                msg.append(f"🔹 След. платеж: {next_payment.payment_date_plan.strftime('%d.%m.%Y')}")
                msg.append(f"🔹 Сумма платежа: {next_payment.planned_amount:.2f} руб.")
            
            if overdue_payments:
                days_overdue = (today - overdue_payments[0].payment_date_plan).days
                msg.append(f"⚠ <b>Просрочка:</b> {days_overdue} дней")
            
            if penalty_amount > 0:
                msg.append(f"⚠ <b>Пени:</b> {penalty_amount:.2f} руб. (1%/день)")

            msg.append("\nВведите сумму платежа:")
            
            await message.answer(
                "\n".join(msg),
                reply_markup=types.ReplyKeyboardRemove(),
                parse_mode=ParseMode.HTML
            )
            await state.set_state(PaymentStates.enter_amount)

    except Exception as e:
        logging.error(f"Ошибка при выборе кредита: {e}", exc_info=True)
        await message.answer("⚠ Ошибка при обработке кредита")
        await state.clear()

@router.message(PaymentStates.enter_amount, F.text.regexp(r'^\d+(\.\d{1,2})?$'))
async def process_payment_amount(message: types.Message, state: FSMContext):
    '''Обработка суммы платежа с перерасчетом платежей если сумма больше, чем нужно'''
    try:
        amount = Decimal(message.text)
        if amount <= 0:
            raise ValueError("Сумма должна быть больше нуля")
            
        data = await state.get_data()
        loan_id = data['loan_id']
        current_date = date.today()
        
        async with async_session() as session:
            # Получаем данные по кредиту
            loan = await session.get(Loan, loan_id)
            if not loan:
                await message.answer("❌ Кредит не найден")
                await state.clear()
                return
            
            # Ищем платеж для проверки минимальной суммы
            payment = await session.scalar(
                select(Payment)
                .where(Payment.loan_id == loan_id)
                .where(Payment.payment_date_fact.is_(None))
                .order_by(Payment.payment_date_plan.asc())
                .limit(1)
            )
            
            if not payment:
                await message.answer("ℹ Нет платежей для погашения")
                await state.clear()
                return
            
            min_payment = Decimal(str(payment.planned_amount))
            
            # Проверяем превышение суммы долга
            if amount > loan.remaining_amount:
                amount = loan.remaining_amount
                await message.answer(
                    f"⚠ Сумма превышает остаток долга. Будет зачислено {amount:.2f} руб."
                )
            
            # Проверяем, превышает ли сумма минимальный платеж
            if round(amount, 2) > round(min_payment, 2):
                # Сохраняем предложенную сумму в состоянии
                await state.update_data(proposed_amount=amount)
                
                # Создаем инлайн-клавиатуру
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="Подтвердить и пересчитать",
                            callback_data="confirm_recalculate"
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            text="Ввести другую сумму",
                            callback_data="enter_new_amount"
                        )
                    ]
                ])
                
                await message.answer(
                    f"ℹ Введенная сумма ({amount:.2f} руб.) превышает ежемесячный платеж ({min_payment:.2f} руб.).\n"
                    "Выберите действие:",
                    reply_markup=keyboard
                )
                return
                
            # Проверяем минимальную сумму
            if round(amount, 2) < round(min_payment, 2):
                await message.answer(
                    f"❌ Сумма платежа ({amount:.2f} руб.) меньше минимального платежа ({min_payment:.2f} руб.).\n"
                    "Пожалуйста, введите сумму, равную или большую минимального платежа:"
                )
                return
            
            # Обновляем платеж
            await update_payment_and_loan(session, payment, loan, amount, current_date, loan_id)
            
            # Проверяем, если кредит полностью закрыт
            if loan.remaining_amount <= 0:
                # Завершаем кредит
                loan.remaining_amount = Decimal('0')
                loan.next_payment_date = None
                loan.status = LoanStatus.CLOSED  # Используем значение из перечисления
                
                # Удаляем все будущие неоплаченные платежи
                await session.execute(
                    delete(Payment)
                    .where(Payment.loan_id == loan_id)
                    .where(Payment.payment_date_fact.is_(None))
                )
                await session.commit()

            # Формируем сообщение
            response_msg = (
                "✅ <b>Платеж успешно зачислен!</b>\n\n"
                f"🔹 Номер кредита: #{loan_id}\n"
                f"🔹 Сумма платежа: {amount:.2f} руб.\n"
                f"🔹 Остаток долга: {loan.remaining_amount:.2f} руб.\n"
                f"🔹 След. платеж: {loan.next_payment_date.strftime('%d.%m.%Y') if loan.next_payment_date else 'нет'}\n\n"
                "Спасибо за своевременный платеж!"
            )
            
            await message.answer(response_msg, parse_mode=ParseMode.HTML)
            await state.clear()
            
    except ValueError as e:
        await message.answer(f"❌ Ошибка: {str(e)}\nПожалуйста, введите корректную сумму:")
    except Exception as e:
        logging.error(f"Ошибка при обработке платежа: {e}", exc_info=True)
        await message.answer("⚠ Произошла ошибка при обработке платежа. Попробуйте позже.")
        await state.clear()


@router.callback_query(F.data == "confirm_recalculate")
async def confirm_recalculate(callback: types.CallbackQuery, state: FSMContext):
    '''Обработка подтверждения суммы с пересчетом платежей'''
    try:
        data = await state.get_data()
        amount = Decimal(data['proposed_amount'])
        loan_id = data['loan_id']
        current_date = date.today()
        
        async with async_session() as session:
            # Получаем кредит с загруженным типом
            loan = await session.get(Loan, loan_id, options=[joinedload(Loan.loan_type)])
            if not loan:
                await callback.message.answer("❌ Кредит не найден")
                await state.clear()
                return
                
            # Проверяем наличие типа кредита и процентной ставки
            if not loan.loan_type or not hasattr(loan.loan_type, 'interest_rate'):
                await callback.message.answer("❌ Не удалось определить процентную ставку по кредиту")
                await state.clear()
                return
                
            # Находим первый непогашенный платеж
            payment = await session.scalar(
                select(Payment)
                .where(Payment.loan_id == loan_id)
                .where(Payment.payment_date_fact.is_(None))
                .order_by(Payment.payment_date_plan.asc())
                .limit(1)
            )
            
            if not payment:
                await callback.message.answer("ℹ Нет платежей для погашения")
                await state.clear()
                return
            
            # 1. Отмечаем текущий платеж как оплаченный
            payment.payment_date_fact = current_date
            payment.actual_amount = amount
            
            # 2. Вычисляем новый остаток
            remaining_amount = loan.remaining_amount - amount
            
            # 3. Удаляем только будущие неоплаченные платежи
            await session.execute(
                delete(Payment)
                .where(Payment.loan_id == loan_id)
                .where(Payment.payment_date_plan > payment.payment_date_plan)
                .where(Payment.payment_date_fact.is_(None))
            )
            
            # 4. Вычисляем оставшийся срок
            remaining_term = loan.term - (await session.scalar(
                select(func.count(Payment.payment_id))
                .where(
                    (Payment.loan_id == loan_id) &
                    (Payment.payment_date_fact.is_not(None))
                )
            ))
            
            # 5. Определяем дату старта новых платежей — следующий месяц после текущего платежа
            # Получаем последний плановый платеж
            last_payment = await session.scalar(
                select(Payment)
                .where(Payment.loan_id == loan_id)
                .order_by(Payment.payment_date_plan.desc())
                .limit(1))
            start_date = last_payment.payment_date_plan if last_payment else date.today()

            
            # 6. Генерируем новый график платежей
            new_payments = await generate_payment_schedule(
                loan_id=loan_id,
                amount=remaining_amount,
                term=remaining_term,
                interest_rate=loan.loan_type.interest_rate,
                start_date=start_date,
                session=session
            )

            
            # 7. Обновляем данные кредита
            loan.remaining_amount = remaining_amount
            loan.next_payment_date = new_payments[0].payment_date_plan if new_payments else None

            # Завершаем кредит, если остаток 0
            if loan.remaining_amount <= 0:
                loan.status = LoanStatus.CLOSED  # Если такое поле есть
                loan.next_payment_date = None

            # 8. Коммитим изменения
            await session.commit()
            
            # Формируем сообщение
            response_msg = (
                "✅ <b>Платеж успешно зачислен!</b>\n\n"
                f"🔹 Номер кредита: #{loan_id}\n"
                f"🔹 Сумма платежа: {amount:.2f} руб.\n"
                f"🔹 Остаток долга: {remaining_amount:.2f} руб.\n"
                f"🔹 След. платеж: {loan.next_payment_date.strftime('%d.%m.%Y') if loan.next_payment_date else 'нет'}\n\n"
                "Спасибо за своевременный платеж!"
            )
            
            await callback.message.edit_text(response_msg, parse_mode=ParseMode.HTML)
            await state.clear()
            
    except Exception as e:
        logging.error(f"Ошибка при подтверждении платежа: {e}", exc_info=True)
        await callback.message.answer("⚠ Произошла ошибка при обработке платежа. Попробуйте позже.")
        await state.clear()

@router.callback_query(F.data == "enter_new_amount")
async def enter_new_amount(callback: types.CallbackQuery, state: FSMContext):
    '''Обработка запроса на ввод новой суммы'''
    await callback.message.edit_text("Пожалуйста, введите новую сумму платежа:")
    await state.set_state(PaymentStates.enter_amount)

#ВЫДАЧА РАЗРЕШЕНИЯ НА КРЕДИТ
@router.message(Command("check_credit"))
async def check_credit_status(message: Message, state: FSMContext):
    """Проверка кредитного рейтинга клиента и возможность получения кредита"""
    async with async_session() as session:
        client = await check_client_registered(message, session)
        if not client:
            return

        # Проверка на наличие активных или просроченных кредитов
        active_or_overdue_loans = await session.scalars(
            select(Loan).where(
                Loan.client_id == client.clientID,
                Loan.status.in_([LoanStatus.ACTIVE, LoanStatus.OVERDUE])
            )
        )
        loans_list = active_or_overdue_loans.all()
        # Получаем кредитный рейтинг клиента
        credit_score = client.creditScore  
        
        # Получаем текущий статус кредита
        credit_status = get_credit_status(credit_score)
        max_credit_amount = get_max_credit_amount(credit_score)
        credit_advice = get_credit_advice(credit_score)

        # Формируем сообщение
        msg = [
            f"📝 <b>Разрешение на выдачу кредита для {client.fullName}:</b>",
            f"🔹 Кредитный рейтинг: {credit_score}",
            f"🔹 Статус: {credit_status}",
            f"🔹 Максимальная сумма кредита, которую можно получить: {max_credit_amount:.2f} руб.",
            "\n<b>Рекомендации для улучшения:</b>",
            credit_advice
        ]
        
        # Если есть активные или просроченные кредиты, добавляем это в сообщение
        if loans_list:
            msg.append("\n❌ ОТКАЗАНО В ВЫДАЧЕ\n У вас есть активные кредиты или просроченные задолженности. "
                       "Невозможно оформить новый кредит до их закрытия.")
        else:
            msg.append("\n✅ ВЫДАЧА КРЕДИТА РАЗРЕШЕНА\nВы можете оформить новый кредит, так как у вас нет активных или просроченных задолженностей.")

        # Отправляем информацию пользователю
        await message.answer(
            "\n".join(msg),
            parse_mode="HTML",
            reply_markup=ReplyKeyboardRemove()
        )

#ДОСРОЧНОЕ ПОГАШЕНИЕ КРЕДИТА(ЛИБО УМЕНЬШЕНИЕ РАЗМЕРА ПЛАТЕЖА ЛИБО УМЕНЬШЕНИЕ КОЛ-ВА ПЛАТЕЖЕЙ)
@router.message(Command("early_repayment"))
async def start_early_repayment_process(message: types.Message, state: FSMContext):
    """Начало процесса досрочного погашения"""
    async with async_session() as session:
        client = await check_client_registered(message, session)
        if not client:
            return

        loans = await session.scalars(
            select(Loan)
            .where(Loan.client_id == client.clientID,
            Loan.status.in_([LoanStatus.ACTIVE, LoanStatus.OVERDUE]))
        )
        loans = loans.all()
        
        if not loans:
            return await message.answer("У вас нет активных кредитов для досрочного погашения")

        await state.update_data(loans={loan.loan_id: loan for loan in loans})
        
        # Создаем кнопки для кредитов
        loan_buttons = [
            [types.KeyboardButton(text=f"Кредит #{l.loan_id} - {l.amount:,.2f}₽")] 
            for l in loans[:10]  # Ограничиваем количество
        ]
        loan_buttons.append([types.KeyboardButton(text="❌ Отмена")])
        
        kb = types.ReplyKeyboardMarkup(
            keyboard=loan_buttons,
            resize_keyboard=True,
            one_time_keyboard=True
        )
        
        await message.answer(
            f"Выберите кредит для досрочного погашения:",
            reply_markup=kb
        )
        await state.set_state(EarlyRepaymentStates.choose_loan)

@router.message(EarlyRepaymentStates.choose_loan, F.text.regexp(r'Кредит #\d+'))
async def choose_loan_for_early_repayment(message: types.Message, state: FSMContext):
    """Обработка выбора кредита для досрочного погашения"""
    try:
        loan_id = int(message.text.split('#')[1].split()[0])
        
        async with async_session() as session:
            loan = await session.get(Loan, loan_id, options=[joinedload(Loan.loan_type)])
            if not loan:
                await message.answer("❌ Кредит не найден")
                await state.clear()
                return
            
            # Получаем все платежи
            payments = await session.scalars(
                select(Payment)
                .where(Payment.loan_id == loan_id)
                .order_by(Payment.payment_date_plan)
            )
            payments = payments.all()
            
            # Рассчитываем общую сумму оплаченных платежей
            total_paid = sum(
                Decimal(str(p.actual_amount)) 
                for p in payments 
                if p.actual_amount is not None
            )
            
            # Обновляем остаток долга
            loan.remaining_amount = loan.amount - total_paid
            
            # Сохраняем данные
            await state.update_data(
                loan_id=loan_id,
                current_loan=loan,
                remaining_amount=loan.remaining_amount
            )
            
            # Создаем клавиатуру с вариантами досрочного погашения
            keyboard = types.ReplyKeyboardMarkup(
                keyboard=[
                    [types.KeyboardButton(text="Уменьшить размер платежей")],
                    [types.KeyboardButton(text="Сократить срок кредита")],
                    [types.KeyboardButton(text="❌ Отмена")]
                ],
                resize_keyboard=True,
                one_time_keyboard=True
            )
            
            await message.answer(
                f"<b>Кредит #{loan_id}</b>\n"
                f"Остаток долга: {loan.remaining_amount:.2f}₽\n\n"
                "Выберите тип досрочного погашения:",
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML
            )
            
            await state.set_state(EarlyRepaymentStates.choose_type)
            
    except Exception as e:
        logging.error(f"Ошибка при выборе кредита: {e}", exc_info=True)
        await message.answer("⚠ Ошибка при обработке кредита")
        await state.clear()

@router.message(EarlyRepaymentStates.choose_type, F.text.in_(["Уменьшить размер платежей", "Сократить срок кредита"]))
async def choose_early_repayment_type(message: types.Message, state: FSMContext):
    """Обработка выбора типа досрочного погашения"""
    try:
        repayment_type = message.text
        data = await state.get_data()
        loan_id = data['loan_id']
        
        await state.update_data(repayment_type=repayment_type)
        
        if repayment_type == "Уменьшить размер платежей":
            await message.answer(
                "Введите сумму, которую хотите внести для уменьшения размера платежей:",
                reply_markup=types.ReplyKeyboardRemove()
            )
            await state.set_state(EarlyRepaymentStates.enter_amount)
        else:
            await message.answer(
                "Введите сумму досрочного погашения для сокращения срока кредита:",
                reply_markup=types.ReplyKeyboardRemove()
            )
            await state.set_state(EarlyRepaymentStates.enter_amount)
            
    except Exception as e:
        logging.error(f"Ошибка при выборе типа погашения: {e}", exc_info=True)
        await message.answer("⚠ Ошибка при обработке запроса")
        await state.clear()


@router.message(EarlyRepaymentStates.enter_amount, F.text.regexp(r'^\d+(\.\d{1,2})?$'))
async def process_early_repayment_amount(message: types.Message, state: FSMContext):
    """Обработка суммы досрочного погашения с пересчетом графика платежей"""
    response_msg = None
    try:
        amount = Decimal(message.text)
        if amount <= 0:
            raise ValueError("Сумма должна быть больше нуля")
        
        data = await state.get_data()
        loan_id = data['loan_id']
        repayment_type = data['repayment_type']
        current_date = date.today()
        
        async with async_session() as session:
            # Получаем кредит с типом (для процентной ставки)
            loan = await session.get(Loan, loan_id, options=[joinedload(Loan.loan_type)])
            if not loan:
                await message.answer("❌ Кредит не найден")
                await state.clear()
                return
            
            if amount > loan.remaining_amount:
                amount = loan.remaining_amount
                await message.answer(
                    f"⚠ Сумма превышает остаток долга. Будет зачислено {amount:.2f} руб."
                )
            
            # Получаем все платежи по кредиту
            payments = await session.scalars(
                select(Payment)
                .where(Payment.loan_id == loan_id)
                .order_by(Payment.payment_date_plan.asc())
            )
            payments_list = list(payments)

            # Добавляем запись о досрочном погашении
            early_payment = Payment(
                loan_id=loan_id,
                payment_date_plan=current_date,
                planned_amount=float(amount),
                payment_date_fact=current_date,
                actual_amount=float(amount),
                is_early_payment=True
            )
            session.add(early_payment)

            # Обновляем остаток по кредиту
            loan.remaining_amount -= amount

            # Удаляем все будущие неоплаченные платежи
            await session.execute(
                delete(Payment)
                .where(Payment.loan_id == loan_id)
                .where(Payment.payment_date_fact.is_(None))
            )

            if loan.remaining_amount <= 0:
                loan.status = "CLOSED"
                loan.next_payment_date = None
                response_msg = (
                    "✅ <b>Кредит полностью погашен!</b>\n\n"
                    f"🔹 Номер кредита: #{loan_id}\n"
                    f"🔹 Сумма погашения: {amount:.2f} руб.\n"
                    "Поздравляем с полным погашением кредита!"
                )
            else:
                # Получаем количество уже совершенных платежей
                paid_payments_count = len([p for p in payments_list if p.payment_date_fact is not None])
                remaining_term = loan.term - paid_payments_count

                # Находим дату последнего совершенного платежа
                last_paid_date = max(
                    p.payment_date_plan 
                    for p in payments_list 
                    if p.payment_date_fact is not None
                ) if any(p.payment_date_fact is not None for p in payments_list) else loan.issue_date

                if repayment_type == "Сократить срок кредита":
                    # Полностью пересчитываем график с новым сроком
                    # Рассчитываем новый срок пропорционально остатку
                    original_term = loan.term
                    original_amount = Decimal(str(loan.amount))
                    paid_ratio = (original_amount - loan.remaining_amount) / original_amount
                    new_term = max(1, math.floor(remaining_term * (1 - paid_ratio)))
                    
                    # Генерируем новый график платежей с пересчетом процентов
                    new_payments = await generate_payment_schedule(
                        loan_id=loan_id,
                        amount=loan.remaining_amount,
                        term=new_term,
                        interest_rate=loan.loan_type.interest_rate,
                        start_date=last_paid_date,
                        session=session
                    )
                    
                    # Получаем новый размер платежа
                    new_monthly_payment = Decimal(str(new_payments[0].planned_amount)) if new_payments else Decimal('0')
                    
                    response_msg = (
                        "✅ <b>Досрочное погашение успешно зачислено!</b>\n\n"
                        f"🔹 Номер кредита: #{loan_id}\n"
                        f"🔹 Сумма погашения: {amount:.2f} руб.\n"
                        f"🔹 Остаток долга: {loan.remaining_amount:.2f} руб.\n"
                        f"🔹 Срок кредита сокращен.\n"
                        f"🔹 Новый срок: {new_term} платеж(а).\n"
                        f"🔹 Новый размер платежа: {new_monthly_payment:.2f} руб."
                    )
                else:
                    # Уменьшение размера платежа с пересчетом по аннуитетной схеме
                    new_payments = await generate_payment_schedule(
                        loan_id=loan_id,
                        amount=loan.remaining_amount,
                        term=remaining_term,
                        interest_rate=loan.loan_type.interest_rate,
                        start_date=last_paid_date,
                        session=session
                    )

                    new_monthly_payment = Decimal(str(new_payments[0].planned_amount)) if new_payments else Decimal('0')

                    response_msg = (
                        "✅ <b>Досрочное погашение успешно зачислено!</b>\n\n"
                        f"🔹 Номер кредита: #{loan_id}\n"
                        f"🔹 Сумма погашения: {amount:.2f} руб.\n"
                        f"🔹 Остаток долга: {loan.remaining_amount:.2f} руб.\n"
                        f"🔹 Новый размер платежа: {new_monthly_payment:.2f} руб.\n"
                        f"🔹 Срок сохранен: {remaining_term} мес."
                    )

                # Обновляем дату следующего платежа
                first_future_payment = await session.scalar(
                    select(Payment)
                    .where(Payment.loan_id == loan_id)
                    .where(Payment.payment_date_fact.is_(None))
                    .order_by(Payment.payment_date_plan.asc())
                    .limit(1)
                )
                loan.next_payment_date = first_future_payment.payment_date_plan if first_future_payment else None

            await session.commit()
            await message.answer(response_msg, parse_mode=ParseMode.HTML)
            await state.clear()

    except ValueError as e:
        await message.answer(f"❌ Ошибка: {str(e)}\nПожалуйста, введите корректную сумму:")
    except Exception as e:
        logging.error(f"Ошибка при досрочном погашении: {e}", exc_info=True)
        await message.answer("⚠ Произошла ошибка при обработке досрочного погашения. Попробуйте позже.")
        await state.clear()

#ПЕРЕРАСЧЕТ С УЧЕТОМ ПЕННИ
@router.message(Command("calculate_penny"))
async def calculate_penny(message: types.Message):
    try:
        current_date = date.today()
        penalties_applied = False

        async with async_session() as session:
            # Сначала находим клиента по telegram_id
            client = await check_client_registered(message, session)
            if not client:
                return

            # Ищем только кредиты этого клиента
            result = await session.scalars(
                select(Loan)
                .where(
                    (Loan.client_id == client.clientID) &
                    (Loan.status.in_([LoanStatus.ACTIVE, LoanStatus.OVERDUE]))
                )
            )
            loans = list(result)

            if not loans:
                await message.answer("ℹ У вас нет активных или просроченных кредитов.")
                return

            for loan in loans:
                loan_overdue = False
                total_penalty = Decimal('0.00')

                payments = await session.scalars(
                    select(Payment)
                    .where(Payment.loan_id == loan.loan_id)
                    .order_by(Payment.payment_date_plan)
                )
                payments_list = list(payments)

                for payment in payments_list:
                    if not payment.payment_date_fact and payment.payment_date_plan < current_date:
                        # Платеж просрочен
                        overdue_days = (current_date - payment.payment_date_plan).days
                        penalty = (Decimal(payment.planned_amount) * Decimal('0.01') * overdue_days).quantize(Decimal('0.01'))

                        payment.penalty_amount = float(penalty)
                        payment.penalty_date = current_date

                        loan_overdue = True
                        penalties_applied = True
                        total_penalty += penalty

                if loan_overdue:
                    loan.status = LoanStatus.OVERDUE
                    loan.remaining_amount += total_penalty

                    unpaid_payments = [p for p in payments_list if not p.payment_date_fact]

                    if not unpaid_payments:
                        continue

                    new_monthly_payment = (Decimal(loan.remaining_amount) / len(unpaid_payments)).quantize(Decimal('0.01'))

                    for payment in unpaid_payments:
                        payment.planned_amount = float(new_monthly_payment)

            await session.commit()

        if penalties_applied:
            await message.answer("✅ Перерасчет оставшихся платежей с учетом пени произведен!")
        else:
            await message.answer("✅ Все хорошо, просрочек по вашим кредитам нет.")

    except Exception as e:
        logging.error(f"Ошибка при перерасчете пеней: {e}", exc_info=True)
        await message.answer("⚠ Произошла ошибка при перерасчете пеней.")

@router.message(Command("set_payment_late"))
async def set_payment_late(message: types.Message):
    try:
        async with async_session() as session:
            # Находим клиента по telegram_id
            client = await check_client_registered(message, session)
            if not client:
                return

            # Выбираем ближайший неоплаченный платеж только для кредитов этого клиента
            payment = await session.scalar(
                select(Payment)
                .join(Loan, Payment.loan_id == Loan.loan_id)
                .where(
                    (Payment.payment_date_fact.is_(None)) &
                    (Loan.client_id == client.clientID)
                )
                .order_by(Payment.payment_date_plan)
                .limit(1)
            )

            if not payment:
                await message.answer("⚠ У вас нет неоплаченных платежей для изменения.")
                return

            # Изменяем платеж
            one_month_ago = date.today() - relativedelta(months=1)
            payment.payment_date_plan = one_month_ago
            payment.payment_date_fact = None
            payment.actual_amount = 0.00
            payment.penalty_date = None
            payment.penalty_amount = 0.00

            # Помечаем кредит как просроченный
            loan = await session.get(Loan, payment.loan_id)
            if loan and loan.status == LoanStatus.ACTIVE:
                loan.status = LoanStatus.OVERDUE

            await session.commit()

        await message.answer(
            f"✅ Платеж ID {payment.payment_id} по кредиту #{payment.loan_id} "
            f"успешно сделан просроченным на {one_month_ago}!"
        )

    except Exception as e:
        logging.error(f"Ошибка при установке просрочки платежа: {e}", exc_info=True)
        await message.answer("⚠ Произошла ошибка при изменении платежа.")
