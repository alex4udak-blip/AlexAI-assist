import { motion } from 'framer-motion';
import { SendHorizontal } from 'lucide-react';

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
    <div className="p-4 border-t border-hud-cyan/30 bg-bg-primary/80 backdrop-blur-md relative overflow-hidden">
      {/* Scan line effect */}
      <div className="absolute inset-0 bg-scanline pointer-events-none opacity-30" />

      {/* HUD corner accents */}
      <div className="absolute top-0 left-0 w-3 h-3 border-t-2 border-l-2 border-hud-cyan/50" />
      <div className="absolute top-0 right-0 w-3 h-3 border-t-2 border-r-2 border-hud-cyan/50" />
      <div className="absolute bottom-0 left-0 w-3 h-3 border-b-2 border-l-2 border-hud-cyan/50" />
      <div className="absolute bottom-0 right-0 w-3 h-3 border-b-2 border-r-2 border-hud-cyan/50" />

      <div className="max-w-3xl mx-auto relative z-10">
        <div className="relative flex items-center gap-3 p-3 rounded-xl
                        bg-gradient-to-br from-hud-cyan/10 to-hud-blue/5
                        border-2 border-hud-cyan/30
                        backdrop-blur-sm
                        shadow-hud-sm
                        transition-all duration-200
                        focus-within:border-hud-cyan/50 focus-within:shadow-hud">
          {/* Animated border glow */}
          <div className="absolute inset-0 rounded-xl bg-gradient-to-r from-hud-cyan/0 via-hud-cyan/20 to-hud-cyan/0
                          opacity-0 transition-opacity duration-200 pointer-events-none
                          group-focus-within:opacity-100" />

          <textarea
            value={value}
            onChange={(e) => onChange(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Спроси что угодно..."
            disabled={disabled}
            rows={1}
            className="flex-1 bg-transparent text-text-primary placeholder:text-text-muted
                       border-0 outline-none ring-0 ring-offset-0
                       focus:border-0 focus:outline-none focus:ring-0 focus:ring-offset-0
                       focus-visible:ring-0 focus-visible:ring-offset-0 focus-visible:outline-none
                       text-sm resize-none min-h-[24px] max-h-32
                       disabled:opacity-50 disabled:cursor-not-allowed
                       relative z-10"
            style={{ height: 'auto' }}
          />

          <motion.button
            onClick={onSend}
            disabled={disabled || !value.trim()}
            aria-label="Отправить сообщение"
            whileHover={value.trim() && !disabled ? { scale: 1.05 } : {}}
            whileTap={value.trim() && !disabled ? { scale: 0.95 } : {}}
            className={`p-2.5 rounded-full transition-all duration-150 shrink-0 relative z-10
                       ${value.trim() && !disabled
                         ? 'bg-gradient-to-br from-hud-cyan to-hud-blue text-white shadow-glow-cyan hover:shadow-hud'
                         : 'bg-white/[0.05] text-text-muted cursor-not-allowed'
                       }`}
          >
            <SendHorizontal className="w-4 h-4" />
            {/* Glow ring on active */}
            {value.trim() && !disabled && (
              <motion.div
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                className="absolute inset-0 rounded-full bg-hud-cyan/30 blur-md -z-10"
              />
            )}
          </motion.button>
        </div>

        <p className="text-xs text-text-muted mt-2 text-center font-mono tracking-wide">
          <span className="text-hud-cyan">ENTER</span> — отправить, <span className="text-hud-cyan">SHIFT+ENTER</span> — новая строка
        </p>
      </div>
    </div>
  );
}
