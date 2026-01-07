import express from 'express';
import { spawn } from 'child_process';
import { writeFileSync, mkdirSync, existsSync } from 'fs';
import { join } from 'path';
import { homedir } from 'os';

const app = express();
app.use(express.json());

// Configuration
const SPAWN_TIMEOUT = parseInt(process.env.SPAWN_TIMEOUT || '120000', 10);
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
  // Skip auth if no token configured (internal network only)
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

    // Build prompt
    const fullPrompt = system
      ? `${system}\n\nUser: ${userMessage}`
      : userMessage;

    // Run Claude CLI
    const result = await runClaude(fullPrompt);

    res.json({
      content: [{ type: 'text', text: result }],
      model: 'claude-sonnet-4-20250514',
      role: 'assistant'
    });
  } catch (error) {
    console.error('Claude error:', error);
    const statusCode = error.message?.includes('timeout') ? 504 : 500;
    res.status(statusCode).json({ error: { message: error.message } });
  }
});

function runClaude(prompt) {
  return new Promise((resolve, reject) => {
    const args = [
      '-p', prompt,
      '--dangerously-skip-permissions',
      '--output-format', 'json'
    ];

    const claude = spawn('claude', args, {
      env: { ...process.env },
      stdio: ['pipe', 'pipe', 'pipe']
    });

    let output = '';
    let errorOutput = '';
    let killed = false;

    // Timeout handler
    const timeout = setTimeout(() => {
      killed = true;
      claude.kill('SIGTERM');
      reject(new Error(`Claude process timeout after ${SPAWN_TIMEOUT}ms`));
    }, SPAWN_TIMEOUT);

    claude.stdout.on('data', (data) => {
      output += data.toString();
    });

    claude.stderr.on('data', (data) => {
      errorOutput += data.toString();
    });

    claude.on('close', (code) => {
      clearTimeout(timeout);
      if (killed) return;

      if (code === 0) {
        try {
          // Parse JSON output
          const jsonResult = JSON.parse(output);
          // Extract text from result
          const text = jsonResult.result || jsonResult.message || output;
          resolve(text);
        } catch {
          // If not JSON, return raw output
          resolve(output.trim());
        }
      } else {
        reject(new Error(errorOutput || `Claude exited with code ${code}`));
      }
    });

    claude.on('error', (err) => {
      clearTimeout(timeout);
      if (!killed) reject(err);
    });
  });
}

app.get('/health', (req, res) => res.json({ status: 'healthy' }));

const PORT = process.env.PORT || 3001;
app.listen(PORT, () => console.log(`Claude proxy on port ${PORT}`));
