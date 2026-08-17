"""
PythonAnywhere WSGI entry point.
Настройте в PythonAnywhere Web → WSGI → 
    from index import app as application
"""
import sys
import os

# Добавляем путь к папке проекта
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

# Импортируем Flask app из bot_webhook
from bot_webhook import app, set_webhook

# Автоматически устанавливаем webhook при старте
try:
    set_webhook()
except Exception as e:
    print(f"Webhook setup error: {e}")

# PythonAnywhere ищет переменную `application`
application = app

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
