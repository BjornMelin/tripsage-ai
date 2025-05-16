# TripSage Frontend Architecture Diagram (Validated 2025)

## High-Level Architecture Overview

```mermaid
graph TB
    subgraph "Client Browser"
        UI[React 19 UI Layer]
        SM[State Management<br/>Zustand + TanStack Query]
        AIH[AI SDK Hooks]
        Cache[Web Operations Cache]
    end
    
    subgraph "Next.js 15 App Router"
        RSC[React Server Components]
        API[API Routes]
        SA[Server Actions]
        MW[Middleware]
        TURBO[Turbopack]
    end
    
    subgraph "External Services"
        AI[Vercel AI SDK<br/>OpenAI/Anthropic]
        MAP[Maps API<br/>Mapbox/Google]
        AUTH[Auth Services<br/>Supabase/Clerk]
    end
    
    subgraph "Backend Services"
        MCP[MCP Servers]
        DB[Databases<br/>Supabase/Neo4j]
        STORE[Object Storage]
    end
    
    UI --> SM
    UI --> AIH
    AIH --> API
    SM --> Cache
    UI --> RSC
    RSC --> API
    API --> AI
    API --> MCP
    MCP --> DB
    UI --> MAP
    SA --> MCP
    MW --> AUTH
    TURBO --> RSC
```

## Component Architecture

```mermaid
graph LR
    subgraph "Feature Components"
        AC[Agent Chat]
        AV[Agent Visualization]
        TP[Trip Planner]
        BR[Budget Tracker]
        MS[Model Selector]
        KM[Key Manager]
    end
    
    subgraph "UI Components"
        BTN[Buttons]
        INP[Inputs]
        CRD[Cards]
        MOD[Modals]
        TBL[Tables]
        CHT[Charts]
    end
    
    subgraph "Layout Components"
        NAV[Navigation]
        SID[Sidebar]
        HDR[Header]
        FTR[Footer]
        LAY[Layouts]
    end
    
    AC --> BTN
    AC --> INP
    AV --> CHT
    TP --> CRD
    TP --> MOD
    BR --> TBL
    BR --> CHT
    
    AC --> LAY
    AV --> LAY
    TP --> LAY
```

## Data Flow Architecture

```mermaid
sequenceDiagram
    participant U as User
    participant UI as React UI
    participant S as Zustand Store
    participant Q as React Query
    participant A as API Route
    participant M as MCP Server
    participant AI as AI Provider
    
    U->>UI: User Input
    UI->>S: Update Local State
    UI->>Q: Trigger Query/Mutation
    Q->>A: HTTP Request
    A->>M: MCP Call
    M->>AI: AI Request
    AI-->>M: AI Response
    M-->>A: Processed Data
    A-->>Q: Response
    Q->>S: Update Cache
    S->>UI: Trigger Re-render
    UI-->>U: Display Result
```

## State Management Architecture

```mermaid
graph TD
    subgraph "Global State (Zustand)"
        CS[Chat Store]
        AS[Agent Store]
        US[User Store]
        PS[Preferences Store]
    end
    
    subgraph "Server State (React Query)"
        TC[Trip Cache]
        FC[Flight Cache]
        AC[Accommodation Cache]
        WC[Weather Cache]
    end
    
    subgraph "Local State (React)"
        FS[Form State]
        MS[Modal State]
        VS[Validation State]
    end
    
    CS --> |Subscribe| UI1[Chat UI]
    AS --> |Subscribe| UI2[Agent UI]
    TC --> |Subscribe| UI3[Trip UI]
    FS --> |Local| UI4[Form UI]
```

## Agent Visualization Flow

```mermaid
graph LR
    subgraph "Agent System"
        TA[Travel Agent]
        FA[Flight Agent]
        HA[Hotel Agent]
        WA[Weather Agent]
        BA[Budget Agent]
    end
    
    subgraph "Visualization Layer"
        AF[Agent Flow]
        AT[Activity Timeline]
        AP[Progress Tracker]
        AN[Network Graph]
    end
    
    subgraph "Real-time Updates"
        WS[WebSocket]
        SSE[Server-Sent Events]
        PL[Polling]
    end
    
    TA --> AF
    FA --> AT
    HA --> AP
    WA --> AN
    BA --> AN
    
    WS --> AF
    SSE --> AT
    PL --> AP
```

## Frontend Build Pipeline

```mermaid
graph TD
    subgraph "Development"
        TS[TypeScript]
        TSX[TSX/JSX]
        CSS[Tailwind CSS]
        TEST[Test Files]
    end
    
    subgraph "Build Process"
        TC[Type Check]
        LINT[ESLint]
        BUNDLE[Vite/Webpack]
        OPT[Optimization]
    end
    
    subgraph "Output"
        JS[JavaScript Bundles]
        CS[CSS Bundles]
        STATIC[Static Assets]
        HTML[HTML Files]
    end
    
    TS --> TC
    TSX --> TC
    TC --> LINT
    LINT --> BUNDLE
    CSS --> BUNDLE
    BUNDLE --> OPT
    OPT --> JS
    OPT --> CS
    OPT --> STATIC
    OPT --> HTML
```

