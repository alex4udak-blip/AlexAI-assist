import { BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Tooltip } from 'recharts';
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card';

interface AppUsageProps {
  data?: { app_name: string; event_count: number }[];
  loading?: boolean;
}

export function AppUsage({ data, loading }: AppUsageProps) {
  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Топ приложений</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-64 skeleton rounded" />
        </CardContent>
      </Card>
    );
  }

  const chartData = (data || []).slice(0, 10);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Топ приложений</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} layout="vertical">
              <XAxis type="number" stroke="#71717a" fontSize={12} />
              <YAxis
                type="category"
                dataKey="app_name"
                stroke="#71717a"
                fontSize={12}
                width={100}
                tickLine={false}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#1f1f23',
                  border: '1px solid rgba(255,255,255,0.08)',
                  borderRadius: '8px',
                  color: '#fafafa',
                }}
              />
              <Bar
                dataKey="event_count"
                fill="#6366f1"
                radius={[0, 4, 4, 0]}
              />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}
