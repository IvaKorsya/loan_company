Перед запуском обязательно прочитайте весь этот файл, так как вся основная информация по структуре записана здесь.
Первостепенная задача - скачать и установить PostgreSQL

Файловая структура проекта:
```Python
loan_company/
├── main.py             # Точка входа
├── config.py           # Конфиг с токеном и настройками
├── handlers/
│   ├── __init__.py     # Пустой файл для модуля
│   ├── basic.py        # Базовые команды (start, help)
│   └── db_handlers.py  # Будущие команды для работы с БД
├── models/             # (Опционально) Модели данных
│   └── __init__.py
├── utils/              # Вспомогательные утилиты
│   └── database.py     # Подключение к БД (позже добавим)
└── requirements.txt    # Зависимости
```
Организация базы данных:

* Credit History
    * CreditHistoryID
    * ClientID
    * BankID
    * LoanID
    * Persent
    * Status
    * Date
    * Amount
* Client
    * clientID
    * fullName
    * passport
    * phone_numbers
    * email
    * registration_date
    * creditScore
```SQL
CREATE TABLE Clients (
    clientId INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    fullName TEXT NOT NULL,
	passport TEXT CHECK (passport ~ '^[А-ЯЁA-Z0-9\s-]+$'),
	phone_number TEXT CHECK (phone_number ~ '^\+?[0-9\s()-]+$'),
	email TEXT CHECK (email ~ '^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'),
	registration_date TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
	credit_score SMALLINT CHECK (credit_score BETWEEN 300 AND 850)
);
```
* LoansType
    * loanType
    * interesRate
    * description
* Payment
    * paymentID
    * LoanID
    * SheduledDate
    * SheduledAmount
    * ActualDate
    * ActualAmount
