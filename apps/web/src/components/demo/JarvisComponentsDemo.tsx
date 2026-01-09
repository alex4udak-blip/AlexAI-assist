import {
  GlassPanel,
  NeonText,
  HolographicCard,
  PulseIndicator,
  DataStream,
  CircuitPattern,
} from '../ui';

/**
 * Demo component showcasing all Jarvis-style UI components
 * This can be imported into any page to demonstrate the components
 */
export function JarvisComponentsDemo() {
  return (
    <div className="min-h-screen bg-bg-primary p-8 space-y-8 relative">
      {/* Background circuit pattern */}
      <CircuitPattern variant="default" opacity={0.1} />

      <div className="relative z-10 space-y-8">
        {/* Header */}
        <div className="text-center space-y-4">
          <NeonText intensity="bright" color="cyan" className="text-4xl font-bold">
            JARVIS UI COMPONENTS
          </NeonText>
          <p className="text-text-secondary">
            Sci-fi interface components for the Observer dashboard
          </p>
        </div>

        {/* GlassPanel Examples */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <GlassPanel variant="default">
            <h3 className="text-text-primary font-semibold mb-2">Default Panel</h3>
            <p className="text-text-secondary text-sm">
              Basic glassmorphism with subtle styling
            </p>
          </GlassPanel>

          <GlassPanel variant="elevated">
            <h3 className="text-text-primary font-semibold mb-2">Elevated Panel</h3>
            <p className="text-text-secondary text-sm">
              Enhanced with shadow and brighter border
            </p>
          </GlassPanel>

          <GlassPanel variant="glow">
            <h3 className="text-text-primary font-semibold mb-2">Glow Panel</h3>
            <p className="text-text-secondary text-sm">
              Maximum glow effect for emphasis
            </p>
          </GlassPanel>
        </div>

        {/* HolographicCard Examples */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <HolographicCard variant="default" showScanline>
            <div className="space-y-3">
              <NeonText intensity="medium" color="cyan" className="text-lg">
                System Status
              </NeonText>
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-text-secondary text-sm">Core Services</span>
                  <PulseIndicator status="active" showLabel={false} size="sm" />
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-text-secondary text-sm">Agent Network</span>
                  <PulseIndicator status="processing" showLabel={false} size="sm" />
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-text-secondary text-sm">Database</span>
                  <PulseIndicator status="active" showLabel={false} size="sm" />
                </div>
              </div>
            </div>
          </HolographicCard>

          <HolographicCard variant="interactive">
            <div className="space-y-3">
              <NeonText intensity="medium" color="blue" className="text-lg">
                Live Data Feed
              </NeonText>
              <DataStream mode="hex" speed="normal" lines={6} />
            </div>
          </HolographicCard>
        </div>

        {/* Status Indicators */}
        <GlassPanel variant="elevated">
          <h3 className="text-text-primary font-semibold mb-4">Status Indicators</h3>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            <div className="text-center space-y-2">
              <PulseIndicator status="active" size="lg" />
              <p className="text-text-secondary text-xs">Active</p>
            </div>
            <div className="text-center space-y-2">
              <PulseIndicator status="processing" size="lg" />
              <p className="text-text-secondary text-xs">Processing</p>
            </div>
            <div className="text-center space-y-2">
              <PulseIndicator status="warning" size="lg" />
              <p className="text-text-secondary text-xs">Warning</p>
            </div>
            <div className="text-center space-y-2">
              <PulseIndicator status="error" size="lg" />
              <p className="text-text-secondary text-xs">Error</p>
            </div>
            <div className="text-center space-y-2">
              <PulseIndicator status="offline" size="lg" />
              <p className="text-text-secondary text-xs">Offline</p>
            </div>
          </div>
        </GlassPanel>

        {/* NeonText Variations */}
        <GlassPanel variant="default">
          <h3 className="text-text-primary font-semibold mb-4">Neon Text Styles</h3>
          <div className="space-y-3">
            <div className="flex items-center gap-4">
              <NeonText intensity="subtle" color="cyan">Subtle Cyan</NeonText>
              <NeonText intensity="medium" color="cyan">Medium Cyan</NeonText>
              <NeonText intensity="bright" color="cyan">Bright Cyan</NeonText>
            </div>
            <div className="flex items-center gap-4">
              <NeonText intensity="medium" color="blue">Blue</NeonText>
              <NeonText intensity="medium" color="green">Green</NeonText>
              <NeonText intensity="medium" color="orange">Orange</NeonText>
              <NeonText intensity="medium" color="violet">Violet</NeonText>
            </div>
            <div>
              <NeonText intensity="bright" color="cyan" animated>
                Animated Glow
              </NeonText>
            </div>
          </div>
        </GlassPanel>

        {/* Data Streams */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <GlassPanel variant="default">
            <h4 className="text-text-primary text-sm font-semibold mb-2">Hex Stream</h4>
            <DataStream mode="hex" speed="fast" lines={5} />
          </GlassPanel>

          <GlassPanel variant="default">
            <h4 className="text-text-primary text-sm font-semibold mb-2">Binary Stream</h4>
            <DataStream mode="binary" speed="normal" lines={5} />
          </GlassPanel>

          <GlassPanel variant="default">
            <h4 className="text-text-primary text-sm font-semibold mb-2">Number Stream</h4>
            <DataStream mode="numbers" speed="slow" lines={5} />
          </GlassPanel>

          <GlassPanel variant="default">
            <h4 className="text-text-primary text-sm font-semibold mb-2">Text Stream</h4>
            <DataStream mode="text" speed="normal" lines={5} />
          </GlassPanel>
        </div>

        {/* Circuit Pattern Variants */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="relative h-32 bg-bg-secondary rounded-xl overflow-hidden">
            <CircuitPattern variant="minimal" opacity={0.3} />
            <div className="relative z-10 flex items-center justify-center h-full">
              <span className="text-text-secondary text-sm">Minimal Pattern</span>
            </div>
          </div>

          <div className="relative h-32 bg-bg-secondary rounded-xl overflow-hidden">
            <CircuitPattern variant="default" opacity={0.3} />
            <div className="relative z-10 flex items-center justify-center h-full">
              <span className="text-text-secondary text-sm">Default Pattern</span>
            </div>
          </div>

          <div className="relative h-32 bg-bg-secondary rounded-xl overflow-hidden">
            <CircuitPattern variant="dense" opacity={0.3} />
            <div className="relative z-10 flex items-center justify-center h-full">
              <span className="text-text-secondary text-sm">Dense Pattern</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
