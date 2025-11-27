# ADR-0008: Migrate to Pydantic v2

**Version**: 1.0.0
**Status**: Superseded by ADR-0023 (AI SDK v6 TypeScript stack)
**Date**: 2025-06-17
**Category**: backend
**Domain**: Pydantic

## Context

TripSage's backend currently uses Pydantic v1 for data validation and serialization. However:

- Pydantic v1 is no longer actively developed
- We have 527 failing tests due to v1→v2 incompatibilities
- Pydantic v2 offers significant performance improvements (5-50x faster)
- FastAPI fully supports Pydantic v2 with enhanced features
- Modern Python patterns require v2 features

The migration is blocking our ability to:

- Update dependencies
- Use modern validation patterns
- Achieve optimal performance
- Maintain code quality

## Decision

We will migrate completely to Pydantic v2, removing all v1 patterns.

Migration approach:

1. Use `bump-pydantic` tool for automated migration
2. Manually fix remaining issues
3. Update all models to use v2 patterns
4. Remove v1 compatibility shims
5. Optimize for v2 performance features

Key changes:

- Replace `Config` classes with `model_config`
- Update validator decorators to v2 syntax
- Use new serialization methods
- Adopt v2 field definitions

## Consequences

### Positive

- **Performance**: 5-50x faster validation and serialization
- **Features**: Access to new v2 capabilities (discriminated unions, etc.)
- **Maintenance**: Supported version with active development
- **Type Safety**: Better mypy integration and type inference
- **Future Proof**: Enables future FastAPI features
- **Simplicity**: Cleaner syntax and better error messages

### Negative

- **Migration Effort**: 1-2 days of focused work required
- **Breaking Changes**: All models need updates
- **Learning Curve**: Developers need to learn v2 patterns
- **Third-party**: Some libraries may not support v2 yet

### Neutral

## Changelog

- 1.0.0 (2025-10-24) — Standardized metadata and formatting; added version and changelog.

- Different import patterns and method names
- New configuration syntax to learn
- Some behavior changes in edge cases

## Alternatives Considered

### Stay on Pydantic v1

Continue using the current version.

**Why not chosen**:

- No longer maintained
- Blocking dependency updates
- Missing performance improvements
- Technical debt accumulation

### Gradual Migration

Support both v1 and v2 simultaneously.

**Why not chosen**:

- Increases complexity significantly
- Compatibility layers add overhead
- Extends migration timeline
- More prone to errors

### Alternative Validation Libraries

Switch to attrs, marshmallow, or other libraries.

**Why not chosen**:

- Would require complete rewrite
- Less FastAPI integration
- Smaller ecosystem
- No clear advantages over Pydantic v2

## References

- [Pydantic v2 Migration Guide](https://docs.pydantic.dev/latest/migration/)
- [Backend Testing Issues](../MIGRATION_SUMMARY.md)
- [Coding Standards](../04_DEVELOPMENT_GUIDE/CODING_STANDARDS.md)
- [bump-pydantic Tool](https://github.com/pydantic/bump-pydantic)
