# Известные проблемы Observer

> Это персональный проект для одного пользователя. Проблемы безопасности типа "multi-tenancy" и "session ownership" здесь не актуальны.

## Критические (ломают функционал)

### 1. Undefined variables в automation.py
**Файл:** `apps/server/src/api/routes/automation.py:778, 790`

Переменные `device_statuses` и `pending_commands` используются но не определены. Endpoint `/devices/{device_id}/sync-status` упадёт с NameError.

**Решение:** Удалить endpoint или реализовать через БД.

---

### 2. Модели без миграций
**Файлы:** `apps/server/src/db/models/automation.py`

Новые модели не имеют миграций:
- `DeviceStatus`
- `CommandResult`
- `Screenshot`
- `Feedback`
- `Session`

**Решение:** Создать миграцию `alembic revision --autogenerate`

---

### 3. Event sync теряет данные
**Файлы:** `apps/desktop/src-tauri/src/sync.rs`, `apps/server/src/api/routes/events.py`

- Desktop генерирует event ID, но сервер его игнорирует
- Нет acknowledgment - desktop не знает сохранились ли events
- При ошибке сети events могут дублироваться (нет deduplication)

**Решение:** Добавить event ID в схему, реализовать ACK протокол.

---

### 4. Offline queue в памяти
**Файл:** `apps/desktop/src-tauri/src/main.rs:17-26`

Events хранятся в `Vec<Event>` в памяти. При краше приложения все несинхронизированные events теряются.

**Решение:** Персистить queue в SQLite.

---

## Высокий приоритет (ограничивают функционал)

### 5. Cross-platform заглушки
Desktop приложение работает полноценно только на macOS:

| Функция | macOS | Windows/Linux |
|---------|-------|---------------|
| App tracking | Работает | Заглушка |
| Settings | Работает | Заглушка |
| Custom commands | Заглушка | Заглушка |

**Файлы:**
- `apps/desktop/src-tauri/src/collector/apps.rs:54-58`
- `apps/desktop/src-tauri/src/commands.rs:167-171`
- `apps/desktop/src-tauri/src/automation/queue.rs:308-309`

---

### 6. Web UI заглушки

| Элемент | Проблема | Файл:строка |
|---------|----------|-------------|
| Agent Edit | Пустой handler | `Agents.tsx:102` |
| Check Connection | Кнопка без handler | `Settings.tsx:179` |
| Settings sync | TODO, не сохраняет на сервер | `Settings.tsx:60` |

---

### 7. Evolution rollback неполный
**Файл:** `apps/server/src/services/evolution/orchestrator.py:915`

Rollback реализован только для агентов. Для MEMORY и BEHAVIOR только лог без действия.

---

## Средний приоритет (технический долг)

### 8. Hardcoded URLs
Production Railway URLs захардкожены в нескольких местах:
- `apps/desktop/src-tauri/src/sync.rs:182, 235`
- `apps/web/src/lib/config.ts:28, 50`
- `apps/server/src/core/config.py:40`

**Решение:** Вынести в env variables.

---

### 9. Race condition в WebSocket
**Файл:** `apps/server/src/api/routes/automation.py:562-596`

Проверка `if device_id not in connected_devices` и последующий доступ не атомарны. Если device отключится между проверкой и отправкой - KeyError.

**Решение:** Использовать `.get()` или try/except.

---

### 10. Недокументированные env variables
Не все env vars описаны в `.env.example` файлах:
- `OBSERVER_WS_URL`, `OBSERVER_API_KEY` для desktop
- `VITE_API_KEY` для web

---

## Низкий приоритет (nice to have)

### 11. Trend indicator в ProductivityScore
Закомментирован из-за отсутствия данных сравнения с бэкенда.

### 12. Broadcast error suppression
`apps/server/src/core/websocket.py:23` - ошибки отправки молча игнорируются.

---

## Не актуально для персонального проекта

Следующие "проблемы" из аудита НЕ являются проблемами для single-user проекта:
- Session ownership validation
- Multi-tenancy enforcement
- Rate limiter bypass через headers
- Audit logs доступ без проверки прав
- CORS permissive settings (всё равно один пользователь)
- API key в query params (логи только мои)
