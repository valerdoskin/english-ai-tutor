FROM python:3.11-slim

WORKDIR /app

# Копируем зависимости и устанавливаем их
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем исходный код
COPY . .

# Создаём папку для аудиофайлов
RUN mkdir -p static/audio

# Порт, на котором работает Flask
EXPOSE 8000

# Запускаем приложение
CMD ["python", "index.py"]
