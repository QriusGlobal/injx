# Type Stub Improvements

**Labels:** `enhancement`, `documentation`

## Description
Create comprehensive type stubs (.pyi files) for better IDE support and type checking.

## Current State
- Inline type annotations exist
- No separate .pyi stub files
- Some generic type information lost in complex cases
- IDE support could be better

## Requirements
- [ ] Complete .pyi files for all public modules
- [ ] Preserve generic type parameters
- [ ] Add detailed Protocol definitions
- [ ] Include overload signatures
- [ ] Document with docstrings

## Structure
```
src/injx/
  __init__.pyi
  container.pyi
  tokens.pyi
  dependencies.pyi
  injection.pyi
  exceptions.pyi
  protocols/
    __init__.pyi
    container.pyi
    resources.pyi
```

## Example Stub File
```python
# container.pyi
from typing import TypeVar, Generic, overload, ContextManager, AsyncContextManager
from .tokens import Token, Scope
from .protocols import ProviderLike

T = TypeVar('T')
U = TypeVar('U')

class Container:
    """Type-safe dependency injection container."""

    @overload
    def register(self, token: Token[T], provider: ProviderLike[T]) -> None: ...

    @overload
    def register(
        self,
        token: Token[T],
        provider: ProviderLike[T],
        *,
        scope: Scope = ...
    ) -> None: ...

    @overload
    def get(self, token: Token[T]) -> T: ...

    @overload
    def get(self, token: type[T]) -> T: ...

    async def aget(self, token: Token[T]) -> T: ...

    def override(self, token: Token[T], value: T) -> None: ...

    def use_overrides(self, overrides: dict[Token[T], T]) -> ContextManager[None]: ...
```

## Benefits
- Better IDE autocomplete
- Improved type checking accuracy
- Documentation in IDEs
- Faster static analysis
- Better generic type inference

## Testing Stubs
```python
# test_stubs.py
import mypy.api

def test_type_stubs():
    """Verify stubs are valid and complete."""
    result = mypy.api.run([
        '--strict',
        '--show-error-codes',
        'src/injx'
    ])
    stdout, stderr, exit_status = result
    assert exit_status == 0, f"Type stub errors: {stdout}"
```

## Success Criteria
- All public APIs have stubs
- mypy --strict passes
- IDEs show proper autocomplete
- Generic types preserved
- Documentation visible in IDEs

## Notes for Contributors
This is a good first issue for those familiar with Python typing! To contribute:
1. Pick a module to stub
2. Create the corresponding .pyi file
3. Include all public APIs
4. Add overloads where appropriate
5. Test with mypy --strict
6. Verify IDE support improves