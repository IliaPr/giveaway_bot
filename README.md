# Sibtrans Giveaway Bot

Telegram-бот для проведения промо-розыгрышей: проверяет подписку на канал, регистрирует участников, сохраняет контактные данные, автоматически распределяет призы и публикует результаты.

Проект объединяет Telegram-интерфейс для участников, защищённую веб-админку для организаторов и фоновый контур, который проводит розыгрыш в заданное время. Все критичные данные хранятся в PostgreSQL, а выгрузку регистраций в Google Sheets можно подключить как дополнительную интеграцию.

## Возможности

- проверка подписки пользователя на Telegram-канал;
- пошаговая регистрация через FSM: ФИО, телефон, компания и должность;
- валидация и нормализация пользовательских данных;
- защита от повторной регистрации на уровне приложения и базы данных;
- настраиваемые категории призов и количество победителей;
- автоматический запуск розыгрыша по расписанию через Celery Beat;
- ручной запуск администратором командой `/run_raffle`;
- персональное уведомление каждого участника о результате;
- публикация итогового списка победителей в Telegram-канале;
- опциональная синхронизация регистраций с Google Sheets;
- веб-админка для просмотра участников, результатов и служебных метаданных;
- миграции базы данных. 

## Как это работает

1. Пользователь запускает бота и подтверждает подписку на канал.
2. Бот последовательно собирает и проверяет регистрационные данные.
3. Регистрация сохраняется в PostgreSQL и, если настроена интеграция, дублируется в Google Sheets.
4. После наступления заданного времени Celery-задача случайно распределяет призы между участниками.
5. Бот отправляет персональные результаты и один раз публикует итоги в канале.

```mermaid
flowchart LR
    User[Участник] --> TG["Telegram Bot<br/>aiogram"]
    TG --> Service[Giveaway Service]
    Service --> DB[(PostgreSQL)]
    Service -. опционально .-> Sheets[Google Sheets]

    Beat[Celery Beat] --> Redis[(Redis)]
    Redis --> Worker[Celery Worker]
    Worker --> DB
    Worker --> API[Telegram Bot API]

    Admin[Организатор] --> Web[FastAPI + SQLAdmin]
    Web --> DB
```

## Технические решения

### Надёжный розыгрыш

Для случайного выбора используется `SystemRandom`. После победы в одной конкурентной категории участник исключается из дальнейшей выборки, поэтому один человек не может получить несколько основных призов. Остальным участникам назначается поощрительный приз.

Результат розыгрыша сохраняется в базе и повторно не генерируется. Транзакционная advisory-блокировка PostgreSQL и уникальное ограничение на участника защищают обработку от одновременного запуска нескольких worker-процессов.

### Доставка с возможностью повторной попытки

Для каждого результата отдельно хранится время отправки уведомления. Если Telegram временно не принял сообщение, следующая Celery-задача повторит отправку только для необработанных записей. Публикация общего поста также защищена служебным флагом от дублирования.

### Независимость от Google Sheets

PostgreSQL остаётся основным источником данных. Ошибка внешней интеграции не блокирует регистрацию: участник сохраняется локально, а информация об ошибке синхронизации становится доступна в админке.

## Стек

| Область | Технологии |
|---|---|
| Telegram-бот | Python 3.14, aiogram 3, Redis FSM |
| API и админка | FastAPI, SQLAdmin, Uvicorn |
| Данные | PostgreSQL, SQLAlchemy 2, Alembic |
| Фоновые задачи | Celery, Celery Beat, Redis |
| Интеграции | Telegram Bot API, Google Sheets API, gspread |
| Конфигурация и модели | python-dotenv, Pydantic |
| Тестирование | unittest |

## Структура проекта

```text
.
├── admin/                 # SQLAdmin: авторизация и представления
├── alembic/               # миграции PostgreSQL
├── db/                    # ORM-модели, схемы и репозиторий
├── deploy/systemd/        # unit-файлы для серверного запуска
├── tests/                 # тесты конфигурации и логики розыгрыша
├── tg/                    # handlers, FSM, клавиатуры и сервисный слой
├── bot_runner.py          # запуск Telegram polling
├── celery_app.py          # worker, beat и задача розыгрыша
├── config.py              # типизированная конфигурация
├── google_sheets.py       # интеграция с Google Sheets
├── main.py                # FastAPI, SQLAdmin и healthcheck
├── raffle_logic.py        # выбор победителей и генерация сообщений
└── runtime.py             # сборка и завершение компонентов приложения
```

