import { motion } from 'framer-motion';

interface ActivityRingsProps {
  productivity: number; // 0-100, hours worked
  focus: number; // 0-100, focus sessions
  automation: number; // 0-100, time saved
}

interface RingProps {
  value: number;
  maxValue: number;
  radius: number;
  strokeWidth: number;
  color: string;
  label: string;
  displayValue: string;
  delay: number;
}

function Ring({ value, maxValue, radius, strokeWidth, color, delay }: Omit<RingProps, 'label' | 'displayValue'>) {
  const circumference = 2 * Math.PI * radius;
  const progress = Math.min(value / maxValue, 1);
  const offset = circumference - progress * circumference;

  return (
    <g>
      {/* Background ring */}
      <circle
        cx="90"
        cy="90"
        r={radius}
        fill="none"
        stroke="rgba(255, 255, 255, 0.06)"
        strokeWidth={strokeWidth}
      />
      {/* Progress ring */}
      <motion.circle
        cx="90"
        cy="90"
        r={radius}
        fill="none"
        stroke={color}
        strokeWidth={strokeWidth}
        strokeLinecap="round"
        strokeDasharray={circumference}
        initial={{ strokeDashoffset: circumference }}
        animate={{ strokeDashoffset: offset }}
        transition={{ duration: 1.2, delay, ease: [0.32, 0.72, 0, 1] }}
        style={{
          transformOrigin: 'center',
          transform: 'rotate(-90deg)',
        }}
      />
    </g>
  );
}

export function ActivityRings({ productivity, focus, automation }: ActivityRingsProps) {
  const rings = [
    {
      value: productivity,
      maxValue: 100,
      radius: 75,
      strokeWidth: 10,
      color: '#ea580c',
      label: 'Productivity',
      displayValue: `${productivity}%`,
      delay: 0,
    },
    {
      value: focus,
      maxValue: 100,
      radius: 58,
      strokeWidth: 10,
      color: '#7c3aed',
      label: 'Focus',
      displayValue: `${focus}%`,
      delay: 0.15,
    },
    {
      value: automation,
      maxValue: 100,
      radius: 41,
      strokeWidth: 10,
      color: '#059669',
      label: 'Automation',
      displayValue: `${automation}%`,
      delay: 0.3,
    },
  ];

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.3 }}
      className="p-5 rounded-xl bg-zinc-900/50 border border-zinc-800"
    >
      <h3 className="text-xs text-zinc-500 font-medium tracking-wide mb-4">
        Activity Rings
      </h3>

      <div className="flex items-center gap-5">
        {/* SVG Rings */}
        <div className="relative flex-shrink-0">
          <svg width="140" height="140" viewBox="0 0 180 180">
            {rings.map((ring, i) => (
              <Ring key={i} {...ring} />
            ))}
          </svg>
          {/* Center text */}
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className="text-2xl font-semibold text-zinc-100 tabular-nums">
              {Math.round((productivity + focus + automation) / 3)}%
            </span>
            <span className="text-[11px] text-zinc-500 font-medium">Average</span>
          </div>
        </div>

        {/* Legend */}
        <div className="flex-1 min-w-0 space-y-3">
          {rings.map((ring, i) => (
            <div key={i} className="flex items-center gap-2.5 min-w-0">
              <div
                className="w-2 h-2 rounded-full flex-shrink-0"
                style={{ backgroundColor: ring.color }}
              />
              <div className="min-w-0 flex-1">
                <p className="text-[11px] text-zinc-500 truncate">{ring.label}</p>
                <p className="text-sm font-medium text-zinc-200 tabular-nums">
                  {ring.displayValue}
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </motion.div>
  );
}
