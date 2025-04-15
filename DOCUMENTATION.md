# 📚 Автодокументация бота

## 🛠 Обработчики команд
### Модуль handlers.basic
#### cmd_about

    Показывает информацию о боте

    Включает:
    - Версию бота
    - Контактные данные
    - Ссылки на документацию

    Использует HTML-форматирование для красивого вывода
    

#### cmd_cancel

    Сбрасывает текущее состояние пользователя

    Функционал:
    - Удаляет клавиатуру
    - Прекращает FSM-процесс (если активен)
    - Отправляет подтверждение отмены

    Важно: Работает только внутри многошаговых процессов
    

#### cmd_help

    Показывает справочную информацию о командах

    Формирует список:
    - Основные команды
    - Админские команды (для админов)
    - Контакты поддержки

    Группирует команды по категориям с Markdown-разметкой
    

#### cmd_start

    Инициализация бота для нового пользователя

    Действия:
    1. Устанавливает меню команд
    2. Отправляет приветственное сообщение
    3. Записывает факт запуска в лог

    Пример ответа:
    -------------
    👋 Иван Иванов, добро пожаловать в CreditBot!
    Ваш надежный помощник в кредитовании.
    

#### hbold

    Make bold text (HTML)

    :param content:
    :param sep:
    :return:
    

#### set_bot_commands
Устанавливает меню команд в зависимости от роли

### Модуль handlers.db_handlers
#### get_credit_advice
Генерирует рекомендации для улучшения рейтинга

#### get_credit_status
Возвращает текстовый статус в зависимости от рейтинга

#### process_email
Обработка email и финальное сохранение

#### process_full_name
Обработка ФИО

#### process_new_phone
Обработка нового номера телефона

#### process_passport
Обработка паспортных данных

#### process_phone
Обработка телефона

#### select
Construct a new :class:`_expression.Select`.


    .. versionadded:: 1.4 - The :func:`_sql.select` function now accepts
       column arguments positionally.   The top-level :func:`_sql.select`
       function will automatically use the 1.x or 2.x style API based on
       the incoming arguments; using :func:`_sql.select` from the
       ``sqlalchemy.future`` module will enforce that only the 2.x style
       constructor is used.

    Similar functionality is also available via the
    :meth:`_expression.FromClause.select` method on any
    :class:`_expression.FromClause`.

    .. seealso::

        :ref:`tutorial_selecting_data` - in the :ref:`unified_tutorial`

    :param \*entities:
      Entities to SELECT from.  For Core usage, this is typically a series
      of :class:`_expression.ColumnElement` and / or
      :class:`_expression.FromClause`
      objects which will form the columns clause of the resulting
      statement.   For those objects that are instances of
      :class:`_expression.FromClause` (typically :class:`_schema.Table`
      or :class:`_expression.Alias`
      objects), the :attr:`_expression.FromClause.c`
      collection is extracted
      to form a collection of :class:`_expression.ColumnElement` objects.

      This parameter will also accept :class:`_expression.TextClause`
      constructs as
      given, as well as ORM-mapped classes.

    

#### show_profile
Показывает профиль клиента

#### start_contact_update
Обновление контактных данных

#### start_phone_update
Запуск процесса изменения телефона

#### start_registration
Начало процесса регистрации

#### validate_phone_number
Валидация и нормализация номера телефона

#### view_credit_info

    Показывает детальную информацию о кредитном рейтинге пользователя
    с историей изменений и рекомендациями.
    

#### view_personal_info
Просмотр личной информации с защитой данных

### Модуль handlers.admin
#### admin_auth
Аутентификация администратора

    При попытке войти в admin-панель пользователя, ID которого нет в ADMIN_ID:
    ----------------------
    ❌ Доступ запрещен
    ----------------------

    Если ID соответвтует находящимся в ADMIN_ID, то запрвашивается пароль:
    ----------------------
    "🔐 <b>Панель администратора</b>
"
    "Введите пароль для доступа:"
    ----------------------
    Если пороль соответвует введённому
    

