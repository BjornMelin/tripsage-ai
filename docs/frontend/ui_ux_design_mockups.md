# TripSage UI/UX Design Mockups & Specifications

## Design System Overview

### Visual Language
- **Style**: Modern, clean, AI-forward with subtle gradients and glass morphism
- **Typography**: Inter for UI, Cal Sans for headings, JetBrains Mono for code
- **Animation**: Smooth micro-interactions, purposeful transitions
- **Theme**: Dark mode first with intelligent light mode adaptation

### Component Library Structure
```
Design System/
├── Primitives/
│   ├── Colors
│   ├── Typography
│   ├── Spacing
│   └── Shadows
├── Components/
│   ├── Buttons
│   ├── Inputs
│   ├── Cards
│   └── Modals
├── Patterns/
│   ├── Chat Interface
│   ├── Agent Cards
│   ├── Progress Indicators
│   └── Data Visualizations
└── Templates/
    ├── Dashboard
    ├── Chat View
    ├── Planning View
    └── Settings
```

## Screen Mockups

### 1. Dashboard / Home Screen
```
┌─────────────────────────────────────────────────────────────────┐
│ ▲ TripSage                                    [@] Profile  [≡]  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Welcome back, Sarah! 👋                                        │
│  Let's plan your next adventure                                 │
│                                                                 │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │ 🤖 Chat with AI │  │ 🗺️ Recent Trips│  │ 💡 Inspiration  │ │
│  │                 │  │                 │  │                 │ │
│  │ Start planning  │  │ Tokyo - 3 days  │  │ Trending now:  │ │
│  │ with our smart  │  │ Paris - 5 days  │  │ • Bali         │ │
│  │ travel agents   │  │ NYC - Weekend   │  │ • Iceland      │ │
│  │                 │  │                 │  │ • Morocco      │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
│                                                                 │
│  Active Agents ────────────────────────────────────────────     │
│  ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐                      │
│  │ 🌐  │ │ ✈️  │ │ 🏨  │ │ 🌤️  │ │ 💰  │   [View All]       │
│  │Web  │ │Flight│ │Hotel│ │Weather│ │Budget│                   │
│  └─────┘ └─────┘ └─────┘ └─────┘ └─────┘                      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 2. AI Chat Interface
```
┌─────────────────────────────────────────────────────────────────┐
│ ← Back         TripSage AI Assistant                    [···]   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Agent Status:  🟢 Planning Agent  🟢 Search Agent       │   │
│  │               🟡 Flight Agent   ⚪ Hotel Agent          │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 🤖 AI Assistant                              10:32 AM   │   │
│  │ Hello! I'm here to help plan your perfect trip.        │   │
│  │ What destination are you thinking about?               │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 👤 You                                      10:33 AM   │   │
│  │ I want to visit Japan for 2 weeks in April             │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 🤖 AI Assistant                              10:33 AM   │   │
│  │ Great choice! Japan in April is perfect for cherry     │   │
│  │ blossoms. Let me help you plan this trip...            │   │
│  │                                                        │   │
│  │ 🔄 Searching for flights...                [████···]   │   │
│  │ 🔄 Finding best locations...               [██·····]   │   │
│  │ ⏳ Checking weather patterns...            [·······]   │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Type your message...                          [📎] [🎤] │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 3. Agent Visualization Panel
```
┌─────────────────────────────────────────────────────────────────┐
│ Agent Network Visualization                             [□ ✕]   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│     ┌───────────┐                                              │
│     │ Planning  │                                              │
│     │  Agent    │───────┐                                      │
│     └───────────┘       │                                      │
│           │             ↓                                      │
│           │       ┌───────────┐     ┌───────────┐             │
│           │       │  Search   │────▶│  Flight   │             │
│           │       │  Agent    │     │  Agent    │             │
│           │       └───────────┘     └───────────┘             │
│           │             │                 │                    │
│           ↓             ↓                 ↓                    │
│     ┌───────────┐ ┌───────────┐   ┌───────────┐              │
│     │  Hotel    │ │  Weather  │   │  Budget   │              │
│     │  Agent    │ │  Agent    │   │  Agent    │              │
│     └───────────┘ └───────────┘   └───────────┘              │
│                                                                │
│  Agent Activity Timeline ──────────────────────────────────    │
│                                                                │
│  10:33:15  Planning Agent      Started trip planning          │
│  10:33:17  Search Agent       Querying destinations           │
│  10:33:20  Flight Agent       Searching available flights     │
│  10:33:22  Weather Agent      Analyzing weather patterns      │
│  10:33:25  Hotel Agent        Finding accommodations          │
│  10:33:28  Budget Agent       Calculating trip costs          │
│                                                                │
└─────────────────────────────────────────────────────────────────┘
```

