import { Send } from 'lucide-react';

interface ChatInputProps {
  value: string;
  onChange: (value: string) => void;
  onSend: () => void;
  disabled?: boolean;
}

export function ChatInput({ value, onChange, onSend, disabled }: ChatInputProps) {
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      onSend();
    }
  };

  return (
    <div className="p-4 border-t border-border-subtle">
      <div className="max-w-3xl mx-auto">
        <div className="flex items-center gap-3 p-3 rounded-xl
                        bg-bg-secondary focus-within:bg-bg-tertiary transition-all duration-200">
          <textarea
            value={value}
            onChange={(e) => onChange(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Спроси что угодно..."
            disabled={disabled}
            rows={1}
            className="flex-1 bg-transparent text-text-primary placeholder:text-text-muted
                       outline-none text-sm resize-none min-h-[24px] max-h-32
                       disabled:opacity-50 disabled:cursor-not-allowed"
            style={{ height: 'auto' }}
          />
          <button
            onClick={onSend}
            disabled={disabled || !value.trim()}
            aria-label="Отправить сообщение"
            className={`p-2.5 rounded-full transition-all duration-150 shrink-0
                       ${value.trim()
                         ? 'bg-hud-cyan text-white hover:bg-hud-cyan/90 hover:shadow-glow-cyan'
                         : 'bg-white/[0.05] text-text-muted cursor-not-allowed'
                       }`}
          >
            <Send className="w-4 h-4 -rotate-45" />
          </button>
        </div>
        <p className="text-xs text-text-muted mt-2 text-center">
          Enter — отправить, Shift+Enter — новая строка
        </p>
      </div>
    </div>
  );
}
