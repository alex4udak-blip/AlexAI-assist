import { Download, Apple, Monitor, CheckCircle, Clock } from 'lucide-react';
import { Card, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';

// TODO: Replace with actual download URL when app is built
const DOWNLOAD_URL = '';

export default function DownloadPage() {
  const features = [
    'Работает в строке меню',
    'Собирает активность через Accessibility API',
    'Автоматически синхронизируется с сервером',
    'Низкое потребление ресурсов',
    'Автоматические обновления',
  ];

  const isAvailable = Boolean(DOWNLOAD_URL);

  const handleDownload = () => {
    if (DOWNLOAD_URL) {
      window.open(DOWNLOAD_URL, '_blank');
    }
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
                  macOS (Universal)
                </h3>
                <p className="text-sm text-text-tertiary">
                  Работает на Intel и Apple Silicon
                </p>
              </div>
            </div>
            <Badge variant={isAvailable ? 'success' : 'warning'}>
              {isAvailable ? 'v0.1.0' : 'В разработке'}
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

          <Button
            className="w-full"
            size="lg"
            disabled={!isAvailable}
            onClick={handleDownload}
          >
            {isAvailable ? (
              <>
                <Download className="w-5 h-5" />
                Скачать для macOS
              </>
            ) : (
              <>
                <Clock className="w-5 h-5" />
                Скоро будет доступно
              </>
            )}
          </Button>

          <p className="text-xs text-text-muted text-center mt-4">
            {isAvailable
              ? 'Требуется macOS 10.15 или новее. ~50 МБ загрузка.'
              : 'Приложение находится в разработке. Следите за обновлениями.'
            }
          </p>
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
              <span>Скачайте .dmg файл, нажав кнопку выше</span>
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
          Возникли проблемы? Посмотрите{' '}
          <a href="#" className="text-accent-primary hover:underline">
            руководство по установке
          </a>{' '}
          или{' '}
          <a href="#" className="text-accent-primary hover:underline">
            сообщите о проблеме
          </a>
          .
        </p>
      </div>
    </div>
  );
}