### 4. Trip Planning View
```
┌─────────────────────────────────────────────────────────────────┐
│ Your Trip to Japan                                    [Save]    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────┬───────────────────────────────────┐   │
│  │ Map View            │ Itinerary                         │   │
│  │                     │                                   │   │
│  │ [Interactive Map    │ Day 1: Tokyo                      │   │
│  │  showing:           │ • Arrival at Narita (2:00 PM)    │   │
│  │  • Tokyo            │ • Check-in at Hotel (4:00 PM)   │   │
│  │  • Kyoto            │ • Dinner in Shibuya (7:00 PM)   │   │
│  │  • Osaka            │                                   │   │
│  │  with route lines]  │ Day 2: Tokyo Exploration         │   │
│  │                     │ • Senso-ji Temple (9:00 AM)     │   │
│  │                     │ • Tsukiji Market (11:00 AM)     │   │
│  │                     │ • Tokyo Tower (2:00 PM)         │   │
│  │                     │ • Akihabara (4:00 PM)           │   │
│  └─────────────────────┴───────────────────────────────────┘   │
│                                                                 │
│  Budget Breakdown ─────────────────────────────────────────     │
│  ┌──────────────┬──────────────┬──────────────┬────────────┐   │
│  │ Flights      │ Hotels       │ Food         │ Activities │   │
│  │ $1,200       │ $800         │ $600         │ $400       │   │
│  │ ████████████ │ ████████     │ ██████       │ ████       │   │
│  └──────────────┴──────────────┴──────────────┴────────────┘   │
│  Total: $3,000 / $3,500 Budget                                  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 5. Settings & API Key Management
```
┌─────────────────────────────────────────────────────────────────┐
│ Settings                                               [□ ✕]   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Account ──────────────────────────────────────────────────     │
│  Email: sarah@example.com                              [Edit]   │
│  Password: ••••••••••                                  [Change] │
│                                                                 │
│  API Keys ─────────────────────────────────────────────────     │
│  ┌────────────────────────────────────────────────────────┐    │
│  │ OpenAI         │ sk-...7h3q  [👁️] [✓ Valid]   [Delete]│    │
│  ├────────────────────────────────────────────────────────┤    │
│  │ Anthropic      │ sk-ant-...9m [👁️] [✓ Valid]  [Delete]│    │
│  ├────────────────────────────────────────────────────────┤    │
│  │ Mapbox         │ pk.ey...8n2  [👁️] [✓ Valid]  [Delete]│    │
│  ├────────────────────────────────────────────────────────┤    │
│  │ Google Maps    │ Not configured    [Add Key]           │    │
│  └────────────────────────────────────────────────────────┘    │
│                                                                 │
│  Model Selection ──────────────────────────────────────────     │
│  Primary Model:  [GPT-4 Turbo    ▼]                            │
│  Fallback Model: [Claude 3 Opus  ▼]                            │
│                                                                 │
│  Preferences ──────────────────────────────────────────────     │
│  Theme:          [🌙 Dark  /  ☀️ Light]                        │
│  Language:       [English        ▼]                            │
│  Currency:       [USD            ▼]                            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Component Specifications

