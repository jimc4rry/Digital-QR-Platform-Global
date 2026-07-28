import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import JsonResponse, HttpResponseBadRequest
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from accounts.views import platform_admin_required
from .models import Feedback, Notification

FEEDBACK_PAGE_SIZE = 20


@require_POST
def submit_feedback(request):
    """AJAX endpoint behind the floating feedback widget - logged-in, non-admin users only."""
    if not request.user.is_authenticated or request.user.is_superuser:
        return JsonResponse({'error': 'auth_required'}, status=403)

    try:
        data = json.loads(request.body)
    except (ValueError, TypeError):
        return HttpResponseBadRequest()

    message = (data.get('message') or '').strip()
    if not message:
        return JsonResponse({'error': 'empty'}, status=400)

    Feedback.objects.create(
        user=request.user,
        message=message[:5000],
        page_url=(data.get('page_url') or '')[:500],
        user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
    )
    return JsonResponse({'success': True})


@platform_admin_required
def feedback_admin_list(request):
    feedback_entries = Feedback.objects.select_related('user', 'user__restaurant')
    page_obj = Paginator(feedback_entries, FEEDBACK_PAGE_SIZE).get_page(request.GET.get('page'))
    return render(request, 'feedback/admin_list.html', {'feedback_entries': page_obj, 'page_obj': page_obj})


@platform_admin_required
def feedback_admin_detail(request, pk):
    """Full detail view for one feedback entry - viewing it marks it read.
    POSTing a reply here saves it on the entry and creates a Notification for
    whoever originally sent the feedback, so they see it in-app rather than
    needing an email round-trip."""
    entry = get_object_or_404(Feedback.objects.select_related('user', 'user__restaurant'), pk=pk)

    if request.method == 'POST':
        reply_text = (request.POST.get('reply') or '').strip()
        if reply_text:
            entry.admin_reply = reply_text
            entry.replied_at = timezone.now()
            entry.save(update_fields=['admin_reply', 'replied_at'])
            Notification.objects.create(
                recipient=entry.user,
                title=_('Reply to your feedback'),
                message=reply_text,
                feedback=entry,
            )
            messages.success(request, _('Reply sent.'))
        return redirect('feedback:admin_detail', pk=entry.pk)

    if not entry.is_read:
        entry.is_read = True
        entry.save(update_fields=['is_read'])
    return render(request, 'feedback/admin_detail.html', {'entry': entry})


@platform_admin_required
def feedback_admin_mark_read(request, pk):
    entry = get_object_or_404(Feedback, pk=pk)
    if request.method == 'POST':
        entry.is_read = not entry.is_read
        entry.save(update_fields=['is_read'])
    return redirect('feedback:admin_list')


@platform_admin_required
def feedback_admin_delete(request, pk):
    entry = get_object_or_404(Feedback, pk=pk)
    if request.method == 'POST':
        entry.delete()
        messages.success(request, _('Feedback deleted.'))
        return redirect('feedback:admin_list')
    return render(request, 'feedback/admin_delete_confirm.html', {'entry': entry})


NOTIFICATION_PAGE_SIZE = 20


@login_required
def notification_list(request):
    """Any logged-in restaurant user's own notifications (owner or staff -
    whoever the Notification.recipient is). Opening this page marks
    everything currently on it read, the same "viewing marks read" pattern
    used for feedback on the admin side."""
    notifications = Notification.objects.filter(recipient=request.user).select_related('feedback')
    page_obj = Paginator(notifications, NOTIFICATION_PAGE_SIZE).get_page(request.GET.get('page'))

    unread_ids = [n.pk for n in page_obj if not n.is_read]
    if unread_ids:
        Notification.objects.filter(pk__in=unread_ids).update(is_read=True)

    return render(request, 'feedback/notification_list.html', {'page_obj': page_obj})