## API Integration Architecture

```mermaid
graph TB
    subgraph "Frontend API Layer"
        AX[Axios Client]
        FE[Fetch Wrapper]
        RT[React Query]
        SW[SWR]
    end
    
    subgraph "API Routes"
        CH[/api/chat]
        TR[/api/trips]
        FL[/api/flights]
        AC[/api/accommodations]
        AU[/api/auth]
    end
    
    subgraph "External APIs"
        OA[OpenAI API]
        AN[Anthropic API]
        MP[Maps APIs]
        BK[Booking APIs]
    end
    
    AX --> CH
    FE --> TR
    RT --> FL
    SW --> AC
    
    CH --> OA
    CH --> AN
    TR --> MP
    FL --> BK
```

## Performance Optimization Strategy

```mermaid
graph LR
    subgraph "Code Optimization"
        CS[Code Splitting]
        TH[Tree Shaking]
        MIN[Minification]
        CMP[Compression]
    end
    
    subgraph "Asset Optimization"
        IMG[Image Optimization]
        FON[Font Loading]
        SVG[SVG Optimization]
        CDN[CDN Delivery]
    end
    
    subgraph "Runtime Optimization"
        LZ[Lazy Loading]
        MEM[Memoization]
        VRT[Virtualization]
        PWA[PWA Caching]
    end
    
    CS --> LZ
    TH --> MIN
    MIN --> CMP
    IMG --> CDN
    FON --> PWA
    SVG --> CDN
    LZ --> MEM
    MEM --> VRT
```

## Security Architecture

```mermaid
graph TD
    subgraph "Client Security"
        CSP[Content Security Policy]
        CORS[CORS Headers]
        XSS[XSS Protection]
        CSRF[CSRF Tokens]
    end
    
    subgraph "API Security"
        JWT[JWT Validation]
        RATE[Rate Limiting]
        VAL[Input Validation]
        SAN[Sanitization]
    end
    
    subgraph "Key Management"
        ENV[Environment Variables]
        ENC[Encryption]
        ROT[Key Rotation]
        AUD[Audit Logging]
    end
    
    CSP --> CORS
    CORS --> JWT
    JWT --> RATE
    RATE --> VAL
    VAL --> SAN
    ENV --> ENC
    ENC --> ROT
    ROT --> AUD
```

## Deployment Architecture

```mermaid
graph TB
    subgraph "Source Control"
        GIT[GitHub Repository]
        PR[Pull Requests]
        ACT[GitHub Actions]
    end
    
    subgraph "Build & Test"
        TST[Test Suite]
        BLD[Build Process]
        CHK[Quality Checks]
    end
    
    subgraph "Deployment Targets"
        DEV[Dev Environment]
        STG[Staging]
        PRD[Production]
    end
    
    subgraph "Infrastructure"
        VCL[Vercel Platform]
        CDN[Vercel CDN]
        EDG[Edge Functions]
    end
    
    GIT --> PR
    PR --> ACT
    ACT --> TST
    TST --> BLD
    BLD --> CHK
    CHK --> DEV
    DEV --> STG
    STG --> PRD
    PRD --> VCL
    VCL --> CDN
    VCL --> EDG
```

## Error Handling Flow

```mermaid
graph TD
    subgraph "Error Sources"
        API[API Errors]
        NET[Network Errors]
        VAL[Validation Errors]
        AI[AI Service Errors]
    end
    
    subgraph "Error Handlers"
        GLB[Global Handler]
        BND[Error Boundary]
        QRY[Query Error]
        FRM[Form Error]
    end
    
    subgraph "User Feedback"
        TST[Toast Messages]
        MDL[Modal Dialogs]
        INL[Inline Errors]
        LOG[Console Logs]
    end
    
    API --> GLB
    NET --> GLB
    VAL --> FRM
    AI --> QRY
    
    GLB --> TST
    BND --> MDL
    QRY --> TST
    FRM --> INL
    
    GLB --> LOG
    BND --> LOG
```

## Testing Architecture

```mermaid
graph LR
    subgraph "Unit Tests"
        CMP[Component Tests]
        HKS[Hook Tests]
        UTL[Utility Tests]
        STR[Store Tests]
    end
    
    subgraph "Integration Tests"
        API[API Tests]
        FLW[Flow Tests]
        INT[Interaction Tests]
    end
    
    subgraph "E2E Tests"
        USR[User Journey]
        CRT[Critical Paths]
        PWA[PWA Tests]
    end
    
    subgraph "Tools"
        VST[Vitest]
        RTL[React Testing Library]
        PLW[Playwright]
        STB[Storybook]
    end
    
    CMP --> VST
    HKS --> RTL
    API --> VST
    USR --> PLW
    CMP --> STB
```

This comprehensive architecture diagram outlines the structure, data flow, and key architectural decisions for the TripSage frontend application, providing a visual guide for development and maintenance.