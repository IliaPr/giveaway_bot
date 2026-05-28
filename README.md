# Sibtrans Giveaway Bot

Telegram-бот для регистрации участников, проверки подписки на канал, записи в Google Sheets и автоматического розыгрыша.

## Обязательные переменные окружения

```env
BOT_TOKEN=123456:telegram-token
DATABASE_URL=postgresql://user:password@localhost:5432/sibtrans_giveaway
```

## Основные настройки

```env
SUBSCRIPTION_CHAT_ID=
SUBSCRIPTION_URL=
RESULTS_CHAT_ID=
RAFFLE_TIMEZONE=
RAFFLE_AT=
RAFFLE_DISPLAY_TEXT=

CERTIFICATE_TITLE=🏆 Сертификат на перевозку
CERTIFICATE_WINNERS=1
MERCH_1_TITLE=🎁 Увлажнитель воздуха
MERCH_1_WINNERS=1
MERCH_2_TITLE=🎁 Термос
MERCH_2_WINNERS=2
MERCH_3_TITLE=🎁 Термокружка
MERCH_3_WINNERS=5

STICKERPACK_TITLE=🎁 Стикерпак Bait Tranzit
STICKERPACK_URL=https://t.me/addstickers/bait_tranzit
ADMIN_IDS=
```

`*_WINNERS` задают число отдельных победителей по категории. Если `MERCH_3_TITLE=🎁 Термокружка` и `MERCH_3_WINNERS=5`, бот выберет 5 разных участников на термокружки.

## Google Sheets

Если нужно сохранять регистрации в Google Sheets, добавьте:

```env
GOOGLE_SHEET_ID=spreadsheet-id
GOOGLE_WORKSHEET_TITLE=Регистрация
GOOGLE_SERVICE_ACCOUNT_FILE=/absolute/path/to/service-account.json
```

Вместо файла можно передать JSON сервисного аккаунта через `GOOGLE_SERVICE_ACCOUNT_JSON`.

## SQLAdmin

Для веб-админки добавьте:

```env
ADMIN_USERNAME=admin
ADMIN_PASSWORD=change_me
ADMIN_SESSION_SECRET=change_me_too
ADMIN_BASE_URL=/admin
ADMIN_TITLE=Sibtrans Admin
```

После запуска админка будет доступна по пути `ADMIN_BASE_URL`.

## Локальный старт всех сервисов

1. Установите зависимости и создайте `.env`:

```bash
poetry install
cp .env.example .env
```

2. Заполните `.env`.
Обязательно проверьте `BOT_TOKEN`, `DB_*`, `REDIS_URL`, `CELERY_*`, `ADMIN_IDS`.

3. Поднимите PostgreSQL.
Если PostgreSQL установлен через Homebrew:

```bash
brew services start postgresql
```

4. Поднимите Redis.
Если Redis установлен через Homebrew:

```bash
brew services start redis
```

5. Примените миграции:

```bash
poetry run alembic upgrade head
```

6. Запустите FastAPI-приложение с polling и SQLAdmin:

```bash
./.venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

7. В отдельном терминале запустите Celery worker:

```bash
./.venv/bin/celery -A celery_app.celery_app worker --loglevel=info
```

8. В отдельном терминале запустите Celery beat:

```bash
./.venv/bin/celery -A celery_app.celery_app beat --loglevel=info
```

После запуска бот получает обновления через polling, поэтому публичный webhook URL и туннель больше не нужны.

После этого должны работать:

- Telegram polling внутри процесса Uvicorn
- админка SQLAdmin на `/admin` или на пути из `ADMIN_BASE_URL`
- фоновая обработка розыгрыша через Celery

## Быстрый список процессов

Нужно держать запущенными одновременно:

- PostgreSQL
- Redis
- FastAPI / Uvicorn
- Celery worker
- Celery beat

## Что важно для Telegram

- Бот должен быть администратором канала/группы, где проверяется подписка.
- Бот должен иметь право писать в канал или группу, куда публикуются итоги.
- Команда `/run_raffle` доступна только пользователям из `ADMIN_IDS`.

## Запуск на сервере через systemd

Если бот должен продолжать работать после выхода из SSH, не запускайте его вручную из shell. Используйте `systemd`.

В репозитории есть готовые шаблоны:

- `deploy/systemd/sibtrans-bot.service`
- `deploy/systemd/sibtrans-celery-worker.service`
- `deploy/systemd/sibtrans-celery-beat.service`

1. Откройте каждый unit-файл и замените `YOUR_USER` и `/path/to/sibtrans_giveaway` на реальные значения сервера.
2. Скопируйте файлы в `/etc/systemd/system/`.
3. Выполните `sudo systemctl daemon-reload`.
4. Включите и запустите сервисы:

```bash
sudo systemctl enable --now sibtrans-bot.service
sudo systemctl enable --now sibtrans-celery-worker.service
sudo systemctl enable --now sibtrans-celery-beat.service
```

5. Проверьте статус:

```bash
sudo systemctl status sibtrans-bot.service
sudo systemctl status sibtrans-celery-worker.service
sudo systemctl status sibtrans-celery-beat.service
```

6. Смотрите логи при необходимости:

```bash
sudo journalctl -u sibtrans-bot.service -f
sudo journalctl -u sibtrans-celery-worker.service -f
sudo journalctl -u sibtrans-celery-beat.service -f
```

`systemd` будет автоматически перезапускать процессы после падения и не привязывает их к SSH-сессии.