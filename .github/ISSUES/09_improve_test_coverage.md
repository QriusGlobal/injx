# Improve Test Coverage

**Labels:** `enhancement`, `documentation`

## Description
Identify and add tests for missing edge cases and error conditions.

## Current State
- 267 test methods
- Good coverage of happy paths
- Some edge cases missing
- Limited stress testing

## Areas to Improve
- [ ] Error condition handling
- [ ] Race condition testing
- [ ] Memory pressure scenarios
- [ ] Large container stress tests (10k+ services)
- [ ] Circular dependency edge cases
- [ ] Scope transition edge cases

## Specific Test Cases Needed

### 1. Error Conditions
```python
def test_resolution_with_failing_factory():
    """Test handling when factory raises exception."""
    container = Container()
    container.register(Service, lambda: raise_error())
    with pytest.raises(ResolutionError) as exc:
        container.get(Service)
    assert "Factory failed" in str(exc.value)

def test_async_cleanup_in_sync_context():
    """Test error when async cleanup required in sync context."""
    # ...
```

### 2. Stress Tests
```python
def test_large_container_performance():
    """Test with 10,000+ registered services."""
    container = Container()
    tokens = []
    for i in range(10000):
        token = Token(f"service_{i}", Service)
        tokens.append(token)
        container.register(token, lambda: Service())
    
    # Measure resolution time
    start = time.perf_counter()
    for token in random.sample(tokens, 100):
        container.get(token)
    elapsed = time.perf_counter() - start
    assert elapsed < 0.1  # 100 resolutions in < 100ms
```

### 3. Edge Cases
```python
def test_circular_dependency_with_scopes():
    """Test circular deps across different scopes."""
    # ...

def test_concurrent_scope_transitions():
    """Test scope changes during concurrent access."""
    # ...
```

## Testing Approach
- Use coverage.py to identify gaps
- Add property-based testing with Hypothesis
- Implement mutation testing
- Add performance regression tests

## Success Criteria
- Test coverage > 95%
- All edge cases documented and tested
- No untested error paths
- Stress tests pass reliably
- CI runs all tests in < 1 minute

## Notes for Contributors
Good first issue! To contribute:
1. Run `uv run pytest --cov=injx --cov-report=html`
2. Open `htmlcov/index.html` to see coverage gaps
3. Pick an uncovered area
4. Write comprehensive tests
5. Ensure tests are fast and reliable