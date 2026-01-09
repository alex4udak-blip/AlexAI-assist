import { useState } from 'react';
import { Calendar, Activity } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { Card } from '../components/ui/Card';
import { Input } from '../components/ui/Input';
import { Select } from '../components/ui/Select';
import { Badge } from '../components/ui/Badge';
import { useTimeline } from '../hooks/useAnalytics';
import { formatDateTime, truncate } from '../lib/utils';

const categoryOptions = [
  { value: '', label: 'Все категории' },
  { value: 'coding', label: 'Программирование' },
  { value: 'browsing', label: 'Браузинг' },
  { value: 'writing', label: 'Письмо' },
  { value: 'communication', label: 'Коммуникация' },
];

export default function History() {
  const [hours, setHours] = useState(24);
  const [category, setCategory] = useState('');
  const [search, setSearch] = useState('');

  const { data: events, loading } = useTimeline(hours);

  const filteredEvents = events?.filter((event) => {
    if (category && event.category !== category) return false;
    if (search) {
      const searchLower = search.toLowerCase();
      return (
        event.app_name?.toLowerCase().includes(searchLower) ||
        event.window_title?.toLowerCase().includes(searchLower)
      );
    }
    return true;
  });

  return (
    <div className="space-y-8 max-w-7xl mx-auto">
      {/* Header with scan line effect */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="relative"
      >
        <h1 className="text-3xl font-bold text-cyan-400 tracking-wider relative flex items-center gap-3">
          <Activity className="w-8 h-8" />
          ИСТОРИЯ АКТИВНОСТИ
          <motion.div
            className="absolute inset-0 bg-gradient-to-r from-transparent via-cyan-400/20 to-transparent"
            animate={{ x: ['-100%', '200%'] }}
            transition={{ duration: 3, repeat: Infinity, ease: 'linear' }}
          />
        </h1>
        <p className="text-purple-400/60 mt-2 font-mono text-sm">
          &gt; Временная шкала событий
        </p>
      </motion.div>

      {/* Filter Controls with Neon Style */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.1 }}
        className="flex flex-wrap gap-4"
      >
        <div className="relative flex-1 min-w-[250px]">
          <Input
            placeholder="Поиск событий..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="[&_input]:border-2 [&_input]:border-cyan-500/30 [&_input]:bg-black/40 [&_input]:text-cyan-100 [&_input]:placeholder:text-cyan-300/30 [&_input]:focus:border-cyan-400 [&_input]:focus:shadow-[0_0_15px_rgba(6,182,212,0.4)] [&_input]:font-mono"
          />
          <motion.div
            className="absolute inset-0 border-2 border-cyan-400/0 rounded-md pointer-events-none"
            whileHover={{ borderColor: 'rgba(6,182,212,0.3)' }}
          />
        </div>

        <Select
          options={categoryOptions}
          value={category}
          onChange={(e) => setCategory(e.target.value)}
          className="w-48 [&_select]:border-2 [&_select]:border-purple-500/30 [&_select]:bg-black/40 [&_select]:text-purple-100 [&_select]:focus:border-purple-400 [&_select]:focus:shadow-[0_0_15px_rgba(168,85,247,0.4)]"
        />

        <Select
          options={[
            { value: '24', label: 'Последние 24 часа' },
            { value: '48', label: 'Последние 48 часов' },
            { value: '72', label: 'Последние 72 часа' },
            { value: '168', label: 'Последняя неделя' },
          ]}
          value={hours.toString()}
          onChange={(e) => setHours(parseInt(e.target.value))}
          className="w-48 [&_select]:border-2 [&_select]:border-purple-500/30 [&_select]:bg-black/40 [&_select]:text-purple-100 [&_select]:focus:border-purple-400 [&_select]:focus:shadow-[0_0_15px_rgba(168,85,247,0.4)]"
        />
      </motion.div>

      {/* Timeline Content */}
      {loading ? (
        <div className="space-y-4">
          {[...Array(10)].map((_, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.3, delay: i * 0.05 }}
              className="relative"
            >
              <div className="h-20 bg-gradient-to-r from-cyan-500/10 to-purple-500/10 border border-cyan-500/20 rounded-lg backdrop-blur-sm">
                <motion.div
                  className="h-full bg-gradient-to-r from-cyan-400/10 via-transparent to-transparent rounded-lg"
                  animate={{ x: ['-100%', '200%'] }}
                  transition={{ duration: 1.5, repeat: Infinity, ease: 'linear', delay: i * 0.1 }}
                />
              </div>
            </motion.div>
          ))}
        </div>
      ) : filteredEvents && filteredEvents.length > 0 ? (
        <div className="relative">
          {/* Glowing Timeline Line */}
          <div className="absolute left-4 top-0 bottom-0 w-[2px] bg-gradient-to-b from-cyan-400 via-purple-400 to-cyan-400 shadow-[0_0_10px_rgba(6,182,212,0.6)]" />

          <div className="space-y-6 relative">
            <AnimatePresence>
              {filteredEvents.map((event, index) => (
                <motion.div
                  key={event.id}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: 20 }}
                  transition={{ duration: 0.3, delay: index * 0.05 }}
                  className="relative pl-12"
                >
                  {/* Timeline Dot with Pulse */}
                  <motion.div
                    className="absolute left-[10px] top-6 w-5 h-5 rounded-full bg-gradient-to-r from-cyan-400 to-purple-400 shadow-[0_0_15px_rgba(6,182,212,0.8)]"
                    animate={{
                      scale: [1, 1.2, 1],
                      boxShadow: [
                        '0 0 15px rgba(6,182,212,0.8)',
                        '0 0 25px rgba(168,85,247,0.8)',
                        '0 0 15px rgba(6,182,212,0.8)'
                      ]
                    }}
                    transition={{ duration: 2, repeat: Infinity, delay: index * 0.2 }}
                  />

                  {/* Event Card with Holographic Effect */}
                  <motion.div
                    whileHover={{ scale: 1.02, translateX: 4 }}
                    className="relative group"
                  >
                    <Card className="bg-black/40 backdrop-blur-xl border-2 border-cyan-500/30 hover:border-cyan-400/50 shadow-[0_0_20px_rgba(6,182,212,0.1)] hover:shadow-[0_0_30px_rgba(6,182,212,0.2)] transition-all overflow-hidden">
                      {/* Holographic Overlay */}
                      <motion.div
                        className="absolute inset-0 bg-gradient-to-r from-transparent via-cyan-400/10 to-transparent pointer-events-none"
                        initial={{ x: '-100%' }}
                        whileHover={{ x: '200%' }}
                        transition={{ duration: 0.8 }}
                      />

                      <div className="flex items-center gap-4 p-4 relative">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1">
                            <p className="font-semibold text-cyan-300 tracking-wide">
                              {event.app_name || 'НЕИЗВЕСТНОЕ ПРИЛОЖЕНИЕ'}
                            </p>
                            {event.category && (
                              <Badge
                                variant="default"
                                className="bg-purple-500/20 text-purple-300 border border-purple-400/30 shadow-[0_0_8px_rgba(168,85,247,0.3)]"
                              >
                                {event.category}
                              </Badge>
                            )}
                          </div>
                          <p className="text-sm text-purple-300/70 truncate font-mono">
                            {truncate(event.window_title || '', 80)}
                          </p>
                        </div>

                        <div className="text-right shrink-0 space-y-1">
                          <p className="text-sm text-cyan-400 font-mono">
                            {formatDateTime(event.timestamp)}
                          </p>
                          <p className="text-xs text-purple-400/60 uppercase tracking-wider">
                            {event.event_type}
                          </p>
                        </div>
                      </div>

                      {/* Bottom Glow Line */}
                      <div className="absolute bottom-0 left-0 right-0 h-[1px] bg-gradient-to-r from-transparent via-cyan-400/50 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
                    </Card>
                  </motion.div>
                </motion.div>
              ))}
            </AnimatePresence>
          </div>
        </div>
      ) : (
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.5 }}
        >
          <Card className="p-12 text-center bg-black/40 backdrop-blur-xl border-2 border-purple-500/30 shadow-[0_0_30px_rgba(168,85,247,0.15)]">
            <motion.div
              animate={{
                scale: [1, 1.1, 1],
                opacity: [0.5, 0.8, 0.5]
              }}
              transition={{ duration: 3, repeat: Infinity }}
            >
              <Calendar className="w-16 h-16 text-cyan-400/50 mx-auto mb-4 drop-shadow-[0_0_15px_rgba(6,182,212,0.4)]" />
            </motion.div>
            <h3 className="text-xl font-bold text-cyan-300 mb-2 tracking-wide">
              СОБЫТИЯ НЕ НАЙДЕНЫ
            </h3>
            <p className="text-purple-300/60 font-mono">
              {search || category
                ? '&gt; Попробуйте изменить фильтры'
                : '&gt; Активность появится здесь, когда сборщик начнёт отправлять данные'}
            </p>
          </Card>
        </motion.div>
      )}
    </div>
  );
}
