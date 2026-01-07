import express from 'express';

const app = express();
app.use(express.json());

const CLAUDE_TOKEN = process.env.CLAUDE_OAUTH_TOKEN;
const API_URL = 'https://api.anthropic.com/v1/messages';

app.post('/v1/messages', async (req, res) => {
  try {
    const response = await fetch(API_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${CLAUDE_TOKEN}`,
        'anthropic-version': '2023-06-01'
      },
      body: JSON.stringify(req.body)
    });

    const data = await response.json();

    if (!response.ok) {
      console.error('Claude API error:', data);
      return res.status(response.status).json(data);
    }

    res.json(data);
  } catch (error) {
    console.error('Proxy error:', error);
    res.status(500).json({ error: { message: error.message } });
  }
});

app.get('/health', (req, res) => {
  res.json({ status: 'healthy' });
});

const PORT = process.env.PORT || 3001;
app.listen(PORT, () => {
  console.log(`Claude proxy running on port ${PORT}`);
});
