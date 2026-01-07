FROM node:22-alpine

# Установка Claude Code CLI
RUN npm install -g @anthropic-ai/claude-code

# Создаём non-root пользователя
RUN addgroup -g 1001 claude && \
    adduser -D -u 1001 -G claude claude

# Создаём рабочую директорию и даём права
WORKDIR /app
RUN chown -R claude:claude /app

# Создаём директорию для Claude конфигов
RUN mkdir -p /home/claude/.claude && \
    chown -R claude:claude /home/claude/.claude

# Переключаемся на non-root пользователя
USER claude

# Копируем файлы
COPY --chown=claude:claude package*.json ./
RUN npm install

COPY --chown=claude:claude . .

# Порт
EXPOSE 8080

CMD ["node", "server.js"]
