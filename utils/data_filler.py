from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from models.base import LoanType  

async def add_default_loan_type(session: AsyncSession):
    """Заполнение таблицы дефолтными типами кредитов."""
    result = await session.execute(select(LoanType))
    loan_types = result.scalars().all()

    if not loan_types:
        loan = LoanType(
            name="Базовый кредит",
            interest_rate=15.5,
            min_amount=10000,
            max_amount=500000,
            min_term = 6,
            max_term = 24,
            description="Стандартный потребительский кредит"
        )
        session.add(loan)
        await session.commit()
        print("Добавлен кредитный продукт: Базовый кредит")
    else:
        print("Типы кредитов уже существуют в базе данных.")
