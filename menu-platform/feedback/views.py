import json

from django.contrib import messages
from django.http import JsonResponse, HttpResponseBadRequest
from django.shortcuts import render, get_object_or_404, redirect
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from accounts.views import platform_admin_required
from .models import Feedback


@require_POST
def submit_feedback(request):
    """AJAX endpoint behind the floating feedback widget - logged-in users only."""
    if not request.user.is_authenticated:
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
    )
    return JsonResponse({'success': True})


@platform_admin_required
def feedback_admin_list(request):
    feedback_entries = Feedback.objects.select_related('user')
    return render(request, 'feedback/admin_list.html', {'feedback_entries': feedback_entries})


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
