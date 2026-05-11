def notifications(request):
    if request.user.is_authenticated:
        unread_count = request.user.notifications.filter(is_read=False).count()
        recent = request.user.notifications.filter(is_read=False).order_by('-created_at')[:5]
        return {'unread_notifications_count': unread_count, 'recent_notifications': recent}
    return {'unread_notifications_count': 0, 'recent_notifications': []}
