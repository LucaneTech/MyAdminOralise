# Refonte Oralise — Plan d'Implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Supprimer Schedule, passer Session.student en M2M, créer l'API JSON calendrier, notifications polling, et migrer les 3 dashboards vers Tailwind v4 + GSAP + FullCalendar.

**Architecture:** Django 5.2 mono-app `dashboard`. API JSON dans `dashboard/api_views.py`. Migrations en 3 étapes séquentielles (add M2M → data → drop FK+Schedule). Templates Tailwind par rôle, chaque rôle avec couleur primaire fixe.

**Tech Stack:** Django 5.2, Tailwind CLI v4 + DaisyUI v5 (npm existant), GSAP 3 (CDN), FullCalendar 6 (CDN), django-lucide (pip).

---

## Fichiers créés / modifiés

| Fichier | Action |
|---|---|
| `dashboard/models.py` | Modifier — M2M students, fix propriétés, nouveau type Notification |
| `dashboard/signals.py` | Réécrire — support M2M, signal notification évaluation |
| `dashboard/forms.py` | Modifier — SessionForm/SessionAdminForm M2M, supprimer ScheduleAdminForm |
| `dashboard/admin.py` | Modifier — supprimer Schedule |
| `dashboard/api_views.py` | Créer — 8 endpoints JSON |
| `dashboard/urls.py` | Modifier — supprimer URLs Schedule, ajouter /api/ |
| `dashboard/views.py` | Modifier — supprimer vues Schedule, corriger queries session |
| `dashboard/tests.py` | Modifier — tests modèles + API |
| `dashboard/migrations/000X_*.py` | Créer — 3 migrations séquentielles |
| `SchoolManagement/settings.py` | Modifier — ajouter lucide |
| `static/assets/css/input.css` | Créer — entry point Tailwind |
| `static/assets/css/output.css` | Généré — compilé par Tailwind CLI |
| `templates/account/login.html` | Modifier — split-screen |
| `templates/dashboard/admin/layouts/base.html` | Réécrire — Tailwind |
| `templates/dashboard/admin/includes/sidenav.html` | Réécrire — Tailwind |
| `templates/dashboard/admin/includes/navigation.html` | Réécrire — Tailwind + polling |
| `templates/dashboard/admin/includes/scripts.html` | Réécrire — GSAP + utils |
| `templates/dashboard/admin/home/index.html` | Modifier — stats corrigées |
| `templates/dashboard/admin/home/sessions_list.html` | Réécrire — FullCalendar |
| `templates/dashboard/teacher/layouts/base.html` | Réécrire — Tailwind |
| `templates/dashboard/teacher/includes/sidenav.html` | Réécrire — Tailwind |
| `templates/dashboard/teacher/includes/navigation.html` | Réécrire — Tailwind + polling |
| `templates/dashboard/teacher/includes/scripts.html` | Réécrire — GSAP + utils |
| `templates/dashboard/teacher/home/index.html` | Modifier — stats corrigées |
| `templates/dashboard/teacher/home/sessions.html` | Réécrire — FullCalendar |
| `templates/dashboard/student/layouts/base.html` | Réécrire — Tailwind |
| `templates/dashboard/student/includes/sidenav.html` | Réécrire — Tailwind |
| `templates/dashboard/student/includes/navigation.html` | Réécrire — Tailwind + polling |
| `templates/dashboard/student/includes/scripts.html` | Réécrire — GSAP |
| `templates/dashboard/student/home/index.html` | Modifier — stats corrigées |
| `templates/dashboard/student/home/sessions.html` | Réécrire — FullCalendar (lecture seule) |
| `templates/dashboard/*/home/profile.html` | Réécrire — refonte profil (×3) |

**Supprimés :**
- `templates/dashboard/admin/home/schedules_list.html`
- `templates/dashboard/teacher/home/schedule.html`
- `templates/dashboard/student/home/schedule.html`
- `templates/dashboard/teacher/includes/schedule_modals.html`

---

## Task 1 : Dépendances + Tailwind build pipeline

**Files:**
- Modify: `SchoolManagement/settings.py`
- Create: `static/assets/css/input.css`

- [ ] **Installer django-lucide**

```bash
source env/bin/activate && pip install django-lucide
```

- [ ] **Ajouter lucide à INSTALLED_APPS dans `SchoolManagement/settings.py`**

Trouver la ligne `"widget_tweaks",` et ajouter après :

```python
    "widget_tweaks",
    "lucide",
```

- [ ] **Créer `static/assets/css/input.css`**

```css
@import "tailwindcss";
@plugin "daisyui";

@layer base {
  :root {
    --color-admin: #26b2bd;
    --color-teacher: #033050;
    --color-student: #d9a505;
  }
}
```

- [ ] **Compiler Tailwind (premier build)**

```bash
npx tailwindcss -i ./static/assets/css/input.css -o ./static/assets/css/output.css
```

Résultat attendu : `static/assets/css/output.css` créé (~100KB+).

- [ ] **Vérifier que Django démarre sans erreur**

```bash
source env/bin/activate && python manage.py check
```

Résultat attendu : `System check identified no issues (0 silenced).`

- [ ] **Commit**

```bash
git add SchoolManagement/settings.py static/assets/css/input.css static/assets/css/output.css
git commit -m "feat: install django-lucide, bootstrap Tailwind v4 build pipeline"
```

---

## Task 2 : Migration Phase 1 — Ajouter Session.students (M2M)

**Files:**
- Modify: `dashboard/models.py`
- Create: migration générée

**Contexte :** On garde temporairement `student (FK)` pour ne pas casser les données. On ajoute `students (M2M)` en parallèle.

- [ ] **Modifier `dashboard/models.py` — ajouter `students` M2M à `Session`**

Dans la classe `Session`, après le champ `teacher` (ligne ~507), ajouter :

```python
    students = models.ManyToManyField(
        Student,
        related_name='sessions_m2m',
        blank=True,
        verbose_name="étudiants"
    )
```

Le champ `student` (FK) reste intact pour l'instant.

- [ ] **Générer la migration**

```bash
source env/bin/activate && python manage.py makemigrations dashboard --name="session_add_students_m2m"
```

Résultat attendu : `dashboard/migrations/0003_session_add_students_m2m.py` créé.

- [ ] **Appliquer la migration**

```bash
python manage.py migrate
```

Résultat attendu : `OK`.

- [ ] **Commit**

```bash
git add dashboard/models.py dashboard/migrations/0003_session_add_students_m2m.py
git commit -m "feat: add Session.students ManyToManyField (phase 1/3)"
```

---

## Task 3 : Migration Phase 2 — Copier FK → M2M

**Files:**
- Create: `dashboard/migrations/0004_session_migrate_student_to_students.py`

- [ ] **Créer la migration de données**

```bash
source env/bin/activate && python manage.py makemigrations dashboard --empty --name="session_migrate_student_to_students"
```

- [ ] **Écrire le contenu de la migration**

Ouvrir le fichier `dashboard/migrations/0004_session_migrate_student_to_students.py` et le remplacer par :

```python
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
```

- [ ] **Appliquer la migration**

```bash
python manage.py migrate
```

Résultat attendu : `OK`.

- [ ] **Vérifier en shell que les données sont copiées**

```bash
python manage.py shell -c "
from dashboard.models import Session
s = Session.objects.first()
if s:
    print('student FK:', s.student_id)
    print('students M2M:', list(s.students.values_list('id', flat=True)))
else:
    print('Aucune session existante — OK')
"
```

Résultat attendu : les IDs correspondent ou `Aucune session`.

- [ ] **Commit**

```bash
git add dashboard/migrations/0004_session_migrate_student_to_students.py
git commit -m "feat: data migration — copy Session.student FK to Session.students M2M"
```

---

## Task 4 : Migration Phase 3 — Supprimer FK student + modèle Schedule

**Files:**
- Modify: `dashboard/models.py`
- Create: migration générée

- [ ] **Modifier `dashboard/models.py`**

**4a. Supprimer le champ `student` (FK) de `Session`** — retirer ces lignes :

```python
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name='sessions',
        verbose_name="étudiant"
    )
```

**4b. Changer `related_name` de `students` M2M** — remplacer `sessions_m2m` par `sessions` :

```python
    students = models.ManyToManyField(
        Student,
        related_name='sessions',
        blank=True,
        verbose_name="étudiants"
    )
```

**4c. Supprimer la classe `Schedule` entière** (lignes ~296-364) — retirer tout le bloc :

```python
# Emploi du temps
class Schedule(models.Model): 
    ...
    def __str__(self):
        return f"{self.language.name} - {self.day} ({self.start_time} - {self.end_time})"
```

**4d. Mettre à jour les propriétés `Student` qui référencent `Session`**

Remplacer `Session.objects.filter(student=self` par `Session.objects.filter(students=self` dans `recent_sessions` et `upcoming_sessions` :

```python
    @property
    def recent_sessions(self):
        return Session.objects.filter(students=self).order_by('-date')[:5]

    @property
    def upcoming_sessions(self):
        today = timezone.now().date()
        return Session.objects.filter(
            students=self,
            date__gte=today,
            status='scheduled'
        ).order_by('date', 'start_time')
```

- [ ] **Générer la migration**

```bash
source env/bin/activate && python manage.py makemigrations dashboard --name="remove_schedule_remove_session_student_fk"
```

- [ ] **Appliquer**

```bash
python manage.py migrate
```

- [ ] **Vérifier**

```bash
python manage.py check
```

Résultat attendu : `0 issues`.

- [ ] **Commit**

```bash
git add dashboard/models.py dashboard/migrations/0005_remove_schedule_remove_session_student_fk.py
git commit -m "feat: remove Schedule model, remove Session.student FK (phase 3/3)"
```

---

## Task 5 : Corriger models.py — propriétés stats + type Notification

**Files:**
- Modify: `dashboard/models.py`

- [ ] **Écrire le test qui vérifie les propriétés (TDD)**

Dans `dashboard/tests.py` :

```python
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
        self.assertAlmostEqual(self.student.total_hours_used, 1.0, places=1)

    def test_hours_remaining(self):
        self.assertAlmostEqual(self.student.hours_remaining, 9.0, places=1)
```

- [ ] **Lancer les tests pour vérifier qu'ils échouent**

```bash
source env/bin/activate && python manage.py test dashboard.tests.TeacherStatsTest dashboard.tests.StudentHoursTest -v 2
```

Résultat attendu : FAIL (propriétés pas encore corrigées).

- [ ] **Corriger `Teacher.total_students` dans `dashboard/models.py`**

Remplacer :

