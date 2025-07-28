import os
import logging
import datetime
from telegram import Update, BotCommand
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ConversationHandler, ContextTypes, filters

TOKEN = os.getenv("TOKEN")

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

NAME, WEIGHT, DATES, INTERVALS = range(4)
user_data = {}
TREATMENT_LABELS = {
    "от блох и клещей": "От блох и клещей",
    "от глистов": "От глистов",
    "комплексная вакцинация": "Комплексная вакцинация"
}

async def set_commands(application):
    commands = [
        BotCommand("start", "Начать настройку питомца"),
        BotCommand("pet", "Показать данные питомца"),
        BotCommand("update", "Обновить данные питомца"),
        BotCommand("delete", "Удалить данные питомца"),
        BotCommand("help", "Справка по командам")
    ]
    await application.bot.set_my_commands(commands)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Привет! 👋 Давай добавим информацию о твоем питомце. Как его зовут?")
    return NAME

async def name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["name"] = update.message.text.strip()
    await update.message.reply_text("Отлично! 🐾 Сколько весит твой питомец? (в килограммах)")
    return WEIGHT

async def weight(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["weight"] = update.message.text.strip()
    await update.message.reply_text("Теперь введи даты последних обработок в формате:\\nОт блох и клещей: 01.06.2025\\nОт глистов: 01.06.2025\\nКомплексная вакцинация: 01.06.2025\\nМожно пропустить те, которые не делались.")
    return DATES

async def dates(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lines = update.message.text.splitlines()
    dates = {}
    for line in lines:
        if ":" not in line:
            continue
        key, val = line.split(":", 1)
        key = key.strip().lower()
        val = val.strip()
        try:
            date = datetime.datetime.strptime(val, "%d.%m.%Y").date()
            dates[key] = date
        except ValueError:
            await update.message.reply_text("Пожалуйста, соблюдай формат даты дд.мм.гггг")
            return DATES
    context.user_data["dates"] = dates
    await update.message.reply_text("Укажи, как часто нужно повторять каждую обработку (в днях):\\nОт блох и клещей: 30\\nОт глистов: 90\\nКомплексная вакцинация: 365")
    return INTERVALS

async def intervals(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lines = update.message.text.splitlines()
    intervals = {}
    for line in lines:
        if ":" not in line:
            continue
        key, val = line.split(":", 1)
        key = key.strip().lower()
        try:
            intervals[key] = int(val.strip())
        except ValueError:
            await update.message.reply_text("Неверный формат интервала, вводи число дней")
            return INTERVALS
    data = {}
    for key, date in context.user_data["dates"].items():
        interval = intervals.get(key)
        if interval is not None:
            data[key] = (date, interval)
    user_data[update.effective_user.id] = {
        "name": context.user_data["name"],
        "weight": context.user_data["weight"],
        "treatments": data
    }
    msg = f"✅ Готово! Вот информацию о твоем питомце:\\n🐶 Имя: {context.user_data['name']}\\n⚖️ Вес: {context.user_data['weight']} кг\\n📅 Обработки:\\n"
    for k, (d, i) in data.items():
        label = TREATMENT_LABELS.get(k, k.title())
        msg += f"{label}: {d.strftime('%d.%m.%Y')} (каждые {i} дней)\\n"
    await update.message.reply_text(msg)
    return ConversationHandler.END

async def pet(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    pet = user_data.get(update.effective_user.id)
    if not pet:
        await update.message.reply_text("Пока что у тебя нет добавленного питомца. Напиши /start, чтобы добавить его 🐾")
        return
    msg = f"🐶 Имя: {pet['name']}\\n⚖️ Вес: {pet['weight']} кг\\n📅 Обработки:\\n"
    for k, (d, i) in pet["treatments"].items():
        label = TREATMENT_LABELS.get(k, k.title())
        msg += f"{label}: {d.strftime('%d.%m.%Y')} (каждые {i} дней)\\n"
    await update.message.reply_text(msg)

async def update_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return await start(update, context)

async def delete(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id in user_data:
        del user_data[update.effective_user.id]
        await update.message.reply_text("Данные питомца удалены.")
    else:
        await update.message.reply_text("Нет данных о питомце.")

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("/start — начать настройку питомца\\n/pet — показать данные питомца\\n/update — изменить данные питомца\\n/delete — удалить данные питомца\\n/help — справка по командам")

async def remind(context: ContextTypes.DEFAULT_TYPE) -> None:
    today = datetime.date.today()
    for uid, pet in user_data.items():
        texts = []
        for k, (last_date, interval) in pet["treatments"].items():
            next_date = last_date + datetime.timedelta(days=interval)
            if next_date == today:
                label = TREATMENT_LABELS.get(k, k.title())
                texts.append(f"🔔 Пора сделать обработку: {label} ({next_date.strftime('%d.%m.%Y')})")
        if texts:
            await context.bot.send_message(chat_id=uid, text="\\n".join(texts))

def main() -> None:
    app = ApplicationBuilder().token(TOKEN).build()
    app.post_init = set_commands
    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start), CommandHandler("update", update_cmd)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, name)],
            WEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, weight)],
            DATES: [MessageHandler(filters.TEXT & ~filters.COMMAND, dates)],
            INTERVALS: [MessageHandler(filters.TEXT & ~filters.COMMAND, intervals)]
        },
        fallbacks=[CommandHandler("help", help_cmd)]
    )
    app.add_handler(conv)
    app.add_handler(CommandHandler("pet", pet))
    app.add_handler(CommandHandler("delete", delete))
    app.add_handler(CommandHandler("help", help_cmd))
    app.job_queue.run_daily(remind, time=datetime.time(hour=9, minute=0))
    app.run_polling()

if __name__ == "__main__":
    main()