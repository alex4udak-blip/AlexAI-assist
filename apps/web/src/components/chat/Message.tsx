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
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className={`flex gap-4 max-w-3xl ${isUser ? 'ml-auto flex-row-reverse' : ''}`}
    >
      {/* Avatar */}
      <div className={`w-8 h-8 rounded-full shrink-0 flex items-center justify-center
                      ${isUser
                        ? 'bg-white/10'
                        : 'bg-gradient-to-br from-violet-500 to-blue-500'
                      }`}>
        {isUser ? (
          <User className="w-4 h-4 text-text-secondary" />
        ) : (
          <Bot className="w-4 h-4 text-white" />
        )}
      </div>

      {/* Message content */}
      <div className={`flex flex-col ${isUser ? 'items-end' : 'items-start'}`}>
        <div className={`px-4 py-3 rounded-2xl text-sm max-w-prose
                        ${isUser
                          ? 'bg-hud-cyan/20 text-text-primary rounded-tr-md'
                          : 'bg-white/[0.05] text-text-secondary rounded-tl-md'
                        }`}>
          <p className="whitespace-pre-wrap leading-relaxed">{message.content}</p>
        </div>
        <span className="text-xs text-text-muted mt-1.5 px-1">
          {formatTime(message.timestamp)}
        </span>
      </div>
    </motion.div>
  );
}
