import { useState, useRef, useEffect, useCallback } from 'react';
import { motion } from 'framer-motion';
import { Bot, Sparkles, ChevronUp, Loader2 } from 'lucide-react';
import { Message } from './Message';
import { ChatInput } from './ChatInput';
import { api, type ChatMessage } from '../../lib/api';

const MESSAGES_PER_PAGE = 30;

export function ChatWindow() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [historyLoaded, setHistoryLoaded] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [hasMore, setHasMore] = useState(false);
  const [totalMessages, setTotalMessages] = useState(0);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const messagesContainerRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    // Only auto-scroll when sending new messages, not when loading more
    if (!loadingMore) {
      scrollToBottom();
    }
  }, [messages, loadingMore]);

  // Load initial history
  useEffect(() => {
    let cancelled = false;

    const loadHistory = async () => {
      try {
        const response = await api.getChatHistory({ limit: MESSAGES_PER_PAGE, offset: 0 });
        if (!cancelled) {
          setMessages((currentMessages) => {
            // Get IDs from history to avoid duplicates
            const historyIds = new Set(response.messages.map((m) => m.id));
            // Keep local messages that aren't in history (sent before history loaded)
            const localOnlyMessages = currentMessages.filter(
              (m) => !historyIds.has(m.id)
            );
            // Merge: history first, then any local messages
            return [...response.messages, ...localOnlyMessages];
          });
          setHasMore(response.has_more);
          setTotalMessages(response.total);
          setHistoryLoaded(true);
        }
      } catch (err) {
        if (!cancelled) {
          console.error('Failed to load chat history:', err);
          setHistoryLoaded(true); // Allow sending even if history fails
        }
      }
    };

    loadHistory();
    return () => { cancelled = true; };
  }, []);

  // Load more older messages
  const loadMoreMessages = useCallback(async () => {
    if (loadingMore || !hasMore) return;

    setLoadingMore(true);
    const container = messagesContainerRef.current;
    const scrollHeightBefore = container?.scrollHeight || 0;

    try {
      // Calculate offset based on currently loaded messages
      const currentOffset = messages.length;
      const response = await api.getChatHistory({
        limit: MESSAGES_PER_PAGE,
        offset: currentOffset,
      });

      setMessages((prev) => {
        // Prepend older messages (they come in chronological order)
        const newIds = new Set(response.messages.map((m) => m.id));
        const existingMessages = prev.filter((m) => !newIds.has(m.id));
        return [...response.messages, ...existingMessages];
      });
      setHasMore(response.has_more);
      setTotalMessages(response.total);

      // Preserve scroll position after loading more
      requestAnimationFrame(() => {
        if (container) {
          const scrollHeightAfter = container.scrollHeight;
          container.scrollTop = scrollHeightAfter - scrollHeightBefore;
        }
      });
    } catch (err) {
      console.error('Failed to load more messages:', err);
    } finally {
      setLoadingMore(false);
    }
  }, [loadingMore, hasMore, messages.length]);

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
    <div className="flex flex-col h-full bg-bg-primary relative overflow-hidden">
      {/* Background effects */}
      <div className="absolute inset-0 bg-hud-radial opacity-30 pointer-events-none" />
      <div className="absolute inset-0 bg-scanline opacity-10 pointer-events-none" />

      {/* Messages with custom scrollbar */}
      <div
        ref={messagesContainerRef}
        className="flex-1 overflow-y-auto p-4 lg:p-6 relative z-10 custom-scrollbar"
      >
        <style>
          {`
            .custom-scrollbar::-webkit-scrollbar {
              width: 8px;
            }
            .custom-scrollbar::-webkit-scrollbar-track {
              background: rgba(6, 182, 212, 0.05);
              border-radius: 4px;
            }
            .custom-scrollbar::-webkit-scrollbar-thumb {
              background: linear-gradient(180deg, rgba(6, 182, 212, 0.4), rgba(59, 130, 246, 0.4));
              border-radius: 4px;
              box-shadow: 0 0 10px rgba(6, 182, 212, 0.3);
            }
            .custom-scrollbar::-webkit-scrollbar-thumb:hover {
              background: linear-gradient(180deg, rgba(6, 182, 212, 0.6), rgba(59, 130, 246, 0.6));
              box-shadow: 0 0 15px rgba(6, 182, 212, 0.5);
            }
          `}
        </style>
        <div className="max-w-3xl mx-auto space-y-6">
          {/* Load more button */}
          {hasMore && messages.length > 0 && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex justify-center"
            >
              <button
                onClick={loadMoreMessages}
                disabled={loadingMore}
                className="flex items-center gap-2 px-4 py-2 rounded-xl
                           border border-hud-cyan/30 bg-gradient-to-br from-hud-cyan/10 to-hud-blue/5
                           text-sm text-text-secondary
                           hover:border-hud-cyan/50 hover:shadow-hud-sm
                           disabled:opacity-50 disabled:cursor-not-allowed
                           backdrop-blur-sm transition-all duration-150"
              >
                {loadingMore ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin text-hud-cyan" />
                    <span>Loading...</span>
                  </>
                ) : (
                  <>
                    <ChevronUp className="w-4 h-4 text-hud-cyan" />
                    <span>Load older messages ({totalMessages - messages.length} more)</span>
                  </>
                )}
              </button>
            </motion.div>
          )}
          {messages.length === 0 ? (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex flex-col items-center justify-center min-h-[60vh] text-center"
            >
              {/* AI Avatar with enhanced glow */}
              <motion.div
                initial={{ scale: 0.8, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                transition={{ delay: 0.2 }}
                className="relative w-20 h-20 mb-8"
              >
                <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-hud-cyan to-hud-blue
                                flex items-center justify-center shadow-hud-lg
                                border border-hud-cyan/50">
                  <Bot className="w-10 h-10 text-white" />
                </div>
                {/* Pulse rings */}
                <motion.div
                  animate={{ scale: [1, 1.3, 1], opacity: [0.5, 0, 0.5] }}
                  transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
                  className="absolute inset-0 rounded-2xl border-2 border-hud-cyan"
                />
                <motion.div
                  animate={{ scale: [1, 1.5, 1], opacity: [0.3, 0, 0.3] }}
                  transition={{ duration: 2, repeat: Infinity, ease: "easeInOut", delay: 0.5 }}
                  className="absolute inset-0 rounded-2xl border-2 border-hud-blue"
                />
              </motion.div>

              <motion.h2
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.3 }}
                className="text-2xl font-semibold text-text-primary tracking-tight mb-3"
              >
                Чат с <span className="text-hud-cyan">Observer</span>
              </motion.h2>
              <motion.p
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.4 }}
                className="text-text-tertiary max-w-md mb-8"
              >
                Задавайте вопросы о паттернах вашей активности, получайте предложения
                по автоматизации или просите помощи с рабочим процессом.
              </motion.p>

              {/* Quick prompts with sci-fi styling */}
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.5 }}
                className="flex flex-col sm:flex-row items-center justify-center gap-3 w-full max-w-2xl"
              >
                {[
                  'Как прошёл мой день?',
                  'Какие паттерны ты заметил?',
                  'Предложи автоматизацию',
                ].map((prompt, index) => (
                  <motion.button
                    key={prompt}
                    whileHover={{ scale: 1.02, y: -2 }}
                    whileTap={{ scale: 0.98 }}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.6 + index * 0.1 }}
                    onClick={() => {
                      setInput(prompt);
                    }}
                    aria-label={`Использовать подсказку: ${prompt}`}
                    className="relative flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl
                               border-2 border-hud-cyan/20 bg-gradient-to-br from-hud-cyan/10 to-hud-blue/5
                               text-sm text-text-secondary whitespace-nowrap
                               hover:border-hud-cyan/40 hover:shadow-hud-sm
                               backdrop-blur-sm
                               transition-all duration-150 w-full sm:w-auto overflow-hidden"
                  >
                    {/* Glow effect on hover */}
                    <div className="absolute inset-0 bg-gradient-to-r from-hud-cyan/0 via-hud-cyan/10 to-hud-cyan/0 opacity-0 hover:opacity-100 transition-opacity" />
                    <Sparkles className="w-4 h-4 text-hud-cyan shrink-0 relative z-10" />
                    <span className="relative z-10">{prompt}</span>
                  </motion.button>
                ))}
              </motion.div>
            </motion.div>
          ) : (
            <>
              {messages.map((message) => (
                <Message key={message.id} message={message} />
              ))}
            </>
          )}

          {/* Enhanced loading indicator with pulse */}
          {loading && (
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              className="flex items-center gap-3"
            >
              {/* AI Avatar with pulse */}
              <div className="relative w-8 h-8 rounded-full bg-gradient-to-br from-hud-cyan to-hud-blue
                              flex items-center justify-center shadow-glow-cyan">
                <Bot className="w-4 h-4 text-white" />
                <motion.div
                  animate={{ scale: [1, 1.2, 1], opacity: [0.5, 0, 0.5] }}
                  transition={{ duration: 1.5, repeat: Infinity, ease: "easeInOut" }}
                  className="absolute inset-0 rounded-full border-2 border-hud-cyan"
                />
              </div>

              {/* Typing indicator */}
              <div className="relative flex items-center gap-2 px-4 py-3 rounded-2xl rounded-tl-md
                              bg-gradient-to-br from-hud-cyan/10 to-hud-blue/5
                              border border-hud-cyan/20 backdrop-blur-sm shadow-hud-sm overflow-hidden">
                {/* Animated scan line */}
                <motion.div
                  animate={{ x: [-100, 200] }}
                  transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
                  className="absolute inset-0 w-20 bg-gradient-to-r from-transparent via-hud-cyan/20 to-transparent skew-x-12"
                />

                {/* Animated dots */}
                <div className="flex gap-1 relative z-10">
                  <motion.span
                    animate={{ y: [0, -8, 0], opacity: [0.5, 1, 0.5] }}
                    transition={{ duration: 1, repeat: Infinity, ease: "easeInOut" }}
                    className="w-2 h-2 bg-hud-cyan rounded-full shadow-glow-cyan"
                  />
                  <motion.span
                    animate={{ y: [0, -8, 0], opacity: [0.5, 1, 0.5] }}
                    transition={{ duration: 1, repeat: Infinity, ease: "easeInOut", delay: 0.2 }}
                    className="w-2 h-2 bg-hud-cyan rounded-full shadow-glow-cyan"
                  />
                  <motion.span
                    animate={{ y: [0, -8, 0], opacity: [0.5, 1, 0.5] }}
                    transition={{ duration: 1, repeat: Infinity, ease: "easeInOut", delay: 0.4 }}
                    className="w-2 h-2 bg-hud-cyan rounded-full shadow-glow-cyan"
                  />
                </div>
                <span className="text-sm text-text-tertiary ml-1 font-mono relative z-10">Observer думает...</span>
              </div>
            </motion.div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input - disabled while loading history or sending */}
      <ChatInput
        value={input}
        onChange={setInput}
        onSend={handleSend}
        disabled={loading || !historyLoaded}
      />
    </div>
  );
}
