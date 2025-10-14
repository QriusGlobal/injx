# Injx Roadmap

## Core Philosophy

Injx is a minimalist dependency injection container that does one thing well: **type-safe dependency resolution with O(1) performance**. We reject feature creep and maintain relentless focus on the essential problems that DI libraries solve.

## First Principles

1. **Type Safety First**: No string-based tokens, full static analysis support
2. **Performance by Design**: Sub-microsecond lookups through algorithmic efficiency
3. **Minimal Complexity**: Core implementation under 300 lines, zero production dependencies
4. **Testing as a Citizen**: First-class testing support, not an afterthought
5. **Explicit over Implicit**: Clear dependency graphs, no magic registration

## Roadmap v0.2.0 → v1.0.0

### Current State: v0.2.0 Foundation ✅
- Type-safe container with Token[T] system
- O(1) lookup performance via pre-computed hashes
- Scope management (Singleton, Transient, Request, Session)
- Circular dependency detection
- Async-safe ContextVar isolation
- Resource cleanup with LIFO ordering

### Immediate Priorities (v0.3.0)

#### 1. Enhanced Error Messages
**Problem**: Resolution failures don't show the full dependency chain
**Solution**: Complete dependency path visualization in error messages
```python
# Before: ResolutionError: Token[UserService] not found
# After: ResolutionError: Cannot resolve Token[UserService]:
#   UserService → DatabaseService → DatabaseConfig
#   Missing dependency: Token[DatabaseConfig]
```

#### 2. First-Class Testing Utilities
**Problem**: Testing with dependency injection should be simpler than production code
**Solution**: Built-in scoped overrides and test isolation
```python
def test_user_service():
    with container.test_scope() as test:
        test.override(DATABASE, MockDatabase())
        service = test.get(USER_SERVICE)
        # Test with isolated dependencies
```

#### 3. Container Introspection
**Problem**: Debugging dependency graphs requires external tools
**Solution**: Built-in container state inspection methods
```python
container.list_tokens()     # All registered dependencies
container.is_singleton(T)   # Check instantiation status
container.dependency_graph() # Visualize dependency relationships
```

### Quality Improvements (v0.4.0)

#### 4. Performance Optimization
**Target**: Maintain sub-microsecond lookup targets as container scales
- Profile-guided optimization based on real usage patterns
- Memory efficiency improvements for large dependency graphs
- Lock optimization for concurrent singleton initialization

#### 5. Enhanced Type Integration
**Target**: Zero-friction IDE experience with full type inference
- Improved generic type preservation through injection chains
- Enhanced protocol support for interface-based dependencies
- Better error messages for type mismatches

#### 6. Debugging Utilities
**Target**: Make dependency graph issues immediately obvious
- Container state dump for debugging
- Dependency cycle visualization
- Performance profiling integration

### Documentation & Polish (v0.5.0)

#### 7. Comprehensive Documentation
**Target**: Complete coverage with practical examples
- Real-world usage patterns (SDKs, web services, testing)
- Migration guides from other DI libraries
- Performance optimization guide

#### 8. Development Experience
**Target**: Smooth onboarding and daily usage
- Enhanced error messages with context
- Better IDE integration via type hints
- Debugging and profiling tools

## What We Won't Build

### Rejected Features
- **Auto-registration/Scanning**: Explicit registration maintains clarity
- **Configuration Files**: Dependencies should be in code, not external config
- **Framework-Specific Integrations**: Frameworks should integrate with us
- **Enterprise Patterns**: Circuit breakers, distributed DI, service mesh
- **Annotation-Based Configuration**: Decorators are sufficient and explicit
- **Hot Reload/Dynamic Dependencies**: Runtime complexity undermines type safety

### Rationale
These features violate our core principles:
- They increase complexity without solving essential problems
- They move dependency definition away from where it's used
- They make the system harder to reason about and debug
- They compromise our "do one thing well" philosophy

## Success Metrics

### Technical Metrics
- **Performance**: Sub-microsecond lookups for 10,000+ dependencies
- **Type Safety**: 100% basedpyright strict mode compliance
- **Reliability**: Zero runtime errors for correct usage patterns
- **Memory**: <500 bytes overhead per registered service

### Adoption Metrics
- **Documentation**: Complete coverage with practical examples
- **Testing**: Comprehensive test suite for all edge cases
- **Developer Experience**: Clear error messages and debugging tools

## Version Strategy

### v0.3.0 - Testing & Debugging Focus
Enhanced error messages, testing utilities, container introspection

### v0.4.0 - Performance & Polish
Performance optimization, type improvements, debugging tools

### v0.5.0 - Documentation & DX
Complete documentation, examples, and developer experience refinements

### v1.0.0 - Production Ready
Stable API, comprehensive documentation, real-world validation

## Principles Checklist

Every feature must satisfy these criteria:
- [ ] Does this solve an essential DI problem?
- [ ] Does this maintain O(1) lookup performance?
- [ ] Does this preserve full type safety?
- [ ] Does this keep the implementation minimal?
- [ ] Does this make testing easier, not harder?
- [ ] Is this explicit and discoverable?

## Conclusion

This roadmap focuses on doing dependency injection exceptionally well rather than becoming another feature-heavy framework. By maintaining our principles and avoiding feature creep, Injx will be the dependency injection library that developers reach for when they need type safety, performance, and reliability without unnecessary complexity.

---

**Last Updated**: October 2025
**Next Review**: v0.3.0 release
**Focus**: Core functionality, developer experience