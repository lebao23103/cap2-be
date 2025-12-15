from django.utils import timezone
from django.core.cache import cache

class ActiveUserMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            # Lưu thời gian truy cập cuối cùng vào Cache (hết hạn sau 5 phút)
            cache.set(f'seen_{request.user.id}', timezone.now(), 180)

        response = self.get_response(request)
        return response
