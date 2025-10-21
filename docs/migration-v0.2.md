# Migration Guide: v0.1.x → v0.2.0

This guide helps you migrate from the deprecated `Injectable` metaclass pattern to the new `@autowire` decorator pattern introduced in injx v0.2.0.

## Breaking Changes Summary

### Removed in v0.2.0

- ❌ `Injectable` metaclass
- ❌ `container.auto_register()` method
- ❌ `Injectable.get_registry()` class method
- ❌ `__injectable__`, `__token_name__`, `__scope__` class attributes

### Added in v0.2.0

- ✅ `@autowire` decorator for automatic registration
- ✅ `wire()` function for advanced dependency control
- ✅ Application startup pattern with `container.activate()` context
- ✅ Type-based resolution with explicit syntax `container.get(Type)`

## Why the Change?

The `Injectable` metaclass was removed for several architectural and practical reasons:

### 1. **Metaclass Conflicts**
Metaclasses don't compose well with other frameworks:

```python
# CONFLICT: Cannot use multiple metaclasses
class User(Base, metaclass=Injectable):  # ❌ Error!
    # SQLAlchemy already uses DeclarativeMeta
    pass

class UserModel(BaseModel, metaclass=Injectable):  # ❌ Error!
    # Pydantic uses ModelMetaclass
    pass
```

### 2. **Hidden Magic vs Explicit Behavior**
The metaclass pattern obscured the registration process:

```python
# OLD: When does registration happen? ❌
class Service(metaclass=Injectable):
    __injectable__ = True
    # Registered... when? At import time? At auto_register()?

container.auto_register()  # Required but easy to forget
```

### 3. **Two-Step Process**
Required both class definition AND manual `auto_register()` call:

```python
# OLD: Two separate steps ❌
class Service(metaclass=Injectable):
    __injectable__ = True

container.auto_register()  # Easy to forget!
```

### 4. **Type Checker Confusion**
Metaclass attributes confused static type checkers:

```python
# OLD: Type checkers don't understand these ❌
class Service(metaclass=Injectable):
    __injectable__: bool = True  # Not a real attribute
    __token_name__: str = "service"  # Magic metaclass config
```

## Migration Patterns

### Pattern 1: Basic Class with Dependencies

**BEFORE (v0.1.x)**:
```python
from injx import Injectable, Scope

class UserService(metaclass=Injectable):
    __injectable__ = True
    __token_name__ = "user_service"
    __scope__ = Scope.SINGLETON

    def __init__(self, db: Database, cache: Cache):
        self.db = db
        self.cache = cache

# Later, elsewhere in your code
container.auto_register()
```

**AFTER (v0.2.0+)**:
```python
from injx import autowire, Scope

# At application startup
container = Container()

with container.activate():
    @autowire(scope=Scope.SINGLETON)
    class UserService:
        def __init__(self, db: Database, cache: Cache):
            self.db = db
            self.cache = cache

# No auto_register() needed - immediate registration
```

**Key Changes**:
- Remove `metaclass=Injectable`
- Remove `__injectable__`, `__token_name__`, `__scope__` attributes
- Add `@autowire(scope=...)` decorator
- Wrap registration in `container.activate()` context
- Remove `container.auto_register()` call

---

### Pattern 2: Resolving Auto-Registered Services

**BEFORE (v0.1.x)**:
```python
# Get token from Injectable registry
email_service_token = Injectable.get_registry()[EmailService]
service = container.get(email_service_token)
```

**AFTER (v0.2.0+)**:
```python
# Direct type-based resolution with subscript syntax
service = container.get(EmailService)

# OR: Explicit method call
service = container.get(EmailService)
```

**Key Changes**:
- Remove `Injectable.get_registry()` calls
- Use type directly as token with `container.get(Type)` syntax
- Simpler, more Pythonic API

---

### Pattern 3: Protocol-Based Dependencies

**BEFORE (v0.1.x)**:
```python
# This never actually existed in the implementation
logger = container.resolve_protocol(Logger)  # ❌ Method doesn't exist
```

**AFTER (v0.2.0+)**:
```python
from injx import Token
from typing import Protocol

# Define protocol
class Logger(Protocol):
    def info(self, msg: str) -> None: ...

# Explicit token registration
LOGGER = Token[Logger]("logger", Logger)
container.register(LOGGER, ConsoleLogger, scope=Scope.SINGLETON)

# Resolve via token
logger = container.get(LOGGER)

# OR: Register with type directly (simpler)
container.register(Logger, ConsoleLogger, scope=Scope.SINGLETON)
logger = container.get(Logger)  # Works via type index
```

**Key Changes**:
- Use `Token[Protocol]` for explicit protocol registration
- OR use type-based registration with the protocol type
- No automatic protocol satisfaction checking (by design - maintains O(1) performance)

