import express from 'express';
import { spawn } from 'child_process';
import { writeFileSync, mkdirSync, existsSync } from 'fs';
import { join } from 'path';
import { homedir } from 'os';
import { randomUUID } from 'crypto';

const app = express();

// Request size limit (10KB max)
app.use(express.json({ limit: '10kb' }));

// Configuration
const INTERNAL_TOKEN = process.env.CCPROXY_INTERNAL_TOKEN;
const CLAUDE_HOME = '/home/claude';

// Setup Claude credentials at startup
const CLAUDE_DIR = join(CLAUDE_HOME, '.claude');
const CREDENTIALS_FILE = join(CLAUDE_DIR, '.credentials.json');

function setupCredentials() {
  try {
    if (!existsSync(CLAUDE_DIR)) {
      mkdirSync(CLAUDE_DIR, { recursive: true });
    }

    const credentials = {
      claudeAiOauth: {
        accessToken: process.env.CLAUDE_OAUTH_TOKEN,
        refreshToken: process.env.CLAUDE_REFRESH_TOKEN || '',
        expiresAt: process.env.CLAUDE_EXPIRES_AT || ''
      }
    };

    // Secure file permissions (owner read/write only)
    writeFileSync(CREDENTIALS_FILE, JSON.stringify(credentials, null, 2), { mode: 0o600 });
    console.log('Claude credentials configured');
  } catch (err) {
    console.error('Failed to setup credentials:', err.message);
  }
}

// Auth middleware for internal requests
function authMiddleware(req, res, next) {
  // In production, require token
  if (process.env.NODE_ENV === 'production' && !INTERNAL_TOKEN) {
    console.warn('WARNING: CCPROXY_INTERNAL_TOKEN not set in production');
  }

  if (!INTERNAL_TOKEN) {
    return next();
  }

  const authHeader = req.headers.authorization;
  if (!authHeader || authHeader !== `Bearer ${INTERNAL_TOKEN}`) {
    return res.status(401).json({ error: { message: 'Unauthorized' } });
  }
  next();
}

setupCredentials();

// Persistent Claude CLI session
let claudeProcess = null;
let restartAttempts = 0;
const MAX_RESTART_DELAY = 60000;

// Request-scoped state to handle concurrent requests
const pendingRequests = new Map();

function startClaudeSession() {
  console.log('Starting persistent Claude session...');

  claudeProcess = spawn('claude', [
    '--input-format', 'stream-json',
    '--output-format', 'stream-json',
    '--dangerously-skip-permissions',
    '--verbose'
  ], {
    env: {
      ...process.env,
      CLAUDE_CODE_OAUTH_TOKEN: process.env.CLAUDE_OAUTH_TOKEN,
      HOME: CLAUDE_HOME
    }
  });

  claudeProcess.stdout.on('data', (data) => {
    restartAttempts = 0;

    const lines = data.toString().split('\n').filter(l => l.trim());

    for (const line of lines) {
      try {
        const parsed = JSON.parse(line);

        // Get current request (FIFO - first pending request)
        const requestIds = Array.from(pendingRequests.keys());
        if (requestIds.length === 0) continue;

        const currentRequestId = requestIds[0];
        const request = pendingRequests.get(currentRequestId);
        if (!request) continue;

        // Collect text deltas
        if (parsed.type === 'assistant' && parsed.message?.content) {
          for (const block of parsed.message.content) {
            if (block.type === 'text') {
              request.response += block.text;
            }
          }
        }

        // End of message
        if (parsed.type === 'result') {
          const finalResponse = request.response || parsed.result || '';
          request.resolve(finalResponse);
          pendingRequests.delete(currentRequestId);
        }
      } catch (e) {
        console.error('JSON parse error:', e.message);
      }
    }
  });

  claudeProcess.stderr.on('data', (data) => {
    console.log('Claude stderr:', data.toString());
  });

  claudeProcess.on('close', (code) => {
    console.log('Claude process closed with code:', code);
    claudeProcess = null;

    // Reject all pending requests
    for (const [id, request] of pendingRequests) {
      request.reject(new Error('Claude session closed'));
      pendingRequests.delete(id);
    }

    // Exponential backoff for restarts
    restartAttempts++;
    const delay = Math.min(1000 * Math.pow(2, restartAttempts - 1), MAX_RESTART_DELAY);
    console.log(`Restarting in ${delay}ms (attempt ${restartAttempts})...`);
    setTimeout(startClaudeSession, delay);
  });

  claudeProcess.on('error', (err) => {
    console.error('Claude process error:', err);
  });
}

function sendMessage(prompt) {
  return new Promise((resolve, reject) => {
    if (!claudeProcess) {
      reject(new Error('Claude session not ready'));
      return;
    }

    const requestId = randomUUID();

    // Store request state
    const requestState = {
      response: '',
      resolve,
      reject,
      timeout: null
    };

    // Timeout 180 sec
    requestState.timeout = setTimeout(() => {
      if (pendingRequests.has(requestId)) {
        pendingRequests.delete(requestId);
        reject(new Error('Timeout waiting for Claude response'));
      }
    }, 180000);

    // Wrap resolve to clear timeout
    const originalResolve = resolve;
    requestState.resolve = (result) => {
      clearTimeout(requestState.timeout);
      originalResolve(result);
    };

    pendingRequests.set(requestId, requestState);

    // Send to stdin
    const message = JSON.stringify({
      type: 'user',
      message: {
        role: 'user',
        content: prompt
      }
    }) + '\n';

    console.log(`[${requestId.slice(0, 8)}] Sending message...`);

    try {
      claudeProcess.stdin.write(message, (err) => {
        if (err) {
          pendingRequests.delete(requestId);
          clearTimeout(requestState.timeout);
          reject(new Error(`Failed to write to stdin: ${err.message}`));
        }
      });
    } catch (err) {
      pendingRequests.delete(requestId);
      clearTimeout(requestState.timeout);
      reject(err);
    }
  });
}

// Increase Express timeout
app.use((req, res, next) => {
  res.setTimeout(180000);
  next();
});

app.post('/v1/messages', authMiddleware, async (req, res) => {
  try {
    const { messages, system } = req.body;

    // Validate request body
    if (!messages || !Array.isArray(messages)) {
      return res.status(400).json({ error: { message: 'messages array required' } });
    }

    const userMessage = messages.find(m => m.role === 'user')?.content || '';

    if (!userMessage) {
      return res.status(400).json({ error: { message: 'user message required' } });
    }

    // Limit message size
    if (userMessage.length > 100000) {
      return res.status(400).json({ error: { message: 'message too long (max 100KB)' } });
    }

    const fullPrompt = system
      ? `${system}\n\nUser: ${userMessage}`
      : userMessage;

    console.log('Sending to persistent session:', userMessage.substring(0, 50) + '...');

    const result = await sendMessage(fullPrompt);

    console.log('Got response, length:', result.length);

    res.json({
      content: [{ type: 'text', text: result }],
      model: 'claude-sonnet-4-20250514',
      role: 'assistant'
    });
  } catch (error) {
    console.error('Error:', error.message);
    const statusCode = error.message?.includes('timeout') ? 504 : 500;
    res.status(statusCode).json({ error: { message: error.message } });
  }
});

app.get('/health', (req, res) => {
  res.json({
    status: 'healthy',
    claudeSession: claudeProcess ? 'active' : 'inactive',
    pendingRequests: pendingRequests.size
  });
});

// Start session on startup
startClaudeSession();

const PORT = process.env.PORT || 3001;
app.listen(PORT, () => {
  console.log(`Claude proxy on port ${PORT}`);
});
