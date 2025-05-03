import io
import csv
from datetime import datetime
from decimal import Decimal
from aiogram import types
from models.user import Client, Loan, Payment

def generate_payments_csv(payments: list[Payment], loan_id: int) -> types.BufferedInputFile:
    """Генерирует CSV файл с графиком платежей"""
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Заголовки
    writer.writerow([
        'Дата платежа', 'Сумма платежа', 'Статус', 
        'Фактическая дата', 'Фактическая сумма', 'Штраф'
    ])
    
    # Данные
    for payment in payments:
        writer.writerow([
            payment.payment_date_plan.strftime('%d.%m.%Y'),
            f"{payment.planned_amount:.2f}",
            "Оплачен" if payment.payment_date_fact else "Ожидается",
            payment.payment_date_fact.strftime('%d.%m.%Y') if payment.payment_date_fact else "-",
            f"{payment.actual_amount:.2f}" if payment.actual_amount else "-",
            f"{payment.penalty_amount:.2f}" if payment.penalty_amount else "-"
        ])
    
    # Сбрасываем буфер в бинарный поток
    csv_data = output.getvalue().encode('utf-8')
    output.close()
    
    return types.BufferedInputFile(
        file=csv_data,
        filename=f"payment_schedule_{loan_id}.csv"
    )