```python
    @property
    def total_students(self):
        return Student.objects.filter(current_teacher=self).count()
```

Par :

```python
    @property
    def total_students(self):
        return Student.objects.filter(current_teachers=self).count()
```

- [ ] **Corriger `Student.total_hours_used` — le rendre dynamique**

Remplacer les propriétés `total_hours_used` et `hours_remaining` dans `Student`. Elles n'existent pas comme `@property` actuellement (c'est un IntegerField). Ajouter APRÈS le champ `objectif_formation` dans `Student` :

```python
    @property
    def total_hours_used(self):
        sessions = Session.objects.filter(students=self, status='completed')
        return round(sum(s.duration_hours for s in sessions), 1)

    @property
    def hours_remaining(self):
        return self.total_hours_purchased - self.total_hours_used
```

Et supprimer (ou conserver comme champ de référence) le champ DB `total_hours_used = models.IntegerField(...)` — **le renommer** `total_hours_used_legacy` pour ne pas casser la migration :

En réalité, garder le champ DB `total_hours_used` risque de conflitter avec la propriété. Renommer le champ DB en `_total_hours_used_db` et utiliser `hours_remaining` via la propriété. 

**Alternative plus simple (retenue)** : Garder le champ DB `total_hours_used` comme `IntegerField` mais ajouter une propriété `computed_hours_used` distincte. La propriété `hours_remaining` utilise la propriété calculée.

Remplacer dans `Student` :

```python
    @property
    def hours_remaining(self):
        return self.total_hours_purchased - self.total_hours_used
```

Par :

```python
    @property
    def computed_hours_used(self):
        sessions = Session.objects.filter(students=self, status='completed')
        return round(sum(s.duration_hours for s in sessions), 1)

    @property
    def hours_remaining(self):
        return self.total_hours_purchased - self.computed_hours_used
```

Et dans les tests remplacer `self.student.total_hours_used` par `self.student.computed_hours_used`.

- [ ] **Ajouter `evaluation_request` dans `Notification.NOTIFICATION_TYPES`**

Dans `Notification`, remplacer :

```python
    NOTIFICATION_TYPES = [
        ('session_reminder', 'Rappel de séance'),
        ('payment_due', 'Paiement dû'),
        ('certificate_ready', 'Certificat disponible'),
        ('evaluation_ready', 'Évaluation disponible'),
        ('system', 'Système')
    ]
```

Par :

```python
    NOTIFICATION_TYPES = [
        ('session_reminder', 'Rappel de séance'),
        ('payment_due', 'Paiement dû'),
        ('certificate_ready', 'Certificat disponible'),
        ('evaluation_ready', 'Évaluation disponible'),
        ('evaluation_request', 'Demande d\'évaluation'),
        ('system', 'Système')
    ]
```

- [ ] **Générer la migration pour le nouveau choice**

```bash
python manage.py makemigrations dashboard --name="notification_add_evaluation_request_type"
python manage.py migrate
```

- [ ] **Relancer les tests**

```bash
python manage.py test dashboard.tests.TeacherStatsTest dashboard.tests.StudentHoursTest -v 2
```

Résultat attendu : PASS (2 tests).

- [ ] **Commit**

```bash
git add dashboard/models.py dashboard/tests.py dashboard/migrations/
git commit -m "fix: correct Teacher.total_students, Student.computed_hours_used, add evaluation_request notification type"
```

---

## Task 6 : Réécrire signals.py

**Files:**
- Modify: `dashboard/signals.py`

- [ ] **Écrire le test du signal notification**

Dans `dashboard/tests.py`, ajouter :

```python
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
```

- [ ] **Lancer pour vérifier FAIL**

```bash
python manage.py test dashboard.tests.SessionNotificationSignalTest -v 2
```

- [ ] **Réécrire `dashboard/signals.py`**

```python
from django.db.models.signals import post_save, pre_save, post_delete
from django.dispatch import receiver
import logging
from django.db.models import Sum
from .models import CustomUser, Student, Teacher, Session, Payment, Notification

logger = logging.getLogger(__name__)


@receiver(post_save, sender=CustomUser)
def sync_user_role(sender, instance, **kwargs):
    try:
        if instance.role == 'student':
            Student.objects.get_or_create(user=instance)
        elif instance.role == 'teacher':
            Teacher.objects.get_or_create(user=instance)
        elif instance.role == 'admin':
            CustomUser.objects.filter(pk=instance.pk).update(
                is_staff=True, is_superuser=True
            )
    except Exception as e:
        logger.error(f"Error syncing role for {instance.username}: {e}", exc_info=True)


@receiver(pre_save, sender=Session)
def store_old_session_status(sender, instance, **kwargs):
    if instance.pk:
        instance._old_status = Session.objects.filter(
            pk=instance.pk
        ).values_list('status', flat=True).first()
    else:
        instance._old_status = None


@receiver(post_save, sender=Session)
def handle_session_completed(sender, instance, **kwargs):
    if instance._old_status != 'completed' and instance.status == 'completed':
        # Notifier chaque étudiant de la session
        for student in instance.students.select_related('user').all():
            already_notified = Notification.objects.filter(
                user=student.user,
                notification_type='evaluation_request',
                message__contains=f"Session {instance.id}"
            ).exists()
            if not already_notified:
                Notification.objects.create(
                    user=student.user,
                    notification_type='evaluation_request',
                    title="Votre cours est terminé — donnez votre avis",
                    message=(
                        f"Votre séance de {instance.language} avec "
                        f"{instance.teacher} du {instance.date} est terminée. "
                        f"Session {instance.id} — Cliquez pour évaluer."
                    ),
                )
            logger.info(f"Notification évaluation créée pour {student} (Session {instance.id})")


@receiver(post_save, sender=Payment)
def update_student_hours_on_payment(sender, instance, created, **kwargs):
    if instance.status == 'paid':
        student = instance.student
        total_purchased = Payment.objects.filter(
            student=student, status='paid'
        ).aggregate(total=Sum('hours_purchased'))['total'] or 0
        student.total_hours_purchased = total_purchased
        student.save(update_fields=['total_hours_purchased'])


@receiver(post_delete, sender=Payment)
def update_student_hours_on_payment_delete(sender, instance, **kwargs):
    if instance.status == 'paid':
        student = instance.student
        total_purchased = Payment.objects.filter(
            student=student, status='paid'
        ).aggregate(total=Sum('hours_purchased'))['total'] or 0
        student.total_hours_purchased = total_purchased
        student.save(update_fields=['total_hours_purchased'])
```

- [ ] **Lancer tous les tests**

```bash
python manage.py test dashboard -v 2
```

Résultat attendu : tous PASS.

- [ ] **Commit**

```bash
git add dashboard/signals.py dashboard/tests.py
git commit -m "feat: rewrite signals — Session M2M notification on completion, dedup guard"
```

---

## Task 7 : Mettre à jour forms.py

**Files:**
- Modify: `dashboard/forms.py`

- [ ] **Supprimer `ScheduleAdminForm`** — retirer le bloc entier (classe et son Meta).

- [ ] **Remplacer `SessionForm`** — changer `student` FK par `students` M2M :

```python
class SessionForm(forms.ModelForm):
    class Meta:
        model = Session
        fields = ['students', 'language', 'date', 'start_time', 'end_time',
                  'type_seance', 'status', 'meeting_link']
        widgets = {
            'students': forms.SelectMultiple(attrs={'class': 'form-control', 'size': '5'}),
            'language': forms.Select(attrs={'class': 'form-control'}),
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'start_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'end_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'type_seance': forms.Select(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'meeting_link': forms.URLInput(attrs={'class': 'form-control',
                                                   'placeholder': 'https://meet.google.com/...'}),
        }

    def __init__(self, *args, **kwargs):
        self.teacher = kwargs.pop('teacher', None)
        super().__init__(*args, **kwargs)
        if self.teacher:
            self.fields['language'].queryset = self.teacher.languages.all()
            self.fields['students'].queryset = Student.objects.filter(
                current_teachers=self.teacher
            )
        else:
            self.fields['students'].queryset = Student.objects.all()
```

- [ ] **Remplacer `SessionAdminForm`** — changer `student` par `students` :

Dans `SessionAdminForm.Meta.fields`, remplacer `'student'` par `'students'`.
Dans `SessionAdminForm.Meta.widgets`, remplacer :

```python
            'student': forms.Select(attrs=W),
```

Par :

```python
            'students': forms.SelectMultiple(attrs=W),
```

- [ ] **Supprimer `Schedule` de l'import** en haut du fichier :

Remplacer :

```python
from dashboard.models import (
    Profile, CustomUser, Resource, Session, Student, Language,
    Certificate, PaiementFormateur, Teacher, Schedule, Payment,
    Evaluation, Request, Notification, Assignment, Comment,
)
```

Par :

```python
from dashboard.models import (
    Profile, CustomUser, Resource, Session, Student, Language,
    Certificate, PaiementFormateur, Teacher, Payment,
    Evaluation, Request, Notification, Assignment, Comment,
)
```

- [ ] **Vérifier**

```bash
source env/bin/activate && python manage.py check
```

Résultat attendu : `0 issues`.

- [ ] **Commit**

```bash
git add dashboard/forms.py
git commit -m "feat: update SessionForm/SessionAdminForm to M2M students, remove ScheduleAdminForm"
```

---

## Task 8 : Créer dashboard/api_views.py

**Files:**
- Create: `dashboard/api_views.py`

```python
import json
from datetime import datetime, date
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
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
```

- [ ] **Vérifier syntaxe**

```bash
source env/bin/activate && python -c "import dashboard.api_views; print('OK')"
```

- [ ] **Commit**

```bash
git add dashboard/api_views.py
git commit -m "feat: create api_views.py — 7 session endpoints + notification unread count"
```

---

## Task 9 : Mettre à jour urls.py + nettoyer views.py

**Files:**
- Modify: `dashboard/urls.py`
- Modify: `dashboard/views.py`
- Modify: `dashboard/admin.py`

- [ ] **Mettre à jour `dashboard/urls.py`**

Remplacer tout le fichier par :

