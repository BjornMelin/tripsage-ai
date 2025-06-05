# Production Deployment Checklist: Database Consolidation

**Migration:** Database consolidation from Neon + Supabase to Supabase-only with pgvector  
**Issues:** #146, #147  
**Target:** 11x faster vector search, $6,000-9,600 annual savings

## Pre-Deployment Verification

### Supabase Environment Checks

- [ ] **Plan Verification**: Confirm Supabase plan supports pgvector extension
- [ ] **Extension Availability**: Verify vectorscale availability (Pro/Enterprise plans)
- [ ] **Resource Limits**: Check database size, connection limits, and compute resources
- [ ] **Backup Strategy**: Ensure current backups are complete and tested

### Application Readiness

- [ ] **Environment Variables**: Remove all Neon-related environment variables
- [ ] **Connection Strings**: Update any hardcoded database connections
- [ ] **Health Checks**: Verify application health check endpoints work with Supabase-only
- [ ] **Monitoring**: Set up performance monitoring for vector operations

## Deployment Steps

### 1. Database Migration

```bash
# Connect to Supabase project
supabase login
supabase projects list

# Enable extensions via dashboard or CLI
supabase extensions enable vector
supabase extensions enable vectorscale  # If available

# OR run SQL migration
psql -h [supabase-host] -U postgres -d postgres -f migrations/20250526_01_enable_pgvector_extensions.sql
```

### 2. Application Deployment

- [ ] **Environment Update**: Deploy updated environment variables
- [ ] **Code Deployment**: Deploy latest application code
- [ ] **Health Check**: Verify application starts successfully
- [ ] **Database Connectivity**: Test database connections work

### 3. Vector Search Configuration

- [ ] **Index Creation**: Create HNSW indexes for vector columns
- [ ] **Performance Tuning**: Configure optimal index parameters
- [ ] **Search Validation**: Test vector search functionality

## Post-Deployment Validation

### Performance Testing

- [ ] **Baseline Metrics**: Record current performance metrics
- [ ] **Vector Search Speed**: Measure query latency (<100ms target)
- [ ] **Throughput Testing**: Verify 471 QPS target capability
- [ ] **Load Testing**: Test under production traffic levels

### Functional Testing

- [ ] **Vector Operations**: Test all vector similarity searches
- [ ] **Data Integrity**: Verify all data migrated correctly
- [ ] **User Workflows**: Test critical user journeys
- [ ] **Error Handling**: Verify error scenarios work correctly

### Monitoring Setup

- [ ] **Database Metrics**: Monitor connection pool, query performance
- [ ] **Application Metrics**: Track response times, error rates
- [ ] **Cost Tracking**: Monitor database usage and costs
- [ ] **Alert Configuration**: Set up alerts for performance degradation

## Rollback Procedure

If issues arise, follow this rollback sequence:

### Immediate Rollback (Application Level)

1. **Revert Code**: Deploy previous application version
2. **Restore Environment**: Restore previous environment variables
3. **Health Check**: Verify application stability

### Database Rollback (If Needed)

1. **Extension Removal**: Run rollback script if vector extensions cause issues

   ```bash
   psql -f migrations/20250526_01_enable_pgvector_extensions_rollback.sql
   ```

2. **Data Restoration**: Restore from backup if data corruption occurs

3. **Service Restoration**: Verify all services operational

## Success Criteria

### Performance Targets

- [ ] **Search Latency**: <100ms p99 for vector searches
- [ ] **Throughput**: ≥471 QPS for vector operations
- [ ] **Availability**: >99.9% uptime during migration
- [ ] **Cost Reduction**: Confirm elimination of Neon costs

### Operational Targets

- [ ] **Single Database**: All operations use Supabase only
- [ ] **Configuration Simplified**: No environment-specific database logic
- [ ] **Documentation Updated**: All docs reflect new architecture
- [ ] **Team Training**: Development team updated on new architecture

## Post-Migration Optimization

### Week 1: Immediate Monitoring

- [ ] **Performance Tracking**: Daily performance metric reviews
- [ ] **Error Monitoring**: Watch for any configuration-related errors
- [ ] **Cost Validation**: Confirm Neon billing has stopped
- [ ] **User Feedback**: Monitor for any user-reported issues

### Week 2-4: Optimization

- [ ] **Index Tuning**: Optimize vector index parameters based on real usage
- [ ] **Query Optimization**: Identify and optimize slow queries
- [ ] **Scaling Assessment**: Plan for traffic growth with new architecture
- [ ] **Documentation**: Update operational runbooks

### Month 1: Long-term Assessment

- [ ] **ROI Validation**: Confirm actual cost savings achieved
- [ ] **Performance Gains**: Measure actual vs. projected performance improvements
- [ ] **Operational Benefits**: Assess reduced complexity benefits
- [ ] **Future Planning**: Plan next optimization phases

## Emergency Contacts

**Database Issues:**

- Primary: Database Team Lead
- Secondary: Platform Engineering
- Escalation: CTO

**Application Issues:**

- Primary: Backend Team Lead
- Secondary: DevOps Engineer
- Escalation: Engineering Manager

## Additional Resources

- [Supabase pgvector Documentation](https://supabase.com/docs/guides/database/extensions/pgvector)
- [pgvector Performance Tuning Guide](https://github.com/pgvector/pgvector#performance)
- [Migration Summary Documentation](./MIGRATION_SUMMARY.md)
- [Rollback Script](../migrations/20250526_01_enable_pgvector_extensions_rollback.sql)

---

**Migration Lead:** _[Your Name]_  
**Date:** _[Deployment Date]_  
**Sign-off:** _[Stakeholder Approval]_