#### admin_panel
Основное меню админки с обновлением команд

    Ввывподит текст и клавиши:
    --------------------------------------------------------------
    🛠 <b>Административная панель</b>
    --------------------------------------------------------------
    |📊 Статистика|👥 Поиск клиента|⚙ Изменить кредитный рейтинг|
    --------------------------------------------------------------
        Статистика (admin_stats)
        Поиск клиентов (admin_find_client)
        Изменить кредитный рейтинг (admin_change_credit)
    

#### change_credit_start
Изменение кредитного рейтинга

#### find_client
Поиск клиента по ID

#### is_admin

    Проверка на право администрирования.
    

#### process_client_id
Обработка ID клиента

#### process_credit_change
Обработка изменения рейтинга

#### select
Construct a new :class:`_expression.Select`.


    .. versionadded:: 1.4 - The :func:`_sql.select` function now accepts
       column arguments positionally.   The top-level :func:`_sql.select`
       function will automatically use the 1.x or 2.x style API based on
       the incoming arguments; using :func:`_sql.select` from the
       ``sqlalchemy.future`` module will enforce that only the 2.x style
       constructor is used.

    Similar functionality is also available via the
    :meth:`_expression.FromClause.select` method on any
    :class:`_expression.FromClause`.

    .. seealso::

        :ref:`tutorial_selecting_data` - in the :ref:`unified_tutorial`

    :param \*entities:
      Entities to SELECT from.  For Core usage, this is typically a series
      of :class:`_expression.ColumnElement` and / or
      :class:`_expression.FromClause`
      objects which will form the columns clause of the resulting
      statement.   For those objects that are instances of
      :class:`_expression.FromClause` (typically :class:`_schema.Table`
      or :class:`_expression.Alias`
      objects), the :attr:`_expression.FromClause.c`
      collection is extracted
      to form a collection of :class:`_expression.ColumnElement` objects.

      This parameter will also accept :class:`_expression.TextClause`
      constructs as
      given, as well as ORM-mapped classes.

    

#### set_bot_commands
Устанавливает меню команд в зависимости от роли

#### show_stats
Показывает статистику

#### update
Construct an :class:`_expression.Update` object.

    E.g.::

        from sqlalchemy import update

        stmt = (
            update(user_table).where(user_table.c.id == 5).values(name="user #5")
        )

    Similar functionality is available via the
    :meth:`_expression.TableClause.update` method on
    :class:`_schema.Table`.

    :param table: A :class:`_schema.Table`
     object representing the database
     table to be updated.


    .. seealso::

        :ref:`tutorial_core_update_delete` - in the :ref:`unified_tutorial`


    

## 🗃 Модели данных
### Base
Базовая модель с поддержкой async

### BaseModel
Usage docs: https://docs.pydantic.dev/2.10/concepts/models/

    A base class for creating Pydantic models.

    Attributes:
        __class_vars__: The names of the class variables defined on the model.
        __private_attributes__: Metadata about the private attributes of the model.
        __signature__: The synthesized `__init__` [`Signature`][inspect.Signature] of the model.

        __pydantic_complete__: Whether model building is completed, or if there are still undefined fields.
        __pydantic_core_schema__: The core schema of the model.
        __pydantic_custom_init__: Whether the model has a custom `__init__` function.
        __pydantic_decorators__: Metadata containing the decorators defined on the model.
            This replaces `Model.__validators__` and `Model.__root_validators__` from Pydantic V1.
        __pydantic_generic_metadata__: Metadata for generic models; contains data used for a similar purpose to
            __args__, __origin__, __parameters__ in typing-module generics. May eventually be replaced by these.
        __pydantic_parent_namespace__: Parent namespace of the model, used for automatic rebuilding of models.
        __pydantic_post_init__: The name of the post-init method for the model, if defined.
        __pydantic_root_model__: Whether the model is a [`RootModel`][pydantic.root_model.RootModel].
        __pydantic_serializer__: The `pydantic-core` `SchemaSerializer` used to dump instances of the model.
        __pydantic_validator__: The `pydantic-core` `SchemaValidator` used to validate instances of the model.

        __pydantic_fields__: A dictionary of field names and their corresponding [`FieldInfo`][pydantic.fields.FieldInfo] objects.
        __pydantic_computed_fields__: A dictionary of computed field names and their corresponding [`ComputedFieldInfo`][pydantic.fields.ComputedFieldInfo] objects.

        __pydantic_extra__: A dictionary containing extra values, if [`extra`][pydantic.config.ConfigDict.extra]
            is set to `'allow'`.
        __pydantic_fields_set__: The names of fields explicitly set during instantiation.
        __pydantic_private__: Values of private attributes set on the model instance.
    

