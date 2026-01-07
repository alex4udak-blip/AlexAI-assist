FROM node:22-alpine

# Install Claude CLI globally
RUN npm install -g @anthropic-ai/claude-code

# Create app directory
WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy source
COPY . .

# Create non-root user for Claude CLI (--dangerously-skip-permissions fails as root)
RUN addgroup -g 1001 -S appgroup && \
    adduser -u 1001 -S appuser -G appgroup && \
    mkdir -p /home/appuser/.claude && \
    chown -R appuser:appgroup /app /home/appuser

# Switch to non-root user
USER appuser

CMD ["node", "server.js"]
