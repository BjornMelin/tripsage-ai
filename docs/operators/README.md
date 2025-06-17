# 🎯 TripSage Operators Documentation

> **Quick Navigation Hub for DevOps & SRE Teams**

## 📚 Documentation Index

### **🚀 Getting Started**

- [Installation Guide](./installation-guide.md) - Complete setup and dependencies
- [Environment Configuration](./environment-configuration.md) - All environment variables and configuration

### **🔧 Deployment & Operations**  

- [Deployment Guide](./deployment-guide.md) - Platform selection, CI/CD, and production deployment
- [Supabase Configuration](./supabase-configuration.md) - Database setup and extensions

### **🔐 Security & Authentication**

- [Security Guide](./security-guide.md) - Comprehensive security implementation
- [Authentication Guide](./authentication-guide.md) - OAuth setup and troubleshooting

### **⚙️ Advanced Configuration**

- [Settings Reference](./settings-reference.md) - Pydantic settings and technical configuration

## 🎯 Quick Links

| **Task** | **Documentation** | **Time Estimate** |
|----------|-------------------|-------------------|
| New deployment | [Installation](./installation-guide.md) → [Deployment](./deployment-guide.md) | 2-4 hours |
| Environment setup | [Environment Configuration](./environment-configuration.md) | 30-60 min |
| Security review | [Security Guide](./security-guide.md) | 1-2 hours |
| OAuth integration | [Authentication Guide](./authentication-guide.md) | 1-3 hours |

## 🏗️ Architecture Overview

**Current TripSage Architecture** (June 2025):

- **Database**: Supabase PostgreSQL with pgvector embeddings
- **Cache**: DragonflyDB (25x faster than Redis)
- **Memory System**: Mem0 with pgvector storage
- **Integrations**: 7 direct SDK integrations + 1 MCP (Airbnb)
- **Authentication**: OAuth (Google, GitHub) with RLS policies
- **Configuration**: Pydantic BaseSettings with BYOK support

## 📈 Documentation Metrics

- **Files**: 8 optimized files (reduced from 22)
- **Duplication**: Eliminated 90%+ environment variable duplication
- **Organization**: Logical grouping by operator workflow
- **Maintenance**: Single source of truth for each topic
