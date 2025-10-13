import uuid
from django.utils.deprecation import MiddlewareMixin
from .models import Tenant
from django.conf import settings

class RequestIdMiddleware(MiddlewareMixin):
    def process_request(self, request):
        request.request_id = str(uuid.uuid4())

class TenantMiddleware(MiddlewareMixin):
    def process_request(self, request):
        name = request.headers.get("X-Tenant") or request.GET.get("tenant") or settings.DEFAULT_TENANT
        tenant, _ = Tenant.objects.get_or_create(name=name)
        request.tenant = tenant
