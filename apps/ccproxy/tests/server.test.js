import { describe, it, before, after } from 'node:test';
import assert from 'node:assert';
import { spawn } from 'child_process';
import http from 'http';

const PORT = 3099;

describe('ccproxy server', () => {
  let serverProcess;

  before(async () => {
    // Start server on test port
    serverProcess = spawn('node', ['server.js'], {
      env: { ...process.env, PORT: PORT.toString() },
      cwd: process.cwd().replace('/tests', ''),
      stdio: ['pipe', 'pipe', 'pipe']
    });

    // Wait for server to start
    await new Promise(resolve => setTimeout(resolve, 1000));
  });

  after(() => {
    if (serverProcess) {
      serverProcess.kill();
    }
  });

  it('should respond to health check', async () => {
    const response = await fetch(`http://localhost:${PORT}/health`);
    assert.strictEqual(response.status, 200);
    const data = await response.json();
    assert.strictEqual(data.status, 'healthy');
  });

  it('should reject requests without messages array', async () => {
    const response = await fetch(`http://localhost:${PORT}/v1/messages`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({})
    });
    assert.strictEqual(response.status, 400);
    const data = await response.json();
    assert.ok(data.error.message.includes('messages array required'));
  });

  it('should reject requests without user message', async () => {
    const response = await fetch(`http://localhost:${PORT}/v1/messages`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ messages: [{ role: 'system', content: 'test' }] })
    });
    assert.strictEqual(response.status, 400);
    const data = await response.json();
    assert.ok(data.error.message.includes('user message required'));
  });

  it('should reject unauthorized requests when token is set', async () => {
    // Start a new server with token
    const tokenServer = spawn('node', ['server.js'], {
      env: { ...process.env, PORT: '3098', CCPROXY_INTERNAL_TOKEN: 'test-token' },
      cwd: process.cwd().replace('/tests', ''),
      stdio: ['pipe', 'pipe', 'pipe']
    });

    await new Promise(resolve => setTimeout(resolve, 1000));

    try {
      const response = await fetch('http://localhost:3098/v1/messages', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ messages: [{ role: 'user', content: 'test' }] })
      });
      assert.strictEqual(response.status, 401);
    } finally {
      tokenServer.kill();
    }
  });
});
