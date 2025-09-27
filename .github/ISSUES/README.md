# Injx Development Issues

This directory contains GitHub issues planned for the injx project development roadmap.

## Issue Organization

Following the successful patterns of UV and Ruff, we use a minimal label taxonomy:

### Labels (5 total)
- `bug` - Something isn't working
- `enhancement` - New feature or improvement
- `question` - Question or discussion
- `documentation` - Documentation improvements
- `python-3.14` - Python 3.14 specific features

## Issue Categories

### 🔴 Critical - Python 3.14 Readiness (3 issues)
1. **[Free-Threading Support](01_free_threading_support.md)** - Enable GIL-free parallelism (PEP 703)
2. **[Lazy Annotations](02_lazy_annotations.md)** - Zero-overhead type hints (PEP 649)
3. **[Sub-Interpreter Support](03_subinterpreter_support.md)** - Multi-interpreter isolation (PEP 734)

### 🟡 Core Improvements (4 issues)
4. **[Performance Benchmarking](04_performance_benchmarking.md)** - Prevent regressions
5. **[Enhanced Error Messages](05_enhanced_error_messages.md)** - Better developer experience
6. **[Memory Optimization](06_memory_optimization.md)** - Reduce overhead per dependency
7. **[Thread-Safety Audit](07_thread_safety_audit.md)** - Verify concurrent safety

### 🟢 Good First Issues (3 issues)
8. **[Add More Examples](08_add_more_examples.md)** - Real-world usage patterns
9. **[Improve Test Coverage](09_improve_test_coverage.md)** - Missing edge cases
10. **[Type Stub Improvements](10_type_stub_improvements.md)** - Better IDE support

## Current Implementation Status

### ✅ What's Working Well
- Type-safe dependency injection with generics
- O(1) lookups with pre-computed hashes
- ContextVar-based async isolation
- Dependencies pattern for grouped injection
- 267 comprehensive tests

### ❌ Gaps to Address
- No free-threading optimization for Python 3.14
- No sub-interpreter support
- No lazy annotation support
- Limited error context in exceptions
- No performance benchmarking suite

## Contributing

To work on an issue:
1. Pick an issue from the list above
2. Create a GitHub issue using the provided description
3. Fork the repository
4. Create a feature branch
5. Submit a PR referencing the issue

## Issue Templates

We provide 3 simple issue templates:
- **[Bug Report](../ISSUE_TEMPLATE/bug_report.yaml)** - Report bugs
- **[Feature Request](../ISSUE_TEMPLATE/feature_request.yaml)** - Suggest enhancements
- **[Question](../ISSUE_TEMPLATE/question.yaml)** - Ask questions

## Development Philosophy

Following UV/Ruff's approach:
- **Minimal labels** - Focus on what matters
- **Clear priorities** - Maintainers know what's important
- **Fast triage** - Simple yes/no decisions
- **Low process overhead** - Ship code, not process

## Roadmap Alignment

These issues align with the project roadmap:
- **Phase 1** (Current): Core functionality and stability
- **Phase 2**: Python 3.14 readiness (issues 1-3)
- **Phase 3**: Performance and developer experience (issues 4-7)
- **Ongoing**: Community contributions (issues 8-10)

## Success Metrics

- All Python 3.14 features implemented before 3.14 stable release
- Performance benchmarks show no regressions
- Community contributions on good first issues
- Positive developer feedback on error messages

---

*Last updated: January 2025*
*Python target: 3.13+ (current), 3.14 (future)*