import { Download, Apple, Monitor, CheckCircle } from 'lucide-react';
import { Card, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';

export default function DownloadPage() {
  const features = [
    'Runs in the menu bar',
    'Collects activity via Accessibility API',
    'Syncs automatically with server',
    'Low resource usage',
    'Auto-updates',
  ];

  return (
    <div className="max-w-2xl mx-auto space-y-8">
      <div className="text-center">
        <div className="w-20 h-20 rounded-2xl bg-accent-gradient flex items-center justify-center mx-auto mb-6">
          <Monitor className="w-10 h-10 text-white" />
        </div>
        <h1 className="text-3xl font-bold text-text-primary">
          Download Observer
        </h1>
        <p className="text-text-tertiary mt-2">
          Get the desktop app to start collecting activity data
        </p>
      </div>

      <Card>
        <CardContent className="p-8">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-3">
              <Apple className="w-8 h-8 text-text-secondary" />
              <div>
                <h3 className="font-semibold text-text-primary">
                  macOS (Universal)
                </h3>
                <p className="text-sm text-text-tertiary">
                  Works on Intel and Apple Silicon
                </p>
              </div>
            </div>
            <Badge variant="success">v0.1.0</Badge>
          </div>

          <ul className="space-y-3 mb-6">
            {features.map((feature) => (
              <li key={feature} className="flex items-center gap-3">
                <CheckCircle className="w-5 h-5 text-status-success" />
                <span className="text-text-secondary">{feature}</span>
              </li>
            ))}
          </ul>

          <Button className="w-full" size="lg">
            <Download className="w-5 h-5" />
            Download for macOS
          </Button>

          <p className="text-xs text-text-muted text-center mt-4">
            Requires macOS 10.15 or later. ~50MB download.
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="p-6">
          <h3 className="font-semibold text-text-primary mb-4">
            Installation Instructions
          </h3>
          <ol className="space-y-4 text-sm text-text-secondary">
            <li className="flex gap-3">
              <span className="w-6 h-6 rounded-full bg-accent-muted text-accent-primary flex items-center justify-center text-xs font-medium shrink-0">
                1
              </span>
              <span>Download the .dmg file from the button above</span>
            </li>
            <li className="flex gap-3">
              <span className="w-6 h-6 rounded-full bg-accent-muted text-accent-primary flex items-center justify-center text-xs font-medium shrink-0">
                2
              </span>
              <span>Open the downloaded file and drag Observer to Applications</span>
            </li>
            <li className="flex gap-3">
              <span className="w-6 h-6 rounded-full bg-accent-muted text-accent-primary flex items-center justify-center text-xs font-medium shrink-0">
                3
              </span>
              <span>
                Launch Observer and grant Accessibility permissions when prompted
              </span>
            </li>
            <li className="flex gap-3">
              <span className="w-6 h-6 rounded-full bg-accent-muted text-accent-primary flex items-center justify-center text-xs font-medium shrink-0">
                4
              </span>
              <span>
                Observer will appear in your menu bar and start collecting data
              </span>
            </li>
          </ol>
        </CardContent>
      </Card>

      <div className="text-center text-sm text-text-muted">
        <p>
          Having trouble? Check the{' '}
          <a href="#" className="text-accent-primary hover:underline">
            installation guide
          </a>{' '}
          or{' '}
          <a href="#" className="text-accent-primary hover:underline">
            report an issue
          </a>
          .
        </p>
      </div>
    </div>
  );
}
