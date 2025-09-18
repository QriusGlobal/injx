# Type Safety & Static Analysis

Injx provides comprehensive static type checking support, ensuring your dependency injection code is type-safe at compile time.

## PEP 561 Compliance

Injx is fully compliant with [PEP 561](https://peps.python.org/pep-0561/) and includes a `py.typed` marker file. This means:

- **Full type information** is available to all type checkers
- **Zero configuration** required for type checking
- **Works with all major type checkers**: mypy, basedpyright, pyright

```
# All of these work out of the box
mypy your_code.py
basedpyright your_code.py  
pyright your_code.py
```

## Supported Type Checkers

### basedpyright (Recommended)

Injx is developed and tested with basedpyright in strict mode:

```
# Install basedpyright
uvx basedpyright --help

# Check your Injx code
uvx basedpyright src/ --strict
```

### mypy

Full mypy compatibility with strict settings:

```
# pyproject.toml
[tool.mypy]
strict = true
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
```

### pyright/pylance

Works with VS Code and other editors supporting pyright:

```
// pyrightconfig.json
{
  "typeCheckingMode": "strict",
  "reportMissingImports": true,
  "reportMissingTypeStubs": true
}
```

## Type-Safe Registration

Injx enforces type compatibility between tokens and providers:

```
from typing import Protocol
from injx import Container, Token, Scope

class Logger(Protocol):
    def info(self, message: str) -> None: ...
    def error(self, message: str) -> None: ...

class ConsoleLogger:
    def info(self, message: str) -> None:
        print(f"INFO: {message}")

    def error(self, message: str) -> None:
        print(f"ERROR: {message}")

class FileLogger:
    def __init__(self, filename: str):
        self.filename = filename

    def info(self, message: str) -> None:
        with open(self.filename, 'a') as f:
            f.write(f"INFO: {message}\n")

    def error(self, message: str) -> None:
        with open(self.filename, 'a') as f:
            f.write(f"ERROR: {message}\n")

container = Container()
LOGGER = Token[Logger]("logger", scope=Scope.SINGLETON)

# ✅ Type-safe registrations - type checker will verify compatibility
container.register(LOGGER, ConsoleLogger)  # OK
container.register(LOGGER, lambda: FileLogger("app.log"))  # OK

# ❌ These would fail type checking
# container.register(LOGGER, str)  # Type error!
# container.register(LOGGER, lambda: "not a logger")  # Type error!
```

## Protocol-Based Type Safety

Injx works seamlessly with Python's Protocol system for structural typing:

### Runtime Protocol Validation

```
from typing import Protocol, runtime_checkable

@runtime_checkable
class DatabaseProtocol(Protocol):
    def connect(self) -> None: ...
    def query(self, sql: str) -> list[dict[str, str]]: ...
    def close(self) -> None: ...

class PostgreSQLDatabase:
    def connect(self) -> None:
        print("Connecting to PostgreSQL")

    def query(self, sql: str) -> list[dict[str, str]]:
        return [{"result": "data"}]

    def close(self) -> None:
        print("Closing PostgreSQL connection")

class InvalidDatabase:
    # Missing required methods!
    def some_method(self) -> None:
        pass

# Runtime validation with @runtime_checkable
DB_TOKEN = Token[DatabaseProtocol]("database")

container.register(DB_TOKEN, PostgreSQLDatabase)  # ✅ Valid

# This would pass static type checking but fail at runtime
# container.register(DB_TOKEN, InvalidDatabase)  # ❌ Runtime error

# Verify at registration time
db_instance = PostgreSQLDatabase()
assert isinstance(db_instance, DatabaseProtocol)  # ✅ True
```

### Generic Protocol Support

```
from typing import Protocol, TypeVar, Generic

T = TypeVar('T')
K = TypeVar('K')
V = TypeVar('V')

class Repository(Protocol, Generic[T]):
    def save(self, entity: T) -> None: ...
    def find_by_id(self, id: int) -> T | None: ...
    def find_all(self) -> list[T]: ...

class Cache(Protocol, Generic[K, V]):
    def get(self, key: K) -> V | None: ...
    def set(self, key: K, value: V) -> None: ...

# Type-safe generic implementations
class User:
    def __init__(self, id: int, name: str):
        self.id = id
        self.name = name

class UserRepository:
    def save(self, user: User) -> None:
        print(f"Saving user: {user.name}")

    def find_by_id(self, id: int) -> User | None:
        return User(id, f"User{id}")

    def find_all(self) -> list[User]:
        return [User(1, "Alice"), User(2, "Bob")]

class MemoryCache:
    def __init__(self) -> None:
        self._data: dict[str, str] = {}

    def get(self, key: str) -> str | None:
        return self._data.get(key)

    def set(self, key: str, value: str) -> None:
        self._data[key] = value

# Type-safe generic token creation
USER_REPO = Token[Repository[User]]("user_repo", scope=Scope.SINGLETON)
STRING_CACHE = Token[Cache[str, str]]("string_cache", scope=Scope.SINGLETON)

container.register(USER_REPO, UserRepository)
container.register(STRING_CACHE, MemoryCache)
```

## Type-Safe Injection Patterns

### Recommended Pattern: Plain Type Annotations

The cleanest and most type-safe approach:

```
from injx import inject

@inject
def user_service(
    repo: Repository[User],
    cache: Cache[str, str],
    logger: Logger
) -> None:
    """All parameters are automatically type-checked and injected."""
    users = repo.find_all()
    logger.info(f"Found {len(users)} users")

    for user in users:
        cache.set(f"user:{user.id}", user.name)
        logger.info(f"Cached user: {user.name}")

# Type checker verifies all dependencies can be resolved
user_service()
```

### Advanced Pattern: Explicit Inject Markers

Use when you need custom providers or explicit control:

```
from typing import Annotated
from injx import Inject

@inject  
def advanced_service(
    # Regular injection - recommended
    logger: Logger,

    # Custom provider - useful for testing/configuration
    config: Annotated[Config, Inject(lambda: Config.from_file("config.yml"))],

    # Regular parameters  
    user_id: int
) -> None:
    logger.info(f"Processing user {user_id}")
    logger.info(f"Using config: {config.database_url}")

# Mixed regular and injected parameters
advanced_service(user_id=123)
```

## Static Analysis Best Practices

### 1. Always Use Type Annotations

```
# ✅ Good - explicit types
@inject
def process_data(logger: Logger, db: Database) -> list[str]:
    return db.query("SELECT name FROM users")

# ❌ Bad - no type information  
@inject
def process_data(logger, db):  # Type checker can't help
    return db.query("SELECT name FROM users")
```

### 2. Use Protocols for Interfaces

```
# ✅ Good - protocol defines interface
class EmailService(Protocol):
    def send_email(self, to: str, subject: str, body: str) -> bool: ...

# ❌ Less ideal - concrete class coupling
class SMTPEmailService:
    def send_email(self, to: str, subject: str, body: str) -> bool: ...
    # Other SMTP-specific methods...
```

### 3. Leverage Union Types for Optional Dependencies

```
from typing import Union

# For optional dependencies, use container overrides instead of Union types
@inject
def service_with_optional_logger(
    db: Database,
    logger: Logger  # Required - override in tests if needed
) -> None:
    logger.info("Service starting")

# In tests, override the logger token
container.override(LOGGER, Mock(spec=Logger))
```

## Type Checking Configuration

### Strict Type Checking Setup

```
# pyproject.toml
[tool.basedpyright]
strict = ["src/"]
typeCheckingMode = "strict"
reportMissingImports = true
reportMissingTypeStubs = true
reportUntypedFunctionDecorator = true
reportUnknownParameterType = true

[tool.mypy]
files = ["src/", "tests/"]
strict = true
warn_return_any = true
warn_unused_configs = true
disallow_any_generics = true
disallow_untyped_defs = true
no_implicit_optional = true
```

### CI/CD Integration

```
# .github/workflows/ci.yml
- name: Type checking
  run: |
    uvx basedpyright src/ --strict
    # or
    uvx mypy src/ --strict
```

## Common Type Safety Patterns

### 1. Factory Functions with Proper Types

```
from typing import Callable

def create_database_factory(config: Config) -> Callable[[], Database]:
    def factory() -> Database:
        if config.db_type == "postgresql":
            return PostgreSQLDatabase(config.db_url)
        elif config.db_type == "sqlite":
            return SQLiteDatabase(config.db_path)
        else:
            raise ValueError(f"Unknown database type: {config.db_type}")
    return factory

# Type-safe factory registration
container.register(DB_TOKEN, create_database_factory(config))
```

### 2. Async Type Safety

```
from typing import Awaitable

class AsyncService(Protocol):
    async def process(self, data: str) -> str: ...

class AsyncServiceImpl:
    async def process(self, data: str) -> str:
        await asyncio.sleep(0.1)
        return f"processed: {data}"

# Type-safe async provider
async def create_async_service() -> AsyncService:
    service = AsyncServiceImpl()
    # Any async setup here
    return service

ASYNC_SERVICE = Token[AsyncService]("async_service")
container.register(ASYNC_SERVICE, create_async_service)

@inject
async def async_handler(service: AsyncService) -> str:
    return await service.process("test data")
```

### 3. Context Manager Type Safety

```
from typing import ContextManager
from contextlib import contextmanager

@contextmanager
def database_transaction() -> ContextManager[Database]:
    db = PostgreSQLDatabase()
    db.begin_transaction()
    try:
        yield db
    finally:
        db.rollback()  # Always rollback for safety

# Type-safe context manager registration
container.register_context_sync(
    Token[Database]("transactional_db"),
    database_transaction
)
```

## Troubleshooting Type Issues

### Common Type Errors and Solutions

#### 1. "Cannot assign to Token[X]"

```
# ❌ Problem
TOKEN = Token[str]("my_token")
container.register(TOKEN, 123)  # Type error: int not assignable to str

# ✅ Solution - fix the type or provider
TOKEN = Token[int]("my_token")
container.register(TOKEN, 123)  # OK

# Or fix the provider
TOKEN = Token[str]("my_token")  
container.register(TOKEN, lambda: "123")  # OK
```

#### 2. "Protocol not satisfied"

```
# ❌ Problem
class IncompleteService:
    def some_method(self) -> None: ...
    # Missing required protocol methods!

container.register(SERVICE_TOKEN, IncompleteService)  # Type error

# ✅ Solution - implement all protocol methods
class CompleteService:
    def some_method(self) -> None: ...
    def required_method(self) -> str: ...  # Add missing methods
```

#### 3. "Cannot resolve generic types"

```
# ❌ Problem - type checker can't infer generic parameters
def create_generic_service():  # No return type annotation
    return GenericService()

# ✅ Solution - explicit type annotation
def create_generic_service() -> GenericService[User]:
    return GenericService[User]()
```

### Debugging Type Issues

Enable verbose type checking:

```
# basedpyright with verbose output
uvx basedpyright src/ --verbose

# mypy with detailed error information
uvx mypy src/ --show-error-codes --show-traceback
```

## IDE Integration

### VS Code with Pylance

```
// .vscode/settings.json
{
    "python.analysis.typeCheckingMode": "strict",
    "python.analysis.autoImportCompletions": true,
    "python.analysis.completeFunctionParens": true,
    "python.analysis.inlayHints.functionReturnTypes": true,
    "python.analysis.inlayHints.variableTypes": true
}
```

### PyCharm

Enable strict type checking in Settings → Editor → Inspections → Python:

- Enable "Type checker" inspections
- Enable "Unresolved references" warnings
- Configure to use mypy or pyright as external tool

## Performance of Type Checking

Injx's type checking has minimal runtime impact:

- **Compile-time only**: Type checking happens during static analysis, not at runtime
- **O(1) token lookups**: Pre-computed hash values for tokens
- **Cached analysis**: Function signature parsing is cached by `@inject`
- **Zero overhead**: No runtime type validation unless explicitly requested with `@runtime_checkable`

This ensures that your production code runs at full speed while maintaining complete type safety during development.
