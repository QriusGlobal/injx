# Add More Examples

**Labels:** `documentation`, `enhancement`

## Description
Create more real-world examples showcasing different use cases of injx.

## Examples Needed
- [ ] CLI application with commands
- [ ] Worker queue processor
- [ ] Plugin system architecture  
- [ ] Testing patterns with mocks
- [ ] Configuration management

## Requirements
- Self-contained, runnable examples
- Clear documentation and comments
- Common patterns demonstrated
- Progressive complexity
- Real-world applicability

## Structure
```
examples/
  cli_app.py          # Click/Typer integration
  worker_queue.py     # Background job processing
  plugin_system.py    # Dynamic loading
  testing.py          # Mock patterns
  config_mgmt.py      # Configuration patterns
  README.md           # Example overview
```

## Example: CLI Application
```python
#!/usr/bin/env python
"""Example: CLI application with dependency injection."""

import click
from injx import Container, Token, inject

# Define services
class Database:
    def get_users(self): ...

class EmailService:
    def send_email(self, to: str, subject: str): ...

# Tokens
DB = Token[Database]("database")
EMAIL = Token[EmailService]("email")

# Setup container
container = Container()
container.register(DB, Database)
container.register(EMAIL, EmailService)
Container.set_active(container)

# CLI commands
@click.group()
def cli():
    """Example CLI application."""
    pass

@cli.command()
@click.argument('user_id')
@inject
def get_user(user_id: str, db: Database):
    """Get user by ID."""
    user = db.get_users(user_id)
    click.echo(f"User: {user}")

@cli.command()
@click.argument('email')
@inject
def send_notification(email: str, email_service: EmailService):
    """Send notification email."""
    email_service.send_email(email, "Notification")
    click.echo(f"Notification sent to {email}")

if __name__ == '__main__':
    cli()
```

## Success Criteria
- Examples run without errors
- Cover common use cases
- Well-documented code
- Follow best practices
- Community contributions

## Notes for Contributors
This is a great first issue for newcomers! Pick one example type and create a well-documented, runnable example. Make sure to:
1. Add docstrings
2. Include type hints
3. Show both simple and advanced usage
4. Add a README explaining the example