import express from 'express';
import { spawn } from 'child_process';
import { writeFileSync, mkdirSync, existsSync } from 'fs';
import { join } from 'path';
import { homedir } from 'os';

const app = express();
app.use(express.json());

// Configuration
const INTERNAL_TOKEN = process.env.CCPROXY_INTERNAL_TOKEN;

// Setup Claude credentials at startup
const CLAUDE_DIR = join(homedir(), '.claude');
const CREDENTIALS_FILE = join(CLAUDE_DIR, '.credentials.json');

function setupCredentials() {
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

  writeFileSync(CREDENTIALS_FILE, JSON.stringify(credentials, null, 2));
  console.log('Claude credentials configured');
}

// Auth middleware for internal requests
function authMiddleware(req, res, next) {
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
let responseResolve = null;
let currentResponse = '';
let restartAttempts = 0;
const MAX_RESTART_DELAY = 60000; // Max 60 sec between restarts

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
      HOME: process.env.HOME || '/home/appuser'
    }
  });

  claudeProcess.stdout.on('data', (data) => {
    // Reset restart attempts on successful output
    restartAttempts = 0;

    const lines = data.toString().split('\n').filter(l => l.trim());

    for (const line of lines) {
      try {
        const parsed = JSON.parse(line);

        // Collect text deltas
        if (parsed.type === 'assistant' && parsed.message?.content) {
          for (const block of parsed.message.content) {
            if (block.type === 'text') {
              currentResponse += block.text;
            }
          }
        }

        // End of message
        if (parsed.type === 'result') {
          if (responseResolve) {
            responseResolve(currentResponse || parsed.result);
            responseResolve = null;
            currentResponse = '';
          }
        }
      } catch (e) {
        // Not JSON, skip
      }
    }
  });

  claudeProcess.stderr.on('data', (data) => {
    console.log('Claude stderr:', data.toString());
  });

  claudeProcess.on('close', (code) => {
    console.log('Claude process closed with code:', code);
    claudeProcess = null;

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

    currentResponse = '';
    responseResolve = resolve;

    // Timeout 180 sec
    const timeout = setTimeout(() => {
      if (responseResolve) {
        responseResolve = null;
        reject(new Error('Timeout waiting for Claude response'));
      }
    }, 180000);

    // Wrap resolve to clear timeout
    const originalResolve = responseResolve;
    responseResolve = (result) => {
      clearTimeout(timeout);
      originalResolve(result);
    };

    // Send to stdin
    const message = JSON.stringify({
      type: 'user',
      message: {
        role: 'user',
        content: prompt
      }
    }) + '\n';

    console.log('Writing to Claude stdin...');
    claudeProcess.stdin.write(message);
  });
}

// Increase Express timeout
app.use((req, res, next) => {
  res.setTimeout(180000); // 3 minutes
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
    claudeSession: claudeProcess ? 'active' : 'inactive'
  });
});

// Start session on startup
startClaudeSession();

const PORT = process.env.PORT || 3001;
app.listen(PORT, () => {
  console.log(`Claude proxy on port ${PORT}`);
});
