from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from dashboard.models import Student, Teacher, Session, Language, Notification, CustomUser

User = get_user_model()


def make_user(username, role, first='Test', last='User'):
    return User.objects.create_user(username=username, password='pass', role=role,
                                    first_name=first, last_name=last)


class TeacherStatsTest(TestCase):
    def setUp(self):
        self.tu = make_user('teacher1', 'teacher')
        self.teacher = Teacher.objects.get(user=self.tu)
        self.su = make_user('student1', 'student')
        self.student = Student.objects.get(user=self.su)
        self.student.current_teachers.add(self.teacher)

    def test_total_students(self):
        self.assertEqual(self.teacher.total_students, 1)


class StudentHoursTest(TestCase):
    def setUp(self):
        self.tu = make_user('teacher2', 'teacher')
        self.teacher = Teacher.objects.get(user=self.tu)
        self.su = make_user('student2', 'student')
        self.student = Student.objects.get(user=self.su)
        self.student.total_hours_purchased = 10
        self.student.save()
        lang = Language.objects.create(name='Anglais', code='en')
        self.session = Session.objects.create(
            teacher=self.teacher, language=lang,
            date='2026-05-01', start_time='10:00', end_time='11:00',
            status='completed'
        )
        self.session.students.add(self.student)

    def test_hours_used_from_sessions(self):
        self.assertAlmostEqual(self.student.computed_hours_used, 1.0, places=1)

    def test_hours_remaining(self):
        self.assertAlmostEqual(self.student.hours_remaining, 9.0, places=1)


class SessionNotificationSignalTest(TestCase):
    def setUp(self):
        self.tu = make_user('teacher3', 'teacher')
        self.teacher = Teacher.objects.get(user=self.tu)
        self.su = make_user('student3', 'student')
        self.student = Student.objects.get(user=self.su)
        lang = Language.objects.create(name='Français', code='fr')
        self.session = Session.objects.create(
            teacher=self.teacher, language=lang,
            date='2026-05-01', start_time='10:00', end_time='11:00',
            status='scheduled'
        )
        self.session.students.add(self.student)

    def test_notification_created_on_completion(self):
        self.session.status = 'completed'
        self.session.save()
        notifs = Notification.objects.filter(
            user=self.student.user,
            notification_type='evaluation_request'
        )
        self.assertEqual(notifs.count(), 1)

    def test_no_duplicate_notification(self):
        self.session.status = 'completed'
        self.session.save()
        self.session.save()  # second save — no duplicate
        notifs = Notification.objects.filter(
            user=self.student.user,
            notification_type='evaluation_request'
        )
        self.assertEqual(notifs.count(), 1)


class ReportingAccessTest(TestCase):
    def setUp(self):
        self.admin_user = make_user('admin_rep', 'admin')
        self.teacher_user = make_user('teacher_rep', 'teacher')
        self.student_user = make_user('student_rep', 'student')
        self.teacher = Teacher.objects.get(user=self.teacher_user)
        self.client = Client()

    def test_admin_reporting_list_requires_login(self):
        r = self.client.get('/administrateur/reporting/')
        self.assertEqual(r.status_code, 302)

    def test_admin_reporting_list_ok_for_admin(self):
        self.client.login(username='admin_rep', password='pass')
        r = self.client.get('/administrateur/reporting/')
        self.assertEqual(r.status_code, 200)

    def test_admin_reporting_list_blocked_for_teacher(self):
        self.client.login(username='teacher_rep', password='pass')
        r = self.client.get('/administrateur/reporting/')
        # @admin_required redirects wrong-role users to login (302)
        self.assertEqual(r.status_code, 302)

    def test_admin_reporting_detail_ok_for_admin(self):
        self.client.login(username='admin_rep', password='pass')
        r = self.client.get(f'/administrateur/reporting/{self.teacher.id}/')
        self.assertEqual(r.status_code, 200)

    def test_admin_reporting_detail_blocked_for_teacher(self):
        self.client.login(username='teacher_rep', password='pass')
        r = self.client.get(f'/administrateur/reporting/{self.teacher.id}/')
        # @admin_required redirects wrong-role users to login (302)
        self.assertEqual(r.status_code, 302)

    def test_teacher_reporting_ok_for_teacher(self):
        self.client.login(username='teacher_rep', password='pass')
        r = self.client.get('/reporting/')
        self.assertEqual(r.status_code, 200)

    def test_teacher_reporting_blocked_for_student(self):
        self.client.login(username='student_rep', password='pass')
        r = self.client.get('/reporting/')
        # @teacher_required redirects non-teachers (302)
        self.assertEqual(r.status_code, 302)


from dashboard.models import SessionSeries
from dashboard.services import generate_series_occurrences, apply_series_edit, apply_series_delete
from datetime import date, time


class SessionSeriesServiceTest(TestCase):
    def setUp(self):
        self.tu = make_user('teacher_s', 'teacher')
        self.teacher = Teacher.objects.get(user=self.tu)
        self.lang = Language.objects.create(name='Espagnol', code='es')

    def _make_series(self, start, end=None, dow=0):
        return SessionSeries.objects.create(
            teacher=self.teacher, language=self.lang,
            day_of_week=dow,
            start_time=time(10, 0), end_time=time(11, 0),
            recurrence_start=start, recurrence_end=end,
        )

    def test_generate_4_weeks(self):
        start = date(2026, 6, 1)   # lundi
        end = date(2026, 6, 22)    # 4 lundis
        series = self._make_series(start, end, dow=0)
        sessions = generate_series_occurrences(series)
        self.assertEqual(len(sessions), 4)
        for i, s in enumerate(sessions):
            self.assertEqual(s.series_index, i)
            self.assertEqual(s.date.weekday(), 0)

    def test_generate_advances_to_correct_day(self):
        # start date is Wednesday, series is Monday → first session on next Monday
        start = date(2026, 6, 3)   # mercredi
        end = date(2026, 6, 15)
        series = self._make_series(start, end, dow=0)
        sessions = generate_series_occurrences(series)
        self.assertEqual(sessions[0].date, date(2026, 6, 8))  # premier lundi

    def test_apply_delete_this(self):
        start = date(2026, 6, 1)
        end = date(2026, 6, 22)
        series = self._make_series(start, end, dow=0)
        sessions = generate_series_occurrences(series)
        apply_series_delete(sessions[1], 'this')
        from dashboard.models import Session
        self.assertEqual(Session.objects.filter(series=series).count(), 3)

    def test_apply_delete_this_and_future(self):
        start = date(2026, 6, 1)
        end = date(2026, 6, 22)
        series = self._make_series(start, end, dow=0)
        sessions = generate_series_occurrences(series)
        apply_series_delete(sessions[1], 'this_and_future')
        from dashboard.models import Session
        self.assertEqual(Session.objects.filter(series=series).count(), 1)

    def test_apply_delete_all(self):
        start = date(2026, 6, 1)
        end = date(2026, 6, 22)
        series = self._make_series(start, end, dow=0)
        sessions = generate_series_occurrences(series)
        apply_series_delete(sessions[0], 'all')
        from dashboard.models import Session
        self.assertEqual(Session.objects.filter(series=series).count(), 0)
        self.assertFalse(SessionSeries.objects.filter(pk=series.pk).exists())
