from django.test import TestCase
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
