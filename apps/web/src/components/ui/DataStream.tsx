import { type HTMLAttributes, forwardRef, useEffect, useState } from 'react';
import { cn } from '../../lib/utils';

interface DataStreamProps extends HTMLAttributes<HTMLDivElement> {
  mode?: 'text' | 'numbers' | 'hex' | 'binary';
  speed?: 'slow' | 'normal' | 'fast';
  data?: string[];
  lines?: number;
  decorative?: boolean;
}

export const DataStream = forwardRef<HTMLDivElement, DataStreamProps>(
  (
    {
      className,
      mode = 'hex',
      speed = 'normal',
      data,
      lines = 5,
      decorative = false,
      ...props
    },
    ref
  ) => {
    const [streamData, setStreamData] = useState<string[]>([]);

    const speedConfig = {
      slow: 2000,
      normal: 1000,
      fast: 500,
    };

    const generateRandomData = (): string => {
      switch (mode) {
        case 'hex':
          return `0x${Math.random().toString(16).substring(2, 10).toUpperCase()}`;
        case 'binary':
          return `0b${Math.random().toString(2).substring(2, 18)}`;
        case 'numbers':
          return `${Math.floor(Math.random() * 1000000)}`;
        case 'text':
          const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
          return Array.from(
            { length: 12 },
            () => chars[Math.floor(Math.random() * chars.length)]
          ).join('');
        default:
          return '';
      }
    };

    useEffect(() => {
      if (data) {
        setStreamData(data);
        return;
      }

      const interval = setInterval(() => {
        setStreamData((prev) => {
          const newData = [...prev, generateRandomData()];
          return newData.slice(-lines);
        });
      }, speedConfig[speed]);

      // Initialize with some data
      setStreamData(Array.from({ length: lines }, () => generateRandomData()));

      return () => clearInterval(interval);
    }, [data, lines, mode, speed]);

    return (
      <div
        ref={ref}
        className={cn(
          'font-mono text-xs overflow-hidden',
          decorative ? 'text-text-muted' : 'text-hud-cyan',
          className
        )}
        {...props}
      >
        <div className="space-y-1">
          {streamData.map((item, index) => (
            <div
              key={`${item}-${index}`}
              className={cn(
                'transition-all duration-300 ease-out',
                'animate-slide-up',
                index === streamData.length - 1 && 'text-hud-cyan drop-shadow-[0_0_4px_currentColor]'
              )}
              style={{
                animationDelay: `${index * 0.05}s`,
              }}
            >
              <span className="inline-block mr-2 text-text-tertiary">
                {String(index).padStart(2, '0')}
              </span>
              <span className="tracking-wider">{item}</span>
            </div>
          ))}
        </div>
      </div>
    );
  }
);

DataStream.displayName = 'DataStream';
