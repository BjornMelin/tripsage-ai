# ❓ Frequently Asked Questions

> **Quick Answers to Common TripSage Questions**  
> Find solutions to common questions about using TripSage AI for travel planning

## 📋 Table of Contents

- [🌟 General Questions](#-general-questions)
- [💻 Technical Questions](#-technical-questions)
- [🔌 API Questions](#-api-questions)
- [🚀 Deployment Questions](#-deployment-questions)
- [🔒 Security & Privacy](#-security--privacy)
- [💰 Pricing & Plans](#-pricing--plans)
- [🆘 Getting Help](#-getting-help)

---

## 🌟 General Questions

### **What makes TripSage different from other travel planning tools?**

TripSage combines AI-powered recommendations with real-time collaboration and advanced memory capabilities, providing personalized travel planning that learns from your preferences. Key differentiators:

- **🧠 AI Memory System**: Learns and remembers your preferences across trips
- **🤝 Real-time Collaboration**: Plan trips together with travel companions
- **🔗 Comprehensive Integration**: Direct API access to flights, hotels, and activities
- **🎯 Personalization**: Tailored recommendations based on your travel history
- **🛠️ Developer-Friendly**: Full API access for custom integrations

### **Is TripSage free to use?**

TripSage offers multiple tiers:

- **🆓 Free Tier**: Basic travel planning with limited AI interactions
- **⭐ Premium**: AI features, unlimited planning, priority support
- **🏢 Enterprise**: Custom integrations, dedicated support, SLA guarantees
- **👨‍💻 Developer**: API access with generous rate limits

### **Can I use TripSage for business travel?**

Yes! TripSage supports business travel with enterprise features:

- **💼 Expense Tracking**: Automatic expense categorization and reporting
- **✅ Approval Workflows**: Multi-level approval processes for bookings
- **📋 Policy Integration**: Enforce company travel policies automatically
- **📊 Analytics**: Travel spend analysis and optimization insights
- **🔐 SSO Integration**: Single sign-on with corporate identity providers

### **What types of trips can TripSage help plan?**

TripSage handles all types of travel:

- **🏖️ Leisure Travel**: Vacations, weekend getaways, family trips
- **💼 Business Travel**: Corporate trips, conferences, client meetings
- **👥 Group Travel**: Family reunions, friend trips, corporate retreats
- **🎒 Adventure Travel**: Backpacking, outdoor activities, unique experiences
- **🌍 International Travel**: Multi-country trips, visa requirements, currency

---

## 💻 Technical Questions

### **What external APIs does TripSage integrate with?**

TripSage integrates with leading travel and location services:

**✈️ Flight APIs:**

- **Duffel**: Primary flight search and booking
- **Amadeus**: Alternative flight data source
- **Skyscanner**: Price comparison and alerts

**🏨 Accommodation APIs:**

- **Booking.com**: Hotel inventory and pricing
- **Airbnb**: Vacation rental listings
- **Expedia**: Hotel and package deals

**🗺️ Location & Maps:**

- **Google Maps**: Location data, directions, places
- **Mapbox**: Custom mapping and geocoding
- **Foursquare**: Points of interest and reviews

**🌤️ Weather & Context:**

- **OpenWeatherMap**: Weather forecasts and historical data
- **TimeZone API**: Time zone information

### **How does the AI memory system work?**

TripSage uses **Mem0** for intelligent memory management:

- **🧠 Vector Embeddings**: Stores preferences as semantic vectors
- **📚 Context Learning**: Learns from conversation patterns
- **🎯 Personalization**: Adapts recommendations based on history
- **🔄 Continuous Learning**: Improves suggestions over time
- **🔒 Privacy-First**: Memory data is encrypted and user-controlled

### **Can I self-host TripSage?**

Yes! TripSage is designed for self-hosting:

- **🐳 Docker Support**: Complete containerized deployment
- **☁️ Cloud-Ready**: Deploy on AWS, GCP, Azure, or any cloud provider
- **📖 Deployment Guides**: Comprehensive setup documentation
- **🔧 Configuration**: Flexible environment-based configuration
- **📊 Monitoring**: Built-in observability and health checks

### **What databases does TripSage support?**

TripSage uses a modern data stack:

- **🐘 PostgreSQL**: Primary database with Supabase
- **🔍 pgvector**: Vector embeddings for AI features
- **⚡ DragonflyDB**: High-performance Redis-compatible cache
- **📊 Analytics**: Optional integration with data warehouses

---

## 🔌 API Questions

### **Are there SDKs available?**

**Current Status:**

- **📚 REST API**: Complete OpenAPI 3.0 specification
- **🔌 WebSocket API**: Real-time chat and updates
- **📖 Interactive Docs**: Swagger UI and ReDoc available

**In Development:**

- **🐍 Python SDK**: Native Python client library
- **📱 JavaScript/TypeScript SDK**: For web and Node.js applications
- **⚛️ React SDK**: React hooks and components
- **📱 Mobile SDKs**: iOS and Android native libraries

### **What are the rate limits for API calls?**

Rate limits vary by plan and endpoint:

**🆓 Free Tier:**

- 100 requests per hour
- 1,000 requests per month
- Basic endpoints only

**⭐ Premium:**

- 1,000 requests per hour
- 50,000 requests per month
- All endpoints available

**🏢 Enterprise:**

- Custom rate limits
- Dedicated infrastructure
- SLA guarantees

**Rate Limit Headers:**

```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1642284000
```

### **How do I get support for API integration?**

Multiple support channels available:

- **📖 Documentation**: Comprehensive guides and examples
- **🔧 Interactive Docs**: Test endpoints at `/api/docs`
- **💬 Developer Discord**: Real-time community support
- **📧 Email Support**: <developers@tripsage.ai>
- **🎯 Premium Support**: Dedicated technical account managers

---

## 🚀 Deployment Questions

### **What are the system requirements for production?**

**Minimum Requirements:**

- **💾 RAM**: 4GB (8GB recommended)
- **⚡ CPU**: 2 cores (4 cores recommended)
- **💿 Storage**: 20GB SSD (50GB recommended)
- **🌐 Network**: 100 Mbps bandwidth

**Recommended Production Setup:**

- **💾 RAM**: 16GB+
- **⚡ CPU**: 8 cores+
- **💿 Storage**: 100GB+ NVMe SSD
- **🌐 Network**: 1 Gbps bandwidth
- **🔄 Load Balancer**: For high availability

### **How do I scale TripSage for high traffic?**

TripSage supports horizontal scaling:

**🔄 Application Scaling:**

- Multiple API server instances
- Load balancer distribution
- Auto-scaling based on metrics

**💾 Database Scaling:**

- Read replicas for query distribution
- Connection pooling with PgBouncer
- Supabase automatic scaling

**⚡ Cache Scaling:**

- DragonflyDB cluster mode
- Redis Sentinel for high availability
- Distributed caching strategies

### **Is TripSage GDPR compliant?**

Yes! TripSage includes comprehensive GDPR compliance:

- **📋 Data Export**: Complete user data export in JSON format
- **🗑️ Data Deletion**: Secure data removal on request
- **✅ Consent Management**: Granular privacy controls
- **🔒 Data Encryption**: End-to-end encryption for sensitive data
- **📊 Audit Logs**: Complete data access logging
- **🌍 Data Residency**: EU data centers available

---

## 🔒 Security & Privacy

### **How is my travel data protected?**

TripSage implements enterprise-grade security:

- **🔐 Encryption**: AES-256 encryption at rest and in transit
- **🛡️ Authentication**: Multi-factor authentication support
- **🔑 API Security**: JWT tokens with configurable expiration
- **🚫 Access Control**: Role-based permissions (RBAC)
- **📊 Audit Logging**: Complete activity tracking
- **🔍 Vulnerability Scanning**: Regular security assessments

### **Can I control what data is stored?**

Absolutely! You have full control:

- **🎛️ Privacy Settings**: Granular data collection controls
- **🧠 Memory Management**: Control AI memory retention
- **📱 Data Portability**: Export your data anytime
- **🗑️ Right to Deletion**: Remove your data completely
- **🔒 Anonymization**: Option to anonymize historical data

---

## 💰 Pricing & Plans

### **What's included in each plan?**

**🆓 Free Plan:**

- Basic trip planning
- 5 AI conversations per month
- Standard support
- Community access

**⭐ Premium Plan ($19/month):**

- Unlimited AI conversations
- Memory features
- Priority support
- Real-time collaboration
- API access (limited)

**🏢 Enterprise Plan (Custom):**

- Unlimited everything
- Custom integrations
- Dedicated support
- SLA guarantees
- On-premise deployment

### **Is there a free trial for premium features?**

Yes! We offer:

- **🎁 14-day free trial** of Premium features
- **💳 No credit card required** for trial
- **🔄 Easy upgrade/downgrade** anytime
- **💰 Money-back guarantee** within 30 days

---

## 🆘 Getting Help

### **How can I get support?**

Multiple support channels:

**📚 Self-Service:**

- [📖 Documentation Hub](../README.md)
- [🔧 Interactive API Docs](http://localhost:8001/api/docs)
- [🎥 Video Tutorials](https://youtube.com/@tripsage)
- [💬 Community Forum](https://community.tripsage.ai)

**🤝 Direct Support:**

- **📧 Email**: <support@tripsage.ai>
- **💬 Live Chat**: Available 24/7 in the app
- **📞 Phone**: Premium and Enterprise customers
- **👨‍💻 Developer Support**: <developers@tripsage.ai>

**🚨 Emergency Support:**

- **24/7 Travel Assistance**: For users currently traveling
- **🔄 Emergency Rebooking**: Last-minute changes and cancellations
- **🛡️ Travel Insurance**: Protection for unexpected events

### **What information should I include in support requests?**

To help us assist you quickly:

**🔍 Basic Information:**

- Your TripSage plan type
- Browser/app version
- Operating system
- Error messages (exact text)

**🐛 For Bug Reports:**

- Steps to reproduce the issue
- Expected vs. actual behavior
- Screenshots or screen recordings
- Console logs (if applicable)

**🔌 For API Issues:**

- API endpoint and method
- Request/response examples
- HTTP status codes
- Rate limit information

## 🔧 Troubleshooting

### **Common Issues and Solutions**

#### **Login Problems**

**Issue**: Can't log in to TripSage  
**Solutions**:

- Clear browser cache and cookies
- Try incognito/private browsing mode  
- Check if email is verified
- Reset password if needed
- Contact support if using SSO

#### **Trip Planning Issues**

**Issue**: AI not understanding my requests  
**Solutions**:

- Be more specific with dates, budget, location
- Use simple, clear language
- Break complex requests into steps
- Try examples like "Weekend trip to Paris under $1000"

**Issue**: No flight results showing  
**Solutions**:

- Check dates are in the future
- Try flexible date ranges
- Consider nearby airports
- Clear search filters
- Try different destinations

#### **Booking Problems**

**Issue**: Payment not processing  
**Solutions**:

- Verify card details and billing address
- Check for sufficient funds
- Try a different payment method
- Contact your bank about international charges
- Reach out to support for assistance

#### **Performance Issues**

**Issue**: App loading slowly  
**Solutions**:

- Check internet connection
- Clear browser cache
- Disable browser extensions
- Try a different browser
- Contact support if persistent

### **Mobile App Issues**

**Issue**: Push notifications not working  
**Solutions**:

- Enable notifications in device settings
- Update the app to latest version
- Check notification preferences in app
- Restart your device
- Reinstall the app if needed

**Issue**: Offline mode not working  
**Solutions**:

- Download trip data while online
- Check storage space on device
- Update to latest app version
- Sync trips before going offline

## 💬 Getting Help

### **Self-Service Options**

- **📚 Help Center**: Searchable knowledge base
- **🎥 Video Tutorials**: Step-by-step guides  
- **💬 Community Forum**: User discussions and tips
- **📖 Documentation**: Complete feature guides

### **Direct Support**

**Email Support**: [support@tripsage.ai](mailto:support@tripsage.ai)

- Response time: Within 24 hours
- Include account email and trip details
- Attach screenshots if helpful

**Live Chat**: Available 24/7 in the app

- Instant responses during business hours
- AI assistant for common questions
- Escalate to human agents when needed

**Phone Support**: Premium and Enterprise customers

- Dedicated support line
- Escalation for urgent issues
- Travel assistance while on trip

### **Business Support**

**Enterprise Customers**:

- Dedicated account manager
- Priority support queue
- Custom integration assistance
- Training and onboarding sessions

**Developer Support**:

- Technical documentation
- API support forum
- Integration assistance
- Rate limit discussions

### **Emergency Support**

**Travel Emergencies**:

- 24/7 rebooking assistance
- Flight cancellation help
- Hotel overbooking resolution
- Travel insurance claims support

**Security Issues**:

- Account security concerns
- Suspicious activity reports
- Data privacy questions
- Immediate account protection

### **Refunds and Cancellations**

**Refund Policy**:

- Free cancellation within 24 hours
- Refunds processed within 5-7 business days
- Service fee may apply for some bookings
- Travel insurance available for protection

**How to Request Refunds**:

1. Go to "My Trips" in your account
2. Select the booking to cancel
3. Follow cancellation workflow
4. Check refund status in account
5. Contact support if issues arise

---

## 🔗 Additional Resources

### **Learning Resources**

- **[🚀 Getting Started Guide](../01_GETTING_STARTED/README.md)** - Quick setup and onboarding
- **[👨‍💻 Developer Guide](../04_DEVELOPMENT_GUIDE/README.md)** - Technical development resources
- **[📚 API Reference](../06_API_REFERENCE/README.md)** - Complete API documentation
- **[🔧 Configuration Guide](../07_CONFIGURATION/README.md)** - Settings and customization

### **Community & Updates**

- **[💬 Discord Community](https://discord.gg/tripsage)** - Real-time discussions
- **[🐦 Twitter](https://twitter.com/tripsage)** - Latest updates and announcements
- **[💼 LinkedIn](https://linkedin.com/company/tripsage)** - Professional updates
- **[📰 Blog](https://blog.tripsage.ai)** - Travel tech insights and tutorials

---

**Still have questions?** We're here to help! Reach out through any of our support channels above. 🤝

> *Last updated: June 16, 2025*
