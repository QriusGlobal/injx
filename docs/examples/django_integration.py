"""Django Integration with Injx - Type-Safe Views and Middleware

This example demonstrates:
- Django view integration with dependency injection
- Middleware with injected services
- Django ORM with DI patterns
- Type-safe view decorators
- Django REST Framework integration

Setup Django project:
    django-admin startproject myproject
    # Copy this file to myproject/views.py
    # Update urls.py to include these views

Run Django:
    python manage.py runserver
"""

from typing import Any, Optional, Protocol, Type, TypeVar, cast
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views import View
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.core.cache import cache as django_cache
from django.db import models, transaction
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from injx import Container, Token, inject, Scope, Dependencies
import json
import logging


# 1. Service protocols for Django
class UserService(Protocol):
    """User service protocol."""

    def get_user(self, user_id: int) -> dict[str, Any]: ...
    def create_user(self, user_data: dict[str, Any]) -> dict[str, Any]: ...
    def update_user(self, user_id: int, user_data: dict[str, Any]) -> dict[str, Any]: ...
    def delete_user(self, user_id: int) -> bool: ...


class EmailService(Protocol):
    """Email service protocol."""

    def send_welcome(self, email: str, name: str) -> bool: ...
    def send_notification(self, email: str, message: str) -> bool: ...


class CacheService(Protocol):
    """Cache service protocol."""

    def get(self, key: str) -> Optional[Any]: ...
    def set(self, key: str, value: Any, timeout: int = 300) -> None: ...
    def delete(self, key: str) -> bool: ...


class AnalyticsService(Protocol):
    """Analytics service protocol."""

    def track_event(self, event: str, properties: dict[str, Any]) -> None: ...
    def track_page_view(self, path: str, user_id: Optional[int] = None) -> None: ...


class AuthService(Protocol):
    """Authentication service protocol."""

    def authenticate(self, username: str, password: str) -> Optional[dict[str, Any]]: ...
    def create_session(self, user_id: int) -> str: ...
    def validate_token(self, token: str) -> Optional[int]: ...


# 2. Django model example
class User(models.Model):
    """Django User model."""

    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'users'


# 3. Service implementations for Django
class DjangoUserService:
    """User service using Django ORM."""

    def get_user(self, user_id: int) -> dict[str, Any]:
        """Get user from Django ORM."""
        try:
            user = User.objects.get(pk=user_id)
            return {
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "is_active": user.is_active
            }
        except User.DoesNotExist:
            raise ValueError(f"User {user_id} not found")

    def create_user(self, user_data: dict[str, Any]) -> dict[str, Any]:
        """Create user with Django ORM."""
        user = User.objects.create(**user_data)
        return {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "is_active": user.is_active
        }

    def update_user(self, user_id: int, user_data: dict[str, Any]) -> dict[str, Any]:
        """Update user with Django ORM."""
        User.objects.filter(pk=user_id).update(**user_data)
        return self.get_user(user_id)

    def delete_user(self, user_id: int) -> bool:
        """Delete user with Django ORM."""
        deleted, _ = User.objects.filter(pk=user_id).delete()
        return deleted > 0


class DjangoCacheService:
    """Cache service using Django's cache framework."""

    def get(self, key: str) -> Optional[Any]:
        """Get from Django cache."""
        return django_cache.get(key)

    def set(self, key: str, value: Any, timeout: int = 300) -> None:
        """Set in Django cache."""
        django_cache.set(key, value, timeout)

    def delete(self, key: str) -> bool:
        """Delete from Django cache."""
        django_cache.delete(key)
        return True


class DjangoEmailService:
    """Email service using Django's email backend."""

    def send_welcome(self, email: str, name: str) -> bool:
        """Send welcome email using Django."""
        from django.core.mail import send_mail
        try:
            send_mail(
                subject=f"Welcome {name}!",
                message=f"Hello {name}, welcome to our platform!",
                from_email="noreply@example.com",
                recipient_list=[email],
                fail_silently=False,
            )
            return True
        except Exception:
            return False

    def send_notification(self, email: str, message: str) -> bool:
        """Send notification email."""
        from django.core.mail import send_mail
        try:
            send_mail(
                subject="Notification",
                message=message,
                from_email="noreply@example.com",
                recipient_list=[email],
                fail_silently=False,
            )
            return True
        except Exception:
            return False


class GoogleAnalyticsService:
    """Analytics service implementation."""

    def __init__(self) -> None:
        self.logger = logging.getLogger(__name__)

    def track_event(self, event: str, properties: dict[str, Any]) -> None:
        """Track custom event."""
        self.logger.info(f"Analytics Event: {event} - {properties}")
        # In production: send to Google Analytics

    def track_page_view(self, path: str, user_id: Optional[int] = None) -> None:
        """Track page view."""
        self.logger.info(f"Page View: {path} (User: {user_id})")
        # In production: send to Google Analytics


