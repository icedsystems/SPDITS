from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import redirect
from django.views import View
from django.views.generic import ListView
from .models import Notification


class NotificationListView(LoginRequiredMixin, ListView):
    model = Notification
    template_name = 'notifications/notification_list.html'
    context_object_name = 'notifications'
    paginate_by = 30

    def get_queryset(self):
        return self.request.user.notifications.order_by('-created_at')


class NotificationMarkReadView(LoginRequiredMixin, View):
    def post(self, request, pk):
        notif = request.user.notifications.filter(pk=pk).first()
        if notif:
            notif.mark_read()
        if request.htmx:
            return JsonResponse({'status': 'ok'})
        return redirect('notifications:list')


class NotificationMarkAllReadView(LoginRequiredMixin, View):
    def post(self, request):
        from django.utils import timezone
        request.user.notifications.filter(is_read=False).update(
            is_read=True, read_at=timezone.now()
        )
        return redirect('notifications:list')
