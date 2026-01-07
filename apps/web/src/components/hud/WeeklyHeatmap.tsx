import { motion } from 'framer-motion';
import { useState } from 'react';

interface HeatmapData {
  day: number; // 0-6 (Mon-Sun)
  hour: number; // 0-23
  value: number; // intensity 0-100
}

interface WeeklyHeatmapProps {
  data?: HeatmapData[];
}

const DAYS = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'];
const HOURS = Array.from({ length: 24 }, (_, i) => i);

function getIntensityColor(value: number): string {
  if (value === 0) return 'rgba(6, 182, 212, 0.05)';
  if (value < 25) return 'rgba(6, 182, 212, 0.2)';
  if (value < 50) return 'rgba(6, 182, 212, 0.4)';
  if (value < 75) return 'rgba(6, 182, 212, 0.6)';
  return 'rgba(6, 182, 212, 0.9)';
}

export function WeeklyHeatmap({ data = [] }: WeeklyHeatmapProps) {
  const [hoveredCell, setHoveredCell] = useState<{ day: number; hour: number } | null>(null);

  // Create a map for quick lookup
  const dataMap = new Map<string, number>();
  data.forEach((d) => {
    dataMap.set(`${d.day}-${d.hour}`, d.value);
  });

  const getValue = (day: number, hour: number) => {
    return dataMap.get(`${day}-${hour}`) || 0;
  };

  const hoveredValue = hoveredCell
    ? getValue(hoveredCell.day, hoveredCell.hour)
    : null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="p-4 rounded-xl bg-bg-secondary/60 backdrop-blur-md border border-border-subtle
                 shadow-inner-glow overflow-hidden"
    >
      <div className="flex items-center justify-between mb-3 gap-2">
        <h3 className="text-xs text-text-muted uppercase tracking-wider font-mono flex-shrink-0">
          Weekly Activity
        </h3>
        {hoveredValue !== null && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="text-[10px] font-mono text-hud-cyan truncate"
          >
            {DAYS[hoveredCell!.day]} {hoveredCell!.hour}:00 — {hoveredValue}%
          </motion.div>
        )}
      </div>

      <div className="flex gap-1">
        {/* Day labels */}
        <div className="flex flex-col gap-1 pr-2">
          {DAYS.map((day) => (
            <div
              key={day}
              className="h-3 flex items-center text-[10px] text-text-muted font-mono"
            >
              {day}
            </div>
          ))}
        </div>

        {/* Grid */}
        <div className="flex-1 overflow-x-auto">
          <div className="flex gap-0.5">
            {HOURS.map((hour) => (
              <div key={hour} className="flex flex-col gap-0.5">
                {DAYS.map((_, dayIndex) => {
                  const value = getValue(dayIndex, hour);
                  return (
                    <motion.div
                      key={`${dayIndex}-${hour}`}
                      initial={{ opacity: 0, scale: 0 }}
                      animate={{ opacity: 1, scale: 1 }}
                      transition={{ delay: (dayIndex + hour) * 0.002 }}
                      className="w-3 h-3 rounded-sm cursor-pointer transition-all duration-150
                                 hover:ring-1 hover:ring-hud-cyan"
                      style={{
                        backgroundColor: getIntensityColor(value),
                        boxShadow: value > 50 ? `0 0 4px rgba(6, 182, 212, ${value / 200})` : 'none',
                      }}
                      onMouseEnter={() => setHoveredCell({ day: dayIndex, hour })}
                      onMouseLeave={() => setHoveredCell(null)}
                    />
                  );
                })}
              </div>
            ))}
          </div>

          {/* Hour labels */}
          <div className="flex gap-0.5 mt-1">
            {HOURS.filter((h) => h % 4 === 0).map((hour) => (
              <div
                key={hour}
                className="text-[10px] text-text-muted font-mono"
                style={{ width: `${(100 / 6)}%` }}
              >
                {hour}:00
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Legend */}
      <div className="flex items-center justify-end gap-2 mt-3">
        <span className="text-[10px] text-text-muted font-mono">Меньше</span>
        {[0, 25, 50, 75, 100].map((v) => (
          <div
            key={v}
            className="w-3 h-3 rounded-sm"
            style={{ backgroundColor: getIntensityColor(v) }}
          />
        ))}
        <span className="text-[10px] text-text-muted font-mono">Больше</span>
      </div>
    </motion.div>
  );
}
