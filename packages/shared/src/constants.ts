// Shared constants for Observer

export const API_VERSION = 'v1';

export const EVENT_TYPES = [
  'app_focus',
  'window_change',
  'url_visit',
  'file_open',
  'clipboard',
  'keystroke',
  'idle',
  'active',
] as const;

export const CATEGORIES = [
  'coding',
  'browsing',
  'writing',
  'communication',
  'design',
  'research',
  'entertainment',
  'other',
] as const;

export const AGENT_TYPES = [
  'monitor',
  'reporter',
  'assistant',
  'automation',
] as const;

export const AGENT_STATUSES = [
  'draft',
  'active',
  'disabled',
  'error',
] as const;

export const TRIGGER_TYPES = [
  'schedule',
  'event',
  'pattern',
  'webhook',
  'manual',
] as const;

export const ACTION_TYPES = [
  'notify',
  'analyze',
  'http',
  'delay',
  'condition',
  'log',
] as const;

export const LOG_LEVELS = [
  'debug',
  'info',
  'warning',
  'error',
] as const;

export const COMPLEXITY_LEVELS = [
  'low',
  'medium',
  'high',
] as const;

export const IMPACT_LEVELS = [
  'low',
  'medium',
  'high',
] as const;

// App categorization rules
export const APP_CATEGORIES: Record<string, string[]> = {
  coding: [
    'code',
    'vscode',
    'visual studio',
    'xcode',
    'intellij',
    'webstorm',
    'pycharm',
    'vim',
    'neovim',
    'emacs',
    'sublime',
    'atom',
    'terminal',
    'iterm',
    'warp',
    'hyper',
  ],
  browsing: [
    'chrome',
    'safari',
    'firefox',
    'edge',
    'opera',
    'brave',
    'arc',
  ],
  communication: [
    'slack',
    'discord',
    'teams',
    'zoom',
    'meet',
    'skype',
    'webex',
    'messages',
    'mail',
    'outlook',
    'gmail',
  ],
  writing: [
    'word',
    'pages',
    'docs',
    'notion',
    'obsidian',
    'bear',
    'ulysses',
    'ia writer',
    'typora',
    'markdown',
  ],
  design: [
    'figma',
    'sketch',
    'photoshop',
    'illustrator',
    'affinity',
    'canva',
    'framer',
  ],
  research: [
    'notion',
    'roam',
    'logseq',
    'evernote',
    'onenote',
    'devonthink',
  ],
  entertainment: [
    'spotify',
    'music',
    'youtube',
    'netflix',
    'twitch',
    'steam',
  ],
};

// Default sync interval in seconds
export const DEFAULT_SYNC_INTERVAL = 30;

// Maximum events to buffer before forcing sync
export const MAX_EVENT_BUFFER = 100;

// Pattern detection settings
export const PATTERN_DETECTION = {
  minOccurrences: 3,
  windowSizeSeconds: 300, // 5 minutes
  sequenceLength: 3,
};

// Productivity tracking
export const PRODUCTIVE_CATEGORIES = [
  'coding',
  'writing',
  'design',
  'research',
];

export const NEUTRAL_CATEGORIES = [
  'browsing',
  'communication',
];

export const UNPRODUCTIVE_CATEGORIES = [
  'entertainment',
];