```python
from django.urls import path
from .views import (
    admin_dashboard, admin_student_view, admin_teacher_view,
    delete_notification, notifications_mark_all_read,
    profile_view, dashboard_view, profile_edit,
    requests_view, settings_view, student_detail_view,
    teacher_detail_view, teacher_view, teacher_courses,
    teacher_assignments, teacher_students,
    api_filter_students, api_filter_assignments,
    session_detail_view, session_status_update, certificates_view,
    evaluations_view, notifications_view, payments_view,
    teacher_sessions_view, student_sessions_view,
    teacher_evaluations_add, evaluation_edit,
    export_students_csv, teacher_student_detail,
    update_request_status, add_request_response,
    resource_create, resource_delete, resource_edit, resources_view,
    teacher_resources_dashboard,
    fiche_pedagogique_edit, fiche_pedagogique_detail,
    admin_sessions_list, admin_valider_session,
    reporting_formateur, paiements_formateurs_list,
    paiement_formateur_create, paiement_formateur_edit, paiement_formateur_delete,
    mes_paiements_formateur,
    admin_certificate_create, admin_certificate_edit, admin_certificates_list,
    certificate_public_view, certificate_detail_student,
    admin_users_list, admin_user_create, admin_user_edit,
    admin_user_reset_password, admin_user_toggle_active, admin_user_delete,
    admin_student_create, admin_student_edit, admin_student_delete,
    admin_teacher_create, admin_teacher_edit, admin_teacher_delete,
    admin_languages_list, admin_language_create, admin_language_edit, admin_language_delete,
    admin_session_create, admin_session_edit, admin_session_delete,
    admin_payments_list, admin_payment_create, admin_payment_edit, admin_payment_delete,
    admin_evaluations_list, admin_evaluation_create, admin_evaluation_edit, admin_evaluation_delete,
    admin_resources_list, admin_resource_create, admin_resource_edit, admin_resource_delete,
    admin_requests_list, admin_request_detail, admin_request_delete,
    admin_notifications_list, admin_notification_create, admin_notification_delete,
    admin_assignments_list, admin_assignment_create, admin_assignment_edit, admin_assignment_delete,
    admin_comments_list, admin_comment_delete,
)
from . import api_views

urlpatterns = [
    # ── API JSON ──────────────────────────────────────────────────
    path('api/sessions/', api_views.api_sessions_feed, name='api_sessions_feed'),
    path('api/sessions/create/', api_views.api_session_create, name='api_session_create'),
    path('api/sessions/<int:session_id>/', api_views.api_session_detail, name='api_session_detail'),
    path('api/sessions/<int:session_id>/update/', api_views.api_session_update, name='api_session_update'),
    path('api/sessions/<int:session_id>/delete/', api_views.api_session_delete, name='api_session_delete'),
    path('api/sessions/<int:session_id>/status/', api_views.api_session_status, name='api_session_status'),
    path('api/notifications/unread/', api_views.api_notifications_unread, name='api_notifications_unread'),

    # ── Teacher ───────────────────────────────────────────────────
    path('teacher/courses/', teacher_courses, name='teacher_courses'),
    path('teacher/assignments/', teacher_assignments, name='teacher_assignments'),
    path('teacher/students/', teacher_students, name='teacher_students'),
    path('teacher/students/<int:student_id>/', teacher_student_detail, name='teacher_student_detail'),
    path('teacher/export-students/', export_students_csv, name='export_students'),
    path('teacher/resources/', teacher_resources_dashboard, name='teacher_resources_dashboard'),
    path('teacher/sessions/', teacher_sessions_view, name='teacher_sessions'),
    path('teacher/evaluations/add/', teacher_evaluations_add, name='teacher_evaluations_add'),
    path('teacher/evaluations/<int:evaluation_id>/edit/', evaluation_edit, name='evaluation_edit'),
    path('teacher/mes-paiements/', mes_paiements_formateur, name='mes_paiements_formateur'),
    path('teacher/<str:username>/', teacher_view, name='teacher_view'),

    # ── Ressources ────────────────────────────────────────────────
    path('ressources/create/', resource_create, name='resource_create'),
    path('ressources/<int:resource_id>/update/', resource_edit, name='resource_edit'),
    path('ressources/<int:resource_id>/delete/', resource_delete, name='resource_delete'),

    # ── Communes ──────────────────────────────────────────────────
    path('profile/view/', profile_view, name='profile_view'),
    path('profile/edit/', profile_edit, name='profile_edit'),
    path('settings/', settings_view, name='settings_view'),
    path('resources/', resources_view, name='resources_view'),
    path('requests/', requests_view, name='requests_view'),
    path('requests/update-status/', update_request_status, name='update_request_status'),
    path('requests/add-response/', add_request_response, name='add_request_response'),
    path('session/<int:session_id>/', session_detail_view, name='session_detail'),
    path('session/<int:session_id>/status/', session_status_update, name='session_status_update'),
    path('session/<int:session_id>/fiche/', fiche_pedagogique_edit, name='fiche_pedagogique_edit'),
    path('session/<int:session_id>/fiche/detail/', fiche_pedagogique_detail, name='fiche_pedagogique_detail'),
    path('certificates/', certificates_view, name='certificates_view'),
    path('evaluations/', evaluations_view, name='evaluations_view'),
    path('notifications/', notifications_view, name='notifications_view'),
    path('notifications/mark-read/', notifications_mark_all_read, name='notifications_mark_all_read'),
    path('notifications/delete/', delete_notification, name='delete_notification'),
    path('payments/', payments_view, name='payments_view'),
    path('sessions/', student_sessions_view, name='student_sessions'),

    # ── Étudiant ──────────────────────────────────────────────────
    path('student/<str:username>/', dashboard_view, name='dashboard_view'),

    # ── API endpoints legacy ───────────────────────────────────────
    path('api/filter-students/', api_filter_students, name='api_filter_students'),
    path('api/filter-assignments/', api_filter_assignments, name='api_filter_assignments'),

    # ── Redirection ────────────────────────────────────────────────
    path('', dashboard_view, name='dashboard_home'),

    # ── Admin ─────────────────────────────────────────────────────
    path('administrateur/', admin_dashboard, name='admin_dashboard'),
    path('administrateur/teachers/', admin_teacher_view, name='admin_teachers'),
    path('administrateur/teachers/<int:teacher_id>/', teacher_detail_view, name='teacher_detail'),
    path('administrateur/students/', admin_student_view, name='admin_students'),
    path('administrateur/students/<int:student_id>/', student_detail_view, name='student_detail'),
    path('administrateur/seances/', admin_sessions_list, name='admin_sessions_list'),
    path('administrateur/seances/<int:session_id>/valider/', admin_valider_session, name='admin_valider_session'),
    path('administrateur/seances/creer/', admin_session_create, name='admin_session_create'),
    path('administrateur/seances/<int:session_id>/modifier/', admin_session_edit, name='admin_session_edit'),
    path('administrateur/seances/<int:session_id>/supprimer/', admin_session_delete, name='admin_session_delete'),
    path('reporting/', reporting_formateur, name='reporting_formateur'),
    path('administrateur/reporting/<int:teacher_id>/', reporting_formateur, name='admin_reporting_formateur'),
    path('administrateur/paiements-formateurs/', paiements_formateurs_list, name='paiements_formateurs_list'),
    path('administrateur/paiements-formateurs/creer/', paiement_formateur_create, name='paiement_formateur_create'),
    path('administrateur/paiements-formateurs/<int:paiement_id>/modifier/', paiement_formateur_edit, name='paiement_formateur_edit'),
    path('administrateur/paiements-formateurs/<int:paiement_id>/supprimer/', paiement_formateur_delete, name='paiement_formateur_delete'),
    path('administrateur/certificats/', admin_certificates_list, name='admin_certificates_list'),
    path('administrateur/certificats/ajouter/', admin_certificate_create, name='admin_certificate_create'),
    path('administrateur/certificats/<int:cert_id>/modifier/', admin_certificate_edit, name='admin_certificate_edit'),
    path('certificats/<int:cert_id>/detail/', certificate_detail_student, name='certificate_detail_student'),
    path('certificat/<str:certificate_id>/', certificate_public_view, name='certificate_public_view'),
    path('administrateur/utilisateurs/', admin_users_list, name='admin_users_list'),
    path('administrateur/utilisateurs/creer/', admin_user_create, name='admin_user_create'),
    path('administrateur/utilisateurs/<int:user_id>/modifier/', admin_user_edit, name='admin_user_edit'),
    path('administrateur/utilisateurs/<int:user_id>/mdp/', admin_user_reset_password, name='admin_user_reset_password'),
    path('administrateur/utilisateurs/<int:user_id>/activer/', admin_user_toggle_active, name='admin_user_toggle_active'),
    path('administrateur/utilisateurs/<int:user_id>/supprimer/', admin_user_delete, name='admin_user_delete'),
    path('administrateur/students/creer/', admin_student_create, name='admin_student_create'),
    path('administrateur/students/<int:student_id>/modifier/', admin_student_edit, name='admin_student_edit'),
    path('administrateur/students/<int:student_id>/supprimer/', admin_student_delete, name='admin_student_delete'),
    path('administrateur/teachers/creer/', admin_teacher_create, name='admin_teacher_create'),
    path('administrateur/teachers/<int:teacher_id>/modifier/', admin_teacher_edit, name='admin_teacher_edit'),
    path('administrateur/teachers/<int:teacher_id>/supprimer/', admin_teacher_delete, name='admin_teacher_delete'),
    path('administrateur/langues/', admin_languages_list, name='admin_languages_list'),
    path('administrateur/langues/creer/', admin_language_create, name='admin_language_create'),
    path('administrateur/langues/<int:lang_id>/modifier/', admin_language_edit, name='admin_language_edit'),
    path('administrateur/langues/<int:lang_id>/supprimer/', admin_language_delete, name='admin_language_delete'),
    path('administrateur/paiements/', admin_payments_list, name='admin_payments_list'),
    path('administrateur/paiements/creer/', admin_payment_create, name='admin_payment_create'),
    path('administrateur/paiements/<int:payment_id>/modifier/', admin_payment_edit, name='admin_payment_edit'),
    path('administrateur/paiements/<int:payment_id>/supprimer/', admin_payment_delete, name='admin_payment_delete'),
    path('administrateur/evaluations/', admin_evaluations_list, name='admin_evaluations_list'),
    path('administrateur/evaluations/creer/', admin_evaluation_create, name='admin_evaluation_create'),
    path('administrateur/evaluations/<int:eval_id>/modifier/', admin_evaluation_edit, name='admin_evaluation_edit'),
    path('administrateur/evaluations/<int:eval_id>/supprimer/', admin_evaluation_delete, name='admin_evaluation_delete'),
    path('administrateur/ressources/', admin_resources_list, name='admin_resources_list'),
    path('administrateur/ressources/creer/', admin_resource_create, name='admin_resource_create'),
    path('administrateur/ressources/<int:resource_id>/modifier/', admin_resource_edit, name='admin_resource_edit'),
    path('administrateur/ressources/<int:resource_id>/supprimer/', admin_resource_delete, name='admin_resource_delete'),
    path('administrateur/demandes/', admin_requests_list, name='admin_requests_list'),
    path('administrateur/demandes/<int:req_id>/', admin_request_detail, name='admin_request_detail'),
    path('administrateur/demandes/<int:req_id>/supprimer/', admin_request_delete, name='admin_request_delete'),
    path('administrateur/notifications/', admin_notifications_list, name='admin_notifications_list'),
    path('administrateur/notifications/creer/', admin_notification_create, name='admin_notification_create'),
    path('administrateur/notifications/<int:notif_id>/supprimer/', admin_notification_delete, name='admin_notification_delete'),
    path('administrateur/devoirs/', admin_assignments_list, name='admin_assignments_list'),
    path('administrateur/devoirs/creer/', admin_assignment_create, name='admin_assignment_create'),
    path('administrateur/devoirs/<int:assign_id>/modifier/', admin_assignment_edit, name='admin_assignment_edit'),
    path('administrateur/devoirs/<int:assign_id>/supprimer/', admin_assignment_delete, name='admin_assignment_delete'),
    path('administrateur/commentaires/', admin_comments_list, name='admin_comments_list'),
    path('administrateur/commentaires/<int:comment_id>/supprimer/', admin_comment_delete, name='admin_comment_delete'),
]
```