## Локальный запуск

### Требования

- Python `3.14`;
- Poetry `2.x`;
- PostgreSQL;
- Redis;
- Telegram-бот, созданный через [@BotFather](https://t.me/BotFather).

### 1. Установите зависимости

```bash
poetry install
cp .env.example .env
```

### 2. Настройте окружение

Минимально необходимые параметры:

```env
BOT_TOKEN=123456:telegram-token

DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=127.0.0.1
DB_PORT=5432
DB_NAME=sibtrans_giveaway

REDIS_URL=redis://localhost:6379/0
```

Вместо набора `DB_*` можно указать одну строку подключения:

```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/sibtrans_giveaway
```

Все доступные параметры с примерами перечислены в [`.env.example`](.env.example).

### 3. Подготовьте инфраструктуру

Запустите PostgreSQL и Redis, создайте базу данных, затем примените миграции:

```bash
poetry run alembic upgrade head
```

### 4. Запустите сервисы

Каждая команда выполняется в отдельном терминале:

```bash
# API, healthcheck и веб-админка
poetry run uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Telegram-бот в polling-режиме
poetry run python bot_runner.py

# Обработчик фоновых задач
poetry run celery -A celery_app.celery_app worker --loglevel=info

# Планировщик розыгрыша
poetry run celery -A celery_app.celery_app beat --loglevel=info
```

Проверить API можно по адресу `http://localhost:8000/healthz`. При заполненных `ADMIN_USERNAME` и `ADMIN_PASSWORD` админка доступна на `http://localhost:8000/admin` или по пути из `ADMIN_BASE_URL`.

## Конфигурация розыгрыша

```env
SUBSCRIPTION_CHAT_ID=@channel
SUBSCRIPTION_URL=https://t.me/channel
RESULTS_CHAT_ID=@channel

RAFFLE_TIMEZONE=Asia/Novosibirsk
RAFFLE_AT=2026-06-04T18:00:00
RAFFLE_DISPLAY_TEXT=4 июня в 18:00

CERTIFICATE_TITLE=🏆 Сертификат 
CERTIFICATE_WINNERS=1
MERCH_1_TITLE=🎁 Увлажнитель воздуха
MERCH_1_WINNERS=1
MERCH_2_TITLE=🎁 Термос
MERCH_2_WINNERS=2
MERCH_3_TITLE=🎁 Термокружка
MERCH_3_WINNERS=5

STICKERPACK_TITLE=🎁 Стикерпак
STICKERPACK_URL=https://t.me/addstickers/example
ADMIN_IDS=123456789,987654321
```

`*_WINNERS` задаёт число отдельных победителей в категории. Категории с нулевым количеством пропускаются. Команда `/run_raffle` доступна только Telegram-пользователям из `ADMIN_IDS`.

> `RAFFLE_AT` определяет фактическое время закрытия регистрации и запуска розыгрыша, а `RAFFLE_DISPLAY_TEXT` — человекочитаемый текст в сообщениях. Эти значения нужно согласовать между собой.

## Google Sheets

Интеграция опциональна. Для её включения укажите таблицу и учётные данные сервисного аккаунта:

```env
GOOGLE_SHEET_ID=spreadsheet-id
GOOGLE_WORKSHEET_TITLE=Регистрация
GOOGLE_SERVICE_ACCOUNT_FILE=/absolute/path/to/service-account.json
```

Вместо файла с учётными данными можно передать JSON через `GOOGLE_SERVICE_ACCOUNT_JSON`. Таблицу необходимо заранее открыть сервисному аккаунту. Если лист с указанным названием отсутствует, приложение создаст его автоматически.

## Telegram-права

- бот должен быть администратором канала или группы, где проверяется подписка;
- бот должен иметь право отправлять сообщения в канал с результатами;
- пользователь должен хотя бы один раз открыть диалог с ботом, чтобы получить персональное уведомление.


## Healthcheck

```http
GET /healthz
```

```json
{"status": "ok"}
```
