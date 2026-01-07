import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

interface HeatmapData {
  day: number;
  hour: number;
  value: number;
}

interface CompactHeatmapProps {
  data: HeatmapData[];
}

const days = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'];
const timeBlocks = ['0-2', '2-4', '4-6', '6-8', '8-10', '10-12', '12-14', '14-16', '16-18', '18-20', '20-22', '22-24'];

export function CompactHeatmap({ data }: CompactHeatmapProps) {
  const [selectedCell, setSelectedCell] = useState<{ day: number; block: number; value: number } | null>(null);

  // Aggregate data into 2-hour blocks
  const aggregatedData: Record<string, number> = {};
  data.forEach(({ day, hour, value }) => {
    const block = Math.floor(hour / 2);
    const key = `${day}-${block}`;
    aggregatedData[key] = (aggregatedData[key] || 0) + value;
  });

  // Find max for normalization
  const maxValue = Math.max(...Object.values(aggregatedData), 1);

  const getIntensity = (day: number, block: number): number => {
    const key = `${day}-${block}`;
    const value = aggregatedData[key] || 0;
    return Math.round((value / maxValue) * 100);
  };

  const getValue = (day: number, block: number): number => {
    const key = `${day}-${block}`;
    return aggregatedData[key] || 0;
  };

  const getColor = (intensity: number): string => {
    if (intensity === 0) return 'bg-white/5';
    if (intensity < 25) return 'bg-hud-cyan/20';
    if (intensity < 50) return 'bg-hud-cyan/40';
    if (intensity < 75) return 'bg-hud-cyan/60';
    return 'bg-hud-cyan/80';
  };

  return (
    <div className="p-4 rounded-xl bg-bg-secondary/60 border border-border-subtle">
      <h3 className="text-xs text-text-muted uppercase tracking-wider font-mono mb-3">
        Активность за неделю
      </h3>

      {/* Day headers */}
      <div className="grid grid-cols-7 gap-1 mb-1">
        {days.map((day) => (
          <div key={day} className="text-center text-[10px] text-text-muted font-mono">
            {day}
          </div>
        ))}
      </div>

      {/* Heatmap grid - 12 rows x 7 columns */}
      <div className="space-y-1">
        {timeBlocks.map((_, blockIndex) => (
          <div key={blockIndex} className="grid grid-cols-7 gap-1">
            {days.map((_, dayIndex) => {
              const intensity = getIntensity(dayIndex, blockIndex);
              const value = getValue(dayIndex, blockIndex);

              return (
                <motion.button
                  key={`${dayIndex}-${blockIndex}`}
                  whileTap={{ scale: 0.9 }}
                  onClick={() => setSelectedCell(
                    selectedCell?.day === dayIndex && selectedCell?.block === blockIndex
                      ? null
                      : { day: dayIndex, block: blockIndex, value }
                  )}
                  className={`aspect-square rounded-sm transition-colors touch-manipulation
                             ${getColor(intensity)}
                             ${selectedCell?.day === dayIndex && selectedCell?.block === blockIndex
                               ? 'ring-2 ring-hud-cyan'
                               : ''
                             }`}
                  style={{ minHeight: '16px' }}
                />
              );
            })}
          </div>
        ))}
      </div>

      {/* Time labels on the side - only show a few */}
      <div className="flex justify-between mt-2 text-[10px] text-text-muted font-mono">
        <span>00:00</span>
        <span>12:00</span>
        <span>24:00</span>
      </div>

      {/* Tooltip */}
      <AnimatePresence>
        {selectedCell && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 10 }}
            className="mt-3 p-3 rounded-lg bg-bg-primary border border-border-subtle"
          >
            <p className="text-sm text-text-primary">
              <span className="font-medium">{days[selectedCell.day]}</span>
              {' '}
              <span className="text-text-muted">{timeBlocks[selectedCell.block]}</span>
            </p>
            <p className="text-xs text-text-muted mt-1">
              Активность: <span className="text-hud-cyan font-mono">{selectedCell.value}</span> событий
            </p>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Legend */}
      <div className="flex items-center justify-center gap-1 mt-3">
        <span className="text-[10px] text-text-muted">Меньше</span>
        <div className="flex gap-0.5">
          <div className="w-3 h-3 rounded-sm bg-white/5" />
          <div className="w-3 h-3 rounded-sm bg-hud-cyan/20" />
          <div className="w-3 h-3 rounded-sm bg-hud-cyan/40" />
          <div className="w-3 h-3 rounded-sm bg-hud-cyan/60" />
          <div className="w-3 h-3 rounded-sm bg-hud-cyan/80" />
        </div>
        <span className="text-[10px] text-text-muted">Больше</span>
      </div>
    </div>
  );
}