- [ ] **Nettoyer views.py — supprimer toutes les vues Schedule**

Dans `dashboard/views.py`, supprimer les fonctions : `add_schedule`, `edit_schedule`, `delete_schedule`, `load_schedule_week`, `filter_schedule`, `quick_add_schedule`, `schedule_view`, `teacher_schedule_view`, `admin_schedules_list`, `admin_schedule_create`, `admin_schedule_edit`, `admin_schedule_delete`.

Supprimer l'import de `Schedule` :

```python
from dashboard.models import (
    # ... retirer Schedule de cette liste
)
```

- [ ] **Corriger dans views.py toutes les références à `session.student` (FK supprimé)**

Faire une recherche globale dans `views.py` de `.student` lié à Session et remplacer par `.students`. Exemples critiques :

```python
# Rechercher et remplacer les patterns :
# session.student  →  session.students.first()   (pour récupérer un seul)
# filter(student=  →  filter(students=
# instance.student →  instance.students.first()
```

- [ ] **Mettre à jour admin.py — supprimer Schedule**

Dans `dashboard/admin.py`, supprimer `admin.site.register(Schedule, ...)` et tout import de Schedule.

- [ ] **Vérifier**

```bash
python manage.py check && python manage.py test dashboard -v 2
```

Résultat attendu : `0 issues`, tous tests PASS.

- [ ] **Supprimer les templates Schedule**

```bash
rm templates/dashboard/admin/home/schedules_list.html
rm templates/dashboard/teacher/home/schedule.html
rm templates/dashboard/student/home/schedule.html
rm templates/dashboard/teacher/includes/schedule_modals.html
```

- [ ] **Commit**

```bash
git add -A
git commit -m "feat: remove Schedule views/URLs/templates, fix all Session student→students refs"
```

---

## Task 10 : Base template Admin (Tailwind)

**Files:**
- Modify: `templates/dashboard/admin/layouts/base.html`
- Modify: `templates/dashboard/admin/includes/sidenav.html`
- Modify: `templates/dashboard/admin/includes/navigation.html`
- Modify: `templates/dashboard/admin/includes/scripts.html`

- [ ] **Écrire `templates/dashboard/admin/layouts/base.html`**

```html
{% load static %}
{% load lucide %}
<!DOCTYPE html>
<html lang="fr" class="h-full">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Oralise Admin | {% block title %}{% endblock %}</title>
  <link rel="icon" href="{% static 'assets/img/icons/favicon.png' %}">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="{% static 'assets/css/output.css' %}">
  {% block extra_css %}{% endblock %}
</head>
<body class="h-full bg-gray-50 font-['Inter'] antialiased">

  <div class="flex h-full">
    {% include "dashboard/admin/includes/sidenav.html" %}

    <div class="flex-1 flex flex-col min-h-screen ml-64">
      {% include "dashboard/admin/includes/navigation.html" %}

      <main class="flex-1 p-6">
        {% if messages %}
          {% for message in messages %}
            <div class="mb-4 px-4 py-3 rounded-md text-sm font-medium
              {% if message.tags == 'error' %}bg-red-50 text-red-700 border border-red-200
              {% elif message.tags == 'success' %}bg-green-50 text-green-700 border border-green-200
              {% else %}bg-blue-50 text-blue-700 border border-blue-200{% endif %}">
              {{ message }}
            </div>
          {% endfor %}
        {% endif %}
        {% block content %}{% endblock %}
      </main>
    </div>
  </div>

  <!-- Modal overlay -->
  <div id="modal-backdrop" class="fixed inset-0 bg-black/50 z-50 hidden items-center justify-center p-4">
    <div id="modal-panel" class="bg-white rounded-md shadow-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
      <div id="modal-content" class="p-6"></div>
    </div>
  </div>

  <!-- GSAP -->
  <script src="https://cdn.jsdelivr.net/npm/gsap@3.12.5/dist/gsap.min.js"></script>
  {% include "dashboard/admin/includes/scripts.html" %}
  {% block extra_js %}{% endblock %}
</body>
</html>
```

- [ ] **Écrire `templates/dashboard/admin/includes/sidenav.html`**

```html
{% load static %}
{% load lucide %}
<aside class="fixed top-0 left-0 h-screen w-64 bg-[#26b2bd] text-white flex flex-col z-40 shadow-xl">
  <!-- Logo -->
  <div class="flex items-center gap-3 px-6 py-5 border-b border-white/20">
    <img src="{% static 'assets/img/icons/favicon.png' %}" alt="Oralise" class="w-8 h-8">
    <span class="text-lg font-semibold tracking-wide">Oralise</span>
  </div>

  <!-- Nav -->
  <nav class="flex-1 overflow-y-auto py-4 px-3 space-y-1">
    <a href="{% url 'admin_dashboard' %}"
       class="flex items-center gap-3 px-3 py-2.5 rounded-md text-sm font-medium transition-colors hover:bg-white/15 {% if request.resolver_match.url_name == 'admin_dashboard' %}bg-white/20{% endif %}">
      {% lucide "layout-dashboard" class="w-4 h-4 shrink-0" %} Tableau de bord
    </a>
    <a href="{% url 'admin_sessions_list' %}"
       class="flex items-center gap-3 px-3 py-2.5 rounded-md text-sm font-medium transition-colors hover:bg-white/15 {% if 'seances' in request.path %}bg-white/20{% endif %}">
      {% lucide "calendar" class="w-4 h-4 shrink-0" %} Séances
    </a>
    <a href="{% url 'admin_students' %}"
       class="flex items-center gap-3 px-3 py-2.5 rounded-md text-sm font-medium transition-colors hover:bg-white/15 {% if 'students' in request.path %}bg-white/20{% endif %}">
      {% lucide "graduation-cap" class="w-4 h-4 shrink-0" %} Étudiants
    </a>
    <a href="{% url 'admin_teachers' %}"
       class="flex items-center gap-3 px-3 py-2.5 rounded-md text-sm font-medium transition-colors hover:bg-white/15 {% if 'teachers' in request.path %}bg-white/20{% endif %}">
      {% lucide "users" class="w-4 h-4 shrink-0" %} Formateurs
    </a>
    <a href="{% url 'admin_payments_list' %}"
       class="flex items-center gap-3 px-3 py-2.5 rounded-md text-sm font-medium transition-colors hover:bg-white/15 {% if 'paiements' in request.path %}bg-white/20{% endif %}">
      {% lucide "credit-card" class="w-4 h-4 shrink-0" %} Paiements
    </a>
    <a href="{% url 'admin_certificates_list' %}"
       class="flex items-center gap-3 px-3 py-2.5 rounded-md text-sm font-medium transition-colors hover:bg-white/15 {% if 'certificats' in request.path %}bg-white/20{% endif %}">
      {% lucide "award" class="w-4 h-4 shrink-0" %} Certificats
    </a>
    <a href="{% url 'admin_evaluations_list' %}"
       class="flex items-center gap-3 px-3 py-2.5 rounded-md text-sm font-medium transition-colors hover:bg-white/15 {% if 'evaluations' in request.path %}bg-white/20{% endif %}">
      {% lucide "bar-chart-2" class="w-4 h-4 shrink-0" %} Évaluations
    </a>
    <a href="{% url 'admin_languages_list' %}"
       class="flex items-center gap-3 px-3 py-2.5 rounded-md text-sm font-medium transition-colors hover:bg-white/15 {% if 'langues' in request.path %}bg-white/20{% endif %}">
      {% lucide "globe" class="w-4 h-4 shrink-0" %} Langues
    </a>
    <a href="{% url 'admin_resources_list' %}"
       class="flex items-center gap-3 px-3 py-2.5 rounded-md text-sm font-medium transition-colors hover:bg-white/15 {% if 'ressources' in request.path %}bg-white/20{% endif %}">
      {% lucide "folder-open" class="w-4 h-4 shrink-0" %} Ressources
    </a>
    <a href="{% url 'admin_requests_list' %}"
       class="flex items-center gap-3 px-3 py-2.5 rounded-md text-sm font-medium transition-colors hover:bg-white/15 {% if 'demandes' in request.path %}bg-white/20{% endif %}">
      {% lucide "mail" class="w-4 h-4 shrink-0" %} Demandes
    </a>
    <a href="{% url 'admin_users_list' %}"
       class="flex items-center gap-3 px-3 py-2.5 rounded-md text-sm font-medium transition-colors hover:bg-white/15 {% if 'utilisateurs' in request.path %}bg-white/20{% endif %}">
      {% lucide "user-cog" class="w-4 h-4 shrink-0" %} Utilisateurs
    </a>
    <a href="{% url 'paiements_formateurs_list' %}"
       class="flex items-center gap-3 px-3 py-2.5 rounded-md text-sm font-medium transition-colors hover:bg-white/15 {% if 'paiements-formateurs' in request.path %}bg-white/20{% endif %}">
      {% lucide "banknote" class="w-4 h-4 shrink-0" %} Paiements formateurs
    </a>
    <a href="{% url 'admin_assignments_list' %}"
       class="flex items-center gap-3 px-3 py-2.5 rounded-md text-sm font-medium transition-colors hover:bg-white/15 {% if 'devoirs' in request.path %}bg-white/20{% endif %}">
      {% lucide "book-open" class="w-4 h-4 shrink-0" %} Devoirs
    </a>
    <a href="{% url 'reporting_formateur' %}"
       class="flex items-center gap-3 px-3 py-2.5 rounded-md text-sm font-medium transition-colors hover:bg-white/15 {% if 'reporting' in request.path %}bg-white/20{% endif %}">
      {% lucide "trending-up" class="w-4 h-4 shrink-0" %} Reporting
    </a>
  </nav>

  <!-- User -->
  <div class="border-t border-white/20 px-4 py-4">
    <div class="flex items-center gap-3">
      <img src="{{ request.user.profile_picture_url }}" alt="avatar" class="w-8 h-8 rounded-md object-cover">
      <div class="flex-1 min-w-0">
        <p class="text-sm font-medium truncate">{{ request.user.get_full_name|default:request.user.username }}</p>
        <p class="text-xs text-white/60 truncate">Admin</p>
      </div>
      <a href="{% url 'account_logout' %}" title="Déconnexion">
        {% lucide "log-out" class="w-4 h-4 text-white/70 hover:text-white" %}
      </a>
    </div>
  </div>
</aside>
```

