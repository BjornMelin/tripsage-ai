# TripSage Frontend Implementation TODO

> **Status**: Pre-Development  
> **Tech Stack**: Next.js 15.3, React 19, TypeScript 5.5, Tailwind CSS v4, shadcn/ui v3-canary, Zustand v5, TanStack Query v5, Vercel AI SDK v5  
> **Backend**: FastAPI with MCP servers (Supabase, Neo4j, Flights, Weather, Maps, etc.)  
> **Last Updated**: January 16, 2025

## Phase 0: Foundation & Setup (Week 1)

### Project Initialization
- [ ] Create Next.js 15.3 project with TypeScript and App Router
  ```bash
  npx create-next-app@latest tripsage-web --typescript --tailwind --app --turbo
  ```
- [ ] Configure TypeScript 5.5+ with strict settings
  ```json
  {
    "compilerOptions": {
      "strict": true,
      "noUnusedLocals": true,
      "noUnusedParameters": true,
      "noImplicitReturns": true,
      "types": ["@types/node", "react/next"]
    }
  }
  ```
- [ ] Enable Turbopack for development and production builds
- [ ] Initialize Git with comprehensive .gitignore
- [ ] Set up environment variables structure (.env.local, .env.example)

### Development Environment
- [ ] Install and configure Biome for linting/formatting
  ```bash
  npm install --save-dev @biomejs/biome
  ```
- [ ] Set up Vitest v2 with React Testing Library
- [ ] Install Playwright v1.48+ for E2E testing
- [ ] Configure Husky for pre-commit hooks
- [ ] Set up VS Code workspace settings
- [ ] Install recommended VS Code extensions

### Core Dependencies Installation
```bash
# UI & Styling
npm install tailwindcss@alpha postcss autoprefixer
npm install @radix-ui/colors @radix-ui/themes
npm install lucide-react framer-motion@^11
npm install clsx tailwind-merge class-variance-authority
npm install next-themes

# State Management & Data
npm install zustand@^5 @tanstack/react-query@^5
npm install react-hook-form@^8 zod@^3
npm install @supabase/supabase-js @supabase/ssr

# AI & Real-time
npm install ai@^5 eventsource-parser
npm install socket.io-client

# Maps & Visualization  
npm install mapbox-gl@^3 react-map-gl@^7
npm install reactflow@^12 recharts@^2

# Development
npm install --save-dev @types/node @types/react
npm install --save-dev vitest @vitejs/plugin-react
npm install --save-dev @testing-library/react @testing-library/user-event
npm install --save-dev @playwright/test
```

### Tailwind CSS v4 Configuration
- [ ] Configure Tailwind with OKLCH color system
  ```css
  /* tailwind.config.js */
  export default {
    content: ['./src/**/*.{js,ts,jsx,tsx,mdx}'],
    theme: {
      extend: {
        colors: {
          primary: 'oklch(var(--primary) / <alpha-value>)',
          secondary: 'oklch(var(--secondary) / <alpha-value>)',
        }
      }
    },
    plugins: [
      require('@tailwindcss/typography'),
      require('@tailwindcss/forms'),
    ],
  }
  ```
- [ ] Set up CSS variables for theming
- [ ] Configure container queries
- [ ] Create responsive breakpoint system

### shadcn/ui v3 Setup
- [ ] Install shadcn/ui CLI with React 19 canary support
  ```bash
  npx shadcn@canary init
  ```
- [ ] Configure components.json for project
- [ ] Install base components:
  - [ ] Button, Card, Dialog, Dropdown Menu
  - [ ] Form, Input, Label, Select
  - [ ] Toast, Alert, Badge, Avatar
  - [ ] Tabs, Accordion, Command, Calendar

## Phase 1: Core Infrastructure (Week 2)

### Directory Structure Setup
- [ ] Create complete project structure as per architecture
- [ ] Set up path aliases in tsconfig.json
  ```json
  {
    "compilerOptions": {
      "paths": {
        "@/*": ["./src/*"],
        "@/components/*": ["./src/components/*"],
        "@/lib/*": ["./src/lib/*"],
        "@/hooks/*": ["./src/hooks/*"]
      }
    }
  }
  ```

### Authentication Foundation
- [ ] Create Supabase client configuration
  ```typescript
  // lib/supabase/client.ts
  import { createBrowserClient } from '@supabase/ssr'
  
  export const supabase = createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
  )
  ```
- [ ] Implement server-side Supabase client
- [ ] Create auth context provider
- [ ] Implement useAuth hook
- [ ] Create auth middleware for protected routes
- [ ] Set up session persistence with cookies

### API Client Architecture
- [ ] Create base API client with error handling
- [ ] Implement request/response interceptors
- [ ] Set up retry logic with exponential backoff
- [ ] Create type-safe API endpoints
- [ ] Implement request cancellation
- [ ] Add comprehensive error types
- [ ] Remove any direct MCP key references
- [ ] Ensure all MCP calls proxy through backend
- [ ] Add API key status monitoring endpoints