---

### Pattern 4: Leaf Services (No Dependencies)

**BEFORE (v0.1.x)**:
```python
class Logger(metaclass=Injectable):
    __injectable__ = True
    __scope__ = Scope.SINGLETON

    def __init__(self):
        self.enabled = True
```

**AFTER (v0.2.0+)**:
```python
with container.activate():
    @autowire  # Default scope is SINGLETON
    class Logger:
        def __init__(self):
            self.enabled = True
```

**Key Changes**:
- Simpler: Just the decorator, no class attributes
- Default scope is `SINGLETON` (no need to specify)

---

### Pattern 5: Complex Constructor Logic

**BEFORE and AFTER are IDENTICAL**:
```python
with container.activate():
    @autowire(scope=Scope.SINGLETON)
    class ComplexService:
        def __init__(self, db: Database, config: Config):
            # ALL initialization logic runs unchanged
            if not config.validate():
                raise ValueError("Invalid configuration")

            self.db = db
            self._connection = db.connect(config.db_url)
            self._cache = {}
            # ... additional setup
```

**Key Insight**: The `@autowire` decorator is an **identity decorator** - it returns the class completely unchanged. All your `__init__` logic runs exactly as before.

---

### Pattern 6: Application Startup Pattern

This is the recommended pattern for organizing dependency registration in v0.2.0+.

**Application Structure**:
```python
# main.py or app.py
from injx import Container, autowire, Scope

container = Container()

def setup_container():
    """Define all services at application startup."""
    with container.activate():
        # Infrastructure layer
        @autowire(scope=Scope.SINGLETON)
        class Database:
            def __init__(self):
                self.connection = None

        @autowire(scope=Scope.SINGLETON)
        class Cache:
            def __init__(self):
                self.store = {}

        # Repository layer
        @autowire(scope=Scope.SINGLETON)
        class UserRepository:
            def __init__(self, db: Database):
                self.db = db

        # Service layer
        @autowire(scope=Scope.SINGLETON)
        class UserService:
            def __init__(self, repo: UserRepository, cache: Cache):
                self.repo = repo
                self.cache = cache

def main():
    # Setup dependencies once at startup
    setup_container()

    # Use anywhere in application
    user_service = container.get(UserService)
    # ... application logic

if __name__ == "__main__":
    main()
```

**Benefits**:
- Single place to see entire dependency graph
- Clear separation: setup vs usage
- No repeated `with container.activate()` blocks throughout codebase
- Easy to test: just call `setup_container()` in test setup

---

### Pattern 7: FastAPI Integration

**BEFORE (v0.1.x)**:
```python
from fastapi import Depends
from injx import Injectable

class UserService(metaclass=Injectable):
    __injectable__ = True
    __token_name__ = "user_service"
    __scope__ = Scope.SINGLETON

    def __init__(self, db: Database):
        self.db = db

def get_user_service(container: Container = Depends(get_container)) -> UserService:
    user_service_token = Injectable.get_registry()[UserService]
    return container.get(user_service_token)

@app.post("/users")
async def create_user(service: UserService = Depends(get_user_service)):
    # ...
```

**AFTER (v0.2.0+)**:
```python
from fastapi import Depends
from injx import autowire, Scope

# At application startup (in lifespan or startup event)
@app.on_event("startup")
async def startup():
    with container.activate():
        @autowire(scope=Scope.SINGLETON)
        class UserService:
            def __init__(self, db: Database):
                self.db = db

# Simplified dependency provider
def get_user_service(container: Container = Depends(get_container)) -> UserService:
    return container.get(UserService)  # Direct type-based resolution

@app.post("/users")
async def create_user(service: UserService = Depends(get_user_service)):
    # ...
```

**Key Changes**:
- Register services in FastAPI startup event
- Simplified `get_user_service()` - no `Injectable.get_registry()`
- Use `container.get(Type)` explicit syntax

---

## Testing Patterns

### Testing with Overrides

**BEFORE (v0.1.x)**:
```python
def test_user_service():
    # Setup
    mock_db = MockDatabase()
    container.auto_register()

    # Override
    db_token = Injectable.get_registry()[Database]
    with container.override(db_token, mock_db):
        service_token = Injectable.get_registry()[UserService]
        service = container.get(service_token)
        # ... test
```

**AFTER (v0.2.0+)**:
```python
def test_user_service():
    # Setup with wire() for manual override
    mock_db = MockDatabase()

    wire(UserService, container=container) \
        .with_override("db", mock_db) \
        .register()

    # Test
    service = container.get(UserService)
    assert service.db is mock_db
    # ... test
```