- [ ] **Écrire `templates/dashboard/admin/includes/navigation.html`**

```html
{% load static %}
{% load lucide %}
<header class="sticky top-0 z-30 bg-white border-b border-gray-100 shadow-sm">
  <div class="flex items-center justify-between px-6 py-3">
    <h1 class="text-base font-semibold text-gray-700">{% block page_title %}Dashboard{% endblock %}</h1>

    <div class="flex items-center gap-4">
      <!-- Notifications -->
      <div class="relative">
        <button id="notif-btn" onclick="toggleNotifPanel()"
                class="relative p-2 rounded-md text-gray-500 hover:bg-gray-100 transition-colors">
          {% lucide "bell" class="w-5 h-5" %}
          <span id="notif-badge"
                class="absolute -top-0.5 -right-0.5 min-w-[18px] h-[18px] bg-red-500 text-white text-[10px] font-bold rounded-full flex items-center justify-center hidden">
            0
          </span>
        </button>
        <!-- Panneau notifications -->
        <div id="notif-panel"
             class="hidden absolute right-0 mt-2 w-80 bg-white rounded-md shadow-xl border border-gray-100 overflow-hidden z-50">
          <div class="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
            <span class="text-sm font-semibold text-gray-700">Notifications</span>
            <a href="{% url 'notifications_mark_all_read' %}" class="text-xs text-[#26b2bd] hover:underline">Tout marquer lu</a>
          </div>
          <div id="notif-list" class="divide-y divide-gray-50 max-h-72 overflow-y-auto">
            <p class="px-4 py-6 text-sm text-gray-400 text-center">Chargement…</p>
          </div>
          <a href="{% url 'notifications_view' %}"
             class="block px-4 py-3 text-xs text-center text-[#26b2bd] hover:bg-gray-50 font-medium">
            Voir tout
          </a>
        </div>
      </div>

      <!-- Profil -->
      <a href="{% url 'profile_view' %}" class="flex items-center gap-2 hover:opacity-80 transition-opacity">
        <img src="{{ request.user.profile_picture_url }}" alt="avatar"
             class="w-8 h-8 rounded-md object-cover ring-2 ring-[#26b2bd]/30">
        <span class="text-sm font-medium text-gray-700 hidden md:block">
          {{ request.user.get_full_name|default:request.user.username }}
        </span>
      </a>
    </div>
  </div>
</header>
```

- [ ] **Écrire `templates/dashboard/admin/includes/scripts.html`**

```html
<script>
// ── GSAP Modal ──────────────────────────────────────────────
const modalBackdrop = document.getElementById('modal-backdrop');
const modalPanel = document.getElementById('modal-panel');
const modalContent = document.getElementById('modal-content');

function openModal(html) {
  modalContent.innerHTML = html;
  modalBackdrop.style.display = 'flex';
  gsap.fromTo(modalBackdrop, { opacity: 0 }, { opacity: 1, duration: 0.2 });
  gsap.fromTo(modalPanel, { y: 60, opacity: 0 }, { y: 0, opacity: 1, duration: 0.3, ease: 'power2.out' });
  const first = modalPanel.querySelector('input, select, textarea');
  if (first) first.focus();
}

function closeModal() {
  gsap.to(modalPanel, { y: 40, opacity: 0, duration: 0.2, ease: 'power2.in' });
  gsap.to(modalBackdrop, {
    opacity: 0, duration: 0.2,
    onComplete: () => { modalBackdrop.style.display = 'none'; modalContent.innerHTML = ''; }
  });
}

function openSessionModal(sessionId) {
  fetch(`/api/sessions/${sessionId}/`)
    .then(r => r.json())
    .then(data => {
      openModal(buildSessionForm(data));
    });
}

function buildSessionForm(data) {
  return `
    <div class="flex items-center justify-between mb-4">
      <h2 class="text-lg font-semibold text-gray-800">${data ? 'Modifier la séance' : 'Créer une séance'}</h2>
      <button onclick="closeModal()" class="text-gray-400 hover:text-gray-600">✕</button>
    </div>
    <p class="text-sm text-gray-500">Utilisez le formulaire dédié pour cette action.</p>
    ${data ? `<a href="/administrateur/seances/${data.id}/modifier/" class="mt-4 inline-block px-4 py-2 bg-[#26b2bd] text-white rounded-md text-sm">Ouvrir le formulaire</a>` : ''}
  `;
}

if (modalBackdrop) {
  modalBackdrop.addEventListener('click', e => { if (e.target === modalBackdrop) closeModal(); });
}
document.addEventListener('keydown', e => { if (e.key === 'Escape') closeModal(); });

// ── Notifications polling ────────────────────────────────────
function getCookie(name) {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop().split(';').shift();
}

function toggleNotifPanel() {
  const panel = document.getElementById('notif-panel');
  if (panel.classList.contains('hidden')) {
    panel.classList.remove('hidden');
    loadNotifications();
  } else {
    panel.classList.add('hidden');
  }
}

function loadNotifications() {
  fetch('/notifications/', { credentials: 'same-origin' })
    .then(r => r.text())
    .then(html => {
      // On utilise l'endpoint API dédié pour le JSON
    });
}

function pollNotifications() {
  fetch('/api/notifications/unread/', { credentials: 'same-origin' })
    .then(r => r.json())
    .then(data => {
      const badge = document.getElementById('notif-badge');
      if (badge) {
        badge.textContent = data.count;
        badge.classList.toggle('hidden', data.count === 0);
      }
    })
    .catch(() => {});
}

pollNotifications();
setInterval(pollNotifications, 30000);

// Fermer le panneau notif au clic extérieur
document.addEventListener('click', e => {
  const panel = document.getElementById('notif-panel');
  const btn = document.getElementById('notif-btn');
  if (panel && btn && !panel.contains(e.target) && !btn.contains(e.target)) {
    panel.classList.add('hidden');
  }
});
</script>
```

- [ ] **Recompiler Tailwind**

```bash
npx tailwindcss -i ./static/assets/css/input.css -o ./static/assets/css/output.css
```

- [ ] **Vérifier le serveur**

```bash
python manage.py runserver
```

Ouvrir `http://127.0.0.1:8000/administrateur/` — vérifier que la sidebar teal s'affiche, pas d'erreur console.

- [ ] **Commit**

```bash
git add templates/dashboard/admin/
git commit -m "feat: admin dashboard — Tailwind base template, sidenav, navbar, GSAP modal, polling"
```

---

## Task 11 : Base templates Teacher (Tailwind)

**Files:**
- Modify: `templates/dashboard/teacher/layouts/base.html`
- Modify: `templates/dashboard/teacher/includes/sidenav.html`
- Modify: `templates/dashboard/teacher/includes/navigation.html`
- Modify: `templates/dashboard/teacher/includes/scripts.html`

**Même pattern que Task 10 avec les changements suivants :**

- [ ] **`templates/dashboard/teacher/layouts/base.html`**

Copier le base admin et remplacer :
- `dashboard/admin/includes/` → `dashboard/teacher/includes/`
- Garder identique sinon.

- [ ] **`templates/dashboard/teacher/includes/sidenav.html`**

Même structure que admin mais :
- Couleur sidebar : `bg-[#033050]`
- Liens nav teacher :

```html
    <a href="{% url 'teacher_view' request.user.username %}">{% lucide "layout-dashboard" ... %} Tableau de bord</a>
    <a href="{% url 'teacher_sessions' %}">{% lucide "calendar" ... %} Séances</a>
    <a href="{% url 'teacher_students' %}">{% lucide "graduation-cap" ... %} Mes étudiants</a>
    <a href="{% url 'teacher_assignments' %}">{% lucide "book-open" ... %} Devoirs</a>
    <a href="{% url 'teacher_resources_dashboard' %}">{% lucide "folder-open" ... %} Ressources</a>
    <a href="{% url 'teacher_evaluations_add' %}">{% lucide "bar-chart-2" ... %} Évaluations</a>
    <a href="{% url 'mes_paiements_formateur' %}">{% lucide "banknote" ... %} Mes paiements</a>
    <a href="{% url 'notifications_view' %}">{% lucide "bell" ... %} Notifications</a>
    <a href="{% url 'requests_view' %}">{% lucide "mail" ... %} Demandes</a>
    <a href="{% url 'profile_view' %}">{% lucide "user" ... %} Profil</a>
```

- Badge rôle en bas : `Teacher`
- Ring avatar : `ring-[#033050]/30`

- [ ] **`templates/dashboard/teacher/includes/navigation.html`**

Même structure que admin, remplacer couleur `#26b2bd` par `#033050` dans les liens.

- [ ] **`templates/dashboard/teacher/includes/scripts.html`**

Copier les scripts admin — identiques (polling + GSAP modal).

- [ ] **Recompiler et vérifier**

```bash
npx tailwindcss -i ./static/assets/css/input.css -o ./static/assets/css/output.css
python manage.py runserver
```

Ouvrir `http://127.0.0.1:8000/teacher/<username>/` — sidebar navy `#033050`.

- [ ] **Commit**

```bash
git add templates/dashboard/teacher/
git commit -m "feat: teacher dashboard — Tailwind base template, sidenav navy #033050"
```

---

## Task 12 : Base templates Student (Tailwind)

**Files:**
- Modify: `templates/dashboard/student/layouts/base.html`
- Modify: `templates/dashboard/student/includes/sidenav.html`
- Modify: `templates/dashboard/student/includes/navigation.html`
- Modify: `templates/dashboard/student/includes/scripts.html`

**Même pattern que Tasks 10-11 avec :**

