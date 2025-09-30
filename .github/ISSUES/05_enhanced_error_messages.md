# Enhanced Error Messages

**Labels:** `enhancement`

## Description
Improve error messages with more context and helpful suggestions for better developer experience.

## Current Issues
- Generic "Token not found" errors
- No resolution chain shown in errors
- No suggestions for similar tokens
- Circular dependency errors lack detail

## Requirements
- [ ] Add resolution chain to ResolutionError
- [ ] Include available tokens in error
- [ ] Implement "did you mean?" suggestions
- [ ] Show dependency graph on circular dependency
- [ ] Add contextual hints for common mistakes

## Example Improvements

### Before
```python
ResolutionError: Token not found: Database
```

### After
```python
ResolutionError: Token 'Database' not found

  Resolution chain:
    UserService -> Repository -> Database

  Available tokens:
    - DatabaseConnection (type: DatabaseConnection)
    - DatabasePool (type: DatabasePool)  
    - CacheDatabase (type: Cache)

  Did you mean 'DatabaseConnection'?

  Hint: Register the token with:
    container.register(Database, database_factory)
```

## Implementation Hints
```python
import difflib

class EnhancedResolutionError(ResolutionError):
    def __init__(self, token: Token, resolution_chain: list[Token], available: list[Token]):
        self.token = token
        self.resolution_chain = resolution_chain
        self.available = available
        self.suggestion = self._find_similar(token.name, available)

    def _find_similar(self, name: str, available: list[Token]) -> str | None:
        names = [t.name for t in available]
        matches = difflib.get_close_matches(name, names, n=1, cutoff=0.6)
        return matches[0] if matches else None
```

## Success Criteria
- Errors provide actionable information
- New developers can self-diagnose issues
- Reduced support burden
- Positive developer feedback

## Additional Improvements
- Color-coded output for terminal
- Structured errors for programmatic handling
- Integration with IDE error panels