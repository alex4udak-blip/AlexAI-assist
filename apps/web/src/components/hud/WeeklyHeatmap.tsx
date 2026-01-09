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

const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
const HOURS = Array.from({ length: 24 }, (_, i) => i);

function getIntensityColor(value: number): string {
  if (value === 0) return 'rgb(39, 39, 42)'; // zinc-800
  if (value < 25) return 'rgb(63, 63, 70)'; // zinc-700
  if (value < 50) return 'rgb(113, 113, 122)'; // zinc-500
  if (value < 75) return 'rgb(161, 161, 170)'; // zinc-400
  return 'rgb(212, 212, 216)'; // zinc-300
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
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.3 }}
      className="p-5 rounded-xl bg-zinc-900/50 border border-zinc-800"
    >
      <div className="flex items-center justify-between mb-4 gap-2">
        <h3 className="text-xs text-zinc-500 font-medium tracking-wide">
          Weekly Activity
        </h3>
        {hoveredValue !== null && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="text-xs text-zinc-400 tabular-nums"
          >
            {DAYS[hoveredCell!.day]} {hoveredCell!.hour}:00 - {hoveredValue}%
          </motion.div>
        )}
      </div>

      <div className="flex gap-1.5">
        {/* Day labels */}
        <div className="flex flex-col gap-0.5 pr-2">
          {DAYS.map((day) => (
            <div
              key={day}
              className="h-3 flex items-center text-[10px] text-zinc-600"
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
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      transition={{ delay: (dayIndex + hour) * 0.002 }}
                      className="w-3 h-3 rounded-[3px] cursor-pointer transition-colors duration-150
                                 hover:ring-1 hover:ring-zinc-500"
                      style={{
                        backgroundColor: getIntensityColor(value),
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
          <div className="flex gap-0.5 mt-1.5">
            {HOURS.filter((h) => h % 4 === 0).map((hour) => (
              <div
                key={hour}
                className="text-[10px] text-zinc-600"
                style={{ width: `${(100 / 6)}%` }}
              >
                {hour}:00
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Legend */}
      <div className="flex items-center justify-end gap-1.5 mt-4">
        <span className="text-[10px] text-zinc-600">Less</span>
        {[0, 25, 50, 75, 100].map((v) => (
          <div
            key={v}
            className="w-3 h-3 rounded-[3px]"
            style={{ backgroundColor: getIntensityColor(v) }}
          />
        ))}
        <span className="text-[10px] text-zinc-600">More</span>
      </div>
    </motion.div>
  );
}