class DjangoAuthService:
    """Authentication service using Django auth."""

    def authenticate(self, username: str, password: str) -> Optional[dict[str, Any]]:
        """Authenticate user with Django."""
        from django.contrib.auth import authenticate
        user = authenticate(username=username, password=password)
        if user:
            return {
                "id": user.id,
                "username": user.username,
                "email": user.email
            }
        return None

    def create_session(self, user_id: int) -> str:
        """Create session token."""
        from django.contrib.sessions.models import Session
        # Simplified - in production use proper session management
        return f"session_{user_id}_{hash(user_id)}"

    def validate_token(self, token: str) -> Optional[int]:
        """Validate session token."""
        # Simplified validation
        if token.startswith("session_"):
            parts = token.split("_")
            if len(parts) == 3:
                return int(parts[1])
        return None


# 4. Define tokens
USER_SERVICE: Token[UserService] = Token("user_service", UserService)
EMAIL_SERVICE: Token[EmailService] = Token("email_service", EmailService)
CACHE_SERVICE: Token[CacheService] = Token("cache_service", CacheService)
ANALYTICS_SERVICE: Token[AnalyticsService] = Token("analytics_service", AnalyticsService)
AUTH_SERVICE: Token[AuthService] = Token("auth_service", AuthService)


# 5. Setup container for Django
def setup_django_container() -> Container:
    """Configure DI container for Django."""
    container = Container()

    # Register services
    container.register(USER_SERVICE, DjangoUserService, scope=Scope.SINGLETON)
    container.register(EMAIL_SERVICE, DjangoEmailService, scope=Scope.SINGLETON)
    container.register(CACHE_SERVICE, DjangoCacheService, scope=Scope.SINGLETON)
    container.register(ANALYTICS_SERVICE, GoogleAnalyticsService, scope=Scope.SINGLETON)
    container.register(AUTH_SERVICE, DjangoAuthService, scope=Scope.SINGLETON)

    return container


# 6. Django view decorator for dependency injection
T = TypeVar('T')


def inject_services(view_func):
    """Decorator to inject services into Django views using Dependencies pattern."""
    @inject
    def wrapper(
        request: HttpRequest,
        *args,
        deps: Dependencies[UserService, CacheService, AnalyticsService],
        **kwargs
    ):
        # Add services to request for access in view
        request.user_service = deps[UserService]  # type: ignore
        request.cache_service = deps[CacheService]  # type: ignore
        request.analytics_service = deps[AnalyticsService]  # type: ignore

        # Track page view
        deps[AnalyticsService].track_page_view(
            request.path,
            getattr(request.user, 'id', None)
        )

        return view_func(request, *args, **kwargs)

    return wrapper


# 7. Django views with dependency injection
@inject_services
def user_detail_view(request: HttpRequest, user_id: int) -> JsonResponse:
    """Get user details with caching."""
    cache_service: CacheService = request.cache_service  # type: ignore
    user_service: UserService = request.user_service  # type: ignore

    # Check cache first
    cache_key = f"user:{user_id}"
    cached_user = cache_service.get(cache_key)

    if cached_user:
        return JsonResponse(cached_user)

    # Get from service
    try:
        user = user_service.get_user(user_id)
        cache_service.set(cache_key, user, timeout=600)
        return JsonResponse(user)
    except ValueError as e:
        return JsonResponse({"error": str(e)}, status=404)


@inject_services
@require_http_methods(["POST"])
def create_user_view(request: HttpRequest) -> JsonResponse:
    """Create new user with email notification."""
    user_service: UserService = request.user_service  # type: ignore
    analytics_service: AnalyticsService = request.analytics_service  # type: ignore

    # Parse request body
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    # Create user with transaction
    with transaction.atomic():
        user = user_service.create_user(data)

        # Track event
        analytics_service.track_event("user_created", {
            "user_id": user["id"],
            "source": "web"
        })

    # Send welcome email asynchronously
    @inject
    def send_welcome_email(
        email_service: EmailService = Depends(EMAIL_SERVICE)
    ) -> None:
        email_service.send_welcome(user["email"], user["name"])

    send_welcome_email()

    return JsonResponse(user, status=201)


