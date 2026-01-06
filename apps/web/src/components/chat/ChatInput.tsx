import { Send, Mic } from 'lucide-react';
import { cn } from '../../lib/utils';

interface ChatInputProps {
  value: string;
  onChange: (value: string) => void;
  onSend: () => void;
  disabled?: boolean;
}

export function ChatInput({
  value,
  onChange,
  onSend,
  disabled,
}: ChatInputProps) {
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      onSend();
    }
  };

  return (
    <div className="border-t border-border-subtle p-4 bg-bg-secondary">
      <div className="flex items-end gap-3">
        <div className="flex-1 relative">
          <textarea
            value={value}
            onChange={(e) => onChange(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Введите сообщение..."
            disabled={disabled}
            rows={1}
            className={cn(
              'w-full bg-bg-tertiary border border-border-default rounded-xl',
              'px-4 py-3 pr-12 text-text-primary placeholder:text-text-muted',
              'focus:border-accent-primary focus:ring-1 focus:ring-accent-primary/30',
              'transition-all duration-200 outline-none resize-none',
              'max-h-32',
              disabled && 'opacity-50 cursor-not-allowed'
            )}
            style={{
              height: 'auto',
              minHeight: '48px',
            }}
          />
          <button
            onClick={onSend}
            disabled={disabled || !value.trim()}
            className={cn(
              'absolute right-2 bottom-2 p-2 rounded-lg transition-colors',
              value.trim()
                ? 'bg-accent-primary text-white hover:bg-accent-hover'
                : 'bg-bg-hover text-text-muted'
            )}
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </div>
      <p className="text-xs text-text-muted mt-2 text-center">
        Нажмите Enter для отправки, Shift+Enter для новой строки
      </p>
    </div>
  );
}
