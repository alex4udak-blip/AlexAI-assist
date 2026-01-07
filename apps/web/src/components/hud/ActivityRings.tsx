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
  glowColor: string;
  label: string;
  displayValue: string;
  delay: number;
}

function Ring({ value, maxValue, radius, strokeWidth, color, glowColor, label, displayValue, delay }: RingProps) {
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
        stroke="rgba(255, 255, 255, 0.05)"
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
        transition={{ duration: 1.5, delay, ease: [0.16, 1, 0.3, 1] }}
        style={{
          filter: `drop-shadow(0 0 8px ${glowColor})`,
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
      strokeWidth: 12,
      color: '#f97316',
      glowColor: 'rgba(249, 115, 22, 0.5)',
      label: 'Продуктивность',
      displayValue: `${productivity}%`,
      delay: 0,
    },
    {
      value: focus,
      maxValue: 100,
      radius: 58,
      strokeWidth: 12,
      color: '#8b5cf6',
      glowColor: 'rgba(139, 92, 246, 0.5)',
      label: 'Фокус',
      displayValue: `${focus}%`,
      delay: 0.2,
    },
    {
      value: automation,
      maxValue: 100,
      radius: 41,
      strokeWidth: 12,
      color: '#10b981',
      glowColor: 'rgba(16, 185, 129, 0.5)',
      label: 'Автоматизация',
      displayValue: `${automation}%`,
      delay: 0.4,
    },
  ];

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      className="p-5 rounded-xl bg-bg-secondary/60 backdrop-blur-md border border-border-subtle
                 shadow-inner-glow"
    >
      <h3 className="text-xs text-text-muted uppercase tracking-wider font-mono mb-4">
        Activity Rings
      </h3>

      <div className="flex items-center gap-6">
        {/* SVG Rings */}
        <div className="relative">
          <svg width="180" height="180" viewBox="0 0 180 180">
            {rings.map((ring, i) => (
              <Ring key={i} {...ring} />
            ))}
          </svg>
          {/* Center text */}
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className="text-2xl font-bold text-text-primary font-mono">
              {Math.round((productivity + focus + automation) / 3)}%
            </span>
            <span className="text-xs text-text-muted">TOTAL</span>
          </div>
        </div>

        {/* Legend */}
        <div className="space-y-3">
          {rings.map((ring, i) => (
            <div key={i} className="flex items-center gap-3">
              <div
                className="w-3 h-3 rounded-full"
                style={{
                  backgroundColor: ring.color,
                  boxShadow: `0 0 10px ${ring.glowColor}`,
                }}
              />
              <div>
                <p className="text-xs text-text-muted">{ring.label}</p>
                <p className="text-sm font-mono font-medium text-text-primary">
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
