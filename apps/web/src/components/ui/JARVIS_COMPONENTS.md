# Jarvis-Style UI Components

These components provide a sci-fi/Jarvis 2026 aesthetic for the Observer dashboard.

## Components

### 1. GlassPanel

Glassmorphism container with backdrop blur and glow effects.

**Props:**
- `variant?: 'default' | 'elevated' | 'glow'` - Visual style variant
- `animated?: boolean` - Enable entrance animation (default: true)

**Example:**
```tsx
import { GlassPanel } from '@/components/ui';

<GlassPanel variant="glow">
  <h2>Content here</h2>
</GlassPanel>
```

---

### 2. NeonText

Glowing text component with adjustable intensity.

**Props:**
- `intensity?: 'subtle' | 'medium' | 'bright'` - Glow intensity
- `color?: 'cyan' | 'blue' | 'green' | 'orange' | 'violet'` - Text color
- `animated?: boolean` - Enable pulsing animation

**Example:**
```tsx
import { NeonText } from '@/components/ui';

<NeonText intensity="bright" color="cyan">
  SYSTEM ONLINE
</NeonText>
```

---

### 3. HolographicCard

Card with holographic effects, corner accents, and optional scanlines.

**Props:**
- `variant?: 'default' | 'interactive'` - Visual style
- `showCorners?: boolean` - Show corner HUD accents (default: true)
- `showScanline?: boolean` - Show scanline effect (default: false)
- `animated?: boolean` - Enable entrance animation (default: true)

**Example:**
```tsx
import { HolographicCard } from '@/components/ui';

<HolographicCard variant="interactive" showScanline>
  <h3>Agent Status</h3>
  <p>All systems operational</p>
</HolographicCard>
```

---

### 4. PulseIndicator

Status indicator with pulsing glow animation.

**Props:**
- `status: 'active' | 'processing' | 'warning' | 'error' | 'offline'` - Status type (required)
- `size?: 'sm' | 'md' | 'lg'` - Indicator size
- `showLabel?: boolean` - Show status label
- `label?: string` - Custom label text

**Example:**
```tsx
import { PulseIndicator } from '@/components/ui';

<PulseIndicator status="active" showLabel />
<PulseIndicator status="processing" size="lg" label="Processing..." />
```

---

### 5. DataStream

Animated data stream with scrolling effect.

**Props:**
- `mode?: 'text' | 'numbers' | 'hex' | 'binary'` - Data display mode
- `speed?: 'slow' | 'normal' | 'fast'` - Animation speed
- `data?: string[]` - Custom data array (optional)
- `lines?: number` - Number of lines to show (default: 5)
- `decorative?: boolean` - Use muted colors for decoration

**Example:**
```tsx
import { DataStream } from '@/components/ui';

<DataStream mode="hex" speed="fast" />
<DataStream mode="text" data={['LOG: System init', 'LOG: Connected']} />
```

---

### 6. CircuitPattern

Decorative SVG circuit board background pattern.

**Props:**
- `variant?: 'default' | 'dense' | 'minimal'` - Pattern density
- `animated?: boolean` - Animate pulse effect (default: true)
- `opacity?: number` - Pattern opacity (default: 0.15)

**Example:**
```tsx
import { CircuitPattern } from '@/components/ui';

<div className="relative">
  <CircuitPattern variant="dense" opacity={0.1} />
  <div className="relative z-10">
    <h1>Content overlays the pattern</h1>
  </div>
</div>
```

---

## Design Principles

All components follow these principles:

1. **GPU-friendly animations** - Only transform and opacity animations
2. **Tailwind CSS** - All styling via Tailwind classes
3. **Framer Motion** - Smooth entrance animations
4. **CSS Variables** - Uses theme colors from tailwind.config.js
5. **TypeScript strict** - Full type safety
6. **Dark theme only** - Optimized for the Observer dark aesthetic

## Color Palette

- **Cyan** (#06b6d4) - Primary HUD color (like Iron Man's arc reactor)
- **Blue** (#3b82f6) - Secondary accent
- **Green** (#22c55e) - Success/active status
- **Orange** (#f97316) - Warning/productivity
- **Violet** (#8b5cf6) - Focus/automation

## Performance Notes

- All animations use `transform` and `opacity` for GPU acceleration
- Backdrop blur is hardware-accelerated
- SVG patterns are lightweight and efficient
- No heavy canvas or WebGL operations
