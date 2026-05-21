from django.db import migrations


def copy_student_to_students(apps, schema_editor):
    Session = apps.get_model('dashboard', 'Session')
    for session in Session.objects.select_related('student').all():
        if session.student_id:
            session.students.add(session.student_id)


def reverse_copy(apps, schema_editor):
    Session = apps.get_model('dashboard', 'Session')
    for session in Session.objects.prefetch_related('students').all():
        first = session.students.first()
        if first:
            session.student_id = first.pk
            session.save(update_fields=['student_id'])


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0003_session_add_students_m2m'),
    ]

    operations = [
        migrations.RunPython(copy_student_to_students, reverse_copy),
    ]