- [ ] **Couleur sidebar** : `bg-[#d9a505]`
- [ ] **Texte sidebar** : `text-gray-900` (le jaune est clair, texte sombre pour contraste)
- [ ] **Liens nav student** :

```html
    <a href="{% url 'dashboard_view' request.user.username %}">{% lucide "layout-dashboard" ... %} Mon espace</a>
    <a href="{% url 'student_sessions' %}">{% lucide "calendar" ... %} Mes séances</a>
    <a href="{% url 'payments_view' %}">{% lucide "credit-card" ... %} Mes paiements</a>
    <a href="{% url 'certificates_view' %}">{% lucide "award" ... %} Mes certificats</a>
    <a href="{% url 'evaluations_view' %}">{% lucide "star" ... %} Évaluations</a>
    <a href="{% url 'resources_view' %}">{% lucide "folder-open" ... %} Ressources</a>
    <a href="{% url 'requests_view' %}">{% lucide "mail" ... %} Demandes</a>
    <a href="{% url 'notifications_view' %}">{% lucide "bell" ... %} Notifications</a>
    <a href="{% url 'profile_view' %}">{% lucide "user" ... %} Profil</a>
```

- [ ] **Recompiler et vérifier** — sidebar dorée `#d9a505`.

- [ ] **Commit**

```bash
git add templates/dashboard/student/
git commit -m "feat: student dashboard — Tailwind base template, sidenav gold #d9a505"
```

---

## Task 13 : Login split-screen

**Files:**
- Modify: `templates/account/login.html`

- [ ] **Réécrire `templates/account/login.html`**

```html
{% extends "account/base.html" %}
{% load socialaccount %}
{% load widget_tweaks %}
{% load static %}
{% load i18n %}

{% block title %}Oralise | Connexion{% endblock %}

{% block content %}
<div class="min-h-screen flex">

  <!-- Gauche : image + accroche -->
  <div class="hidden md:flex md:w-1/2 relative flex-col">
    <div class="absolute inset-0 bg-cover bg-center"
         style="background-image: url('{% static "assets/img/theme/img-login.jpg" %}')"></div>
    <div class="absolute inset-0 bg-[#033050]/70"></div>
    <!-- Logo haut gauche -->
    <div class="relative z-10 p-6">
      <img src="{% static 'assets/img/icons/favicon.png' %}" alt="Oralise" class="w-10 h-10">
    </div>
    <!-- Accroche centrée -->
    <div class="relative z-10 flex-1 flex flex-col justify-end p-10 pb-16">
      <h2 class="text-3xl font-bold text-white leading-tight mb-3">
        Gérez votre école<br>en toute clarté.
      </h2>
      <p class="text-white/70 text-base">La plateforme tout-en-un d'Oralise.</p>
    </div>
  </div>

  <!-- Droite : formulaire -->
  <div class="w-full md:w-1/2 flex items-center justify-center bg-white px-8 py-12">
    <div class="w-full max-w-sm">

      <!-- Mobile logo -->
      <div class="flex justify-center mb-8 md:hidden">
        <img src="{% static 'assets/img/icons/favicon.png' %}" alt="Oralise" class="w-12 h-12">
      </div>

      <h1 class="text-2xl font-bold text-gray-900 mb-1">Connexion</h1>
      <p class="text-sm text-gray-500 mb-8">Entrez vos identifiants pour accéder à votre espace.</p>

      <form method="post" action="{% url 'account_login' %}" class="space-y-5">
        {% csrf_token %}

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1.5">Adresse email</label>
          {{ form.login|add_class:"w-full px-4 py-2.5 border border-gray-200 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-[#26b2bd]/40 focus:border-[#26b2bd] transition" }}
        </div>

        <div>
          <div class="flex items-center justify-between mb-1.5">
            <label class="block text-sm font-medium text-gray-700">Mot de passe</label>
            <a href="{% url 'account_reset_password' %}" class="text-xs text-[#26b2bd] hover:underline">
              Mot de passe oublié ?
            </a>
          </div>
          {{ form.password|add_class:"w-full px-4 py-2.5 border border-gray-200 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-[#26b2bd]/40 focus:border-[#26b2bd] transition" }}
        </div>

        {% if form.errors %}
          <p class="text-sm text-red-600">Email ou mot de passe incorrect.</p>
        {% endif %}

        <button type="submit"
                class="w-full py-2.5 bg-gray-900 text-white text-sm font-semibold rounded-md hover:bg-gray-800 transition-colors">
          Se connecter
        </button>
      </form>
    </div>
  </div>

</div>
{% endblock %}
```

- [ ] **Vérifier** : `http://127.0.0.1:8000/accounts/login/` — split-screen, image gauche, formulaire droit.

- [ ] **Commit**

```bash
git add templates/account/login.html
git commit -m "feat: login split-screen — image left, form right, responsive"
```

---

## Task 14 : Page Profil — Refonte (3 rôles)

**Files:**
- Modify: `templates/dashboard/admin/home/` (si profil admin existe)
- Modify: `templates/dashboard/teacher/home/profile.html`
- Modify: `templates/dashboard/student/home/profile.html`

- [ ] **Écrire `templates/dashboard/student/home/profile.html`**

```html
{% extends "dashboard/student/layouts/base.html" %}
{% load static %}
{% load lucide %}

{% block title %}Mon Profil{% endblock %}
{% block page_title %}Mon Profil{% endblock %}

{% block content %}
<div class="max-w-3xl mx-auto space-y-6">

  <!-- Header profil -->
  <div class="bg-white rounded-md shadow-xl p-6 flex items-start gap-6">
    <div class="relative shrink-0">
      <img src="{{ request.user.profile_picture_url }}" alt="avatar"
           class="w-24 h-24 rounded-md object-cover ring-4 ring-[#d9a505]/30">
    </div>
    <div class="flex-1 min-w-0">
      <div class="flex items-center gap-3 flex-wrap mb-1">
        <h1 class="text-xl font-bold text-gray-900">{{ request.user.get_full_name }}</h1>
        <span class="px-2 py-0.5 text-xs font-semibold bg-[#d9a505] text-white rounded-md">Étudiant</span>
        {% if student.matricule %}
          <span class="text-xs text-gray-400 font-mono">{{ student.matricule }}</span>
        {% endif %}
      </div>
      <p class="text-sm text-gray-500">
        {{ profile.city }}{% if profile.city and profile.country %} · {% endif %}{{ profile.country }}
        {% if profile.number %} · {{ profile.number }}{% endif %}
      </p>
    </div>
    <a href="{% url 'profile_edit' %}"
       class="shrink-0 flex items-center gap-2 px-4 py-2 bg-[#d9a505] text-white text-sm font-medium rounded-md hover:opacity-90 transition-opacity">
      {% lucide "pencil" class="w-3.5 h-3.5" %} Modifier
    </a>
  </div>

  <!-- Stats -->
  <div class="grid grid-cols-3 gap-4">
    <div class="bg-white rounded-md shadow-xl p-5 text-center">
      <p class="text-3xl font-bold text-[#d9a505]">{{ total_sessions }}</p>
      <p class="text-xs text-gray-500 mt-1 font-medium">Séances totales</p>
    </div>
    <div class="bg-white rounded-md shadow-xl p-5 text-center">
      <p class="text-3xl font-bold text-[#d9a505]">{{ student.hours_remaining|default:"0" }}</p>
      <p class="text-xs text-gray-500 mt-1 font-medium">Heures restantes</p>
    </div>
    <div class="bg-white rounded-md shadow-xl p-5 text-center">
      <p class="text-3xl font-bold text-[#d9a505]">{{ avg_rating|default:"—" }}</p>
      <p class="text-xs text-gray-500 mt-1 font-medium">Note moyenne</p>
    </div>
  </div>

  <!-- Corps -->
  <div class="bg-white rounded-md shadow-xl p-6 space-y-5">
    {% if profile.about and profile.about.strip %}
    <div>
      <h3 class="text-sm font-semibold text-gray-700 mb-2 flex items-center gap-2">
        {% lucide "user" class="w-4 h-4 text-[#d9a505]" %} À propos
      </h3>
      <p class="text-sm text-gray-600 leading-relaxed">{{ profile.about }}</p>
    </div>
    {% endif %}

    {% if student.languages.all %}
    <div>
      <h3 class="text-sm font-semibold text-gray-700 mb-2 flex items-center gap-2">
        {% lucide "globe" class="w-4 h-4 text-[#d9a505]" %} Langues
      </h3>
      <div class="flex flex-wrap gap-2">
        {% for lang in student.languages.all %}
          <span class="px-3 py-1 text-xs font-medium bg-[#d9a505]/10 text-[#d9a505] rounded-md">{{ lang.name }}</span>
        {% endfor %}
      </div>
    </div>
    {% endif %}

    {% if student.objectif_formation %}
    <div>
      <h3 class="text-sm font-semibold text-gray-700 mb-2 flex items-center gap-2">
        {% lucide "target" class="w-4 h-4 text-[#d9a505]" %} Objectif de formation
      </h3>
      <p class="text-sm text-gray-600 leading-relaxed">{{ student.objectif_formation }}</p>
    </div>
    {% endif %}
  </div>

</div>
{% endblock %}
```

- [ ] **Adapter `templates/dashboard/teacher/home/profile.html`** — même structure, remplacer :
  - Couleur `#d9a505` → `#033050`
  - Badge `Étudiant` → `Formateur`
  - Stats : Étudiants actifs / Séances ce mois / Taux horaire
  - Sections : spécialité, langues, about

- [ ] **Adapter `templates/dashboard/admin/home/` profil** si existant — badge `Admin`, couleur `#26b2bd`, sans stats.

- [ ] **S'assurer que les vues `profile_view` passent `avg_rating` au contexte**

Dans `views.py`, dans la vue `profile_view`, ajouter au contexte pour le student :

```python
from django.db.models import Avg
avg_rating = Comment.objects.filter(
    teacher__in=student.current_teachers.all()
).aggregate(avg=Avg('rating'))['avg']
context['avg_rating'] = round(avg_rating, 1) if avg_rating else None
```

- [ ] **Commit**

```bash
git add templates/dashboard/ dashboard/views.py
git commit -m "feat: profile pages — avatar, stats cards, sections about/languages/objectif"
```

---

## Task 15 : Pages Calendrier — FullCalendar (Admin + Teacher)

**Files:**
- Modify: `templates/dashboard/admin/home/sessions_list.html`
- Modify: `templates/dashboard/teacher/home/sessions.html`

- [ ] **Écrire `templates/dashboard/admin/home/sessions_list.html`**

