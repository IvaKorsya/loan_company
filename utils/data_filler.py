from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from models.base import LoanType  

async def add_default_loan_types(session: AsyncSession):
    """Заполнение таблицы стандартными типами кредитов."""
    default_loan_types = [
        {
            "type_id": 1,
            "name": "Экспресс-кредит",
            "interest_rate": 19.9,
            "min_amount": 5000,
            "max_amount": 100000,
            "min_term": 3,
            "max_term": 12,
            "description": "Быстрый кредит наличными с минимальным пакетом документов"
        },
        {
            "type_id": 2,
            "name": "Потребительский стандарт",
            "interest_rate": 14.9,
            "min_amount": 30000,
            "max_amount": 300000,
            "min_term": 6,
            "max_term": 36,
            "description": "Стандартный кредит на любые цели"
        },
        {
            "type_id": 3,
            "name": "Кредит для бизнеса",
            "interest_rate": 12.5,
            "min_amount": 100000,
            "max_amount": 2000000,
            "min_term": 12,
            "max_term": 60,
            "description": "Специальные условия для предпринимателей"
        },
        {
            "type_id": 4,
            "name": "Образовательный",
            "interest_rate": 8.9,
            "min_amount": 20000,
            "max_amount": 500000,
            "min_term": 6,
            "max_term": 84,
            "description": "Кредит на образование со льготной ставкой"
        },
        {
            "type_id": 5,
            "name": "Автокредит",
            "interest_rate": 10.9,
            "min_amount": 100000,
            "max_amount": 5000000,
            "min_term": 12,
            "max_term": 84,
            "description": "Кредит на покупку автомобиля"
        }
    ]

    existing_types = await session.execute(select(LoanType.name))
    existing_names = {name[0] for name in existing_types}

    for loan_type_data in default_loan_types:
        if loan_type_data["name"] not in existing_names:
            loan_type = LoanType(**loan_type_data)
            session.add(loan_type)
    
    await session.commit()