### State Management Setup
- [ ] Create Zustand stores:
  - [ ] Auth store (user, session, preferences)
  - [ ] UI store (theme, sidebar, modals)
  - [ ] Trip store (current trip, drafts)
  - [ ] Agent store (active agents, conversations)
- [ ] Implement store persistence
- [ ] Add TypeScript interfaces for all stores
- [ ] Create store selectors with proper typing

### Real-time Communication Infrastructure
- [ ] Set up SSE client for agent streaming
- [ ] Implement WebSocket fallback
- [ ] Create connection status monitoring
- [ ] Add reconnection logic
- [ ] Implement message queue for offline support

## Phase 2: Authentication & User Management (Week 3)

### Authentication Pages
- [ ] Create login page with form validation
- [ ] Implement register page with password requirements
- [ ] Add forgot password flow
- [ ] Create email verification page
- [ ] Implement OAuth login (Google, GitHub)
- [ ] Add loading states and error handling

### User Profile Management
- [ ] Create profile page layout
- [ ] Implement profile edit form
- [ ] Add avatar upload with image optimization
- [ ] Create preferences section
- [ ] Implement notification settings
- [ ] Add security settings (password change, 2FA)

### API Key Management (BYOK)
- [ ] Create secure API key management interface:
  ```typescript
  interface ApiKeyFormData {
    service: string;        // 'google_maps', 'duffel_flights', 'weather_api', etc.
    apiKey: string;
    description?: string;   // Optional field for user's notes/reminders
  }
  ```
- [ ] Implement key input form components:
  - [ ] ApiKeyManager component with masked input:
    ```typescript
    export function ApiKeyForm() {
      const [formData, setFormData] = useState<ApiKeyFormData>({
        service: '',
        apiKey: '',
        description: '',
      });
      const [showKey, setShowKey] = useState(false);
      const [inputActive, setInputActive] = useState(false);
      const keyInputRef = useRef<HTMLInputElement>(null);
      
      // Auto-clear key after 60 seconds of inactivity
      useEffect(() => {
        let timeout: NodeJS.Timeout;
        if (inputActive && formData.apiKey) {
          timeout = setTimeout(() => {
            setFormData(prev => ({ ...prev, apiKey: '' }));
            toast.info("API key cleared for security");
          }, 60000);
        }
        
        return () => clearTimeout(timeout);
      }, [inputActive, formData.apiKey]);
      
      const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        
        try {
          const response = await submitApiKey(formData);
          toast.success(`API key for ${formData.service} saved successfully!`);
          // Clear key immediately from state
          setFormData(prev => ({ ...prev, apiKey: '' }));
        } catch (error) {
          toast.error(`Failed to save API key: ${error.message}`);
        }
      };
      
      return (
        <form onSubmit={handleSubmit} className="space-y-4">
          <ServiceSelector 
            value={formData.service} 
            onChange={(value) => setFormData(prev => ({ ...prev, service: value }))}
          />
          
          <div className="relative">
            <Label htmlFor="apiKey">API Key</Label>
            <div className="flex gap-2">
              <Input
                id="apiKey"
                ref={keyInputRef}
                type={showKey ? "text" : "password"}
                value={formData.apiKey}
                onChange={(e) => setFormData(prev => ({ ...prev, apiKey: e.target.value }))}
                onFocus={() => setInputActive(true)}
                onBlur={() => setInputActive(false)}
                autoComplete="off"
                spellCheck={false}
                className="font-mono"
              />
              <Button 
                type="button" 
                variant="outline" 
                size="icon"
                onClick={() => setShowKey(!showKey)}
              >
                {showKey ? <EyeOffIcon /> : <EyeIcon />}
              </Button>
              <Button 
                type="button" 
                variant="outline" 
                size="icon"
                onClick={() => setFormData(prev => ({ ...prev, apiKey: '' }))}
                disabled={!formData.apiKey}
              >
                <XIcon />
              </Button>
            </div>
            <p className="text-sm text-gray-500 mt-1">
              Never stored in plaintext. Encrypted with envelope encryption.
            </p>
          </div>
          
          <div>
            <Label htmlFor="description">Description (optional)</Label>
            <Input
              id="description"
              value={formData.description}
              onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
              placeholder="Personal account key, Work key, etc."
            />
          </div>
          
          <div className="flex justify-between">
            <Button
              type="button"
              variant="outline"
              onClick={() => validateKey(formData)}
              disabled={!formData.apiKey || !formData.service}
            >
              Test Key
            </Button>
            <Button 
              type="submit"
              disabled={!formData.apiKey || !formData.service}
            >
              Save Key
            </Button>
          </div>
        </form>
      );
    }
    ```
  - [ ] ServiceSelector component with customized options per user:
    ```typescript
    interface ServiceSelectorProps {
      value: string;
      onChange: (value: string) => void;
    }
    
    export function ServiceSelector({ value, onChange }: ServiceSelectorProps) {
      const [services, setServices] = useState([]);
      
      // Fetch available services from backend
      useEffect(() => {
        fetch('/api/services/available')
          .then(res => res.json())
          .then(data => setServices(data));
      }, []);
    
      return (
        <div className="space-y-2">
          <Label htmlFor="service">Service</Label>
          <Select 
            value={value} 
            onValueChange={onChange}
          >
            <SelectTrigger id="service">
              <SelectValue placeholder="Select a service" />
            </SelectTrigger>
            <SelectContent>
              {services.map(service => (
                <SelectItem 
                  key={service.id} 
                  value={service.id}
                >
                  <div className="flex items-center gap-2">
                    <img 
                      src={service.icon} 
                      alt={service.name} 
                      className="w-4 h-4" 
                    />
                    <span>{service.name}</span>
                  </div>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      );
    }
    ```
  - [ ] Toggle visibility button with automatic re-hiding after 10 seconds
  - [ ] Clear input button with visual confirmation
  - [ ] Form auto-clearing system with timeout notifications