```html
{% extends "dashboard/admin/layouts/base.html" %}
{% load static %}
{% load lucide %}

{% block title %}Séances{% endblock %}
{% block page_title %}Calendrier des séances{% endblock %}

{% block extra_css %}
<link href="https://cdn.jsdelivr.net/npm/fullcalendar@6.1.11/index.global.min.css" rel="stylesheet">
{% endblock %}

{% block content %}
<div class="bg-white rounded-md shadow-xl p-4">
  <div id="calendar"></div>
</div>

<!-- Modal Session -->
<div id="session-modal-backdrop"
     class="fixed inset-0 bg-black/50 z-50 hidden items-center justify-center p-4">
  <div id="session-modal-panel"
       class="bg-white rounded-md shadow-xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
    <div id="session-modal-content" class="p-6"></div>
  </div>
</div>
{% endblock %}

{% block extra_js %}
<script src="https://cdn.jsdelivr.net/npm/fullcalendar@6.1.11/index.global.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/fullcalendar@6.1.11/locales/fr.global.min.js"></script>
<script>
const smBackdrop = document.getElementById('session-modal-backdrop');
const smPanel    = document.getElementById('session-modal-panel');
const smContent  = document.getElementById('session-modal-content');

function openSessionModal(html) {
  smContent.innerHTML = html;
  smBackdrop.style.display = 'flex';
  gsap.fromTo(smBackdrop, {opacity:0}, {opacity:1, duration:0.2});
  gsap.fromTo(smPanel, {y:60, opacity:0}, {y:0, opacity:1, duration:0.3, ease:'power2.out'});
}
function closeSessionModal() {
  gsap.to(smPanel, {y:40, opacity:0, duration:0.2, ease:'power2.in'});
  gsap.to(smBackdrop, {opacity:0, duration:0.2,
    onComplete: () => { smBackdrop.style.display='none'; smContent.innerHTML=''; }
  });
}
smBackdrop.addEventListener('click', e => { if(e.target===smBackdrop) closeSessionModal(); });
document.addEventListener('keydown', e => { if(e.key==='Escape') closeSessionModal(); });

function getCookie(name) {
  const v = `; ${document.cookie}`.split(`; ${name}=`);
  if (v.length===2) return v.pop().split(';').shift();
}

function sessionDetailHtml(data) {
  const stList = (data.extendedProps.students||[]).join(', ') || '—';
  const statusColors = {
    scheduled:'bg-blue-100 text-blue-700',
    completed:'bg-green-100 text-green-700',
    cancelled:'bg-red-100 text-red-700',
    rescheduled:'bg-amber-100 text-amber-700',
    absent:'bg-orange-100 text-orange-700',
  };
  const sc = statusColors[data.extendedProps.status] || 'bg-gray-100 text-gray-700';
  return `
    <div class="flex items-center justify-between mb-4">
      <h2 class="text-lg font-semibold text-gray-800">Détail séance</h2>
      <button onclick="closeSessionModal()" class="text-gray-400 hover:text-gray-600 text-xl leading-none">✕</button>
    </div>
    <div class="space-y-3 text-sm">
      <div class="flex justify-between"><span class="text-gray-500">Langue</span><span class="font-medium">${data.extendedProps.language}</span></div>
      <div class="flex justify-between"><span class="text-gray-500">Formateur</span><span class="font-medium">${data.extendedProps.teacher}</span></div>
      <div class="flex justify-between"><span class="text-gray-500">Étudiants</span><span class="font-medium">${stList}</span></div>
      <div class="flex justify-between"><span class="text-gray-500">Statut</span>
        <span class="px-2 py-0.5 rounded-md text-xs font-semibold ${sc}">${data.extendedProps.status_display}</span>
      </div>
    </div>
    <div class="mt-5 flex gap-3">
      <a href="/administrateur/seances/${data.extendedProps.session_id}/modifier/"
         class="flex-1 text-center py-2 bg-[#26b2bd] text-white text-sm font-medium rounded-md hover:opacity-90 transition">
        Modifier
      </a>
      <button onclick="deleteSession(${data.extendedProps.session_id})"
              class="flex-1 py-2 bg-red-50 text-red-600 text-sm font-medium rounded-md hover:bg-red-100 transition">
        Supprimer
      </button>
    </div>
  `;
}

function deleteSession(id) {
  if (!confirm('Supprimer cette séance ?')) return;
  fetch(`/api/sessions/${id}/delete/`, {
    method: 'POST',
    headers: {'X-CSRFToken': getCookie('csrftoken')}
  }).then(r => r.json()).then(d => {
    if (d.success) { closeSessionModal(); calendar.refetchEvents(); }
  });
}

let calendar;
document.addEventListener('DOMContentLoaded', function() {
  calendar = new FullCalendar.Calendar(document.getElementById('calendar'), {
    initialView: 'timeGridWeek',
    locale: 'fr',
    height: 'auto',
    headerToolbar: {
      left: 'prev,next today',
      center: 'title',
      right: 'dayGridMonth,timeGridWeek,timeGridDay,listWeek'
    },
    slotMinTime: '07:00:00',
    slotMaxTime: '21:00:00',
    events: '/api/sessions/',
    editable: true,
    selectable: true,
    select: function(info) {
      window.location.href = `/administrateur/seances/creer/?start=${info.startStr}&end=${info.endStr}`;
    },
    eventClick: function(info) {
      openSessionModal(sessionDetailHtml(info.event));
    },
    eventDrop: function(info) {
      const s = info.event.startStr;
      const e = info.event.endStr;
      fetch(`/api/sessions/${info.event.id}/update/`, {
        method: 'POST',
        headers: {'X-CSRFToken': getCookie('csrftoken'), 'Content-Type': 'application/json'},
        body: JSON.stringify({
          date: s.substring(0,10),
          start_time: s.substring(11,16),
          end_time: e.substring(11,16)
        })
      }).then(r => r.json()).then(d => { if(!d.success) info.revert(); });
    },
    eventResize: function(info) {
      const s = info.event.startStr;
      const e = info.event.endStr;
      fetch(`/api/sessions/${info.event.id}/update/`, {
        method: 'POST',
        headers: {'X-CSRFToken': getCookie('csrftoken'), 'Content-Type': 'application/json'},
        body: JSON.stringify({
          date: s.substring(0,10),
          start_time: s.substring(11,16),
          end_time: e.substring(11,16)
        })
      }).then(r => r.json()).then(d => { if(!d.success) info.revert(); });
    }
  });
  calendar.render();
});
</script>
{% endblock %}
```

- [ ] **Écrire `templates/dashboard/teacher/home/sessions.html`**

Copier le template admin ci-dessus et remplacer :
- `extends` → `"dashboard/teacher/layouts/base.html"`
- Couleur `#26b2bd` → `#033050`
- `select` handler → `window.location.href = '/administrateur/seances/creer/?...'` → garder le même (ou désactiver si Teacher ne peut pas créer via URL admin)
- Lien "Modifier" → `/teacher/sessions/<id>/` si la vue teacher existe, sinon `/administrateur/seances/<id>/modifier/`
- Conserver `editable: true` et `selectable: true` pour le teacher

- [ ] **Écrire `templates/dashboard/student/home/sessions.html`** (lecture seule)

Même template, mais :
- `editable: false, selectable: false`
- Supprimer le bloc boutons Modifier/Supprimer dans le modal
- Modale affiche uniquement le détail (langue, formateur, statut, date)
- Pas de handler `select`

- [ ] **Vérifier** : ouvrir le calendrier admin, vérifier les événements apparaissent, le drag fonctionne.

- [ ] **Commit**

```bash
git add templates/dashboard/
git commit -m "feat: calendar pages — FullCalendar 6, GSAP modals, drag-drop, admin/teacher/student"
```

---

## Task 16 : Dashboard homes — stats corrigées

**Files:**
- Modify: `templates/dashboard/admin/home/index.html`
- Modify: `templates/dashboard/teacher/home/index.html`
- Modify: `templates/dashboard/student/home/index.html`
- Modify: `dashboard/views.py` (contexte stats)

- [ ] **Corriger les contextes stats dans `views.py`**

Dans `admin_dashboard` :

```python
from dashboard.models import Student, Teacher, Session, Payment
context = {
    'total_students': Student.objects.count(),
    'total_teachers': Teacher.objects.count(),
    'total_sessions': Session.objects.count(),
    'sessions_today': Session.objects.filter(date=date.today()).count(),
    'sessions_completed': Session.objects.filter(status='completed').count(),
    'revenue_total': Payment.objects.filter(status='paid').aggregate(
        total=Sum('amount'))['total'] or 0,
}
```

Dans `teacher_view` (dashboard teacher), ajouter :

```python
today = timezone.now().date()
context['sessions_today_count'] = Session.objects.filter(
    teacher=teacher, date=today).count()
context['sessions_week_count'] = Session.objects.filter(
    teacher=teacher,
    date__gte=today,
    date__lte=today + timedelta(days=7)
).count()
context['total_students_count'] = teacher.total_students
```

Dans `dashboard_view` (student), ajouter :

```python
context['total_sessions'] = Session.objects.filter(students=student).count()
context['completed_sessions'] = Session.objects.filter(
    students=student, status='completed').count()
context['hours_remaining'] = student.hours_remaining
```

- [ ] **Écrire `templates/dashboard/admin/home/index.html`** (stats cards Tailwind)