### BigInteger
A type for bigger ``int`` integers.

    Typically generates a ``BIGINT`` in DDL, and otherwise acts like
    a normal :class:`.Integer` on the Python side.

    

### Client
Модель клиента кредитной компании с защитой данных
    Основные поля:
    clientID            --- Integer, primary_key, autoincrement
    fullName            --- String(100),nullable
    passport            --- String(20), unique, nullable
    telegram_id         --- BigInteger, unique, nullable
    phone_numbers       --- JSON, nullable
    email               --- String(100), unique, nullable
    registration_date   --- DateTime
    creditScore         --- Integer
    

### Column
Represents a column in a database table.

### CreditHistory
Модуль работы с кредитной историей

### Date
A type for ``datetime.date()`` objects.

### DateTime
A type for ``datetime.datetime()`` objects.

    Date and time types return objects from the Python ``datetime``
    module.  Most DBAPIs have built in support for the datetime
    module, with the noted exception of SQLite.  In the case of
    SQLite, date and time types are stored as strings which are then
    converted back to datetime objects when rows are returned.

    For the time representation within the datetime type, some
    backends include additional options, such as timezone support and
    fractional seconds support.  For fractional seconds, use the
    dialect-specific datatype, such as :class:`.mysql.TIME`.  For
    timezone support, use at least the :class:`_types.TIMESTAMP` datatype,
    if not the dialect-specific datatype object.

    

