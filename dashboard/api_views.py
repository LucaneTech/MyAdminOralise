import json
from datetime import datetime, date
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.utils import timezone

from .models import Session, Student, Teacher, Language, Notification
from .forms import SessionForm


STATUS_COLORS = {
    'scheduled': '#3b82f6',
    'completed': '#22c55e',
    'cancelled': '#ef4444',
    'rescheduled': '#f59e0b',
    'absent': '#f97316',
}


def _session_to_event(session):
    start_dt = datetime.combine(session.date, session.start_time)
    end_dt = datetime.combine(session.date, session.end_time)
    student_names = ', '.join(
        s.user.get_full_name() for s in session.students.select_related('user').all()
    )
    return {
        'id': session.id,
        'title': f"{session.language} — {student_names or '—'}",
        'start': start_dt.isoformat(),
        'end': end_dt.isoformat(),
        'color': STATUS_COLORS.get(session.status, '#6b7280'),
        'extendedProps': {
            'status': session.status,
            'status_display': session.get_status_display(),
            'teacher': str(session.teacher),
            'language': str(session.language),
            'students': [s.user.get_full_name() for s in session.students.all()],
            'session_id': session.id,
        },
    }


def _base_queryset(request):
    role = request.user.role
    qs = Session.objects.select_related('teacher__user', 'language').prefetch_related('students__user')
    if role == 'teacher':
        qs = qs.filter(teacher=request.user.teacher)
    elif role == 'student':
        qs = qs.filter(students=request.user.student)
    return qs


@login_required
@require_GET
def api_sessions_feed(request):
    """FullCalendar feed — GET /api/sessions/?start=...&end=..."""
    qs = _base_queryset(request)
    start = request.GET.get('start')
    end = request.GET.get('end')
    if start:
        qs = qs.filter(date__gte=start[:10])
    if end:
        qs = qs.filter(date__lte=end[:10])
    # Admin filters
    if request.user.role == 'admin':
        if request.GET.get('teacher_id'):
            qs = qs.filter(teacher_id=request.GET['teacher_id'])
        if request.GET.get('student_id'):
            qs = qs.filter(students__id=request.GET['student_id'])
        if request.GET.get('language_id'):
            qs = qs.filter(language_id=request.GET['language_id'])
    events = [_session_to_event(s) for s in qs]
    return JsonResponse(events, safe=False)


@login_required
def api_session_detail(request, session_id):
    """GET /api/sessions/<id>/ — détail JSON pour pré-remplir modale"""
    session = get_object_or_404(Session, pk=session_id)
    data = {
        'id': session.id,
        'teacher_id': session.teacher_id,
        'language_id': session.language_id,
        'date': str(session.date),
        'start_time': str(session.start_time)[:5],
        'end_time': str(session.end_time)[:5],
        'status': session.status,
        'type_seance': session.type_seance,
        'meeting_link': session.meeting_link or '',
        'theme_cours': session.theme_cours,
        'students': list(session.students.values_list('id', flat=True)),
        'notes': session.notes,
    }
    return JsonResponse(data)


@login_required
@require_POST
def api_session_create(request):
    """POST /api/sessions/create/"""
    if request.user.role not in ('admin', 'teacher'):
        return JsonResponse({'success': False, 'error': 'Non autorisé'}, status=403)
    teacher = None
    if request.user.role == 'teacher':
        teacher = request.user.teacher
    form = SessionForm(request.POST, teacher=teacher)
    if form.is_valid():
        session = form.save(commit=False)
        if request.user.role == 'teacher':
            session.teacher = teacher
        session.save()
        form.save_m2m()
        return JsonResponse({'success': True, 'session_id': session.id,
                             'event': _session_to_event(session)})
    return JsonResponse({'success': False, 'errors': form.errors}, status=400)


@login_required
@require_POST
def api_session_update(request, session_id):
    """POST /api/sessions/<id>/update/ — form data ou JSON drag-drop"""
    if request.user.role not in ('admin', 'teacher'):
        return JsonResponse({'success': False, 'error': 'Non autorisé'}, status=403)
    session = get_object_or_404(Session, pk=session_id)

    # Drag-drop JSON payload
    content_type = request.content_type or ''
    if 'application/json' in content_type:
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'JSON invalide'}, status=400)
        if 'date' in data:
            session.date = data['date']
        if 'start_time' in data:
            session.start_time = data['start_time']
        if 'end_time' in data:
            session.end_time = data['end_time']
        session.save(update_fields=['date', 'start_time', 'end_time'])
        return JsonResponse({'success': True, 'event': _session_to_event(session)})

    # Form POST
    teacher = request.user.teacher if request.user.role == 'teacher' else None
    form = SessionForm(request.POST, instance=session, teacher=teacher)
    if form.is_valid():
        form.save()
        return JsonResponse({'success': True, 'event': _session_to_event(session)})
    return JsonResponse({'success': False, 'errors': form.errors}, status=400)


@login_required
@require_POST
def api_session_delete(request, session_id):
    """POST /api/sessions/<id>/delete/"""
    if request.user.role not in ('admin', 'teacher'):
        return JsonResponse({'success': False, 'error': 'Non autorisé'}, status=403)
    session = get_object_or_404(Session, pk=session_id)
    session.delete()
    return JsonResponse({'success': True})


@login_required
@require_POST
def api_session_status(request, session_id):
    """POST /api/sessions/<id>/status/ body: {status: 'completed'}"""
    if request.user.role not in ('admin', 'teacher'):
        return JsonResponse({'success': False, 'error': 'Non autorisé'}, status=403)
    session = get_object_or_404(Session, pk=session_id)
    try:
        data = json.loads(request.body)
        new_status = data.get('status')
    except (json.JSONDecodeError, AttributeError):
        return JsonResponse({'success': False, 'error': 'JSON invalide'}, status=400)
    valid = [s[0] for s in Session.STATUS_CHOICES]
    if new_status not in valid:
        return JsonResponse({'success': False, 'error': 'Statut invalide'}, status=400)
    session.status = new_status
    session.save(update_fields=['status'])
    return JsonResponse({'success': True, 'status': new_status,
                         'event': _session_to_event(session)})


@login_required
@require_GET
def api_notifications_unread(request):
    """GET /api/notifications/unread/ — polling badge"""
    count = Notification.objects.filter(user=request.user, is_read=False).count()
    return JsonResponse({'count': count})
