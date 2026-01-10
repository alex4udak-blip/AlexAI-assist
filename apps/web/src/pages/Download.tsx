import { useState, useEffect } from 'react';
import { Download, Apple, Monitor, CheckCircle, Clock, Cpu, Loader2 } from 'lucide-react';
import { Card, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';

// GitHub Release URLs
const REPO = 'alex4udak-blip/AlexAI-assist';
const RELEASES_URL = `https://github.com/${REPO}/releases/latest`;
const API_RELEASES_URL = `https://api.github.com/repos/${REPO}/releases/latest`;

// Fallback version if API call fails
const FALLBACK_VERSION = __APP_VERSION__;

export default function DownloadPage() {
  const [version, setVersion] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Fetch latest version from GitHub API
    fetch(API_RELEASES_URL)
      .then(res => res.json())
      .then(data => {
        if (data.tag_name) {
          // Remove 'v' prefix if present
          const ver = data.tag_name.replace(/^v/, '');
          setVersion(ver);
        } else {
          setVersion(FALLBACK_VERSION);
        }
      })
      .catch(() => {
        setVersion(FALLBACK_VERSION);
      })
      .finally(() => {
        setLoading(false);
      });
  }, []);

  const currentVersion = version || FALLBACK_VERSION;
  const downloadUrlArm = `https://github.com/${REPO}/releases/download/v${currentVersion}/Observer_${currentVersion}_aarch64.dmg`;
  const downloadUrlIntel = `https://github.com/${REPO}/releases/download/v${currentVersion}/Observer_${currentVersion}_x64.dmg`;

  const features = [
    'Работает в строке меню',
    'Собирает активность через Accessibility API',
    'Автоматически синхронизируется с сервером',
    'Низкое потребление ресурсов',
    'Автоматические обновления',
  ];

  const isAvailable = !loading && version !== null;

  const handleDownloadArm = () => {
    window.open(downloadUrlArm, '_blank');
  };

  const handleDownloadIntel = () => {
    window.open(downloadUrlIntel, '_blank');
  };

  return (
    <div className="max-w-2xl mx-auto space-y-8">
      <div className="text-center">
        <div className="w-20 h-20 rounded-2xl bg-accent-gradient flex items-center justify-center mx-auto mb-6">
          <Monitor className="w-10 h-10 text-white" />
        </div>
        <h1 className="text-3xl font-bold text-text-primary">
          Скачать Observer
        </h1>
        <p className="text-text-tertiary mt-2">
          Получите десктопное приложение для сбора данных об активности
        </p>
      </div>

      <Card>
        <CardContent className="p-8">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-3">
              <Apple className="w-8 h-8 text-text-secondary" />
              <div>
                <h3 className="font-semibold text-text-primary">
                  macOS
                </h3>
                <p className="text-sm text-text-tertiary">
                  Выберите версию для вашего Mac
                </p>
              </div>
            </div>
            <Badge variant={isAvailable ? 'success' : 'warning'}>
              {loading ? (
                <span className="flex items-center gap-1">
                  <Loader2 className="w-3 h-3 animate-spin" />
                  Загрузка
                </span>
              ) : (
                `v${currentVersion}`
              )}
            </Badge>
          </div>

          <ul className="space-y-3 mb-6">
            {features.map((feature) => (
              <li key={feature} className="flex items-center gap-3">
                <CheckCircle className="w-5 h-5 text-status-success" />
                <span className="text-text-secondary">{feature}</span>
              </li>
            ))}
          </ul>

          <div className="space-y-3">
            <Button
              className="w-full"
              size="lg"
              disabled={!isAvailable}
              onClick={handleDownloadArm}
            >
              {isAvailable ? (
                <>
                  <Download className="w-5 h-5" />
                  Скачать для Apple Silicon (M1/M2/M3)
                </>
              ) : (
                <>
                  <Clock className="w-5 h-5" />
                  Скоро будет доступно
                </>
              )}
            </Button>

            <Button
              className="w-full"
              variant="secondary"
              size="lg"
              disabled={!isAvailable}
              onClick={handleDownloadIntel}
            >
              {isAvailable ? (
                <>
                  <Cpu className="w-5 h-5" />
                  Скачать для Intel Mac
                </>
              ) : (
                <>
                  <Clock className="w-5 h-5" />
                  Скоро будет доступно
                </>
              )}
            </Button>
          </div>

          <p className="text-xs text-text-muted text-center mt-4">
            {isAvailable ? (
              <>
                Требуется macOS 10.15 или новее. ~50 МБ загрузка.{' '}
                <a
                  href={RELEASES_URL}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-accent-primary hover:underline"
                >
                  Все релизы
                </a>
              </>
            ) : (
              'Приложение находится в разработке. Следите за обновлениями.'
            )}
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="p-6">
          <h3 className="font-semibold text-text-primary mb-4">
            Как узнать какой у меня Mac?
          </h3>
          <div className="text-sm text-text-secondary space-y-2 mb-4">
            <p>Нажмите на значок Apple в левом верхнем углу экрана и выберите "Об этом Mac":</p>
            <ul className="list-disc list-inside ml-2 space-y-1">
              <li><strong>Apple M1/M2/M3</strong> - скачайте версию для Apple Silicon</li>
              <li><strong>Intel Core i5/i7/i9</strong> - скачайте версию для Intel</li>
            </ul>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="p-6">
          <h3 className="font-semibold text-text-primary mb-4">
            Инструкция по установке
          </h3>
          <ol className="space-y-4 text-sm text-text-secondary">
            <li className="flex gap-3">
              <span className="w-6 h-6 rounded-full bg-accent-muted text-accent-primary flex items-center justify-center text-xs font-medium shrink-0">
                1
              </span>
              <span>Скачайте .dmg файл для вашего Mac</span>
            </li>
            <li className="flex gap-3">
              <span className="w-6 h-6 rounded-full bg-accent-muted text-accent-primary flex items-center justify-center text-xs font-medium shrink-0">
                2
              </span>
              <span>Откройте скачанный файл и перетащите Observer в Программы</span>
            </li>
            <li className="flex gap-3">
              <span className="w-6 h-6 rounded-full bg-accent-muted text-accent-primary flex items-center justify-center text-xs font-medium shrink-0">
                3
              </span>
              <span>
                Запустите Observer и предоставьте разрешение Accessibility при запросе
              </span>
            </li>
            <li className="flex gap-3">
              <span className="w-6 h-6 rounded-full bg-accent-muted text-accent-primary flex items-center justify-center text-xs font-medium shrink-0">
                4
              </span>
              <span>
                Observer появится в строке меню и начнёт сбор данных
              </span>
            </li>
          </ol>
        </CardContent>
      </Card>

      <div className="text-center text-sm text-text-muted">
        <p>
          Возникли проблемы?{' '}
          <a
            href={`https://github.com/${REPO}/issues`}
            target="_blank"
            rel="noopener noreferrer"
            className="text-accent-primary hover:underline"
          >
            Сообщите о проблеме
          </a>
        </p>
      </div>
    </div>
  );
}