# 8. Class-based views with DI
class UserAPIView(View):
    """Class-based view with dependency injection."""

    @inject
    def setup(
        self,
        request: HttpRequest,
        *args,
        deps: Dependencies[UserService, CacheService, EmailService],
        **kwargs
    ) -> None:
        """Setup method with injected dependencies using Dependencies pattern."""
        super().setup(request, *args, **kwargs)
        self.user_service = deps[UserService]
        self.cache_service = deps[CacheService]
        self.email_service = deps[EmailService]

    def get(self, request: HttpRequest, user_id: int) -> JsonResponse:
        """Handle GET request."""
        try:
            user = self.user_service.get_user(user_id)
            return JsonResponse(user)
        except ValueError:
            return JsonResponse({"error": "User not found"}, status=404)

    def put(self, request: HttpRequest, user_id: int) -> JsonResponse:
        """Handle PUT request."""
        try:
            data = json.loads(request.body)
            user = self.user_service.update_user(user_id, data)

            # Invalidate cache
            self.cache_service.delete(f"user:{user_id}")

            return JsonResponse(user)
        except (json.JSONDecodeError, ValueError) as e:
            return JsonResponse({"error": str(e)}, status=400)

    def delete(self, request: HttpRequest, user_id: int) -> JsonResponse:
        """Handle DELETE request."""
        if self.user_service.delete_user(user_id):
            self.cache_service.delete(f"user:{user_id}")
            return JsonResponse({"message": "User deleted"})
        return JsonResponse({"error": "User not found"}, status=404)


# 9. Django REST Framework integration
class UserSerializer(serializers.ModelSerializer):
    """DRF serializer for User model."""

    class Meta:
        model = User
        fields = ['id', 'name', 'email', 'is_active', 'created_at']


class UserViewSet(viewsets.ModelViewSet):
    """DRF ViewSet with dependency injection."""

    queryset = User.objects.all()
    serializer_class = UserSerializer

    @inject
    def __init__(
        self,
        *args,
        deps: Dependencies[CacheService, AnalyticsService, EmailService],
        **kwargs
    ):
        """Initialize with injected services using Dependencies pattern."""
        super().__init__(*args, **kwargs)
        self.cache_service = deps[CacheService]
        self.analytics_service = deps[AnalyticsService]
        self.email_service = deps[EmailService]

    def retrieve(self, request: Request, pk: Optional[int] = None) -> Response:
        """Override retrieve to add caching."""
        if pk:
            # Check cache first
            cache_key = f"drf_user:{pk}"
            cached = self.cache_service.get(cache_key)

            if cached:
                return Response(cached)

            # Get from database
            response = super().retrieve(request, pk)
            self.cache_service.set(cache_key, response.data, timeout=300)

            # Track analytics
            self.analytics_service.track_event("user_viewed", {"user_id": pk})

            return response
        return super().retrieve(request, pk)

    @action(detail=True, methods=['post'])
    def send_notification(self, request: Request, pk: Optional[int] = None) -> Response:
        """Custom action to send notification."""
        user = self.get_object()
        message = request.data.get('message', 'Hello!')

        success = self.email_service.send_notification(user.email, message)

        if success:
            self.analytics_service.track_event("notification_sent", {
                "user_id": user.id,
                "type": "manual"
            })
            return Response({"status": "sent"})
        return Response({"status": "failed"}, status=500)


# 10. Django middleware with DI
class DIMiddleware:
    """Middleware that uses dependency injection."""

    @inject
    def __init__(
        self,
        get_response,
        deps: Dependencies[AnalyticsService, CacheService]
    ):
        """Initialize middleware with services using Dependencies pattern."""
        self.get_response = get_response
        self.analytics_service = deps[AnalyticsService]
        self.cache_service = deps[CacheService]

    def __call__(self, request: HttpRequest) -> HttpResponse:
        """Process request/response."""
        # Before view
        self.analytics_service.track_page_view(request.path)

        # Check if response is cached
        if request.method == "GET":
            cache_key = f"page:{request.path}"
            cached_response = self.cache_service.get(cache_key)
            if cached_response:
                return HttpResponse(cached_response)

        response = self.get_response(request)

        # After view - cache GET responses
        if request.method == "GET" and response.status_code == 200:
            cache_key = f"page:{request.path}"
            self.cache_service.set(cache_key, response.content, timeout=60)

        return response


# 11. Django settings.py configuration
"""
# Add to your Django settings.py:

from django_integration import setup_django_container
from injx import Container

# Initialize DI container on Django startup
container = setup_django_container()
Container.set_active(container)

# Add middleware
MIDDLEWARE = [
    # ... other middleware
    'myproject.views.DIMiddleware',
]
"""


# 12. Django urls.py configuration
"""
# Add to your urls.py:

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    user_detail_view,
    create_user_view,
    UserAPIView,
    UserViewSet
)

router = DefaultRouter()
router.register(r'api/users', UserViewSet)

urlpatterns = [
    path('users/<int:user_id>/', user_detail_view, name='user_detail'),
    path('users/create/', create_user_view, name='create_user'),
    path('users/<int:user_id>/api/', UserAPIView.as_view(), name='user_api'),
    path('', include(router.urls)),
]
"""