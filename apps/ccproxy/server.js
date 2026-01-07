import Anthropic from '@anthropic-ai/sdk';
import express from 'express';

const app = express();
app.use(express.json());

const client = new Anthropic({
  apiKey: process.env.CLAUDE_OAUTH_TOKEN
});

app.post('/v1/messages', async (req, res) => {
  try {
    const { model, max_tokens, system, messages } = req.body;

    const response = await client.messages.create({
      model: model || 'claude-sonnet-4-20250514',
      max_tokens: max_tokens || 4096,
      system: system,
      messages: messages
    });

    res.json(response);
  } catch (error) {
    console.error('Claude API error:', error);
    res.status(error.status || 500).json({
      error: { message: error.message }
    });
  }
});

app.get('/health', (req, res) => {
  res.json({ status: 'healthy' });
});

const PORT = process.env.PORT || 3001;
app.listen(PORT, () => {
  console.log(`Claude proxy running on port ${PORT}`);
});
