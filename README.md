# Observer - Персональная AI Мета-Агентная Система

Полноценная персональная AI система, которая наблюдает за вашим рабочим процессом, находит паттерны поведения и создаёт автономных агентов для повышения эффективности работы.

## Возможности

- Наблюдает за всеми действиями на Mac через Accessibility API (без скриншотов)
- Находит паттерны в вашем поведении
- Предлагает автоматизации на основе обнаруженных паттернов
- Создаёт агентов, которые работают автономно
- Может писать код, деплоить и исправлять баги самостоятельно

## Архитектура

```
RAILWAY (облако)
├── server/          → FastAPI бэкенд
├── web/             → React дашборд + PWA
├── PostgreSQL       → База данных (Railway addon)
└── Redis            → Очереди (Railway addon)

GITHUB ACTIONS
├── Собирает Mac приложение (.dmg) при каждом пуше в main
├── Автодеплой сервера на Railway
└── Автодеплой веб-дашборда на Railway

MAC (локально)
└── Observer.app     → Меню-бар + Сборщик (Tauri)
    ├── Собирает данные через Accessibility API
    ├── Отправляет на Railway сервер
    ├── Показывает уведомления
    └── Быстрые действия в меню

ANDROID
└── PWA              → Установка веб-дашборда как приложения
```

## Быстрый старт

### Процесс разработки

1. Клонируйте этот репозиторий
2. Запушьте в main ветку
3. Подключите репозиторий к Railway для авто-деплоя
4. Скачайте Mac приложение с веб-дашборда

### Переменные окружения

#### Сервер (Railway)
```
DATABASE_URL=             # Автоматически от Railway PostgreSQL
REDIS_URL=                # Автоматически от Railway Redis
ANTHROPIC_API_KEY=        # API ключ от console.anthropic.com
ALLOWED_ORIGINS_STR=      # URL вашего веб-дашборда
SECRET_KEY=               # Генерация: openssl rand -hex 32
```

#### Веб (Railway)
```
VITE_API_URL=             # URL сервера
VITE_WS_URL=              # WebSocket URL (wss://...)
```

## Технологический стек

### Сервер
- Python 3.12+
- FastAPI
- SQLAlchemy 2.0 (async)
- Alembic (миграции)
- PostgreSQL
- Redis

### Веб-дашборд
- React 18 + TypeScript
- Vite
- Tailwind CSS
- Framer Motion
- Recharts
- Lucide React (иконки)
- PWA с service worker

### Mac приложение
- Tauri 2.0
- Rust бэкенд
- React фронтенд
- Авто-обновления

## Структура проекта

```
AlexAI-assist/
├── CLAUDE.md                 # Инструкции для Claude Code
├── README.md
├── .github/workflows/        # CI/CD пайплайны
│   ├── build-mac.yml        # Сборка Mac приложения
│   ├── ci.yml               # CI проверки
│   ├── deploy-server.yml    # Деплой сервера на Railway
│   └── deploy-web.yml       # Деплой веб-дашборда на Railway
├── docs/
│   └── KNOWN_ISSUES.md      # Известные проблемы
├── apps/
│   ├── server/              # FastAPI бэкенд
│   ├── web/                 # React дашборд
│   └── desktop/             # Tauri Mac приложение
└── packages/
    └── shared/              # Общие типы и константы
```

## Лицензия

MIT
