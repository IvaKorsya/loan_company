import inspect
from pathlib import Path
from handlers import basic, db_handlers, admin
from models import user

def generate_docs():
    """Генерирует Markdown-документацию проекта"""
    docs = "# 📚 Автодокументация бота\n\n"

    # Документируем обработчики
    docs += "## 🛠 Обработчики команд\n"
    for module in [basic, db_handlers, admin]:
        docs += f"### Модуль {module.__name__}\n"
        for name, obj in inspect.getmembers(module):
            if inspect.isfunction(obj) and obj.__doc__:
                docs += f"#### {name}\n{obj.__doc__}\n\n"

    # Документируем модели
    docs += "## 🗃 Модели данных\n"
    for name, obj in inspect.getmembers(user):
        if inspect.isclass(obj) and obj.__doc__:
            docs += f"### {name}\n{obj.__doc__}\n\n"

    # Сохраняем в файл
    Path("DOCUMENTATION.md").write_text(docs, encoding="utf-8")
    print("✅ Документация сгенерирована в DOCUMENTATION.md")

if __name__ == "__main__":
    generate_docs()