**Alternative: Use container.override()**:
```python
def test_user_service():
    # Register normally
    with container.activate():
        @autowire
        class UserService:
            def __init__(self, db: Database):
                self.db = db

    # Override for test
    mock_db = MockDatabase()
    with container.override(Database, mock_db):
        service = container.get(UserService)
        assert service.db is mock_db
```

---

## Common Migration Mistakes

### ❌ Mistake 1: Forgetting `container.activate()` Context

```python
# WRONG: No activate context
@autowire
class Service:
    def __init__(self, db: Database):
        self.db = db
# Error: No active container!
```

```python
# CORRECT: Within activate context
with container.activate():
    @autowire
    class Service:
        def __init__(self, db: Database):
            self.db = db
```

---

### ❌ Mistake 2: Using Old `get_registry()` Pattern

```python
# WRONG: Injectable.get_registry() doesn't exist
token = Injectable.get_registry()[Service]  # ❌
```

```python
# CORRECT: Direct type-based resolution
service = container.get(Service)  # ✅
```

---

### ❌ Mistake 3: Expecting Metaclass Attributes to Work

```python
# WRONG: These attributes do nothing with @autowire
@autowire
class Service:
    __injectable__ = True  # ❌ Ignored
    __token_name__ = "svc"  # ❌ Ignored
    __scope__ = Scope.SINGLETON  # ❌ Ignored
```

```python
# CORRECT: Scope goes in decorator parameter
@autowire(scope=Scope.SINGLETON)
class Service:
    def __init__(self):
        pass
```

---

### ❌ Mistake 4: Mixing Injectable and @autowire

```python
# WRONG: Can't use both (Injectable is removed)
class Service(metaclass=Injectable):  # ❌ Injectable doesn't exist
    @autowire  # ❌ Redundant even if it did
    def __init__(self):
        pass
```

```python
# CORRECT: Just use @autowire
with container.activate():
    @autowire
    class Service:
        def __init__(self):
            pass
```

---

## Automated Migration Script

For large codebases, you can use this search-and-replace strategy:

### Step 1: Find all Injectable usage
```bash
# Find all files with Injectable
grep -r "Injectable" --include="*.py" .

# Find all metaclass usage
grep -r "metaclass=Injectable" --include="*.py" .
```

### Step 2: Replace imports
```python
# FIND:
from injx import Injectable

# REPLACE WITH:
from injx import autowire
```

### Step 3: Replace class definitions
```python
# FIND:
class (\w+)\(metaclass=Injectable\):
    __injectable__ = True
    __token_name__ = "(\w+)"
    __scope__ = Scope\.(\w+)

# REPLACE WITH:
@autowire(scope=Scope.\3)
class \1:
```

### Step 4: Replace resolution calls
```python
# FIND:
Injectable\.get_registry\(\)\[(\w+)\]

# REPLACE WITH:
\1
```

### Step 5: Remove auto_register calls
```python
# FIND:
container\.auto_register\(\)

# REPLACE WITH:
# (delete line)
```

### Step 6: Add activate context
Manually wrap registration sections with:
```python
with container.activate():
    # ... @autowire decorated classes
```

---

## Checklist

Use this checklist to verify complete migration:

- [ ] Remove all `metaclass=Injectable` from class definitions
- [ ] Remove all `__injectable__`, `__token_name__`, `__scope__` class attributes
- [ ] Replace with `@autowire` decorator (with scope parameter if needed)
- [ ] Wrap all `@autowire` usage in `container.activate()` context
- [ ] Remove all `container.auto_register()` calls
- [ ] Replace `Injectable.get_registry()[Type]` with `Type` directly
- [ ] Update all `container[Type]` to `container.get(Type)`
- [ ] Remove `Injectable` from imports
- [ ] Add `autowire` to imports
- [ ] Update tests to use `wire()` for overrides or `container.override()`
- [ ] Run type checker (should pass with no errors)
- [ ] Run test suite (should pass)

---

## Getting Help

If you encounter migration issues:

1. **Check the Examples**: See `examples/basic_usage.py` and `examples/fastapi_app.py` for complete working examples
2. **Review the Spec**: See `docs/specs/autowiring-spec.rst` for full implementation details
3. **Type Safety**: Ensure all `__init__` parameters have type hints
4. **Active Container**: Verify `@autowire` usage is within `container.activate()` context

---

## Summary

The migration from `Injectable` metaclass to `@autowire` decorator provides:

✅ **Better Framework Compatibility**: No metaclass conflicts
✅ **Explicit Behavior**: Clear when registration happens
✅ **Simpler API**: One-step registration, no `auto_register()`
✅ **Type Safety**: Better static type checker support
✅ **Performance**: Pre-compiled resolution paths, O(1) lookups
✅ **Testing**: Identity decorator preserves class for mocking

The new pattern is more Pythonic, more explicit, and better aligned with modern Python best practices.
