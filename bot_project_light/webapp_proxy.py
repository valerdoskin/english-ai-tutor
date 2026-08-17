"""
webapp_proxy.py — лёгкий прокси-модуль для веб-интерфейса.

Раньше этот файл дублировал все эндпоинты Flask-приложения из bot_webhook.py,
что приводило к рассинхронизации схем БД и конфликту портов.

Теперь он просто переиспользует готовое Flask-приложение из bot_webhook.py.
Используйте его как WSGI-entry point, если хотите запустить только веб API:

    from webapp_proxy import app as application

Или через уже существующий index.py:

    from index import app as application
"""
from bot_webhook import app  # повторно используем единое Flask-приложение

# Просто переимпортируем app, чтобы старые импорты (from webapp_proxy import app)
# продолжали работать без изменений в конфигурации PythonAnywhere.
__all__ = ["app"]

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
