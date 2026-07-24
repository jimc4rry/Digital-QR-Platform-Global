import json

from django.contrib import messages
from django.core.paginator import Paginator
from django.http import JsonResponse, HttpResponseBadRequest
from django.shortcuts import render, get_object_or_404, redirect
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from accounts.views import platform_admin_required
from .models import Feedback

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
    """Full detail view for one feedback entry - viewing it marks it read."""
    entry = get_object_or_404(Feedback.objects.select_related('user', 'user__restaurant'), pk=pk)
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
