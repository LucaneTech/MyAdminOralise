from datetime import timedelta
from dashboard.models import Session, SessionSeries


def generate_series_occurrences(series: SessionSeries) -> list:
    """Génère toutes les occurrences Session d'une SessionSeries."""
    from datetime import date as _date
    end = series.recurrence_end or (series.recurrence_start + timedelta(days=365))
    current = series.recurrence_start
    # Avancer jusqu'au bon jour de semaine (0=lundi, Python weekday() convention)
    days_ahead = (series.day_of_week - current.weekday()) % 7
    current = current + timedelta(days=days_ahead)

    sessions = []
    index = 0
    while current <= end:
        session = Session.objects.create(
            teacher=series.teacher,
            language=series.language,
            date=current,
            start_time=series.start_time,
            end_time=series.end_time,
            type_seance=series.type_seance,
            meeting_link=series.meeting_link or '',
            status='scheduled',
            series=series,
            series_index=index,
        )
        if series.students.exists():
            session.students.set(series.students.all())
        sessions.append(session)
        current += timedelta(weeks=1)
        index += 1
    return sessions


_SCHEDULE_FIELDS = {'start_time', 'end_time', 'teacher', 'language', 'type_seance', 'meeting_link'}


def apply_series_edit(session: Session, scope: str, cleaned_data: dict):
    """
    scope: 'this' | 'this_and_future' | 'all'
    Propagates only scheduling fields (_SCHEDULE_FIELDS), not dates or pedagogical content.
    """
    propagatable = {k: v for k, v in cleaned_data.items() if k in _SCHEDULE_FIELDS}
    students = cleaned_data.get('students')

    if scope == 'this':
        for k, v in cleaned_data.items():
            if k != 'students':
                setattr(session, k, v)
        session.save()
        if students is not None:
            session.students.set(students)

    elif scope == 'this_and_future':
        qs = Session.objects.filter(
            series=session.series,
            series_index__gte=session.series_index
        )
        qs.update(**propagatable)
        if students is not None:
            for s in qs:
                s.students.set(students)

    elif scope == 'all':
        qs = Session.objects.filter(series=session.series)
        qs.update(**propagatable)
        if students is not None:
            for s in qs:
                s.students.set(students)
        # Update the series itself
        series_obj = session.series
        for k, v in propagatable.items():
            if hasattr(series_obj, k):
                setattr(series_obj, k, v)
        series_obj.save()


def apply_series_delete(session: Session, scope: str):
    """
    scope: 'this' | 'this_and_future' | 'all'
    """
    if scope == 'this':
        session.delete()
    elif scope == 'this_and_future':
        Session.objects.filter(
            series=session.series,
            series_index__gte=session.series_index
        ).delete()
    elif scope == 'all':
        series_obj = session.series
        series_pk = series_obj.pk
        Session.objects.filter(series_id=series_pk).delete()
        SessionSeries.objects.filter(pk=series_pk).delete()
