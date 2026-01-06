# Observer - Personal AI Meta-Agent System

A complete personal AI system that observes your workflow, finds patterns, and creates autonomous agents to help you work more efficiently.

## Features

- Observes everything you do on Mac via Accessibility API (not screenshots)
- Finds patterns in your behavior
- Suggests automations based on detected patterns
- Creates agents that work autonomously
- Can code, deploy, and fix bugs by itself

## Architecture

```
RAILWAY (cloud)
├── server/          → FastAPI backend
├── web/             → React dashboard + PWA
├── PostgreSQL       → Database (Railway addon)
└── Redis            → Queues (Railway addon)

GITHUB ACTIONS
└── Builds Mac app (.dmg) on each release

MAC (local)
└── Observer.app     → Menu Bar + Collector (Tauri)
    ├── Collects data via Accessibility API
    ├── Sends to Railway server
    ├── Shows notifications
    └── Quick actions menu

ANDROID
└── PWA              → Install web dashboard as app
```

## Getting Started

### Development Flow

1. Clone this repository
2. Push to main branch
3. Connect repo to Railway for auto-deploy
4. Download Mac app from the web dashboard

### Environment Variables

#### Server (Railway)
```
DATABASE_URL=             # Auto-set by Railway PostgreSQL
REDIS_URL=                # Auto-set by Railway Redis
CLAUDE_OAUTH_TOKEN=       # Your Claude API token
ALLOWED_ORIGINS=          # Your web dashboard URL
SECRET_KEY=               # Generate: openssl rand -hex 32
```

#### Web (Railway)
```
VITE_API_URL=             # Server URL
VITE_WS_URL=              # WebSocket URL (wss://...)
```

## Tech Stack

### Server
- Python 3.12+
- FastAPI
- SQLAlchemy 2.0 (async)
- Alembic (migrations)
- PostgreSQL
- Redis

### Web Dashboard
- React 18 + TypeScript
- Vite
- Tailwind CSS
- Framer Motion
- Recharts
- Lucide React (icons)
- PWA with service worker

### Mac App
- Tauri 2.0
- Rust backend
- React frontend
- Auto-updater

## Project Structure

```
observer/
├── CLAUDE.md                 # Instructions for Claude Code
├── README.md
├── .github/workflows/        # CI/CD pipelines
├── apps/
│   ├── server/              # FastAPI backend
│   ├── web/                 # React dashboard
│   └── desktop/             # Tauri Mac app
└── packages/
    └── shared/              # Shared types and constants
```

## License

MIT
