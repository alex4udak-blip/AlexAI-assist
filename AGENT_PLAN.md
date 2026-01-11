# Observer AI Agents — Полный план

## Концепция

Observer + Claude Code CLI = автономные AI агенты, работающие 24/7 на Mac, используя безлимитную подписку Claude Max $200/мес.

```
┌─────────────────────────────────────────────────────────────────┐
│                        MAC (24/7)                               │
│                                                                 │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────┐ │
│  │ Screenpipe  │───▶│  Observer   │───▶│ Claude Code CLI     │ │
│  │             │    │  Desktop    │    │ (подписка Max $200) │ │
│  │ • OCR экран │    │             │◀───│                     │ │
│  │ • Аудио     │    │ • Триггеры  │    │ $ claude -p "..."   │ │
│  │ • Контекст  │    │ • Агенты    │    │                     │ │
│  │             │    │ • Действия  │    │ Безлимит токенов!   │ │
│  └─────────────┘    └──────┬──────┘    └─────────────────────┘ │
│                            │                                    │
│                            ▼                                    │
│              ┌───────────────────────────┐                     │
│              │      Автоматизация        │                     │
│              │ • Shell команды           │                     │
│              │ • AppleScript             │                     │
│              │ • Hotkeys                 │                     │
│              │ • Browser automation      │                     │
│              │ • Git операции            │                     │
│              └───────────────────────────┘                     │
└─────────────────────────────────────────────────────────────────┘
```

## Стоимость

| Компонент | Стоимость |
|-----------|-----------|
| Claude Max $200 | $200/мес (уже есть) |
| Railway Server | $5-20/мес (уже есть) |
| Screenpipe | $0 |
| Observer Desktop | $0 |
| **ДОПОЛНИТЕЛЬНО** | **$0** |

## Фазы разработки

### Фаза 1: Базовая интеграция ✅ (текущая)

**Файлы:**
- `apps/desktop/src-tauri/src/agents/mod.rs`
- `apps/desktop/src-tauri/src/agents/claude_code.rs`

**Функционал:**
```rust
// Вызов Claude Code CLI
pub fn ask_claude(prompt: &str) -> Result<AgentResponse, String>

// Выполнение команды
pub fn execute_command(cmd: &str) -> Result<String, String>

// Агентный цикл
pub fn run_agent_task(context: &str, max_iterations: u32) -> Result<String, String>
```

**AgentResponse формат:**
```json
{
  "action": "command" | "notify" | "skip",
  "cmd": "shell команда или null",
  "reason": "объяснение"
}
```

---

### Фаза 2: Триггеры

**Когда агент запускается автоматически:**

1. **Error Trigger** — ошибка в терминале
   - Screenpipe OCR видит "Error:", "Exception:", "Failed:"
   - Запускает агента с контекстом ошибки

2. **Idle Trigger** — пользователь отошёл
   - Нет активности 5+ минут
   - Агент работает над задачами из очереди

3. **Schedule Trigger** — по расписанию
   - Каждый час проверяй логи
   - Каждое утро обнови зависимости

4. **Pattern Trigger** — паттерн поведения
   - Открыл PR → запусти code review агента
   - Закрыл Zoom → создай заметки встречи

**Файлы:**
- `apps/desktop/src-tauri/src/agents/triggers.rs`

```rust
pub enum Trigger {
    Error { pattern: String },
    Idle { minutes: u32 },
    Schedule { cron: String },
    Pattern { app: String, event: String },
}

pub fn check_triggers(screenpipe_data: &ScreenpipeFrame) -> Vec<Trigger>
```

---

### Фаза 3: Типы агентов

**1. DevOps Agent**
```
Триггер: Ошибка в терминале
Контекст: OCR терминала + последние команды
Действия:
- Анализирует ошибку
- Предлагает/выполняет фикс
- Проверяет результат
```

**2. Code Review Agent**
```
Триггер: Открыт PR на GitHub
Контекст: Diff файлов + история коммитов
Действия:
- Анализирует изменения
- Пишет комментарии
- Проверяет тесты
```

**3. Architect Agent**
```
Триггер: Создан новый файл/модуль
Контекст: Структура проекта + conventions
Действия:
- Проверяет архитектуру
- Предлагает улучшения
- Создаёт документацию
```

**4. Server Monitor Agent**
```
Триггер: Schedule (каждые 5 мин) или алерт
Контекст: Логи серверов + метрики
Действия:
- Проверяет здоровье сервисов
- Реагирует на проблемы
- Уведомляет о критичном
```

**5. Git Assistant Agent**
```
Триггер: Много uncommitted изменений
Контекст: Git diff + история
Действия:
- Предлагает разбить на коммиты
- Генерирует commit messages
- Создаёт PR description
```

**6. Meeting Notes Agent**
```
Триггер: Zoom/Meet закрылся
Контекст: Аудио транскрипция от Screenpipe
Действия:
- Суммирует встречу
- Выделяет action items
- Сохраняет в Notion/Obsidian
```

**Файлы:**
- `apps/desktop/src-tauri/src/agents/devops.rs`
- `apps/desktop/src-tauri/src/agents/code_review.rs`
- `apps/desktop/src-tauri/src/agents/architect.rs`
- `apps/desktop/src-tauri/src/agents/server_monitor.rs`
- `apps/desktop/src-tauri/src/agents/git_assistant.rs`
- `apps/desktop/src-tauri/src/agents/meeting_notes.rs`

