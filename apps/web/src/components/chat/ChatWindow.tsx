import { useState, useRef, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Bot, Sparkles } from 'lucide-react';
import { Message } from './Message';
import { ChatInput } from './ChatInput';
import { api, type ChatMessage } from '../../lib/api';

export function ChatWindow() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [historyLoaded, setHistoryLoaded] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Load history and merge with any pending messages
  useEffect(() => {
    api.getChatHistory()
      .then((history) => {
        setMessages((currentMessages) => {
          // Get IDs from history to avoid duplicates
          const historyIds = new Set(history.map((m) => m.id));
          // Keep local messages that aren't in history (sent before history loaded)
          const localOnlyMessages = currentMessages.filter(
            (m) => !historyIds.has(m.id)
          );
          // Merge: history first, then any local messages
          return [...history, ...localOnlyMessages];
        });
        setHistoryLoaded(true);
      })
      .catch((err) => {
        console.error('Failed to load chat history:', err);
        setHistoryLoaded(true); // Allow sending even if history fails
      });
  }, []);

  const handleSend = async () => {
    if (!input.trim() || loading) return;

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: input,
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    try {
      const response = await api.chat(input);
      const assistantMessage: ChatMessage = {
        id: response.id,
        role: 'assistant',
        content: response.response,
        timestamp: response.timestamp,
      };
      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      const errorMessage: ChatMessage = {
        id: Date.now().toString(),
        role: 'assistant',
        content: 'Извините, произошла ошибка. Попробуйте ещё раз.',
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 lg:p-6 scrollbar-hide">
        <div className="max-w-3xl mx-auto space-y-6">
          {messages.length === 0 ? (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex flex-col items-center justify-center min-h-[60vh] text-center"
            >
              <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-violet-500 to-blue-500
                              flex items-center justify-center mb-6 shadow-glow">
                <Bot className="w-8 h-8 text-white" />
              </div>
              <h2 className="text-2xl font-semibold text-text-primary tracking-tight mb-3">
                Чат с Observer
              </h2>
              <p className="text-text-tertiary max-w-md mb-8">
                Задавайте вопросы о паттернах вашей активности, получайте предложения
                по автоматизации или просите помощи с рабочим процессом.
              </p>

              {/* Quick prompts */}
              <div className="flex flex-col sm:flex-row items-center justify-center gap-3 w-full max-w-2xl">
                {[
                  'Как прошёл мой день?',
                  'Какие паттерны ты заметил?',
                  'Предложи автоматизацию',
                ].map((prompt) => (
                  <button
                    key={prompt}
                    onClick={() => {
                      setInput(prompt);
                    }}
                    aria-label={`Использовать подсказку: ${prompt}`}
                    className="flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl
                               border border-border-subtle bg-white/[0.02]
                               text-sm text-text-secondary whitespace-nowrap
                               hover:bg-white/[0.05] hover:border-border-default
                               transition-all duration-150 w-full sm:w-auto"
                  >
                    <Sparkles className="w-4 h-4 text-hud-cyan shrink-0" />
                    {prompt}
                  </button>
                ))}
              </div>
            </motion.div>
          ) : (
            <>
              {messages.map((message) => (
                <Message key={message.id} message={message} />
              ))}
            </>
          )}

          {/* Loading indicator */}
          {loading && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex items-center gap-3"
            >
              <div className="w-8 h-8 rounded-full bg-gradient-to-br from-violet-500 to-blue-500
                              flex items-center justify-center">
                <Bot className="w-4 h-4 text-white" />
              </div>
              <div className="flex items-center gap-2 px-4 py-3 rounded-2xl rounded-tl-md bg-white/[0.05]">
                <div className="flex gap-1">
                  <span className="w-2 h-2 bg-hud-cyan rounded-full animate-bounce" />
                  <span className="w-2 h-2 bg-hud-cyan rounded-full animate-bounce"
                        style={{ animationDelay: '0.1s' }} />
                  <span className="w-2 h-2 bg-hud-cyan rounded-full animate-bounce"
                        style={{ animationDelay: '0.2s' }} />
                </div>
                <span className="text-sm text-text-tertiary ml-1">Observer думает...</span>
              </div>
            </motion.div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input */}
      <ChatInput
        value={input}
        onChange={setInput}
        onSend={handleSend}
        disabled={loading}
      />
    </div>
  );
}
