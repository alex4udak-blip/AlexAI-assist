import { Component, type ReactNode } from 'react';
import { motion } from 'framer-motion';
import { AlertTriangle, RefreshCw } from 'lucide-react';
import { Button } from './ui/Button';
import { GlassPanel } from './ui/GlassPanel';

interface ErrorBoundaryProps {
  children: ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo): void {
    console.error('ErrorBoundary caught an error:', error, errorInfo);
  }

  handleReload = (): void => {
    window.location.reload();
  };

  render(): ReactNode {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-bg-primary flex items-center justify-center p-4">
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.3 }}
          >
            <GlassPanel variant="elevated" className="max-w-md text-center">
              <div className="flex justify-center mb-4">
                <div className="p-3 rounded-full bg-status-error/10">
                  <AlertTriangle className="w-8 h-8 text-status-error" />
                </div>
              </div>

              <h1 className="text-xl font-semibold text-text-primary mb-2">
                Something went wrong
              </h1>

              <p className="text-text-secondary mb-6">
                An unexpected error occurred. Please try reloading the page.
              </p>

              {this.state.error && (
                <div className="mb-6 p-3 rounded-lg bg-bg-secondary border border-border-subtle">
                  <p className="text-sm text-text-muted font-mono break-all">
                    {this.state.error.message}
                  </p>
                </div>
              )}

              <Button onClick={this.handleReload} variant="primary">
                <RefreshCw className="w-4 h-4" />
                Reload Page
              </Button>
            </GlassPanel>
          </motion.div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
