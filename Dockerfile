# Указываем базовый образ с Python 3.10
FROM python:3.10-slim

# Рабочая директория в контейнере
WORKDIR /app

# Скопировать все файлы
COPY . /app

# Установить зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Переменная окружения для токена
ENV TOKEN=${TOKEN}

# Команда запуска
CMD ["python", "dogcare_bot.py"]