### Chat Message Component
```jsx
interface ChatMessageProps {
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  isStreaming?: boolean;
  attachments?: Attachment[];
  agentInfo?: AgentInfo;
}

// Visual states:
// - Normal message with avatar and content
// - Streaming message with typing indicator
// - Message with code blocks and syntax highlighting
// - Message with images and file attachments
// - Agent-specific styling and indicators
```

### Agent Status Card
```jsx
interface AgentStatusProps {
  agentId: string;
  name: string;
  status: 'idle' | 'thinking' | 'working' | 'completed' | 'error';
  currentTask?: string;
  progress?: number;
  metrics?: AgentMetrics;
}

// Visual features:
// - Animated status indicator
// - Progress bar for long-running tasks
// - Expandable details panel
// - Real-time metric updates
// - Error state with retry options
```

### API Key Input Component
```jsx
interface APIKeyInputProps {
  provider: string;
  value?: string;
  onSave: (key: string) => void;
  onValidate: (key: string) => Promise<boolean>;
}

// Features:
// - Masked input with show/hide toggle
// - Real-time validation
// - Copy to clipboard
// - Secure storage indicator
// - Usage statistics display
```

## Interaction Patterns

### 1. Conversational Flow
- Natural language input with auto-suggestions
- Multi-turn conversations with context retention
- Quick action buttons for common queries
- Voice input/output capabilities
- File and image upload with drag-and-drop

### 2. Agent Orchestration
- Visual representation of agent collaboration
- Real-time status updates
- Progress tracking for multi-step operations
- Error recovery and retry mechanisms
- Manual agent intervention options

### 3. Progressive Disclosure
- Collapsed/expanded states for complex information
- Tooltips for additional context
- Drill-down navigation for detailed views
- Contextual help and documentation
- Keyboard shortcuts for power users

## Responsive Design Breakpoints

### Mobile (< 768px)
- Single column layout
- Bottom sheet modals
- Swipeable panels
- Simplified navigation
- Touch-optimized controls

### Tablet (768px - 1024px)
- Two-column layout where appropriate
- Side panel for agent status
- Floating action buttons
- Adaptive navigation

### Desktop (> 1024px)
- Full multi-panel layout
- Persistent sidebars
- Keyboard navigation
- Advanced visualization options
- Multi-window support

## Animation Guidelines

### Micro-interactions
- Button hover: scale(1.02) with ease-out
- Focus states: ring animation
- Loading states: skeleton screens
- Success feedback: checkmark animation
- Error states: shake animation

### Page Transitions
- Route changes: fade with slight slide
- Modal entrance: scale-up from center
- Panel slides: horizontal slide
- Tab switches: fade transition
- Data updates: smooth morphing

### Agent Animations
- Status changes: color pulse
- Activity indicators: rotating rings
- Progress bars: smooth fill
- Connection lines: flow animation
- Completion states: burst effect

## Accessibility Standards

### WCAG 2.1 AA Compliance
- Color contrast: 4.5:1 minimum
- Focus indicators: visible outlines
- Screen reader: ARIA labels
- Keyboard navigation: full support
- Motion preferences: respect reduced motion

### Semantic HTML
- Proper heading hierarchy
- Landmark regions
- Form labels and descriptions
- Button vs. link usage
- Table headers and captions

## Performance Metrics

### Target Metrics
- First Contentful Paint: < 1.5s
- Time to Interactive: < 3.5s
- Cumulative Layout Shift: < 0.1
- Total Bundle Size: < 500kb
- Lighthouse Score: > 90

### Optimization Strategies
- Code splitting by route
- Image lazy loading
- Component lazy loading
- Service worker caching
- CDN asset delivery

## Brand Guidelines

### Voice & Tone
- Friendly and approachable
- Knowledgeable but not condescending
- Encouraging exploration
- Clear and concise
- Culturally sensitive

### Visual Identity
- Logo placement: top-left
- Brand colors: purple accent
- Icon style: outlined, 24px
- Border radius: 8px standard
- Shadow depth: 3 levels

This comprehensive design system ensures consistency, usability, and scalability across the TripSage platform while maintaining a modern, AI-forward aesthetic that enhances the travel planning experience.