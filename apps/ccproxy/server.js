import { ClaudeCode } from 'claude-code-js';
import express from 'express';

const app = express();
app.use(express.json());

const claude = new ClaudeCode({
  oauth: {
    accessToken: process.env.CLAUDE_OAUTH_TOKEN,
    refreshToken: process.env.CLAUDE_REFRESH_TOKEN || '',
    expiresAt: parseInt(process.env.CLAUDE_EXPIRES_AT || '0')
  }
});

app.post('/v1/messages', async (req, res) => {
  try {
    const { messages, system } = req.body;
    const userMessage = messages.find(m => m.role === 'user')?.content || '';

    const response = await claude.chat({
      prompt: userMessage,
      systemPrompt: system || 'You are a helpful assistant.'
    });

    if (response.success) {
      res.json({
        content: [{ type: 'text', text: response.message.result }],
        model: 'claude-sonnet-4-20250514',
        role: 'assistant'
      });
    } else {
      res.status(500).json({ error: response.error });
    }
  } catch (error) {
    console.error('Claude error:', error);
    res.status(500).json({ error: { message: error.message } });
  }
});

app.get('/health', (req, res) => res.json({ status: 'healthy' }));

const PORT = process.env.PORT || 3001;
app.listen(PORT, () => console.log(`Proxy on ${PORT}`));
