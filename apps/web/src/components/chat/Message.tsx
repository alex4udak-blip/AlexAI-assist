import { motion } from 'framer-motion';
import { User, Bot } from 'lucide-react';
import { formatTime } from '../../lib/utils';
import type { ChatMessage } from '../../lib/api';

interface MessageProps {
  message: ChatMessage;
}

export function Message({ message }: MessageProps) {
  const isUser = message.role === 'user';

  return (
    <motion.div
      initial={{ opacity: 0, y: 10, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{
        duration: 0.3,
        ease: [0.16, 1, 0.3, 1]
      }}
      className={`flex gap-4 max-w-3xl ${isUser ? 'ml-auto flex-row-reverse' : ''}`}
    >
      {/* Avatar with glow */}
      <div className={`w-8 h-8 rounded-full shrink-0 flex items-center justify-center relative
                      ${isUser
                        ? 'bg-gradient-to-br from-violet-500 to-purple-600 shadow-glow-blue'
                        : 'bg-gradient-to-br from-hud-cyan to-hud-blue shadow-glow-cyan'
                      }`}>
        {isUser ? (
          <User className="w-4 h-4 text-white" />
        ) : (
          <Bot className="w-4 h-4 text-white" />
        )}
        {/* Pulse ring */}
        <div className={`absolute inset-0 rounded-full animate-pulse-slow
                        ${isUser ? 'bg-violet-500/20' : 'bg-hud-cyan/20'}`} />
      </div>

      {/* Message content with glassmorphism */}
      <div className={`flex flex-col ${isUser ? 'items-end' : 'items-start'}`}>
        <motion.div
          whileHover={{ scale: 1.01 }}
          className={`relative px-4 py-3 rounded-2xl text-sm max-w-prose
                      backdrop-blur-sm border overflow-hidden
                      ${isUser
                        ? 'bg-gradient-to-br from-violet-500/20 to-purple-600/10 border-violet-500/30 text-text-primary rounded-tr-md shadow-glow-blue'
                        : 'bg-gradient-to-br from-hud-cyan/10 to-hud-blue/5 border-hud-cyan/20 text-text-secondary rounded-tl-md shadow-glow-cyan'
                      }`}>
          {/* Circuit pattern overlay for AI messages */}
          {!isUser && (
            <div
              className="absolute inset-0 opacity-[0.03] pointer-events-none"
              style={{
                backgroundImage: `
                  linear-gradient(90deg, transparent 24%, rgba(6, 182, 212, 0.3) 25%, rgba(6, 182, 212, 0.3) 26%, transparent 27%, transparent 74%, rgba(6, 182, 212, 0.3) 75%, rgba(6, 182, 212, 0.3) 76%, transparent 77%, transparent),
                  linear-gradient(90deg, transparent 24%, rgba(6, 182, 212, 0.3) 25%, rgba(6, 182, 212, 0.3) 26%, transparent 27%, transparent 74%, rgba(6, 182, 212, 0.3) 75%, rgba(6, 182, 212, 0.3) 76%, transparent 77%, transparent)
                `,
                backgroundSize: '20px 20px',
                backgroundPosition: '0 0, 10px 10px'
              }}
            />
          )}

          {/* Inner glow */}
          <div className={`absolute inset-0 rounded-2xl pointer-events-none
                          ${isUser
                            ? 'shadow-inner-glow opacity-50'
                            : 'shadow-inner-glow opacity-30'
                          }`} />

          <p className="whitespace-pre-wrap leading-relaxed relative z-10">{message.content}</p>
        </motion.div>

        {/* Timestamp with terminal font */}
        <span className="text-xs text-text-muted mt-1.5 px-1 font-mono tracking-wider">
          {formatTime(message.timestamp)}
        </span>
      </div>
    </motion.div>
  );
}