---

### Фаза 4: Очередь задач

**Пользователь может дать список задач:**

```
Observer Task Queue:
1. [ ] Напиши тесты для auth модуля
2. [ ] Пофикси все ESLint warnings
3. [ ] Обнови README с новым API
4. [ ] Добавь логирование в payment service
```

**Агент работает над ними когда:**
- Пользователь idle (на созвоне, отошёл)
- Нет срочных триггеров
- Есть доступ к нужным файлам

**Файлы:**
- `apps/desktop/src-tauri/src/agents/task_queue.rs`
- `apps/server/src/api/routes/agent_tasks.py`

```rust
pub struct AgentTask {
    id: String,
    description: String,
    project_path: String,
    priority: Priority,
    status: TaskStatus,
    created_at: DateTime,
}

pub fn get_next_task() -> Option<AgentTask>
pub fn complete_task(id: &str, result: &str)
pub fn fail_task(id: &str, error: &str)
```

---

### Фаза 5: Безопасность и подтверждения

**Уровни действий:**

```
SAFE (автоматически):
- Читать файлы
- Запускать тесты
- Анализировать код
- Создавать файлы в /tmp

CONFIRM (notification + одобрение):
- Изменять файлы проекта
- Git commit
- Устанавливать пакеты

FORBIDDEN (никогда):
- Git push
- Удалять файлы вне проекта
- Доступ к ~/.ssh, credentials
- Операции на production
```

**Файлы:**
- `apps/desktop/src-tauri/src/agents/security.rs`

```rust
pub enum ActionLevel {
    Safe,
    NeedsConfirmation,
    Forbidden,
}

pub fn classify_action(cmd: &str) -> ActionLevel
pub fn request_confirmation(action: &str) -> bool
```

---

### Фаза 6: UI и мониторинг

**Agent Dashboard в Observer:**
- Список активных агентов
- История действий
- Очередь задач
- Логи и ошибки

**Notifications:**
- Агент выполнил задачу
- Агент нужна помощь
- Агент ждёт подтверждения

---

## Команды Claude Code

```bash
# Простой вызов
claude -p 'промт'

# С системным промптом (из файла)
claude -p "$(cat system_prompt.txt) Контекст: ..."

# Интерактивный режим (для сложных задач)
claude
```

## Системный промпт для агентов

```
Ты AI агент Observer на Mac пользователя Alex.
Твоя задача — помогать с разработкой автоматически.

КОНТЕКСТ ПРОЕКТА:
- Путь: {project_path}
- Технологии: {tech_stack}
- Текущая ветка: {git_branch}

ПРАВИЛА:
1. Отвечай ТОЛЬКО валидным JSON
2. Не выполняй деструктивные команды без подтверждения
3. Если не уверен — используй action: "notify"
4. Проверяй результат после каждого действия

ФОРМАТ ОТВЕТА:
{
  "action": "command" | "notify" | "skip" | "confirm",
  "cmd": "команда или null",
  "reason": "объяснение на русском",
  "next_step": "что проверить после"
}
```

## Пример полного цикла

```
1. Screenpipe OCR: "Error: Module 'lodash' not found"

2. Observer триггерит Error Agent

3. Observer вызывает:
   $ claude -p '[системный промпт] Контекст: Терминал показывает
   "Error: Module lodash not found" в проекте /Users/alex/myapp'

4. Claude отвечает:
   {"action": "command", "cmd": "npm install lodash",
    "reason": "Модуль не установлен", "next_step": "Повторить npm start"}

5. Observer выполняет: npm install lodash

6. Observer проверяет результат через Screenpipe

7. Observer снова вызывает Claude с обновлённым контекстом

8. Claude: {"action": "command", "cmd": "npm start",
    "reason": "Модуль установлен, запускаем", "next_step": "Проверить что сервер поднялся"}

9. Observer выполняет: npm start

10. Screenpipe видит: "Server running on port 3000"

11. Claude: {"action": "skip", "reason": "Проблема решена, сервер работает"}

12. Агент завершает работу
```

## Текущий статус

- [x] Observer Desktop базовый функционал
- [x] Screenpipe интеграция
- [x] WebSocket automation
- [x] Suggestions с Accept/Decline
- [x] Claude Code CLI работает
- [ ] **Фаза 1**: Базовая интеграция Claude Code в Observer
- [ ] **Фаза 2**: Триггеры
- [ ] **Фаза 3**: Типы агентов
- [ ] **Фаза 4**: Очередь задач
- [ ] **Фаза 5**: Безопасность
- [ ] **Фаза 6**: UI

## Файловая структура (план)

```
apps/desktop/src-tauri/src/
├── agents/
│   ├── mod.rs
│   ├── claude_code.rs      # Интеграция с Claude CLI
│   ├── triggers.rs         # Система триггеров
│   ├── task_queue.rs       # Очередь задач
│   ├── security.rs         # Проверка безопасности
│   ├── types/
│   │   ├── devops.rs
│   │   ├── code_review.rs
│   │   ├── architect.rs
│   │   ├── server_monitor.rs
│   │   ├── git_assistant.rs
│   │   └── meeting_notes.rs
│   └── prompts/
│       ├── system.txt
│       ├── devops.txt
│       ├── code_review.txt
│       └── ...
```

---

**Автор:** Alex + Claude
**Дата:** 2026-01-11
**Версия:** 0.1
