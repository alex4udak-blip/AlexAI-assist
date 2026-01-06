import { User, Bot } from 'lucide-react';
import { formatTime, cn } from '../../lib/utils';
import type { ChatMessage } from '../../lib/api';

interface MessageProps {
  message: ChatMessage;
}

export function Message({ message }: MessageProps) {
  const isUser = message.role === 'user';

  return (
    <div
      className={cn(
        'flex gap-3 animate-in',
        isUser ? 'flex-row-reverse' : ''
      )}
    >
      <div
        className={cn(
          'w-8 h-8 rounded-lg flex items-center justify-center shrink-0',
          isUser ? 'bg-accent-gradient' : 'bg-bg-tertiary'
        )}
      >
        {isUser ? (
          <User className="w-4 h-4 text-white" />
        ) : (
          <Bot className="w-4 h-4 text-text-secondary" />
        )}
      </div>
      <div
        className={cn(
          'flex-1 max-w-[80%]',
          isUser ? 'text-right' : ''
        )}
      >
        <div
          className={cn(
            'inline-block rounded-2xl px-4 py-2.5 text-sm',
            isUser
              ? 'bg-accent-primary text-white rounded-tr-sm'
              : 'bg-bg-tertiary text-text-primary rounded-tl-sm'
          )}
        >
          <p className="whitespace-pre-wrap">{message.content}</p>
        </div>
        <p className="text-xs text-text-muted mt-1">
          {formatTime(message.timestamp)}
        </p>
      </div>
    </div>
  );
}