### EmailStr

        Info:
            To use this type, you need to install the optional
            [`email-validator`](https://github.com/JoshData/python-email-validator) package:

            ```bash
            pip install email-validator
            ```

        Validate email addresses.

        ```python
        from pydantic import BaseModel, EmailStr

        class Model(BaseModel):
            email: EmailStr

        print(Model(email='contact@mail.com'))
        #> email='contact@mail.com'
        ```
        

### Enum
Generic Enum Type.

    The :class:`.Enum` type provides a set of possible string values
    which the column is constrained towards.

    The :class:`.Enum` type will make use of the backend's native "ENUM"
    type if one is available; otherwise, it uses a VARCHAR datatype.
    An option also exists to automatically produce a CHECK constraint
    when the VARCHAR (so called "non-native") variant is produced;
    see the  :paramref:`.Enum.create_constraint` flag.

    The :class:`.Enum` type also provides in-Python validation of string
    values during both read and write operations.  When reading a value
    from the database in a result set, the string value is always checked
    against the list of possible values and a ``LookupError`` is raised
    if no match is found.  When passing a value to the database as a
    plain string within a SQL statement, if the
    :paramref:`.Enum.validate_strings` parameter is
    set to True, a ``LookupError`` is raised for any string value that's
    not located in the given list of possible values; note that this
    impacts usage of LIKE expressions with enumerated values (an unusual
    use case).

    The source of enumerated values may be a list of string values, or
    alternatively a PEP-435-compliant enumerated class.  For the purposes
    of the :class:`.Enum` datatype, this class need only provide a
    ``__members__`` method.

    When using an enumerated class, the enumerated objects are used
    both for input and output, rather than strings as is the case with
    a plain-string enumerated type::

        import enum
        from sqlalchemy import Enum


        class MyEnum(enum.Enum):
            one = 1
            two = 2
            three = 3


        t = Table("data", MetaData(), Column("value", Enum(MyEnum)))

        connection.execute(t.insert(), {"value": MyEnum.two})
        assert connection.scalar(t.select()) is MyEnum.two

    Above, the string names of each element, e.g. "one", "two", "three",
    are persisted to the database; the values of the Python Enum, here
    indicated as integers, are **not** used; the value of each enum can
    therefore be any kind of Python object whether or not it is persistable.

    In order to persist the values and not the names, the
    :paramref:`.Enum.values_callable` parameter may be used.   The value of
    this parameter is a user-supplied callable, which  is intended to be used
    with a PEP-435-compliant enumerated class and  returns a list of string
    values to be persisted.   For a simple enumeration that uses string values,
    a callable such as  ``lambda x: [e.value for e in x]`` is sufficient.

    .. seealso::

        :ref:`orm_declarative_mapped_column_enums` - background on using
        the :class:`_sqltypes.Enum` datatype with the ORM's
        :ref:`ORM Annotated Declarative <orm_declarative_mapped_column>`
        feature.

        :class:`_postgresql.ENUM` - PostgreSQL-specific type,
        which has additional functionality.

        :class:`.mysql.ENUM` - MySQL-specific type

    

### ForeignKey
Defines a dependency between two columns.

    ``ForeignKey`` is specified as an argument to a :class:`_schema.Column`
    object,
    e.g.::

        t = Table(
            "remote_table",
            metadata,
            Column("remote_id", ForeignKey("main_table.id")),
        )

    Note that ``ForeignKey`` is only a marker object that defines
    a dependency between two columns.   The actual constraint
    is in all cases represented by the :class:`_schema.ForeignKeyConstraint`
    object.   This object will be generated automatically when
    a ``ForeignKey`` is associated with a :class:`_schema.Column` which
    in turn is associated with a :class:`_schema.Table`.   Conversely,
    when :class:`_schema.ForeignKeyConstraint` is applied to a
    :class:`_schema.Table`,
    ``ForeignKey`` markers are automatically generated to be
    present on each associated :class:`_schema.Column`, which are also
    associated with the constraint object.

    Note that you cannot define a "composite" foreign key constraint,
    that is a constraint between a grouping of multiple parent/child
    columns, using ``ForeignKey`` objects.   To define this grouping,
    the :class:`_schema.ForeignKeyConstraint` object must be used, and applied
    to the :class:`_schema.Table`.   The associated ``ForeignKey`` objects
    are created automatically.

    The ``ForeignKey`` objects associated with an individual
    :class:`_schema.Column`
    object are available in the `foreign_keys` collection
    of that column.

    Further examples of foreign key configuration are in
    :ref:`metadata_foreignkeys`.

    

### Integer
A type for ``int`` integers.

### JSON
Represent a SQL JSON type.

    .. note::  :class:`_types.JSON`
       is provided as a facade for vendor-specific
       JSON types.  Since it supports JSON SQL operations, it only
       works on backends that have an actual JSON type, currently:

       * PostgreSQL - see :class:`sqlalchemy.dialects.postgresql.JSON` and
         :class:`sqlalchemy.dialects.postgresql.JSONB` for backend-specific
         notes

       * MySQL - see
         :class:`sqlalchemy.dialects.mysql.JSON` for backend-specific notes

       * SQLite as of version 3.9 - see
         :class:`sqlalchemy.dialects.sqlite.JSON` for backend-specific notes

       * Microsoft SQL Server 2016 and later - see
         :class:`sqlalchemy.dialects.mssql.JSON` for backend-specific notes

    :class:`_types.JSON` is part of the Core in support of the growing
    popularity of native JSON datatypes.

    The :class:`_types.JSON` type stores arbitrary JSON format data, e.g.::

        data_table = Table(
            "data_table",
            metadata,
            Column("id", Integer, primary_key=True),
            Column("data", JSON),
        )

        with engine.connect() as conn:
            conn.execute(
                data_table.insert(), {"data": {"key1": "value1", "key2": "value2"}}
            )

    **JSON-Specific Expression Operators**

    The :class:`_types.JSON`
    datatype provides these additional SQL operations:

    * Keyed index operations::

        data_table.c.data["some key"]

    * Integer index operations::

        data_table.c.data[3]

    * Path index operations::

        data_table.c.data[("key_1", "key_2", 5, ..., "key_n")]

    * Data casters for specific JSON element types, subsequent to an index
      or path operation being invoked::

        data_table.c.data["some key"].as_integer()

      .. versionadded:: 1.3.11

    Additional operations may be available from the dialect-specific versions
    of :class:`_types.JSON`, such as
    :class:`sqlalchemy.dialects.postgresql.JSON` and
    :class:`sqlalchemy.dialects.postgresql.JSONB` which both offer additional
    PostgreSQL-specific operations.

    **Casting JSON Elements to Other Types**

    Index operations, i.e. those invoked by calling upon the expression using
    the Python bracket operator as in ``some_column['some key']``, return an
    expression object whose type defaults to :class:`_types.JSON` by default,
    so that
    further JSON-oriented instructions may be called upon the result type.
    However, it is likely more common that an index operation is expected
    to return a specific scalar element, such as a string or integer.  In
    order to provide access to these elements in a backend-agnostic way,
    a series of data casters are provided:

    * :meth:`.JSON.Comparator.as_string` - return the element as a string

    * :meth:`.JSON.Comparator.as_boolean` - return the element as a boolean

    * :meth:`.JSON.Comparator.as_float` - return the element as a float

    * :meth:`.JSON.Comparator.as_integer` - return the element as an integer

    These data casters are implemented by supporting dialects in order to
    assure that comparisons to the above types will work as expected, such as::

        # integer comparison
        data_table.c.data["some_integer_key"].as_integer() == 5

        # boolean comparison
        data_table.c.data["some_boolean"].as_boolean() == True

    .. versionadded:: 1.3.11 Added type-specific casters for the basic JSON
       data element types.

    .. note::

        The data caster functions are new in version 1.3.11, and supersede
        the previous documented approaches of using CAST; for reference,
        this looked like::

           from sqlalchemy import cast, type_coerce
           from sqlalchemy import String, JSON

           cast(data_table.c.data["some_key"], String) == type_coerce(55, JSON)

        The above case now works directly as::

            data_table.c.data["some_key"].as_integer() == 5

        For details on the previous comparison approach within the 1.3.x
        series, see the documentation for SQLAlchemy 1.2 or the included HTML
        files in the doc/ directory of the version's distribution.

    **Detecting Changes in JSON columns when using the ORM**

    The :class:`_types.JSON` type, when used with the SQLAlchemy ORM, does not
    detect in-place mutations to the structure.  In order to detect these, the
    :mod:`sqlalchemy.ext.mutable` extension must be used, most typically
    using the :class:`.MutableDict` class.  This extension will
    allow "in-place" changes to the datastructure to produce events which
    will be detected by the unit of work.  See the example at :class:`.HSTORE`
    for a simple example involving a dictionary.

    Alternatively, assigning a JSON structure to an ORM element that
    replaces the old one will always trigger a change event.

    **Support for JSON null vs. SQL NULL**

    When working with NULL values, the :class:`_types.JSON` type recommends the
    use of two specific constants in order to differentiate between a column
    that evaluates to SQL NULL, e.g. no value, vs. the JSON-encoded string of
    ``"null"``. To insert or select against a value that is SQL NULL, use the
    constant :func:`.null`. This symbol may be passed as a parameter value
    specifically when using the :class:`_types.JSON` datatype, which contains
    special logic that interprets this symbol to mean that the column value
    should be SQL NULL as opposed to JSON ``"null"``::

        from sqlalchemy import null

        conn.execute(table.insert(), {"json_value": null()})

    To insert or select against a value that is JSON ``"null"``, use the
    constant :attr:`_types.JSON.NULL`::

        conn.execute(table.insert(), {"json_value": JSON.NULL})

    The :class:`_types.JSON` type supports a flag
    :paramref:`_types.JSON.none_as_null` which when set to True will result
    in the Python constant ``None`` evaluating to the value of SQL
    NULL, and when set to False results in the Python constant
    ``None`` evaluating to the value of JSON ``"null"``.    The Python
    value ``None`` may be used in conjunction with either
    :attr:`_types.JSON.NULL` and :func:`.null` in order to indicate NULL
    values, but care must be taken as to the value of the
    :paramref:`_types.JSON.none_as_null` in these cases.

    **Customizing the JSON Serializer**

    The JSON serializer and deserializer used by :class:`_types.JSON`
    defaults to
    Python's ``json.dumps`` and ``json.loads`` functions; in the case of the
    psycopg2 dialect, psycopg2 may be using its own custom loader function.

    In order to affect the serializer / deserializer, they are currently
    configurable at the :func:`_sa.create_engine` level via the
    :paramref:`_sa.create_engine.json_serializer` and
    :paramref:`_sa.create_engine.json_deserializer` parameters.  For example,
    to turn off ``ensure_ascii``::

        engine = create_engine(
            "sqlite://",
            json_serializer=lambda obj: json.dumps(obj, ensure_ascii=False),
        )

    .. versionchanged:: 1.3.7

        SQLite dialect's ``json_serializer`` and ``json_deserializer``
        parameters renamed from ``_json_serializer`` and
        ``_json_deserializer``.

    .. seealso::

        :class:`sqlalchemy.dialects.postgresql.JSON`

        :class:`sqlalchemy.dialects.postgresql.JSONB`

        :class:`sqlalchemy.dialects.mysql.JSON`

        :class:`sqlalchemy.dialects.sqlite.JSON`

    

### Loan
Модель кредита клиента

### Mapped
Represent an ORM mapped attribute on a mapped class.

    This class represents the complete descriptor interface for any class
    attribute that will have been :term:`instrumented` by the ORM
    :class:`_orm.Mapper` class.   Provides appropriate information to type
    checkers such as pylance and mypy so that ORM-mapped attributes
    are correctly typed.

    The most prominent use of :class:`_orm.Mapped` is in
    the :ref:`Declarative Mapping <orm_explicit_declarative_base>` form
    of :class:`_orm.Mapper` configuration, where used explicitly it drives
    the configuration of ORM attributes such as :func:`_orm.mapped_class`
    and :func:`_orm.relationship`.

    .. seealso::

        :ref:`orm_explicit_declarative_base`

        :ref:`orm_declarative_table`

    .. tip::

        The :class:`_orm.Mapped` class represents attributes that are handled
        directly by the :class:`_orm.Mapper` class. It does not include other
        Python descriptor classes that are provided as extensions, including
        :ref:`hybrids_toplevel` and the :ref:`associationproxy_toplevel`.
        While these systems still make use of ORM-specific superclasses
        and structures, they are not :term:`instrumented` by the
        :class:`_orm.Mapper` and instead provide their own functionality
        when they are accessed on a class.

    .. versionadded:: 1.4


    

### Numeric
Base for non-integer numeric types, such as
    ``NUMERIC``, ``FLOAT``, ``DECIMAL``, and other variants.

    The :class:`.Numeric` datatype when used directly will render DDL
    corresponding to precision numerics if available, such as
    ``NUMERIC(precision, scale)``.  The :class:`.Float` subclass will
    attempt to render a floating-point datatype such as ``FLOAT(precision)``.

    :class:`.Numeric` returns Python ``decimal.Decimal`` objects by default,
    based on the default value of ``True`` for the
    :paramref:`.Numeric.asdecimal` parameter.  If this parameter is set to
    False, returned values are coerced to Python ``float`` objects.

    The :class:`.Float` subtype, being more specific to floating point,
    defaults the :paramref:`.Float.asdecimal` flag to False so that the
    default Python datatype is ``float``.

    .. note::

        When using a :class:`.Numeric` datatype against a database type that
        returns Python floating point values to the driver, the accuracy of the
        decimal conversion indicated by :paramref:`.Numeric.asdecimal` may be
        limited.   The behavior of specific numeric/floating point datatypes
        is a product of the SQL datatype in use, the Python :term:`DBAPI`
        in use, as well as strategies that may be present within
        the SQLAlchemy dialect in use.   Users requiring specific precision/
        scale are encouraged to experiment with the available datatypes
        in order to determine the best results.

    

### Payment
Модель платежа по кредиту

### String
The base for all string and character types.

    In SQL, corresponds to VARCHAR.

    The `length` field is usually required when the `String` type is
    used within a CREATE TABLE statement, as VARCHAR requires a length
    on most databases.

    

### date
date(year, month, day) --> date object

### datetime
datetime(year, month, day[, hour[, minute[, second[, microsecond[,tzinfo]]]]])

The year, month and day arguments are required. tzinfo may be None, or an
instance of a tzinfo subclass. The remaining arguments may be ints.