- [ ] Create key submission endpoint integration:
  ```typescript
  const submitApiKey = async (data: ApiKeyFormData) => {
    // Always validate key format first
    if (!validateKeyFormat(data.service, data.apiKey)) {
      throw new Error("Invalid key format");
    }
    
    // Use secure HTTPS submission
    const response = await fetch('/api/user/keys', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${sessionToken}`,
        'Content-Type': 'application/json',
        'X-CSRF-Token': csrfToken, // Additional security
      },
      body: JSON.stringify({
        service: data.service,
        api_key: data.apiKey,
        description: data.description || undefined,
      }),
    });
    
    // Clear key from memory immediately after submission
    data.apiKey = '';
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.message || "Failed to save API key");
    }
    
    return response.json();
  };
  
  // Test key with service before saving
  const validateKey = async (data: ApiKeyFormData) => {
    const response = await fetch('/api/user/keys/validate', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${sessionToken}`,
        'Content-Type': 'application/json',
        'X-CSRF-Token': csrfToken,
      },
      body: JSON.stringify({
        service: data.service,
        api_key: data.apiKey,
      }),
    });
    
    // Clear key from memory immediately after validation
    data.apiKey = '';
    
    const result = await response.json();
    
    if (result.valid) {
      toast.success(`API key for ${data.service} is valid!`);
      return true;
    } else {
      toast.error(`API key validation failed: ${result.message}`);
      return false;
    }
  };
  
  // Validate key format to catch obvious errors client-side
  const validateKeyFormat = (service: string, apiKey: string): boolean => {
    // Service-specific validation patterns
    const patterns: Record<string, RegExp> = {
      'google_maps': /^AIza[0-9A-Za-z-_]{35}$/,
      'openai': /^sk-[0-9a-zA-Z]{48}$/,
      'duffel_flights': /^duffel_test|live_[0-9a-zA-Z]{43}$/,
      'weather_api': /^[0-9a-f]{32}$/,
      // Add more service patterns as needed
    };
    
    // Default validation - check minimum length
    if (!patterns[service]) {
      return apiKey.length >= 16;
    }
    
    return patterns[service].test(apiKey);
  };
  ```
- [ ] Build key status display components:
  - [ ] ApiKeyStatusList component with comprehensive display:
    ```typescript
    interface ApiKeyStatus {
      id: string;
      service: string;
      serviceName: string;
      serviceIcon: string;
      isValid: boolean;
      lastUsed: string | null;
      rotationDue: string | null;
      usageCount: number;
      usageQuota: number | null;
      keyPreview: string; // Format: AB12...XY89 (first/last 2 chars only)
      description: string | null;
      created: string;
    }
    
    export function ApiKeyStatusList() {
      const [keyStatuses, setKeyStatuses] = useState<ApiKeyStatus[]>([]);
      const [isLoading, setIsLoading] = useState(true);
      
      const fetchKeyStatuses = useCallback(async () => {
        setIsLoading(true);
        try {
          const response = await fetch('/api/user/keys', {
            headers: {
              'Authorization': `Bearer ${sessionToken}`,
            },
          });
          
          if (!response.ok) {
            throw new Error('Failed to fetch key statuses');
          }
          
          const data = await response.json();
          setKeyStatuses(data);
        } catch (error) {
          toast.error(`Error: ${error.message}`);
        } finally {
          setIsLoading(false);
        }
      }, [sessionToken]);
      
      useEffect(() => {
        fetchKeyStatuses();
      }, [fetchKeyStatuses]);
      
      const handleDeleteKey = async (id: string) => {
        if (!confirm('Are you sure you want to delete this API key?')) {
          return;
        }
        
        try {
          const response = await fetch(`/api/user/keys/${id}`, {
            method: 'DELETE',
            headers: {
              'Authorization': `Bearer ${sessionToken}`,
              'X-CSRF-Token': csrfToken,
            },
          });
          
          if (!response.ok) {
            throw new Error('Failed to delete API key');
          }
          
          toast.success('API key deleted successfully');
          fetchKeyStatuses();
        } catch (error) {
          toast.error(`Error: ${error.message}`);
        }
      };
      
      const handleRotateKey = (id: string, service: string) => {
        // Open key rotation dialog
        setKeyToRotate({ id, service });
      };
      
      if (isLoading) {
        return <KeyStatusSkeleton count={3} />;
      }
      
      if (keyStatuses.length === 0) {
        return <EmptyKeyState onAddKey={() => setShowKeyForm(true)} />;
      }
      
      return (
        <div className="space-y-4">
          {keyStatuses.map(key => (
            <div key={key.id} className="border rounded-lg p-4 bg-card">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <img 
                    src={key.serviceIcon} 
                    alt={key.serviceName} 
                    className="w-6 h-6" 
                  />
                  <div>
                    <h3 className="font-medium">{key.serviceName}</h3>
                    <p className="text-sm text-muted-foreground">
                      {key.description || 'No description'}
                    </p>
                  </div>
                </div>
                <KeyStatusBadge isValid={key.isValid} />
              </div>
              
              <div className="mt-3 text-sm">
                <div className="flex justify-between py-1">
                  <span className="text-muted-foreground">Key preview:</span>
                  <span className="font-mono">{key.keyPreview}</span>
                </div>
                <div className="flex justify-between py-1">
                  <span className="text-muted-foreground">Last used:</span>
                  <span>{key.lastUsed ? formatRelativeTime(key.lastUsed) : 'Never'}</span>
                </div>
                <div className="flex justify-between py-1">
                  <span className="text-muted-foreground">Created:</span>
                  <span>{formatDate(key.created)}</span>
                </div>
                {key.rotationDue && (
                  <div className="flex justify-between py-1">
                    <span className="text-muted-foreground">Rotation due:</span>
                    <span className={isKeyRotationOverdue(key.rotationDue) ? 'text-destructive' : ''}>
                      {formatDate(key.rotationDue)}
                    </span>
                  </div>
                )}
                {key.usageQuota && (
                  <div className="py-1">
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Usage:</span>
                      <span>{key.usageCount} / {key.usageQuota}</span>
                    </div>
                    <Progress 
                      value={(key.usageCount / key.usageQuota) * 100} 
                      className="h-1 mt-1"
                    />
                  </div>
                )}
              </div>
              
              <div className="flex gap-2 mt-4">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => handleRotateKey(key.id, key.service)}
                >
                  <RefreshCwIcon className="w-4 h-4 mr-1" />
                  Rotate
                </Button>
                <Button
                  size="sm"
                  variant="destructive"
                  onClick={() => handleDeleteKey(key.id)}
                >
                  <TrashIcon className="w-4 h-4 mr-1" />
                  Delete
                </Button>
              </div>
            </div>
          ))}
          <Button onClick={() => setShowKeyForm(true)}>
            <PlusIcon className="w-4 h-4 mr-1" />
            Add New API Key
          </Button>
        </div>
      );
    }
    ```
  - [ ] KeyStatusBadge with health indicators:
    ```typescript
    function KeyStatusBadge({ isValid }: { isValid: boolean }) {
      if (isValid) {
        return (
          <Badge variant="success" className="h-6">
            <CheckCircleIcon className="w-3 h-3 mr-1" />
            Valid
          </Badge>
        );
      }
      
      return (
        <Badge variant="destructive" className="h-6">
          <XCircleIcon className="w-3 h-3 mr-1" />
          Invalid
        </Badge>
      );
    }
    ```
  - [ ] Dynamic rotation date highlighting and notifications
  - [ ] Usage metrics visualization with quotas and warnings
  - [ ] Interactive service health indicators
- [ ] Add key management features:
  - [ ] RotateKeyDialog for secure key rotation:
    ```typescript
    interface RotateKeyDialogProps {
      keyId: string;
      service: string;
      open: boolean;
      onOpenChange: (open: boolean) => void;
      onRotated: () => void;
    }
    
    export function RotateKeyDialog({
      keyId,
      service,
      open,
      onOpenChange,
      onRotated,
    }: RotateKeyDialogProps) {
      const [newKey, setNewKey] = useState('');
      const [validating, setValidating] = useState(false);
      
      const handleRotate = async () => {
        setValidating(true);
        
        try {
          // First validate the new key
          const validationResult = await fetch('/api/user/keys/validate', {
            method: 'POST',
            headers: {
              'Authorization': `Bearer ${sessionToken}`,
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              service,
              api_key: newKey,
            }),
          }).then(res => res.json());
          
          if (!validationResult.valid) {
            toast.error(`Invalid API key: ${validationResult.message}`);
            return;
          }
          
          // Then perform the rotation
          const response = await fetch(`/api/user/keys/${keyId}/rotate`, {
            method: 'POST',
            headers: {
              'Authorization': `Bearer ${sessionToken}`,
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              new_api_key: newKey,
            }),
          });
          
          if (!response.ok) {
            throw new Error(`Failed to rotate key: ${response.statusText}`);
          }
          
          toast.success('API key rotated successfully');
          setNewKey('');
          onOpenChange(false);
          onRotated();
        } catch (error) {
          toast.error(`Error: ${error.message}`);
        } finally {
          setValidating(false);
        }
      };
      
      return (
        <Dialog open={open} onOpenChange={onOpenChange}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Rotate API Key</DialogTitle>
              <DialogDescription>
                Enter your new API key for {service}. The old key will be replaced.
              </DialogDescription>
            </DialogHeader>
            
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="newApiKey">New API Key</Label>
                <Input
                  id="newApiKey"
                  type="password"
                  value={newKey}
                  onChange={(e) => setNewKey(e.target.value)}
                  autoComplete="off"
                  spellCheck="false"
                  className="font-mono"
                />
              </div>
              
              <Alert variant="warning">
                <AlertCircleIcon className="h-4 w-4" />
                <AlertTitle>Important</AlertTitle>
                <AlertDescription>
                  Make sure your new key is active before rotating. Your old key will be permanently deleted.
                </AlertDescription>
              </Alert>
            </div>
            
            <DialogFooter>
              <Button
                variant="outline"
                onClick={() => onOpenChange(false)}
              >
                Cancel
              </Button>
              <Button
                onClick={handleRotate}
                disabled={!newKey || validating}
              >
                {validating ? (
                  <>
                    <Loader2Icon className="mr-2 h-4 w-4 animate-spin" />
                    Validating...
                  </>
                ) : (
                  'Rotate Key'
                )}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      );
    }
    ```
  - [ ] Key health check dashboard with service-specific features
  - [ ] Delete key functionality with secure confirmation
  - [ ] Automatic key rotation reminder system
  - [ ] Key usage analytics with detailed metrics
- [ ] Implement security features:
  - [ ] Secure auto-clearing input forms with timeouts:
    ```typescript
    function useSecureInput(defaultTimeout = 60000) {
      const [value, setValueInternal] = useState('');
      const [lastActivity, setLastActivity] = useState(Date.now());
      const timeoutRef = useRef<NodeJS.Timeout | null>(null);
      
      const setValue = useCallback((newValue: string) => {
        setValueInternal(newValue);
        setLastActivity(Date.now());
      }, []);
      
      const clear = useCallback(() => {
        setValueInternal('');
      }, []);
      
      // Reset timeout on each value change
      useEffect(() => {
        if (timeoutRef.current) {
          clearTimeout(timeoutRef.current);
        }
        
        if (value) {
          timeoutRef.current = setTimeout(() => {
            setValueInternal('');
            toast.info("Input cleared for security", { id: "security-clear" });
          }, defaultTimeout);
        }
        
        return () => {
          if (timeoutRef.current) {
            clearTimeout(timeoutRef.current);
          }
        };
      }, [value, defaultTimeout]);
      
      return { value, setValue, clear };
    }
    ```
  - [ ] Session timeout for sensitive sections:
    ```typescript
    function useSecurityTimeout(onTimeout: () => void, timeoutMs = 300000) {
      const lastActivityRef = useRef(Date.now());
      const timeoutRef = useRef<NodeJS.Timeout | null>(null);
      
      useEffect(() => {
        const checkActivity = () => {
          const now = Date.now();
          if (now - lastActivityRef.current > timeoutMs) {
            onTimeout();
          }
        };
        
        const handleActivity = () => {
          lastActivityRef.current = Date.now();
        };
        
        // Reset activity on user interaction
        window.addEventListener('mousemove', handleActivity);
        window.addEventListener('keydown', handleActivity);
        window.addEventListener('click', handleActivity);
        
        // Check for timeout every minute
        timeoutRef.current = setInterval(checkActivity, 60000);
        
        return () => {
          window.removeEventListener('mousemove', handleActivity);
          window.removeEventListener('keydown', handleActivity);
          window.removeEventListener('click', handleActivity);
          
          if (timeoutRef.current) {
            clearInterval(timeoutRef.current);
          }
        };
      }, [onTimeout, timeoutMs]);
    }
    
    // Usage in settings page
    function ApiKeyManagementPage() {
      const router = useRouter();
      
      useSecurityTimeout(() => {
        toast.info("Session expired for security reasons");
        router.push('/dashboard');
      }, 300000); // 5 minutes
      
      // Rest of component...
    }
    ```
  - [ ] Enhanced CSP headers for key management pages:
    ```typescript
    // middleware.ts
    import { NextResponse } from 'next/server';
    import type { NextRequest } from 'next/server';
    
    export function middleware(request: NextRequest) {
      const response = NextResponse.next();
      
      // Enhanced security for API key management pages
      if (request.nextUrl.pathname.startsWith('/dashboard/settings/api-keys')) {
        // Strict CSP for sensitive pages
        response.headers.set(
          'Content-Security-Policy',
          `default-src 'self';
           script-src 'self' 'unsafe-inline';
           style-src 'self' 'unsafe-inline';
           img-src 'self' data:;
           connect-src 'self';
           form-action 'self';
           frame-ancestors 'none';`
        );
        
        // Prevent browsers from caching sensitive pages
        response.headers.set('Cache-Control', 'no-store, max-age=0');
        
        // Prevent browser from filling in credentials
        response.headers.set('X-Autocomplete-Disabled', 'true');
      }
      
      return response;
    }
    
    export const config = {
      matcher: ['/dashboard/settings/:path*'],
    };
    ```
  - [ ] Audit log visualization with filtering:
    ```typescript
    interface KeyAuditLogEntry {
      id: string;
      timestamp: string;
      action: 'create' | 'update' | 'delete' | 'rotate' | 'use' | 'validate';
      serviceId: string;
      serviceName: string;
      success: boolean;
      errorMessage?: string;
      ip?: string;
      userAgent?: string;
      location?: string;
    }
    
    function KeyAuditLog() {
      const [logs, setLogs] = useState<KeyAuditLogEntry[]>([]);
      const [filters, setFilters] = useState({
        service: 'all',
        action: 'all',
        status: 'all',
      });
      
      // Fetch and display audit logs with filtering
      // ...implementation details...
    }
    ```
  - [ ] Safety warnings for unusual activity
  - [ ] Secure field clearing with client-side timeouts

### Protected Routes
- [ ] Create route protection middleware
- [ ] Implement role-based access control
- [ ] Add loading states for auth checks
- [ ] Create custom 401/403 error pages
- [ ] Implement session refresh logic

## Phase 3: Dashboard & Core UI (Week 4)

### Dashboard Layout
- [ ] Create main dashboard layout with sidebar
- [ ] Implement responsive navigation
- [ ] Add breadcrumb navigation
- [ ] Create user dropdown menu
- [ ] Implement theme toggle
- [ ] Add notification center

### Dashboard Pages
- [ ] Create dashboard home with:
  - [ ] Trip overview cards
  - [ ] Recent activity feed
  - [ ] Quick action buttons
  - [ ] Statistics widgets
- [ ] Implement trips list page
- [ ] Add search and filter functionality
- [ ] Create empty states
- [ ] Add loading skeletons

### UI Components Library
- [ ] Extend shadcn/ui components:
  - [ ] Custom Button variants
  - [ ] Enhanced Card with hover effects
  - [ ] Animated Modal with Framer Motion
  - [ ] Custom Toast notifications
- [ ] Create travel-specific components:
  - [ ] TripCard
  - [ ] DestinationCard
  - [ ] DateRangePicker
  - [ ] BudgetInput
  - [ ] PassengerSelector

## Phase 4: Agent Integration (Week 5)

### Agent Infrastructure
- [ ] Create agent service layer
- [ ] Implement Vercel AI SDK v5 integration
- [ ] Set up streaming parsers
- [ ] Create agent type definitions
- [ ] Implement agent discovery

### Agent-Specific UI Components
- [ ] Create AgentProgress component:
  ```tsx
  interface AgentProgressProps {
    agent: string;
    status: 'idle' | 'thinking' | 'active' | 'complete';
    progress?: number;
    task?: string;
  }
  ```
  - [ ] Animated progress indicators
  - [ ] Status-specific icons and colors
  - [ ] Task description display
  - [ ] Completion animations
- [ ] Build AgentHandoffTransition:
  ```tsx
  interface HandoffProps {
    from: string;
    to: string;
    reason: string;
    animate?: boolean;
  }
  ```
  - [ ] Smooth transition animations
  - [ ] Context preservation display
  - [ ] Handoff reason visualization
  - [ ] Agent avatar transitions
- [ ] Implement AgentCapabilitiesGrid:
  - [ ] Service availability indicators
  - [ ] Capability cards with descriptions
  - [ ] Real-time status updates
  - [ ] Interactive tooltips
- [ ] Create DecisionVisualization:
  ```tsx
  interface DecisionProps {
    options: Array<{
      id: string;
      reasoning: string;
      confidence: number;
      selected: boolean;
    }>;
  }
  ```
  - [ ] Decision tree visualization
  - [ ] Confidence meters
  - [ ] Reasoning explanations
  - [ ] Path highlighting

### Chat Interface
- [ ] Create chat layout component
- [ ] Implement message list with virtualization
- [ ] Add message input with multiline support
- [ ] Create typing indicators
- [ ] Implement file attachments
- [ ] Add message reactions

### MCP Tool Invocation Display
- [ ] Create ToolInvocationCard:
  ```tsx
  interface ToolInvocationProps {
    toolName: string;
    service: string;
    parameters: Record<string, any>;
    timestamp: Date;
    status: 'pending' | 'success' | 'error';
    result?: any;
    error?: string;
  }
  ```
  - [ ] Collapsible parameter display
  - [ ] JSON syntax highlighting
  - [ ] Status animations
  - [ ] Error details formatting
- [ ] Build ServiceCallFlow:
  - [ ] Sequential call visualization
  - [ ] Parallel call indicators
  - [ ] Dependency mapping
  - [ ] Execution timeline
- [ ] Implement RealtimeDataStream:
  - [ ] Live data updates
  - [ ] Stream status indicators
  - [ ] Buffer visualizations
  - [ ] Connection quality display

### Streaming UI Components
- [ ] Create streaming text component
- [ ] Implement tool invocation display
- [ ] Add thinking/reasoning display
- [ ] Create progress indicators
- [ ] Implement cancellation UI
- [ ] Add retry functionality

### Agent-Specific Features
- [ ] Create agent selector interface
- [ ] Implement agent handoff visualization
- [ ] Add agent capability display
- [ ] Create conversation history
- [ ] Implement conversation branching
- [ ] Add export/share functionality

## Phase 5: Trip Planning Features (Week 6)

### Trip Creation Flow
- [ ] Create trip wizard with steps:
  - [ ] Destination selection
  - [ ] Date range picker
  - [ ] Traveler details
  - [ ] Budget setting
  - [ ] Preferences
- [ ] Implement form validation
- [ ] Add progress indicators
- [ ] Create review screen

### Itinerary Builder
- [ ] Create drag-and-drop interface
- [ ] Implement day-by-day view
- [ ] Add activity cards
- [ ] Create timeline visualization
- [ ] Implement auto-save
- [ ] Add collaboration features

### Search & Discovery
- [ ] Create unified search interface
- [ ] Implement destination search
- [ ] Add activity discovery
- [ ] Create recommendation engine UI
- [ ] Implement filters and sorting
- [ ] Add map-based search

### Web Crawling UI Integration
- [ ] Create CrawlingStatus component:
  ```tsx
  interface CrawlingStatusProps {
    url: string;
    status: 'pending' | 'crawling' | 'complete' | 'error';
    progress: number;
    extractedData?: any;
  }
  ```
  - [ ] Progress bars with stages
  - [ ] URL validation display
  - [ ] Extracted data preview
  - [ ] Error handling UI
- [ ] Build WebSearchResults:
  - [ ] Result cards with thumbnails
  - [ ] Relevance scoring display
  - [ ] Quick preview functionality
  - [ ] Source verification badges
- [ ] Implement CrawlOptimizer:
  - [ ] Optimal engine selection UI
  - [ ] Performance metrics display
  - [ ] Cost estimation preview
  - [ ] Manual override options

## Phase 6: Booking & Reservations (Week 7)

### Flight Search & Booking
- [ ] Create flight search form
- [ ] Implement result display with sorting
- [ ] Add flight details modal
- [ ] Create price comparison view
- [ ] Implement booking flow
- [ ] Add confirmation pages

### Accommodation Management
- [ ] Create hotel search interface
- [ ] Implement result grid/list toggle
- [ ] Add detailed hotel pages
- [ ] Create booking calendar
- [ ] Implement reservation management
- [ ] Add cancellation flow

### Payment Integration
- [ ] Create payment form components
- [ ] Implement saved payment methods
- [ ] Add billing address management
- [ ] Create invoice generation
- [ ] Implement refund handling

## Phase 7: Maps & Visualization (Week 8)

### Interactive Maps
- [ ] Integrate Mapbox GL JS v3
- [ ] Create custom map styles
- [ ] Implement location markers
- [ ] Add route visualization
- [ ] Create POI clustering
- [ ] Implement location search

### Data Visualization
- [ ] Create budget breakdown charts
- [ ] Implement trip timeline
- [ ] Add weather visualization
- [ ] Create analytics dashboard
- [ ] Implement comparison views
- [ ] Add export functionality

### Workflow Visualization
- [ ] Integrate React Flow v12
- [ ] Create agent workflow diagram
- [ ] Implement interactive nodes
- [ ] Add real-time updates
- [ ] Create custom node types
- [ ] Implement zoom/pan controls

## Phase 8: Real-time Features (Week 9)

### Live Collaboration
- [ ] Implement real-time trip editing
- [ ] Add presence indicators
- [ ] Create collaborative cursors
- [ ] Implement comment system
- [ ] Add activity feeds
- [ ] Create notification system

### Agent Communication
- [ ] Implement real-time agent status
- [ ] Add progress tracking
- [ ] Create event streaming
- [ ] Implement error recovery
- [ ] Add offline queue
- [ ] Create sync indicators

### Push Notifications
- [ ] Set up service worker
- [ ] Implement push subscription
- [ ] Create notification preferences
- [ ] Add in-app notifications
- [ ] Implement notification history
- [ ] Add action buttons

## Phase 9: Performance Optimization (Week 10)

### Code Optimization
- [ ] Implement code splitting
- [ ] Add lazy loading for routes
- [ ] Optimize bundle sizes
- [ ] Implement tree shaking
- [ ] Add prefetching strategies

### Image & Asset Optimization
- [ ] Implement Next.js Image optimization
- [ ] Add responsive images
- [ ] Create image placeholders
- [ ] Implement lazy loading
- [ ] Add WebP support

### Caching Strategies
- [ ] Configure TanStack Query caching
- [ ] Implement service worker caching
- [ ] Add static asset caching
- [ ] Create offline fallbacks
- [ ] Implement cache invalidation

### Performance Monitoring
- [ ] Add Web Vitals tracking
- [ ] Implement custom performance marks
- [ ] Create performance dashboard
- [ ] Add real user monitoring
- [ ] Implement error tracking

## Phase 10: Testing & Quality Assurance (Week 11)

### Unit Testing
- [ ] Write component tests with Vitest
- [ ] Test custom hooks
- [ ] Add store tests
- [ ] Test utility functions
- [ ] Create test fixtures
- [ ] Achieve 80% coverage

### Integration Testing
- [ ] Test auth flows
- [ ] Test API integration
- [ ] Test agent communication
- [ ] Test state management
- [ ] Test error scenarios
- [ ] Test offline functionality

### E2E Testing
- [ ] Create Playwright test suite
- [ ] Test critical user paths
- [ ] Add visual regression tests
- [ ] Test responsive design
- [ ] Test accessibility
- [ ] Create test reports

### Accessibility Audit
- [ ] Add ARIA labels
- [ ] Test keyboard navigation
- [ ] Verify screen reader support
- [ ] Check color contrast
- [ ] Test focus management
- [ ] Fix accessibility issues

## Phase 11: Deployment & DevOps (Week 12)

### Vercel Deployment
- [ ] Configure Vercel project
- [ ] Set up environment variables
- [ ] Configure build settings
- [ ] Set up preview deployments
- [ ] Configure custom domains
- [ ] Add SSL certificates

### CI/CD Pipeline
- [ ] Set up GitHub Actions
- [ ] Create build workflow
- [ ] Add test automation
- [ ] Implement deployment flow
- [ ] Add security scanning
- [ ] Create release process

### Monitoring Setup
- [ ] Configure Sentry error tracking
- [ ] Set up Vercel Analytics
- [ ] Add custom metrics
- [ ] Create alerts
- [ ] Implement logging
- [ ] Add uptime monitoring

### Documentation
- [ ] Write component documentation
- [ ] Create API documentation
- [ ] Add code comments
- [ ] Write deployment guide
- [ ] Create troubleshooting docs
- [ ] Add contributing guidelines

## Phase 12: Polish & Launch (Week 13)

### Final UI/UX Review
- [ ] Conduct design review
- [ ] Fix UI inconsistencies
- [ ] Optimize animations
- [ ] Review responsive design
- [ ] Test cross-browser compatibility
- [ ] Gather user feedback

### Performance Audit
- [ ] Run Lighthouse audits
- [ ] Optimize Core Web Vitals
- [ ] Review bundle sizes
- [ ] Test loading performance
- [ ] Verify caching strategies
- [ ] Implement final optimizations

### Security Review
- [ ] Conduct security audit
- [ ] Review authentication flows
- [ ] Check API security
- [ ] Verify CSP headers
- [ ] Test input validation
- [ ] Implement rate limiting

### Launch Preparation
- [ ] Create launch checklist
- [ ] Prepare marketing materials
- [ ] Set up support documentation
- [ ] Configure monitoring alerts
- [ ] Test rollback procedures
- [ ] Schedule launch

## Success Metrics

### Performance Targets
- Page load time < 1.5s (FCP)
- Time to Interactive < 3s
- Lighthouse score > 95
- Bundle size < 200KB (initial)
- 60fps scrolling performance

### Quality Metrics
- Test coverage > 80%
- Zero critical bugs
- Accessibility score > 95
- TypeScript strict mode compliance
- No console errors in production

### User Experience
- Mobile responsive (100%)
- Offline functionality
- Real-time updates < 100ms
- Error recovery < 3s
- Search results < 500ms

## Post-Launch Roadmap

### Month 1
- Bug fixes based on user feedback
- Performance optimizations
- Adding missing features
- Improving error handling

### Month 2-3
- Voice interface integration
- Advanced AI features
- Native mobile app development
- API versioning

### Future Enhancements
- Blockchain integration for bookings
- AR/VR travel previews
- Social features and sharing
- Marketplace for travel services
- Multi-language support

---

## Notes

1. Each phase can be adjusted based on team size and priorities
2. Consider parallel development for independent features
3. Maintain regular testing throughout all phases
4. Follow the established coding standards (KISS, DRY, YAGNI)
5. Use the backend MCP services through the FastAPI proxy
6. Prioritize mobile experience throughout development
7. Keep accessibility in mind from the start