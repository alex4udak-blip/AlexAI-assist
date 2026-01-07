import express from 'express';
import { spawn } from 'child_process';
import { writeFileSync, unlinkSync, mkdirSync, existsSync } from 'fs';
import { join } from 'path';
import { homedir } from 'os';

const app = express();
app.use(express.json());

// Setup Claude credentials
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

setupCredentials();

app.post('/v1/messages', async (req, res) => {
  try {
    const { messages, system } = req.body;
    const userMessage = messages.find(m => m.role === 'user')?.content || '';

    const fullPrompt = system
      ? `System: ${system}\n\nUser: ${userMessage}`
      : userMessage;

    const result = await runClaude(fullPrompt);

    res.json({
      content: [{ type: 'text', text: result }],
      model: 'claude-sonnet-4-20250514',
      role: 'assistant'
    });
  } catch (error) {
    console.error('Claude error:', error);
    res.status(500).json({ error: { message: error.message } });
  }
});

function runClaude(prompt) {
  return new Promise((resolve, reject) => {
    const claude = spawn('claude', ['-p', prompt, '--no-input'], {
      env: { ...process.env },
      stdio: ['pipe', 'pipe', 'pipe']
    });

    let output = '';
    let errorOutput = '';

    claude.stdout.on('data', (data) => {
      output += data.toString();
    });

    claude.stderr.on('data', (data) => {
      errorOutput += data.toString();
    });

    claude.on('close', (code) => {
      if (code === 0) {
        resolve(output.trim());
      } else {
        reject(new Error(errorOutput || `Claude exited with code ${code}`));
      }
    });

    claude.on('error', (err) => {
      reject(err);
    });
  });
}

app.get('/health', (req, res) => res.json({ status: 'healthy' }));

const PORT = process.env.PORT || 3001;
app.listen(PORT, () => console.log(`Claude proxy on port ${PORT}`));