```html
{% extends "dashboard/admin/layouts/base.html" %}
{% load static %}
{% load lucide %}
{% load humanize %}

{% block title %}Tableau de bord{% endblock %}
{% block page_title %}Tableau de bord{% endblock %}

{% block content %}
<!-- Stats cards -->
<div class="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
  <div class="bg-white rounded-md shadow-xl p-5">
    <div class="flex items-center justify-between mb-3">
      <span class="text-xs font-semibold text-gray-500 uppercase tracking-wider">Étudiants</span>
      {% lucide "graduation-cap" class="w-5 h-5 text-[#26b2bd]" %}
    </div>
    <p class="text-3xl font-bold text-gray-900">{{ total_students }}</p>
  </div>
  <div class="bg-white rounded-md shadow-xl p-5">
    <div class="flex items-center justify-between mb-3">
      <span class="text-xs font-semibold text-gray-500 uppercase tracking-wider">Formateurs</span>
      {% lucide "users" class="w-5 h-5 text-[#26b2bd]" %}
    </div>
    <p class="text-3xl font-bold text-gray-900">{{ total_teachers }}</p>
  </div>
  <div class="bg-white rounded-md shadow-xl p-5">
    <div class="flex items-center justify-between mb-3">
      <span class="text-xs font-semibold text-gray-500 uppercase tracking-wider">Séances aujourd'hui</span>
      {% lucide "calendar" class="w-5 h-5 text-[#26b2bd]" %}
    </div>
    <p class="text-3xl font-bold text-gray-900">{{ sessions_today }}</p>
  </div>
  <div class="bg-white rounded-md shadow-xl p-5">
    <div class="flex items-center justify-between mb-3">
      <span class="text-xs font-semibold text-gray-500 uppercase tracking-wider">CA total</span>
      {% lucide "banknote" class="w-5 h-5 text-[#26b2bd]" %}
    </div>
    <p class="text-3xl font-bold text-gray-900">{{ revenue_total|intcomma }} MAD</p>
  </div>
</div>

<!-- Sessions récentes + Actions rapides -->
<div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
  <!-- Sessions récentes -->
  <div class="lg:col-span-2 bg-white rounded-md shadow-xl">
    <div class="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
      <h2 class="text-sm font-semibold text-gray-700">Séances récentes</h2>
      <a href="{% url 'admin_sessions_list' %}" class="text-xs text-[#26b2bd] hover:underline">Voir le calendrier</a>
    </div>
    <div class="divide-y divide-gray-50">
      {% for session in recent_sessions %}
      <div class="px-5 py-3 flex items-center justify-between hover:bg-gray-50 transition-colors">
        <div>
          <p class="text-sm font-medium text-gray-800">{{ session.language }} — {{ session.teacher }}</p>
          <p class="text-xs text-gray-400">{{ session.date }} · {{ session.start_time|time:"H:i" }}</p>
        </div>
        <span class="px-2 py-0.5 text-xs font-semibold rounded-md
          {% if session.status == 'completed' %}bg-green-100 text-green-700
          {% elif session.status == 'cancelled' %}bg-red-100 text-red-700
          {% else %}bg-blue-100 text-blue-700{% endif %}">
          {{ session.get_status_display }}
        </span>
      </div>
      {% empty %}
        <p class="px-5 py-8 text-sm text-gray-400 text-center">Aucune séance récente</p>
      {% endfor %}
    </div>
  </div>

  <!-- Actions rapides -->
  <div class="bg-white rounded-md shadow-xl">
    <div class="px-5 py-4 border-b border-gray-100">
      <h2 class="text-sm font-semibold text-gray-700">Actions rapides</h2>
    </div>
    <div class="p-4 space-y-2">
      <a href="{% url 'admin_student_create' %}"
         class="flex items-center gap-3 px-4 py-3 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors border border-gray-100">
        {% lucide "user-plus" class="w-4 h-4 text-[#26b2bd]" %} Ajouter un étudiant
      </a>
      <a href="{% url 'admin_teacher_create' %}"
         class="flex items-center gap-3 px-4 py-3 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors border border-gray-100">
        {% lucide "user-plus" class="w-4 h-4 text-[#26b2bd]" %} Ajouter un formateur
      </a>
      <a href="{% url 'admin_session_create' %}"
         class="flex items-center gap-3 px-4 py-3 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors border border-gray-100">
        {% lucide "calendar-plus" class="w-4 h-4 text-[#26b2bd]" %} Créer une séance
      </a>
      <a href="{% url 'admin_payment_create' %}"
         class="flex items-center gap-3 px-4 py-3 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors border border-gray-100">
        {% lucide "credit-card" class="w-4 h-4 text-[#26b2bd]" %} Enregistrer un paiement
      </a>
    </div>
  </div>
</div>
{% endblock %}
```

- [ ] **Adapter `templates/dashboard/teacher/home/index.html`** — même structure, couleur `#033050`, stats : séances today, séances semaine, étudiants actifs.

- [ ] **Adapter `templates/dashboard/student/home/index.html`** — couleur `#d9a505`, stats : séances totales, séances complétées, heures restantes.

- [ ] **Ajouter `recent_sessions` au contexte admin_dashboard dans `views.py`**

```python
from dashboard.models import Session
context['recent_sessions'] = Session.objects.select_related(
    'teacher__user', 'language'
).order_by('-date', '-start_time')[:8]
```

- [ ] **Vérifier**

```bash
python manage.py runserver
```

Naviguer sur les 3 dashboards — vérifier les chiffres sont corrects.

- [ ] **Commit**

```bash
git add templates/dashboard/ dashboard/views.py
git commit -m "feat: dashboard homes — Tailwind stats cards, recent sessions, corrected counts"
```

---

## Task 17 : GSAP modals sur les pages CRUD restantes

**Files:**
- Modify: Toutes les pages liste admin (`*.html` dans `dashboard/admin/home/`)

**Principe :** Chaque page liste (students, teachers, payments, etc.) conserve son tableau de données mais les boutons "Créer" et "Modifier" ouvrent des modales GSAP au lieu de naviguer vers une page séparée.

- [ ] **Pattern modal à appliquer sur chaque page liste**

Dans chaque template liste, remplacer le lien "Créer" par un bouton :

```html
<!-- AVANT -->
<a href="{% url 'admin_student_create' %}">Ajouter</a>

<!-- APRÈS -->
<button onclick="loadModal('{% url 'admin_student_create' %}')"
        class="flex items-center gap-2 px-4 py-2 bg-[#26b2bd] text-white text-sm font-semibold rounded-md hover:opacity-90 transition">
  {% lucide "plus" class="w-4 h-4" %} Ajouter
</button>
```

Dans `scripts.html` admin (Task 10), ajouter la fonction `loadModal` :

```javascript
function loadModal(url) {
  fetch(url, {headers: {'X-Requested-With': 'XMLHttpRequest'}})
    .then(r => r.text())
    .then(html => {
      // Extraire uniquement le bloc formulaire si la réponse est une page complète
      const parser = new DOMParser();
      const doc = parser.parseFromString(html, 'text/html');
      const formBlock = doc.querySelector('form') || doc.querySelector('.modal-body');
      openModal(formBlock ? formBlock.outerHTML : html);
    });
}
```

- [ ] **Appliquer sur les pages liste admin** :
  - `students_list.html` (si existe) ou la vue `admin_student_view`
  - `list_teachers.html`
  - `payments_list.html`
  - `evaluations_list.html`
  - `languages_list.html`
  - `notifications_list.html`
  - `assignments_list.html`

  Pour chaque page : remplacer les boutons "Ajouter" et "Modifier" selon le pattern ci-dessus.

- [ ] **Les formulaires doivent gérer la soumission AJAX**

Dans chaque vue de création/modification, détecter si c'est une requête AJAX :

```python
def admin_student_create(request):
    ...
    if form.is_valid():
        form.save()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'redirect': reverse('admin_students')})
        return redirect('admin_students')
    ...
```

Côté JS, intercepter la soumission du formulaire dans la modale :

Ajouter dans `scripts.html` :

```javascript
document.addEventListener('submit', function(e) {
  const form = e.target;
  if (modalContent.contains(form)) {
    e.preventDefault();
    const formData = new FormData(form);
    fetch(form.action || window.location.href, {
      method: 'POST',
      body: formData,
      headers: {'X-Requested-With': 'XMLHttpRequest', 'X-CSRFToken': getCookie('csrftoken')}
    }).then(r => r.json()).then(data => {
      if (data.success) {
        closeModal();
        if (data.redirect) window.location.href = data.redirect;
        else window.location.reload();
      } else {
        // Afficher les erreurs dans la modale
        const errDiv = modalContent.querySelector('.modal-errors');
        if (errDiv && data.errors) errDiv.innerHTML = JSON.stringify(data.errors);
      }
    });
  }
});
```

- [ ] **Recompiler Tailwind**

```bash
npx tailwindcss -i ./static/assets/css/input.css -o ./static/assets/css/output.css
```

- [ ] **Test manuel** : ouvrir la liste students admin → cliquer "Ajouter" → modale s'ouvre avec animation GSAP.

- [ ] **Commit**

```bash
git add templates/dashboard/ dashboard/views.py dashboard/api_views.py
git commit -m "feat: GSAP modals on all admin CRUD pages — unified loadModal + AJAX form submit"
```

---

## Task 18 : Recompiler + vérification finale

- [ ] **Build Tailwind production**

```bash
npx tailwindcss -i ./static/assets/css/input.css -o ./static/assets/css/output.css --minify
```

- [ ] **Collecter les statiques**

```bash
source env/bin/activate && python manage.py collectstatic --noinput
```

- [ ] **Lancer la suite de tests complète**

```bash
python manage.py test dashboard -v 2
```

Résultat attendu : tous PASS.

- [ ] **Vérifier le check Django**

```bash
python manage.py check
```

Résultat attendu : `0 issues`.

- [ ] **Test manuel golden path**

1. Login → page split-screen ✓
2. Admin dashboard → stats correctes, sidebar teal ✓
3. Admin séances → FullCalendar s'affiche, événements visibles ✓
4. Drag d'un événement → mise à jour sans rechargement ✓
5. Teacher dashboard → sidebar navy ✓
6. Teacher: marquer séance "Terminée" → notification créée pour l'étudiant ✓
7. Student dashboard → badge notification mis à jour (polling 30s) ✓
8. Student: page séances → lecture seule, pas de drag ✓
9. Profil admin → refonte visible ✓
10. Toutes les URL Schedule → 404 ou redirigent ✓

- [ ] **Commit final**

```bash
git add -A
git commit -m "feat: production build — Tailwind minified, all checks pass, refonte Oralise complete"
```

---

## Checklist Self-Review

- [x] **Schedule supprimé** : modèle, migrations, vues, URLs, templates → Task 4, 9
- [x] **Session.students M2M** : 3 migrations séquentielles → Tasks 2-4
- [x] **Données préservées** : migration RunPython → Task 3
- [x] **Stats corrigées** : Teacher.total_students, Student.computed_hours_used → Task 5
- [x] **Signal notification** : evaluation_request sur completion → Task 6
- [x] **API JSON** : 7 endpoints session + 1 unread → Task 8
- [x] **Polling 30s** : scripts.html → Task 10
- [x] **FullCalendar** : admin + teacher + student → Task 15
- [x] **GSAP modals** : base templates + CRUD pages → Tasks 10-12, 17
- [x] **Login split-screen** → Task 13
- [x] **Profil refonte** → Task 14
- [x] **Dashboard homes** → Task 16
- [x] **Tailwind build** : input.css compilé → Tasks 1, 18
- [x] **django-lucide** → Task 1
- [x] **Tests** : modèles + signal + API → Tasks 5-6
- [x] **PaiementFormateur.calculer_montant** : utilise `students` M2M → corrigé dans Task 4 (models.py)
