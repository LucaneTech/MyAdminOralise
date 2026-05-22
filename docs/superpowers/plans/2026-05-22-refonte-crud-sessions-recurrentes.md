# Refonte CRUD + Séances Récurrentes + Graphes Dynamiques — Plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Supprimer tous les modals/popups des dashboards, refondre les formulaires en pages dédiées pro/modernes, ajouter un système de séances récurrentes (Google Calendar style), et corriger les graphes admin pour qu'ils soient 100% dynamiques.

**Architecture:** Django mono-app (`dashboard`), vues dans `views.py`, formulaires dans `forms.py`, logique métier séances récurrentes dans `dashboard/services.py` (nouveau fichier). Les 4 modules sont indépendants mais doivent être exécutés dans l'ordre car les séances récurrentes dépendent du nouveau modèle.

**Tech Stack:** Django 4.x, Tailwind CSS (classes utilitaires), Chart.js 4.4, lucide templatetag, python-dateutil non requis (stdlib `datetime` suffit).

---

## Fichiers créés / modifiés

| Fichier | Action |
|---|---|
| `dashboard/models.py` | Modify — ajouter `SessionSeries`, FK sur `Session` |
| `dashboard/services.py` | Create — logique récurrence |
| `dashboard/forms.py` | Modify — `SessionSeriesAdminForm`, champs `is_recurring`/`recurrence_end` sur `SessionAdminForm` |
| `dashboard/views.py` | Modify — nouvelles vues série, modifier session create/edit/delete, vues teacher assignments |
| `dashboard/urls.py` | Modify — nouvelles routes série + teacher assignments |
| `dashboard/tests.py` | Modify — tests services + vues série |
| `templates/dashboard/admin/layouts/base.html` | Modify — supprimer modal HTML |
| `templates/dashboard/admin/includes/scripts.html` | Modify — supprimer loadModal/openModal/closeModal |
| `templates/dashboard/admin/home/admin_form.html` | Modify — redesign |
| `templates/dashboard/admin/home/session_form.html` | Modify — redesign + section récurrence |
| `templates/dashboard/admin/home/student_form.html` | Modify — redesign |
| `templates/dashboard/admin/home/teacher_form.html` | Modify — redesign |
| `templates/dashboard/admin/home/paiement_formateur_form.html` | Modify — redesign |
| `templates/dashboard/admin/home/certificate_form.html` | Modify — redesign |
| `templates/dashboard/admin/home/session_series_form.html` | Create |
| `templates/dashboard/admin/home/session_series_list.html` | Create |
| `templates/dashboard/admin/home/session_scope_choice.html` | Create |
| `templates/dashboard/admin/home/assignments_list.html` | Modify — suppr modal |
| `templates/dashboard/admin/home/evaluations_list.html` | Modify — suppr modal |
| `templates/dashboard/admin/home/languages_list.html` | Modify — suppr modal |
| `templates/dashboard/admin/home/list_students.html` | Modify — suppr modal |
| `templates/dashboard/admin/home/list_teachers.html` | Modify — suppr modal |
| `templates/dashboard/admin/home/payments_list.html` | Modify — suppr modal |
| `templates/dashboard/admin/home/notifications_list.html` | Modify — suppr modal |
| `templates/dashboard/admin/home/sessions_list.html` | Modify — suppr modal inline |
| `templates/dashboard/admin/home/index.html` | Modify — graphes dynamiques |
| `templates/dashboard/teacher/layouts/base.html` | Modify — suppr modal HTML |
| `templates/dashboard/teacher/includes/scripts.html` | Modify — suppr modal JS |
| `templates/dashboard/teacher/home/assignments.html` | Modify — suppr modal, liens directs |
| `templates/dashboard/teacher/home/courses.html` | Modify — suppr modal placeholder |
| `templates/dashboard/teacher/home/resources.html` | Modify — suppr modals inline |
| `templates/dashboard/teacher/home/evaluations.html` | Modify — suppr modals inline |
| `templates/dashboard/teacher/home/assignment_form.html` | Create |
| `templates/dashboard/teacher/home/resource_form.html` | Create |

---

## PARTIE A — SessionSeries : modèle + services

### Task 1 : SessionSeries model + FK sur Session

**Files:**
- Modify: `dashboard/models.py` — après ligne 583 (fin de Session), avant `# Paiements`

- [ ] **Ajouter `SessionSeries` dans models.py** — insérer avant `# Paiements` (ligne 584) :

```python
# Séances récurrentes — série
class SessionSeries(models.Model):
    DAY_CHOICES = [
        (0, 'Lundi'), (1, 'Mardi'), (2, 'Mercredi'),
        (3, 'Jeudi'), (4, 'Vendredi'), (5, 'Samedi'), (6, 'Dimanche'),
    ]
    teacher = models.ForeignKey(
        'Teacher', on_delete=models.CASCADE, related_name='session_series',
        verbose_name="formateur"
    )
    language = models.ForeignKey(
        'Language', on_delete=models.CASCADE, verbose_name="langue"
    )
    students = models.ManyToManyField(
        'Student', blank=True, related_name='session_series',
        verbose_name="étudiants"
    )
    day_of_week = models.IntegerField(choices=DAY_CHOICES, verbose_name="jour de la semaine")
    start_time = models.TimeField(verbose_name="heure de début")
    end_time = models.TimeField(verbose_name="heure de fin")
    recurrence_start = models.DateField(verbose_name="début de la série")
    recurrence_end = models.DateField(
        null=True, blank=True, verbose_name="fin de la série (vide = 12 mois)"
    )
    type_seance = models.CharField(
        max_length=20,
        choices=[('individuelle', 'Individuelle'), ('groupe', 'Groupe')],
        default='individuelle', verbose_name="type de séance"
    )
    meeting_link = models.URLField(blank=True, null=True, verbose_name="lien de réunion")
    notes = models.TextField(blank=True, verbose_name="notes")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "série de séances"
        verbose_name_plural = "séries de séances"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.teacher} — {self.get_day_of_week_display()} {self.start_time}"
```

- [ ] **Ajouter `series` et `series_index` à `Session`** — dans la class `Session` (models.py), après le champ `feedback` (dernier champ), avant `class Meta` ou `@property` :

```python
    series = models.ForeignKey(
        'SessionSeries', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='occurrences',
        verbose_name="série récurrente"
    )
    series_index = models.PositiveIntegerField(
        null=True, blank=True, verbose_name="index dans la série"
    )
```

- [ ] **Générer la migration :**

```bash
cd /home/lucane/myprojects/MyAdminOralise
source env/bin/activate
python manage.py makemigrations dashboard --name sessionseries_and_session_series_fk
```

Expected output : `Migrations for 'dashboard': dashboard/migrations/0003_sessionseries_and_session_series_fk.py`

- [ ] **Appliquer la migration :**

```bash
python manage.py migrate
```

Expected : `Applying dashboard.0003_sessionseries_and_session_series_fk... OK`

- [ ] **Commit :**

```bash
git add dashboard/models.py dashboard/migrations/
git commit -m "feat: add SessionSeries model + series FK on Session"
```

---

### Task 2 : services.py — logique récurrence

**Files:**
- Create: `dashboard/services.py`

- [ ] **Écrire le test d'abord** — ajouter dans `dashboard/tests.py` :

```python
from dashboard.models import SessionSeries, Language, Teacher, Student
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
        from dashboard.models import Session, SessionSeries
        self.assertEqual(Session.objects.filter(series=series).count(), 0)
        self.assertFalse(SessionSeries.objects.filter(pk=series.pk).exists())
```

- [ ] **Lancer le test pour vérifier qu'il échoue :**

```bash
python manage.py test dashboard.tests.SessionSeriesServiceTest -v 2
```

Expected : `ImportError: cannot import name 'generate_series_occurrences' from 'dashboard.services'`

- [ ] **Créer `dashboard/services.py` :**

```python
from datetime import timedelta
from dashboard.models import Session, SessionSeries


def generate_series_occurrences(series: SessionSeries) -> list:
    """Génère toutes les occurrences Session d'une SessionSeries."""
    from datetime import date as _date
    end = series.recurrence_end or (series.recurrence_start + timedelta(days=365))
    current = series.recurrence_start
    # Avancer jusqu'au bon jour de semaine (0=lundi)
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
    cleaned_data : champs scalaires uniquement (pas students, pas date).
    Propager uniquement les champs de planning (_SCHEDULE_FIELDS).
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
        # Mettre à jour la série elle-même
        series = session.series
        for k, v in propagatable.items():
            if hasattr(series, k):
                setattr(series, k, v)
        series.save()


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
        series = session.series
        Session.objects.filter(series=series).delete()
        series.delete()
```

- [ ] **Lancer les tests pour vérifier qu'ils passent :**

```bash
python manage.py test dashboard.tests.SessionSeriesServiceTest -v 2
```

Expected : `OK` (5 tests passent)

- [ ] **Commit :**

```bash
git add dashboard/services.py dashboard/tests.py
git commit -m "feat: services.py — generate_series_occurrences, apply_series_edit, apply_series_delete"
```

---

### Task 3 : SessionSeriesAdminForm + champs récurrence sur SessionAdminForm

**Files:**
- Modify: `dashboard/forms.py`

- [ ] **Ajouter `SessionSeriesAdminForm` à la fin de forms.py** (après `AssignmentAdminForm`) :

```python
class SessionSeriesAdminForm(forms.ModelForm):
    class Meta:
        model = SessionSeries
        fields = [
            'teacher', 'language', 'students',
            'day_of_week', 'start_time', 'end_time',
            'recurrence_start', 'recurrence_end',
            'type_seance', 'meeting_link', 'notes',
        ]
        widgets = {
            'teacher': forms.Select(attrs={'class': TW_SELECT}),
            'language': forms.Select(attrs={'class': TW_SELECT}),
            'students': forms.SelectMultiple(attrs={'class': TW_SELECT + ' h-32'}),
            'day_of_week': forms.Select(attrs={'class': TW_SELECT}),
            'start_time': forms.TimeInput(attrs={'class': TW_INPUT, 'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'class': TW_INPUT, 'type': 'time'}),
            'recurrence_start': forms.DateInput(attrs={'class': TW_INPUT, 'type': 'date'}),
            'recurrence_end': forms.DateInput(attrs={'class': TW_INPUT, 'type': 'date'}),
            'type_seance': forms.Select(attrs={'class': TW_SELECT}),
            'meeting_link': forms.URLInput(attrs={'class': TW_INPUT}),
            'notes': forms.Textarea(attrs={'class': TW_TEXTAREA, 'rows': 3}),
        }
```

- [ ] **Ajouter l'import `SessionSeries` dans forms.py** — ligne 1, modifier l'import models existant :

```python
from dashboard.models import (
    Profile, CustomUser, Resource, Session, SessionSeries, Student, Language,
    Certificate, PaiementFormateur, Teacher, Payment,
    Evaluation, Request, Notification, Assignment, Comment,
)
```

- [ ] **Commit :**

```bash
git add dashboard/forms.py
git commit -m "feat: SessionSeriesAdminForm in forms.py"
```

---

### Task 4 : Vues admin séries + modification create/edit/delete session

**Files:**
- Modify: `dashboard/views.py` — ajouter après `admin_session_delete` (ligne ~2985)
- Modify: `dashboard/views.py` — modifier `admin_session_create`, `admin_session_edit`, `admin_session_delete`
- Modify: `dashboard/urls.py`

- [ ] **Ajouter l'import `SessionSeries` et `SessionSeriesAdminForm` dans le bloc d'imports admin** (views.py ligne ~2599) :

```python
from .forms import (
    AdminUserCreateForm, AdminUserEditForm, AdminResetPasswordForm,
    StudentAdminForm, TeacherAdminForm, LanguageForm,
    SessionAdminForm, SessionSeriesAdminForm, PaymentAdminForm, EvaluationAdminForm,
    ResourceAdminForm, RequestAdminForm, NotificationAdminForm,
    AssignmentAdminForm,
)
from dashboard.models import Evaluation, Assignment, Submission, SessionSeries
from dashboard.services import generate_series_occurrences, apply_series_edit, apply_series_delete
```

- [ ] **Remplacer `admin_session_create`** (views.py ligne ~2937) :

```python
@admin_required
def admin_session_create(request):
    if request.method == 'POST':
        is_recurring = request.POST.get('is_recurring') == 'on'
        if is_recurring:
            form = SessionSeriesAdminForm(request.POST)
            if form.is_valid():
                series = form.save()
                occurrences = generate_series_occurrences(series)
                messages.success(request, f"Série créée — {len(occurrences)} séances générées.")
                return redirect('admin_sessions_list')
            return render(request, 'dashboard/admin/home/session_form.html', {
                'form': SessionAdminForm(), 'series_form': form,
                'titre': 'Créer une séance', 'section_active': 'sessions',
                'is_recurring': True,
            })
        else:
            form = SessionAdminForm(request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, "Séance créée.")
                return redirect('admin_sessions_list')
    else:
        form = SessionAdminForm()
    return render(request, 'dashboard/admin/home/session_form.html', {
        'form': form,
        'series_form': SessionSeriesAdminForm(),
        'titre': 'Créer une séance',
        'section_active': 'sessions',
    })
```

- [ ] **Remplacer `admin_session_edit`** (views.py ligne ~2952) :

```python
@admin_required
def admin_session_edit(request, session_id):
    session = get_object_or_404(Session, id=session_id)
    if request.method == 'POST':
        # Cas série : rediriger vers scope choice
        if session.series_id and not request.POST.get('_scope'):
            return redirect(
                reverse('admin_session_scope_edit', args=[session_id])
                + '?' + request.POST.urlencode()
            )
        scope = request.POST.get('_scope')
        form = SessionAdminForm(request.POST, instance=session)
        if form.is_valid():
            if scope:
                apply_series_edit(session, scope, form.cleaned_data)
                messages.success(request, f"Modification appliquée ({scope}).")
            else:
                form.save()
                messages.success(request, "Séance mise à jour.")
            return redirect('admin_sessions_list')
    else:
        form = SessionAdminForm(instance=session)
    return render(request, 'dashboard/admin/home/session_form.html', {
        'form': form,
        'series_form': SessionSeriesAdminForm(),
        'session': session,
        'titre': f'Modifier séance — {session.date}',
        'section_active': 'sessions',
    })
```

- [ ] **Remplacer `admin_session_delete`** (views.py ligne ~2969) :

```python
@admin_required
def admin_session_delete(request, session_id):
    session = get_object_or_404(Session, id=session_id)
    if request.method == 'POST':
        scope = request.POST.get('scope', 'this')
        if session.series_id:
            apply_series_delete(session, scope)
            messages.success(request, "Suppression appliquée.")
        else:
            session.delete()
            messages.success(request, "Séance supprimée.")
        return redirect('admin_sessions_list')
    return render(request, 'dashboard/admin/home/confirm_delete.html', {
        'objet': session,
        'back_url': 'admin_sessions_list',
        'section_active': 'sessions',
        'titre': f'Supprimer la séance du {session.date}',
        'is_series': bool(session.series_id),
    })
```

- [ ] **Ajouter les vues série après `admin_session_delete`** :

```python
@admin_required
def admin_session_scope_edit(request, session_id):
    session = get_object_or_404(Session, id=session_id)
    if request.method == 'POST':
        scope = request.POST.get('scope', 'this')
        form = SessionAdminForm(request.POST, instance=session)
        if form.is_valid():
            apply_series_edit(session, scope, form.cleaned_data)
            messages.success(request, "Modification appliquée.")
        return redirect('admin_sessions_list')
    # Récupérer les données soumises depuis le formulaire précédent
    post_data = request.GET.copy()
    form = SessionAdminForm(post_data, instance=session)
    form.is_valid()  # peupler cleaned_data sans bloquer
    return render(request, 'dashboard/admin/home/session_scope_choice.html', {
        'session': session, 'form': form,
        'section_active': 'sessions', 'titre': 'Portée de la modification',
    })


@admin_required
def admin_session_series_list(request):
    series_list = SessionSeries.objects.select_related('teacher', 'language').order_by('-created_at')
    return render(request, 'dashboard/admin/home/session_series_list.html', {
        'series_list': series_list, 'section_active': 'sessions', 'titre': 'Séries récurrentes',
    })


@admin_required
def admin_session_series_delete(request, series_id):
    series = get_object_or_404(SessionSeries, id=series_id)
    if request.method == 'POST':
        series.occurrences.all().delete()
        series.delete()
        messages.success(request, "Série et toutes ses séances supprimées.")
        return redirect('admin_session_series_list')
    count = series.occurrences.count()
    return render(request, 'dashboard/admin/home/confirm_delete.html', {
        'objet': series,
        'back_url': 'admin_session_series_list',
        'section_active': 'sessions',
        'titre': f'Supprimer la série — {count} séances seront effacées',
    })
```

- [ ] **Ajouter les URLs** dans `dashboard/urls.py` — après la ligne `admin_session_delete` :

```python
from dashboard.views import (
    admin_session_scope_edit,
    admin_session_series_list,
    admin_session_series_delete,
)
```

Et dans `urlpatterns` :

```python
path('administrateur/seances/<int:session_id>/modifier/scope/', admin_session_scope_edit, name='admin_session_scope_edit'),
path('administrateur/seances/series/', admin_session_series_list, name='admin_session_series_list'),
path('administrateur/seances/series/<int:series_id>/supprimer/', admin_session_series_delete, name='admin_session_series_delete'),
```

- [ ] **Test de la vue create série** — ajouter dans `dashboard/tests.py` :

```python
class AdminSessionSeriesViewTest(TestCase):
    def setUp(self):
        self.admin = make_user('admin_sv', 'admin')
        self.client = Client()
        self.client.login(username='admin_sv', password='pass')
        self.teacher = Teacher.objects.get(user=make_user('t_sv', 'teacher'))
        self.lang = Language.objects.create(name='Allemand', code='de')

    def test_create_series_generates_occurrences(self):
        from django.urls import reverse
        response = self.client.post(reverse('admin_session_create'), {
            'is_recurring': 'on',
            'teacher': self.teacher.pk,
            'language': self.lang.pk,
            'day_of_week': 0,
            'start_time': '10:00',
            'end_time': '11:00',
            'recurrence_start': '2026-06-01',
            'recurrence_end': '2026-06-22',
            'type_seance': 'individuelle',
        })
        self.assertRedirects(response, reverse('admin_sessions_list'))
        from dashboard.models import SessionSeries, Session
        self.assertEqual(SessionSeries.objects.count(), 1)
        self.assertEqual(Session.objects.filter(series__isnull=False).count(), 4)
```

- [ ] **Lancer les tests :**

```bash
python manage.py test dashboard.tests.AdminSessionSeriesViewTest -v 2
```

Expected : `OK`

- [ ] **Commit :**

```bash
git add dashboard/views.py dashboard/urls.py dashboard/tests.py
git commit -m "feat: admin session series views + scope edit/delete logic"
```

---

### Task 5 : Templates séances récurrentes

**Files:**
- Create: `templates/dashboard/admin/home/session_series_list.html`
- Create: `templates/dashboard/admin/home/session_scope_choice.html`
- Modify: `templates/dashboard/admin/home/session_form.html`

- [ ] **Créer `session_series_list.html`** :

```html
{% extends 'dashboard/admin/layouts/base.html' %}
{% load lucide %}
{% block title %}Séries récurrentes{% endblock %}
{% block content %}
<div class="flex items-center justify-between mb-6">
  <div>
    <h1 class="text-xl font-bold text-gray-900">Séries récurrentes</h1>
    <p class="text-xs text-gray-400 mt-0.5">Séances planifiées automatiquement chaque semaine</p>
  </div>
  <a href="{% url 'admin_session_create' %}" class="inline-flex items-center gap-1.5 px-3 py-2 bg-[#056f77] text-white text-xs font-semibold rounded-sm hover:bg-[#045f66] transition">
    {% lucide "plus" class="w-3.5 h-3.5" %} Nouvelle série
  </a>
</div>

<div class="bg-white rounded-sm border border-gray-100 shadow-sm overflow-hidden">
  <table class="w-full text-sm">
    <thead class="bg-gray-50 border-b border-gray-100">
      <tr>
        <th class="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">Formateur</th>
        <th class="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">Langue</th>
        <th class="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">Jour / Heure</th>
        <th class="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">Période</th>
        <th class="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">Séances</th>
        <th class="px-4 py-3"></th>
      </tr>
    </thead>
    <tbody class="divide-y divide-gray-50">
      {% for s in series_list %}
      <tr class="hover:bg-gray-50/50 transition-colors">
        <td class="px-4 py-3 font-medium text-gray-800">{{ s.teacher }}</td>
        <td class="px-4 py-3 text-gray-600">{{ s.language }}</td>
        <td class="px-4 py-3 text-gray-600">{{ s.get_day_of_week_display }} · {{ s.start_time|time:"H:i" }}–{{ s.end_time|time:"H:i" }}</td>
        <td class="px-4 py-3 text-gray-500 text-xs">
          {{ s.recurrence_start }} → {% if s.recurrence_end %}{{ s.recurrence_end }}{% else %}<span class="text-gray-400">∞ 12 mois</span>{% endif %}
        </td>
        <td class="px-4 py-3">
          <span class="px-2 py-0.5 text-xs font-semibold bg-sky-50 text-sky-700 rounded-sm">{{ s.occurrences.count }} séances</span>
        </td>
        <td class="px-4 py-3 text-right">
          <a href="{% url 'admin_session_series_delete' s.id %}"
             class="inline-flex items-center gap-1 px-2.5 py-1.5 text-xs font-medium text-red-600 border border-red-200 rounded-sm hover:bg-red-50 transition">
            {% lucide "trash-2" class="w-3 h-3" %} Supprimer
          </a>
        </td>
      </tr>
      {% empty %}
      <tr><td colspan="6" class="px-4 py-10 text-center text-sm text-gray-400">Aucune série récurrente</td></tr>
      {% endfor %}
    </tbody>
  </table>
</div>
{% endblock %}
```

- [ ] **Créer `session_scope_choice.html`** :

```html
{% extends 'dashboard/admin/layouts/base.html' %}
{% load lucide %}
{% block title %}Portée de la modification{% endblock %}
{% block content %}
<div class="max-w-lg mx-auto mt-8">
  <div class="bg-white rounded-sm border border-gray-100 shadow-sm overflow-hidden">
    <div class="px-5 py-4 border-b border-gray-100 flex items-center gap-3">
      {% lucide "calendar-range" class="w-5 h-5 text-[#26b2bd]" %}
      <div>
        <h1 class="text-sm font-semibold text-gray-800">Séance récurrente</h1>
        <p class="text-xs text-gray-400 mt-0.5">Cette séance fait partie d'une série. Quelle portée souhaitez-vous appliquer ?</p>
      </div>
    </div>
    <form method="post">
      {% csrf_token %}
      {% for field in form %}
        <input type="hidden" name="{{ field.html_name }}" value="{{ field.value|default:'' }}">
      {% endfor %}
      <div class="p-5 space-y-3">
        <label class="flex items-start gap-3 p-3 border border-gray-200 rounded-sm cursor-pointer hover:bg-gray-50 transition has-[:checked]:border-[#26b2bd] has-[:checked]:bg-[#26b2bd]/5">
          <input type="radio" name="scope" value="this" class="mt-0.5 text-[#26b2bd]" checked>
          <div>
            <p class="text-sm font-semibold text-gray-800">Seulement cette séance</p>
            <p class="text-xs text-gray-400">Les autres séances de la série ne sont pas modifiées</p>
          </div>
        </label>
        <label class="flex items-start gap-3 p-3 border border-gray-200 rounded-sm cursor-pointer hover:bg-gray-50 transition has-[:checked]:border-[#26b2bd] has-[:checked]:bg-[#26b2bd]/5">
          <input type="radio" name="scope" value="this_and_future" class="mt-0.5 text-[#26b2bd]">
          <div>
            <p class="text-sm font-semibold text-gray-800">Cette séance et les suivantes</p>
            <p class="text-xs text-gray-400">Modifie cette séance et toutes les occurrences futures de la série</p>
          </div>
        </label>
        <label class="flex items-start gap-3 p-3 border border-gray-200 rounded-sm cursor-pointer hover:bg-gray-50 transition has-[:checked]:border-[#26b2bd] has-[:checked]:bg-[#26b2bd]/5">
          <input type="radio" name="scope" value="all" class="mt-0.5 text-[#26b2bd]">
          <div>
            <p class="text-sm font-semibold text-gray-800">Toutes les séances de la série</p>
            <p class="text-xs text-gray-400">Modifie toutes les occurrences passées et futures</p>
          </div>
        </label>
      </div>
      <div class="px-5 py-3 border-t border-gray-100 flex justify-end gap-3">
        <a href="{% url 'admin_sessions_list' %}" class="px-4 py-2 border border-gray-200 text-gray-600 text-sm font-medium rounded-sm hover:bg-gray-50 transition">Annuler</a>
        <button type="submit" class="px-5 py-2 bg-[#056f77] text-white text-sm font-semibold rounded-sm hover:bg-[#045f66] transition">Confirmer</button>
      </div>
    </form>
  </div>
</div>
{% endblock %}
```

- [ ] **Commit :**

```bash
git add templates/dashboard/admin/home/session_series_list.html templates/dashboard/admin/home/session_scope_choice.html
git commit -m "feat: session series list + scope choice templates"
```

---

## PARTIE B — Supprimer l'infrastructure modale

### Task 6 : Nettoyer admin scripts.html et base.html

**Files:**
- Modify: `templates/dashboard/admin/includes/scripts.html`
- Modify: `templates/dashboard/admin/layouts/base.html`

- [ ] **Remplacer le contenu de `templates/dashboard/admin/includes/scripts.html`** — supprimer tout le bloc GSAP Modal (lignes 1–91), garder uniquement les notifications :

```html
<script>
// ── Notifications polling ────────────────────────────────────
function toggleNotifPanel() {
  const panel = document.getElementById('notif-panel');
  panel.classList.toggle('hidden');
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

document.addEventListener('click', e => {
  const panel = document.getElementById('notif-panel');
  const btn = document.getElementById('notif-btn');
  if (panel && btn && !panel.contains(e.target) && !btn.contains(e.target)) {
    panel.classList.add('hidden');
  }
});
</script>
```

- [ ] **Retirer le HTML modal de `templates/dashboard/admin/layouts/base.html`** — chercher et supprimer les 3 lignes (41–43) :

```html
  <div id="modal-backdrop" class="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4" style="display:none">
    <div id="modal-panel" class="bg-white rounded-sm shadow-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
      <div id="modal-content" class="p-6"></div>
```

Et la ligne de fermeture `</div>` correspondante (ligne 44).

- [ ] **Faire de même pour teacher** — mêmes suppressions dans :
  - `templates/dashboard/teacher/layouts/base.html` lignes 41–44
  - `templates/dashboard/teacher/includes/scripts.html` — supprimer tout sauf le code non-modal (polling notifs si présent, ou vider)

- [ ] **Commit :**

```bash
git add templates/dashboard/admin/includes/scripts.html templates/dashboard/admin/layouts/base.html
git add templates/dashboard/teacher/includes/scripts.html templates/dashboard/teacher/layouts/base.html
git commit -m "refactor: remove modal infrastructure from admin + teacher base layouts"
```

---

### Task 7 : Mettre à jour les 8 templates liste admin

**Files:**
- Modify: 8 templates dans `templates/dashboard/admin/home/`

Pour chacun, remplacer `onclick="loadModal('{% url '...' %}')"` par `<a href="{% url '...' %}">`.

- [ ] **`languages_list.html`** — remplacer les 3 occurrences `onclick="loadModal(...)"`  par `href` :

```html
<!-- Avant -->
<button onclick="loadModal('{% url 'admin_language_create' %}')" ...>

<!-- Après -->
<a href="{% url 'admin_language_create' %}" class="inline-flex items-center gap-1.5 px-3 py-1.5 bg-cyan-600 text-white text-xs font-semibold rounded-sm hover:bg-cyan-500 transition">
  {% lucide "plus" class="w-3.5 h-3.5" %} Ajouter
</a>
```

Et pour edit :
```html
<!-- Avant -->
<button onclick="loadModal('{% url 'admin_language_edit' lang.id %}')" ...>

<!-- Après -->
<a href="{% url 'admin_language_edit' lang.id %}" class="...même classes...">
  {% lucide "pencil" class="w-3 h-3" %}
</a>
```

- [ ] **`assignments_list.html`** — remplacer les 2 occurrences par `<a href>` vers `admin_assignment_create` et `admin_assignment_edit`.

- [ ] **`evaluations_list.html`** — remplacer les 2 occurrences par `<a href>` vers `admin_evaluation_create` et `admin_evaluation_edit`.

- [ ] **`list_students.html`** — remplacer la 1 occurrence par `<a href>` vers `admin_student_create`.

- [ ] **`list_teachers.html`** — remplacer les 2 occurrences par `<a href>` vers `admin_teacher_create` et `admin_teacher_edit`.

- [ ] **`payments_list.html`** — remplacer les 2 occurrences par `<a href>` vers `admin_payment_create` et `admin_payment_edit`.

- [ ] **`notifications_list.html`** — remplacer la 1 occurrence par `<a href>` vers `admin_notification_create`.

- [ ] **`sessions_list.html`** — supprimer les lignes 12–42 (modal-backdrop, smBackdrop, smPanel, smContent, openSessionModal, closeSessionModal). Remplacer `onclick="openSessionModal(...)` par `<a href="{% url 'admin_session_edit' session.id %}">`.

- [ ] **Commit :**

```bash
git add templates/dashboard/admin/home/
git commit -m "refactor: replace loadModal() calls with direct href links in admin list templates"
```

---

## PARTIE C — Redesign formulaires admin

Le design système appliqué à tous les formulaires :
- **Label** : `block text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1.5`
- **Input** : widget attrs déjà définis via `TW_INPUT` en forms.py
- **Section header** : `flex items-center gap-2.5 px-5 py-3.5 border-b border-gray-100 bg-gray-50/60`
- **Card** : `bg-white rounded-sm border border-gray-100 shadow-sm`
- **Footer** : `sticky bottom-0 bg-white/95 backdrop-blur-sm border-t border-gray-100 px-6 py-3.5 flex justify-between items-center mt-6`
- **Save button** : `inline-flex items-center gap-1.5 px-5 py-2.5 bg-[#056f77] text-white text-sm font-semibold rounded-sm hover:bg-[#045f66] transition`
- **Cancel button** : `inline-flex items-center gap-1.5 px-4 py-2.5 border border-gray-200 text-gray-600 text-sm font-medium rounded-sm hover:bg-gray-50 transition`

### Task 8 : Redesign admin_form.html (formulaire générique)

**Files:**
- Modify: `templates/dashboard/admin/home/admin_form.html`

- [ ] **Réécrire `admin_form.html`** :

```html
{% extends 'dashboard/admin/layouts/base.html' %}
{% load lucide %}
{% block title %}{{ titre }}{% endblock %}

{% block content %}
<div class="flex items-center gap-3 mb-6">
  {% if back_url %}
  <a href="{% url back_url %}" class="w-8 h-8 flex items-center justify-center border border-gray-200 rounded-sm hover:bg-gray-50 transition text-gray-500">
    {% lucide "arrow-left" class="w-4 h-4" %}
  </a>
  {% endif %}
  <div>
    <h1 class="text-lg font-bold text-gray-900">{{ titre }}</h1>
    <p class="text-xs text-gray-400 mt-0.5">Renseignez les champs ci-dessous</p>
  </div>
</div>

{% if messages %}{% for msg in messages %}
<div class="mb-4 px-4 py-3 rounded-sm text-sm font-medium
  {% if msg.tags == 'error' %}bg-red-50 text-red-700 border border-red-200
  {% elif msg.tags == 'success' %}bg-emerald-50 text-emerald-700 border border-emerald-200
  {% else %}bg-sky-50 text-sky-700 border border-sky-200{% endif %}">{{ msg }}</div>
{% endfor %}{% endif %}

<form method="post" enctype="multipart/form-data">
  {% csrf_token %}
  <div class="bg-white rounded-sm border border-gray-100 shadow-sm">
    <div class="p-5 grid grid-cols-1 md:grid-cols-2 gap-5">
      {% for field in form %}
      <div {% if field.field.widget.attrs.rows or field.field.widget.__class__.__name__ == 'SelectMultiple' %}class="md:col-span-2"{% endif %}>
        <label class="block text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1.5" for="{{ field.id_for_label }}">
          {{ field.label }}{% if field.field.required %} <span class="text-red-500">*</span>{% endif %}
        </label>
        {{ field }}
        {% if field.help_text %}<p class="text-xs text-gray-400 mt-1">{{ field.help_text }}</p>{% endif %}
        {% if field.errors %}{% for e in field.errors %}<p class="text-xs text-red-600 mt-1">{{ e }}</p>{% endfor %}{% endif %}
      </div>
      {% endfor %}
    </div>
  </div>

  <div class="sticky bottom-0 bg-white/95 backdrop-blur-sm border-t border-gray-100 px-0 py-4 flex justify-between items-center mt-6">
    {% if back_url %}
    <a href="{% url back_url %}" class="inline-flex items-center gap-1.5 px-4 py-2.5 border border-gray-200 text-gray-600 text-sm font-medium rounded-sm hover:bg-gray-50 transition">Annuler</a>
    {% else %}<div></div>{% endif %}
    <button type="submit" class="inline-flex items-center gap-1.5 px-5 py-2.5 bg-[#056f77] text-white text-sm font-semibold rounded-sm hover:bg-[#045f66] transition">
      {% lucide "save" class="w-4 h-4" %} Enregistrer
    </button>
  </div>
</form>
{% endblock %}
```

- [ ] **Commit :**

```bash
git add templates/dashboard/admin/home/admin_form.html
git commit -m "refactor: redesign admin_form.html — pro layout, no modal artifacts"
```

---

### Task 9 : Redesign session_form.html + section récurrence

**Files:**
- Modify: `templates/dashboard/admin/home/session_form.html`

- [ ] **Réécrire `session_form.html`** :

```html
{% extends 'dashboard/admin/layouts/base.html' %}
{% load lucide %}
{% block title %}{{ titre }}{% endblock %}

{% block content %}
<div class="flex items-center gap-3 mb-6">
  <a href="{% url 'admin_sessions_list' %}" class="w-8 h-8 flex items-center justify-center border border-gray-200 rounded-sm hover:bg-gray-50 transition text-gray-500">
    {% lucide "arrow-left" class="w-4 h-4" %}
  </a>
  <div>
    <h1 class="text-lg font-bold text-gray-900">{{ titre }}</h1>
    <p class="text-xs text-gray-400 mt-0.5">
      {% if session %}Séance du {{ session.date }}{% else %}Nouvelle séance ou série récurrente{% endif %}
    </p>
  </div>
</div>

{% if messages %}{% for msg in messages %}
<div class="mb-4 px-4 py-3 rounded-sm text-sm font-medium
  {% if msg.tags == 'error' %}bg-red-50 text-red-700 border border-red-200
  {% elif msg.tags == 'success' %}bg-emerald-50 text-emerald-700 border border-emerald-200
  {% else %}bg-sky-50 text-sky-700 border border-sky-200{% endif %}">{{ msg }}</div>
{% endfor %}{% endif %}

{% if session and session.series %}
<div class="mb-5 flex items-start gap-3 px-4 py-3 bg-amber-50 border border-amber-200 rounded-sm">
  {% lucide "repeat" class="w-4 h-4 text-amber-600 mt-0.5 shrink-0" %}
  <p class="text-xs text-amber-800">Cette séance fait partie d'une <strong>série récurrente</strong>. La modification vous demandera quelle portée appliquer.</p>
</div>
{% endif %}

<!-- Toggle séance unique / récurrente (création uniquement) -->
{% if not session %}
<div class="flex gap-1 mb-5 p-1 bg-gray-100 rounded-sm w-fit">
  <button type="button" id="tab-single"
    onclick="switchTab('single')"
    class="px-4 py-1.5 text-xs font-semibold rounded-sm transition bg-white shadow-sm text-gray-800">
    Séance unique
  </button>
  <button type="button" id="tab-recurring"
    onclick="switchTab('recurring')"
    class="px-4 py-1.5 text-xs font-semibold rounded-sm transition text-gray-500 hover:text-gray-700">
    Série récurrente
  </button>
</div>
{% endif %}

<!-- ─── Formulaire séance unique ─────────────────────────── -->
<div id="form-single" {% if is_recurring %}class="hidden"{% endif %}>
<form method="post" id="form-single-el">
  {% csrf_token %}
  <div class="space-y-4">

    <div class="bg-white rounded-sm border border-gray-100 shadow-sm">
      <div class="flex items-center gap-2.5 px-5 py-3.5 border-b border-gray-100 bg-gray-50/60">
        {% lucide "info" class="w-4 h-4 text-[#26b2bd]" %}
        <span class="text-xs font-semibold text-gray-600 uppercase tracking-wide">Identification</span>
      </div>
      <div class="p-5 grid grid-cols-1 md:grid-cols-2 gap-4">
        {% for field in form %}{% if field.html_name in 'teacher,language,date,start_time,end_time,duree_minutes,type_seance,status,meeting_link' %}
        <div {% if field.html_name == 'meeting_link' %}class="md:col-span-2"{% endif %}>
          <label class="block text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1.5">{{ field.label }}{% if field.field.required %} <span class="text-red-500">*</span>{% endif %}</label>
          {{ field }}
          {% if field.errors %}{% for e in field.errors %}<p class="text-xs text-red-600 mt-1">{{ e }}</p>{% endfor %}{% endif %}
        </div>
        {% endif %}{% endfor %}
      </div>
    </div>

    <div class="bg-white rounded-sm border border-blue-100 shadow-sm">
      <div class="flex items-center gap-2.5 px-5 py-3.5 border-b border-blue-100 bg-blue-50/40">
        {% lucide "users" class="w-4 h-4 text-blue-600" %}
        <span class="text-xs font-semibold text-gray-600 uppercase tracking-wide">Étudiants assignés</span>
        <span class="text-xs text-gray-400 ml-auto">Ctrl/Cmd pour sélection multiple</span>
      </div>
      <div class="p-5">
        {% for field in form %}{% if field.html_name == 'students' %}
        <label class="block text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1.5">{{ field.label }}</label>
        {{ field }}
        {% if field.errors %}{% for e in field.errors %}<p class="text-xs text-red-600 mt-1">{{ e }}</p>{% endfor %}{% endif %}
        {% endif %}{% endfor %}
      </div>
    </div>

    <div class="bg-white rounded-sm border border-gray-100 shadow-sm">
      <div class="flex items-center gap-2.5 px-5 py-3.5 border-b border-gray-100 bg-gray-50/60">
        {% lucide "book-open" class="w-4 h-4 text-[#26b2bd]" %}
        <span class="text-xs font-semibold text-gray-600 uppercase tracking-wide">Contenu pédagogique</span>
      </div>
      <div class="p-5 space-y-4">
        {% for field in form %}{% if field.html_name in 'theme_cours,observations_formateur,prochaine_etape' %}
        <div>
          <label class="block text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1.5">{{ field.label }}</label>
          {{ field }}
          {% if field.errors %}{% for e in field.errors %}<p class="text-xs text-red-600 mt-1">{{ e }}</p>{% endfor %}{% endif %}
        </div>
        {% endif %}{% endfor %}
      </div>
    </div>

    <div class="bg-white rounded-sm border border-gray-100 shadow-sm">
      <div class="flex items-center gap-2.5 px-5 py-3.5 border-b border-gray-100 bg-gray-50/60">
        {% lucide "bar-chart-2" class="w-4 h-4 text-[#26b2bd]" %}
        <span class="text-xs font-semibold text-gray-600 uppercase tracking-wide">Compétences évaluées</span>
      </div>
      <div class="p-5 grid grid-cols-2 md:grid-cols-3 gap-4">
        {% for field in form %}{% if 'comp_' in field.html_name or field.html_name in 'participation,comprehension_score,engagement' %}
        <div>
          <label class="block text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1.5">{{ field.label }}</label>
          {{ field }}
          {% if field.errors %}{% for e in field.errors %}<p class="text-xs text-red-600 mt-1">{{ e }}</p>{% endfor %}{% endif %}
        </div>
        {% endif %}{% endfor %}
      </div>
    </div>

    <div class="bg-white rounded-sm border border-gray-100 shadow-sm">
      <div class="flex items-center gap-2.5 px-5 py-3.5 border-b border-gray-100 bg-gray-50/60">
        {% lucide "clipboard-check" class="w-4 h-4 text-[#26b2bd]" %}
        <span class="text-xs font-semibold text-gray-600 uppercase tracking-wide">Devoirs & Validation</span>
      </div>
      <div class="p-5 grid grid-cols-1 md:grid-cols-2 gap-4">
        {% for field in form %}{% if field.html_name in 'difficultes,devoir_donne,description_devoir,seance_realisee,fiche_completee,statut_validation' %}
        <div>
          <label class="block text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1.5">{{ field.label }}</label>
          {{ field }}
          {% if field.errors %}{% for e in field.errors %}<p class="text-xs text-red-600 mt-1">{{ e }}</p>{% endfor %}{% endif %}
        </div>
        {% endif %}{% endfor %}
      </div>
    </div>

  </div>
  <div class="sticky bottom-0 bg-white/95 backdrop-blur-sm border-t border-gray-100 py-4 flex justify-between items-center mt-6">
    <a href="{% url 'admin_sessions_list' %}" class="inline-flex items-center gap-1.5 px-4 py-2.5 border border-gray-200 text-gray-600 text-sm font-medium rounded-sm hover:bg-gray-50 transition">Annuler</a>
    <button type="submit" class="inline-flex items-center gap-1.5 px-5 py-2.5 bg-[#056f77] text-white text-sm font-semibold rounded-sm hover:bg-[#045f66] transition">
      {% lucide "save" class="w-4 h-4" %} Enregistrer
    </button>
  </div>
</form>
</div>

<!-- ─── Formulaire série récurrente ─────────────────────── -->
<div id="form-recurring" {% if not is_recurring %}class="hidden"{% endif %}>
<form method="post" id="form-recurring-el">
  {% csrf_token %}
  <input type="hidden" name="is_recurring" value="on">
  <div class="space-y-4">

    <div class="bg-white rounded-sm border border-[#26b2bd]/30 shadow-sm">
      <div class="flex items-center gap-2.5 px-5 py-3.5 border-b border-[#26b2bd]/20 bg-[#26b2bd]/5">
        {% lucide "repeat" class="w-4 h-4 text-[#26b2bd]" %}
        <span class="text-xs font-semibold text-gray-600 uppercase tracking-wide">Planification récurrente</span>
        <span class="ml-auto text-xs text-[#26b2bd] font-medium">Toutes les semaines</span>
      </div>
      <div class="p-5 grid grid-cols-1 md:grid-cols-2 gap-4">
        {% for field in series_form %}
        <div {% if field.html_name in 'notes,students' %}class="md:col-span-2"{% endif %}>
          <label class="block text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1.5">
            {{ field.label }}{% if field.field.required %} <span class="text-red-500">*</span>{% endif %}
          </label>
          {{ field }}
          {% if field.errors %}{% for e in field.errors %}<p class="text-xs text-red-600 mt-1">{{ e }}</p>{% endfor %}{% endif %}
        </div>
        {% endfor %}
      </div>
      <div class="px-5 pb-4">
        <p class="text-xs text-gray-400 bg-gray-50 px-3 py-2 rounded-sm border border-gray-100">
          {% lucide "info" class="w-3 h-3 inline mr-1" %}
          Les séances seront générées automatiquement chaque semaine jusqu'à la date de fin (ou 12 mois si vide).
        </p>
      </div>
    </div>

  </div>
  <div class="sticky bottom-0 bg-white/95 backdrop-blur-sm border-t border-gray-100 py-4 flex justify-between items-center mt-6">
    <a href="{% url 'admin_sessions_list' %}" class="inline-flex items-center gap-1.5 px-4 py-2.5 border border-gray-200 text-gray-600 text-sm font-medium rounded-sm hover:bg-gray-50 transition">Annuler</a>
    <button type="submit" class="inline-flex items-center gap-1.5 px-5 py-2.5 bg-[#26b2bd] text-white text-sm font-semibold rounded-sm hover:opacity-90 transition">
      {% lucide "calendar-range" class="w-4 h-4" %} Créer la série
    </button>
  </div>
</form>
</div>

{% endblock %}

{% block extra_js %}
<script>
function switchTab(tab) {
  const single = document.getElementById('form-single');
  const recurring = document.getElementById('form-recurring');
  const tabSingle = document.getElementById('tab-single');
  const tabRecurring = document.getElementById('tab-recurring');
  if (tab === 'single') {
    single.classList.remove('hidden');
    recurring.classList.add('hidden');
    tabSingle.classList.add('bg-white', 'shadow-sm', 'text-gray-800');
    tabSingle.classList.remove('text-gray-500');
    tabRecurring.classList.remove('bg-white', 'shadow-sm', 'text-gray-800');
    tabRecurring.classList.add('text-gray-500');
  } else {
    single.classList.add('hidden');
    recurring.classList.remove('hidden');
    tabRecurring.classList.add('bg-white', 'shadow-sm', 'text-gray-800');
    tabRecurring.classList.remove('text-gray-500');
    tabSingle.classList.remove('bg-white', 'shadow-sm', 'text-gray-800');
    tabSingle.classList.add('text-gray-500');
  }
}
</script>
{% endblock %}
```

- [ ] **Commit :**

```bash
git add templates/dashboard/admin/home/session_form.html
git commit -m "refactor: redesign session_form.html + recurring series tab"
```

---

### Task 10 : Redesign student_form.html, teacher_form.html

**Files:**
- Modify: `templates/dashboard/admin/home/student_form.html`
- Modify: `templates/dashboard/admin/home/teacher_form.html`

- [ ] **Réécrire `student_form.html`** :

```html
{% extends 'dashboard/admin/layouts/base.html' %}
{% load lucide %}
{% block title %}{{ titre }}{% endblock %}

{% block content %}
<div class="flex items-center gap-3 mb-6">
  <a href="{% url 'admin_students' %}" class="w-8 h-8 flex items-center justify-center border border-gray-200 rounded-sm hover:bg-gray-50 transition text-gray-500">
    {% lucide "arrow-left" class="w-4 h-4" %}
  </a>
  <div>
    <p class="text-xs text-gray-400 uppercase tracking-wide font-medium">Étudiants → {{ titre }}</p>
    <h1 class="text-lg font-bold text-gray-900 mt-0.5">{{ titre }}</h1>
  </div>
</div>

{% if messages %}{% for msg in messages %}
<div class="mb-4 px-4 py-3 rounded-sm text-sm font-medium
  {% if msg.tags == 'error' %}bg-red-50 text-red-700 border border-red-200
  {% elif msg.tags == 'success' %}bg-emerald-50 text-emerald-700 border border-emerald-200
  {% else %}bg-sky-50 text-sky-700 border border-sky-200{% endif %}">{{ msg }}</div>
{% endfor %}{% endif %}

<form method="post">
  {% csrf_token %}
  <div class="space-y-4">

    {% if user_form %}
    <div class="bg-white rounded-sm border border-gray-100 shadow-sm">
      <div class="flex items-center gap-2.5 px-5 py-3.5 border-b border-gray-100 bg-gray-50/60">
        {% lucide "user" class="w-4 h-4 text-violet-500" %}
        <span class="text-xs font-semibold text-gray-600 uppercase tracking-wide">Compte utilisateur</span>
      </div>
      <div class="p-5 grid grid-cols-1 md:grid-cols-2 gap-4">
        {% for field in user_form %}
        <div>
          <label class="block text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1.5">{{ field.label }}{% if field.field.required %} <span class="text-red-500">*</span>{% endif %}</label>
          {{ field }}
          {% if field.errors %}{% for e in field.errors %}<p class="text-xs text-red-600 mt-1">{{ e }}</p>{% endfor %}{% endif %}
        </div>
        {% endfor %}
      </div>
    </div>
    {% endif %}

    <div class="bg-white rounded-sm border border-gray-100 shadow-sm">
      <div class="flex items-center gap-2.5 px-5 py-3.5 border-b border-gray-100 bg-gray-50/60">
        {% lucide "graduation-cap" class="w-4 h-4 text-violet-500" %}
        <span class="text-xs font-semibold text-gray-600 uppercase tracking-wide">Profil étudiant</span>
      </div>
      <div class="p-5 grid grid-cols-1 md:grid-cols-2 gap-4">
        {% for field in form %}
        <div {% if field.html_name in 'current_teachers,objectif_formation' %}class="md:col-span-2"{% endif %}>
          <label class="block text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1.5">{{ field.label }}{% if field.field.required %} <span class="text-red-500">*</span>{% endif %}</label>
          {{ field }}
          {% if field.errors %}{% for e in field.errors %}<p class="text-xs text-red-600 mt-1">{{ e }}</p>{% endfor %}{% endif %}
        </div>
        {% endfor %}
      </div>
    </div>

  </div>
  <div class="sticky bottom-0 bg-white/95 backdrop-blur-sm border-t border-gray-100 py-4 flex justify-between items-center mt-6">
    <a href="{% url 'admin_students' %}" class="inline-flex items-center gap-1.5 px-4 py-2.5 border border-gray-200 text-gray-600 text-sm font-medium rounded-sm hover:bg-gray-50 transition">Annuler</a>
    <button type="submit" class="inline-flex items-center gap-1.5 px-5 py-2.5 bg-[#056f77] text-white text-sm font-semibold rounded-sm hover:bg-[#045f66] transition">
      {% lucide "save" class="w-4 h-4" %} Enregistrer
    </button>
  </div>
</form>
{% endblock %}
```

- [ ] **Réécrire `teacher_form.html`** (même structure, adapter les libellés et couleurs amber) :

```html
{% extends 'dashboard/admin/layouts/base.html' %}
{% load lucide %}
{% block title %}{{ titre }}{% endblock %}

{% block content %}
<div class="flex items-center gap-3 mb-6">
  <a href="{% url 'admin_teachers' %}" class="w-8 h-8 flex items-center justify-center border border-gray-200 rounded-sm hover:bg-gray-50 transition text-gray-500">
    {% lucide "arrow-left" class="w-4 h-4" %}
  </a>
  <div>
    <p class="text-xs text-gray-400 uppercase tracking-wide font-medium">Formateurs → {{ titre }}</p>
    <h1 class="text-lg font-bold text-gray-900 mt-0.5">{{ titre }}</h1>
  </div>
</div>

{% if messages %}{% for msg in messages %}
<div class="mb-4 px-4 py-3 rounded-sm text-sm font-medium
  {% if msg.tags == 'error' %}bg-red-50 text-red-700 border border-red-200
  {% elif msg.tags == 'success' %}bg-emerald-50 text-emerald-700 border border-emerald-200
  {% else %}bg-sky-50 text-sky-700 border border-sky-200{% endif %}">{{ msg }}</div>
{% endfor %}{% endif %}

<form method="post">
  {% csrf_token %}
  <div class="space-y-4">

    {% if user_form %}
    <div class="bg-white rounded-sm border border-gray-100 shadow-sm">
      <div class="flex items-center gap-2.5 px-5 py-3.5 border-b border-gray-100 bg-gray-50/60">
        {% lucide "user" class="w-4 h-4 text-amber-500" %}
        <span class="text-xs font-semibold text-gray-600 uppercase tracking-wide">Compte utilisateur</span>
      </div>
      <div class="p-5 grid grid-cols-1 md:grid-cols-2 gap-4">
        {% for field in user_form %}
        <div>
          <label class="block text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1.5">{{ field.label }}{% if field.field.required %} <span class="text-red-500">*</span>{% endif %}</label>
          {{ field }}
          {% if field.errors %}{% for e in field.errors %}<p class="text-xs text-red-600 mt-1">{{ e }}</p>{% endfor %}{% endif %}
        </div>
        {% endfor %}
      </div>
    </div>
    {% endif %}

    <div class="bg-white rounded-sm border border-gray-100 shadow-sm">
      <div class="flex items-center gap-2.5 px-5 py-3.5 border-b border-gray-100 bg-gray-50/60">
        {% lucide "briefcase" class="w-4 h-4 text-amber-500" %}
        <span class="text-xs font-semibold text-gray-600 uppercase tracking-wide">Profil formateur</span>
      </div>
      <div class="p-5 grid grid-cols-1 md:grid-cols-2 gap-4">
        {% for field in form %}
        <div {% if field.html_name == 'languages' %}class="md:col-span-2"{% endif %}>
          <label class="block text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1.5">{{ field.label }}{% if field.field.required %} <span class="text-red-500">*</span>{% endif %}</label>
          {{ field }}
          {% if field.errors %}{% for e in field.errors %}<p class="text-xs text-red-600 mt-1">{{ e }}</p>{% endfor %}{% endif %}
        </div>
        {% endfor %}
      </div>
    </div>

  </div>
  <div class="sticky bottom-0 bg-white/95 backdrop-blur-sm border-t border-gray-100 py-4 flex justify-between items-center mt-6">
    <a href="{% url 'admin_teachers' %}" class="inline-flex items-center gap-1.5 px-4 py-2.5 border border-gray-200 text-gray-600 text-sm font-medium rounded-sm hover:bg-gray-50 transition">Annuler</a>
    <button type="submit" class="inline-flex items-center gap-1.5 px-5 py-2.5 bg-[#056f77] text-white text-sm font-semibold rounded-sm hover:bg-[#045f66] transition">
      {% lucide "save" class="w-4 h-4" %} Enregistrer
    </button>
  </div>
</form>
{% endblock %}
```

- [ ] **Commit :**

```bash
git add templates/dashboard/admin/home/student_form.html templates/dashboard/admin/home/teacher_form.html
git commit -m "refactor: redesign student_form.html + teacher_form.html"
```

---

### Task 11 : Redesign paiement_formateur_form.html + certificate_form.html

**Files:**
- Modify: `templates/dashboard/admin/home/paiement_formateur_form.html`
- Modify: `templates/dashboard/admin/home/certificate_form.html`

- [ ] **Lire les templates actuels** pour connaître leur back_url et leurs sections :

```bash
head -30 templates/dashboard/admin/home/paiement_formateur_form.html
head -30 templates/dashboard/admin/home/certificate_form.html
```

- [ ] **Réécrire `paiement_formateur_form.html`** avec le layout unifié :

```html
{% extends 'dashboard/admin/layouts/base.html' %}
{% load lucide %}
{% block title %}{{ titre }}{% endblock %}

{% block content %}
<div class="flex items-center gap-3 mb-6">
  <a href="{% url 'admin_paiements_formateurs' %}" class="w-8 h-8 flex items-center justify-center border border-gray-200 rounded-sm hover:bg-gray-50 transition text-gray-500">
    {% lucide "arrow-left" class="w-4 h-4" %}
  </a>
  <div>
    <p class="text-xs text-gray-400 uppercase tracking-wide font-medium">Paiements formateurs → {{ titre }}</p>
    <h1 class="text-lg font-bold text-gray-900 mt-0.5">{{ titre }}</h1>
  </div>
</div>

{% if messages %}{% for msg in messages %}
<div class="mb-4 px-4 py-3 rounded-sm text-sm font-medium
  {% if msg.tags == 'error' %}bg-red-50 text-red-700 border border-red-200
  {% elif msg.tags == 'success' %}bg-emerald-50 text-emerald-700 border border-emerald-200
  {% else %}bg-sky-50 text-sky-700 border border-sky-200{% endif %}">{{ msg }}</div>
{% endfor %}{% endif %}

<div class="max-w-2xl">
<form method="post">
  {% csrf_token %}
  <div class="space-y-4">

    <div class="bg-white rounded-sm border border-gray-100 shadow-sm">
      <div class="flex items-center gap-2.5 px-5 py-3.5 border-b border-gray-100 bg-gray-50/60">
        {% lucide "user-check" class="w-4 h-4 text-teal-500" %}
        <span class="text-xs font-semibold text-gray-600 uppercase tracking-wide">Formateur & Période</span>
      </div>
      <div class="p-5 grid grid-cols-1 md:grid-cols-2 gap-4">
        {% for field in form %}{% if field.html_name in 'formateur,periode_debut,periode_fin,statut' %}
        <div>
          <label class="block text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1.5">{{ field.label }}{% if field.field.required %} <span class="text-red-500">*</span>{% endif %}</label>
          {{ field }}
          {% if field.errors %}{% for e in field.errors %}<p class="text-xs text-red-600 mt-1">{{ e }}</p>{% endfor %}{% endif %}
        </div>
        {% endif %}{% endfor %}
      </div>
    </div>

    <div class="bg-white rounded-sm border border-gray-100 shadow-sm">
      <div class="flex items-center gap-2.5 px-5 py-3.5 border-b border-gray-100 bg-gray-50/60">
        {% lucide "banknote" class="w-4 h-4 text-teal-500" %}
        <span class="text-xs font-semibold text-gray-600 uppercase tracking-wide">Montant & Notes</span>
      </div>
      <div class="p-5 grid grid-cols-1 md:grid-cols-2 gap-4">
        {% for field in form %}{% if field.html_name not in 'formateur,periode_debut,periode_fin,statut' %}
        <div {% if field.html_name == 'notes' %}class="md:col-span-2"{% endif %}>
          <label class="block text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1.5">{{ field.label }}{% if field.field.required %} <span class="text-red-500">*</span>{% endif %}</label>
          {{ field }}
          {% if field.errors %}{% for e in field.errors %}<p class="text-xs text-red-600 mt-1">{{ e }}</p>{% endfor %}{% endif %}
        </div>
        {% endif %}{% endfor %}
      </div>
    </div>

  </div>
  <div class="sticky bottom-0 bg-white/95 backdrop-blur-sm border-t border-gray-100 py-4 flex justify-between items-center mt-6">
    <a href="{% url 'admin_paiements_formateurs' %}" class="inline-flex items-center gap-1.5 px-4 py-2.5 border border-gray-200 text-gray-600 text-sm font-medium rounded-sm hover:bg-gray-50 transition">Annuler</a>
    <button type="submit" class="inline-flex items-center gap-1.5 px-5 py-2.5 bg-[#056f77] text-white text-sm font-semibold rounded-sm hover:bg-[#045f66] transition">
      {% lucide "save" class="w-4 h-4" %} Enregistrer
    </button>
  </div>
</form>
</div>
{% endblock %}
```

- [ ] **Réécrire `certificate_form.html`** avec le même layout :

```html
{% extends 'dashboard/admin/layouts/base.html' %}
{% load lucide %}
{% block title %}{{ titre }}{% endblock %}

{% block content %}
<div class="flex items-center gap-3 mb-6">
  <a href="{% url 'admin_certificates_list' %}" class="w-8 h-8 flex items-center justify-center border border-gray-200 rounded-sm hover:bg-gray-50 transition text-gray-500">
    {% lucide "arrow-left" class="w-4 h-4" %}
  </a>
  <div>
    <p class="text-xs text-gray-400 uppercase tracking-wide font-medium">Certificats → {{ titre }}</p>
    <h1 class="text-lg font-bold text-gray-900 mt-0.5">{{ titre }}</h1>
  </div>
</div>

{% if messages %}{% for msg in messages %}
<div class="mb-4 px-4 py-3 rounded-sm text-sm font-medium
  {% if msg.tags == 'error' %}bg-red-50 text-red-700 border border-red-200
  {% elif msg.tags == 'success' %}bg-emerald-50 text-emerald-700 border border-emerald-200
  {% else %}bg-sky-50 text-sky-700 border border-sky-200{% endif %}">{{ msg }}</div>
{% endfor %}{% endif %}

<div class="max-w-2xl">
<form method="post">
  {% csrf_token %}
  <div class="space-y-4">

    <div class="bg-white rounded-sm border border-gray-100 shadow-sm">
      <div class="flex items-center gap-2.5 px-5 py-3.5 border-b border-gray-100 bg-gray-50/60">
        {% lucide "user" class="w-4 h-4 text-yellow-500" %}
        <span class="text-xs font-semibold text-gray-600 uppercase tracking-wide">Étudiant & Formation</span>
      </div>
      <div class="p-5 grid grid-cols-1 md:grid-cols-2 gap-4">
        {% for field in form %}{% if field.html_name in 'student,language,issued_date,duree_formation' %}
        <div>
          <label class="block text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1.5">{{ field.label }}{% if field.field.required %} <span class="text-red-500">*</span>{% endif %}</label>
          {{ field }}
          {% if field.errors %}{% for e in field.errors %}<p class="text-xs text-red-600 mt-1">{{ e }}</p>{% endfor %}{% endif %}
        </div>
        {% endif %}{% endfor %}
      </div>
    </div>

    <div class="bg-white rounded-sm border border-gray-100 shadow-sm">
      <div class="flex items-center gap-2.5 px-5 py-3.5 border-b border-gray-100 bg-gray-50/60">
        {% lucide "award" class="w-4 h-4 text-yellow-500" %}
        <span class="text-xs font-semibold text-gray-600 uppercase tracking-wide">Compétences & Appréciation</span>
      </div>
      <div class="p-5 space-y-4">
        {% for field in form %}{% if field.html_name not in 'student,language,issued_date,duree_formation' %}
        <div>
          <label class="block text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1.5">{{ field.label }}{% if field.field.required %} <span class="text-red-500">*</span>{% endif %}</label>
          {{ field }}
          {% if field.errors %}{% for e in field.errors %}<p class="text-xs text-red-600 mt-1">{{ e }}</p>{% endfor %}{% endif %}
        </div>
        {% endif %}{% endfor %}
      </div>
    </div>

  </div>
  <div class="sticky bottom-0 bg-white/95 backdrop-blur-sm border-t border-gray-100 py-4 flex justify-between items-center mt-6">
    <a href="{% url 'admin_certificates_list' %}" class="inline-flex items-center gap-1.5 px-4 py-2.5 border border-gray-200 text-gray-600 text-sm font-medium rounded-sm hover:bg-gray-50 transition">Annuler</a>
    <button type="submit" class="inline-flex items-center gap-1.5 px-5 py-2.5 bg-[#056f77] text-white text-sm font-semibold rounded-sm hover:bg-[#045f66] transition">
      {% lucide "save" class="w-4 h-4" %} Enregistrer
    </button>
  </div>
</form>
</div>
{% endblock %}
```

- [ ] **Commit :**

```bash
git add templates/dashboard/admin/home/paiement_formateur_form.html templates/dashboard/admin/home/certificate_form.html
git commit -m "refactor: redesign paiement_formateur_form + certificate_form"
```

---

## PARTIE D — Teacher modals → pages

### Task 12 : Vues + URLs teacher assignments

**Files:**
- Modify: `dashboard/views.py` — refactoriser `teacher_assignments`, ajouter `teacher_assignment_create/edit/delete`
- Modify: `dashboard/urls.py`
- Create: `templates/dashboard/teacher/home/assignment_form.html`

- [ ] **Remplacer `teacher_assignments`** (views.py ligne ~969) — retirer le POST JSON :

```python
@teacher_required
def teacher_assignments(request):
    teacher = get_object_or_404(Teacher, user=request.user)
    languages = Language.objects.filter(teachers=teacher)
    assignments = Assignment.objects.filter(language__in=languages).order_by('-created_at')
    return render(request, 'dashboard/teacher/home/assignments.html', {
        'teacher': teacher, 'assignments': assignments, 'languages': languages,
        'segment': 'assignments',
    })


@teacher_required
def teacher_assignment_create(request):
    teacher = get_object_or_404(Teacher, user=request.user)
    languages = Language.objects.filter(teachers=teacher)
    if request.method == 'POST':
        form = AssignmentAdminForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Devoir créé.")
            return redirect('teacher_assignments')
    else:
        form = AssignmentAdminForm()
    return render(request, 'dashboard/teacher/home/assignment_form.html', {
        'form': form, 'titre': 'Nouveau devoir', 'languages': languages,
    })


@teacher_required
def teacher_assignment_edit(request, assign_id):
    assignment = get_object_or_404(Assignment, id=assign_id)
    teacher = get_object_or_404(Teacher, user=request.user)
    languages = Language.objects.filter(teachers=teacher)
    if request.method == 'POST':
        form = AssignmentAdminForm(request.POST, instance=assignment)
        if form.is_valid():
            form.save()
            messages.success(request, "Devoir mis à jour.")
            return redirect('teacher_assignments')
    else:
        form = AssignmentAdminForm(instance=assignment)
    return render(request, 'dashboard/teacher/home/assignment_form.html', {
        'form': form, 'assignment': assignment,
        'titre': f'Modifier — {assignment.title}', 'languages': languages,
    })


@teacher_required
def teacher_assignment_delete(request, assign_id):
    assignment = get_object_or_404(Assignment, id=assign_id)
    if request.method == 'POST':
        assignment.delete()
        messages.success(request, "Devoir supprimé.")
        return redirect('teacher_assignments')
    return render(request, 'dashboard/teacher/home/assignment_form.html', {
        'assignment': assignment, 'confirming_delete': True,
        'titre': f'Supprimer — {assignment.title}',
    })
```

- [ ] **Ajouter les imports manquants** dans urls.py et les URLs :

```python
# Dans urls.py, ajouter à l'import :
from dashboard.views import teacher_assignment_create, teacher_assignment_edit, teacher_assignment_delete

# Dans urlpatterns :
path('teacher/assignments/creer/', teacher_assignment_create, name='teacher_assignment_create'),
path('teacher/assignments/<int:assign_id>/modifier/', teacher_assignment_edit, name='teacher_assignment_edit'),
path('teacher/assignments/<int:assign_id>/supprimer/', teacher_assignment_delete, name='teacher_assignment_delete'),
```

- [ ] **Créer `templates/dashboard/teacher/home/assignment_form.html`** :

```html
{% extends 'dashboard/teacher/layouts/base.html' %}
{% load lucide %}
{% block title %}{{ titre }}{% endblock %}

{% block content %}
<div class="flex items-center gap-3 mb-6">
  <a href="{% url 'teacher_assignments' %}" class="w-8 h-8 flex items-center justify-center border border-gray-200 rounded-sm hover:bg-gray-50 transition text-gray-500">
    {% lucide "arrow-left" class="w-4 h-4" %}
  </a>
  <div>
    <p class="text-xs text-gray-400 uppercase tracking-wide font-medium">Devoirs → {{ titre }}</p>
    <h1 class="text-lg font-bold text-gray-900 mt-0.5">{{ titre }}</h1>
  </div>
</div>

{% if confirming_delete %}
<div class="max-w-md mx-auto mt-8 bg-white rounded-sm border border-red-100 shadow-sm p-6">
  <p class="text-sm text-gray-700 mb-4">Supprimer le devoir <strong>{{ assignment.title }}</strong> ? Cette action est irréversible.</p>
  <form method="post" class="flex justify-end gap-3">
    {% csrf_token %}
    <a href="{% url 'teacher_assignments' %}" class="px-4 py-2.5 border border-gray-200 text-gray-600 text-sm font-medium rounded-sm hover:bg-gray-50 transition">Annuler</a>
    <button type="submit" class="px-4 py-2.5 bg-red-600 text-white text-sm font-semibold rounded-sm hover:bg-red-700 transition">Supprimer</button>
  </form>
</div>
{% else %}

{% if messages %}{% for msg in messages %}
<div class="mb-4 px-4 py-3 rounded-sm text-sm font-medium
  {% if msg.tags == 'error' %}bg-red-50 text-red-700 border border-red-200
  {% elif msg.tags == 'success' %}bg-emerald-50 text-emerald-700 border border-emerald-200
  {% else %}bg-sky-50 text-sky-700 border border-sky-200{% endif %}">{{ msg }}</div>
{% endfor %}{% endif %}

<div class="max-w-2xl">
<form method="post">
  {% csrf_token %}
  <div class="bg-white rounded-sm border border-gray-100 shadow-sm">
    <div class="flex items-center gap-2.5 px-5 py-3.5 border-b border-gray-100 bg-gray-50/60">
      {% lucide "file-text" class="w-4 h-4 text-[#26b2bd]" %}
      <span class="text-xs font-semibold text-gray-600 uppercase tracking-wide">Informations du devoir</span>
    </div>
    <div class="p-5 grid grid-cols-1 md:grid-cols-2 gap-4">
      {% for field in form %}
      <div {% if field.html_name in 'description,file' %}class="md:col-span-2"{% endif %}>
        <label class="block text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1.5">{{ field.label }}{% if field.field.required %} <span class="text-red-500">*</span>{% endif %}</label>
        {{ field }}
        {% if field.errors %}{% for e in field.errors %}<p class="text-xs text-red-600 mt-1">{{ e }}</p>{% endfor %}{% endif %}
      </div>
      {% endfor %}
    </div>
  </div>
  <div class="sticky bottom-0 bg-white/95 backdrop-blur-sm border-t border-gray-100 py-4 flex justify-between items-center mt-6">
    <a href="{% url 'teacher_assignments' %}" class="inline-flex items-center gap-1.5 px-4 py-2.5 border border-gray-200 text-gray-600 text-sm font-medium rounded-sm hover:bg-gray-50 transition">Annuler</a>
    <button type="submit" class="inline-flex items-center gap-1.5 px-5 py-2.5 bg-[#056f77] text-white text-sm font-semibold rounded-sm hover:bg-[#045f66] transition">
      {% lucide "save" class="w-4 h-4" %} Enregistrer
    </button>
  </div>
</form>
</div>
{% endif %}
{% endblock %}
```

- [ ] **Mettre à jour `assignments.html`** — supprimer le modal inline (lignes 94–160), remplacer le bouton "Nouveau Devoir" :

```html
<!-- Remplacer : onclick="openAddModal()" -->
<!-- Par : -->
<a href="{% url 'teacher_assignment_create' %}" class="inline-flex items-center gap-1.5 px-3 py-1.5 bg-[#26b2bd] text-white text-xs font-semibold rounded-sm hover:opacity-90 transition">
  {% lucide "plus" class="w-3.5 h-3.5" %} Nouveau devoir
</a>
```

Et dans la table, remplacer `onclick="openEditAssignmentModal({{ assignment.id }})"` par :

```html
<a href="{% url 'teacher_assignment_edit' assignment.id %}" class="...">{% lucide "pencil" class="w-3 h-3" %}</a>
<a href="{% url 'teacher_assignment_delete' assignment.id %}" class="...">{% lucide "trash-2" class="w-3 h-3" %}</a>
```

- [ ] **Commit :**

```bash
git add dashboard/views.py dashboard/urls.py templates/dashboard/teacher/home/
git commit -m "feat: teacher assignment CRUD pages — replace JSON modal with standard form views"
```

---

### Task 13 : Supprimer modals teacher resources + evaluations + courses

**Files:**
- Modify: `templates/dashboard/teacher/home/resources.html`
- Modify: `templates/dashboard/teacher/home/evaluations.html`
- Modify: `templates/dashboard/teacher/home/courses.html`
- Create: `templates/dashboard/teacher/home/resource_form.html`

Les vues `resource_create` et `resource_edit` existent déjà et font un `redirect()`. Il faut juste créer un template de formulaire et supprimer les modals inline.

- [ ] **Créer `resource_form.html`** :

```html
{% extends 'dashboard/teacher/layouts/base.html' %}
{% load lucide %}
{% block title %}{{ titre|default:"Ressource" }}{% endblock %}

{% block content %}
<div class="flex items-center gap-3 mb-6">
  <a href="{% url 'teacher_resources_dashboard' %}" class="w-8 h-8 flex items-center justify-center border border-gray-200 rounded-sm hover:bg-gray-50 transition text-gray-500">
    {% lucide "arrow-left" class="w-4 h-4" %}
  </a>
  <div>
    <p class="text-xs text-gray-400 uppercase tracking-wide font-medium">Ressources → {{ titre|default:"Nouvelle ressource" }}</p>
    <h1 class="text-lg font-bold text-gray-900 mt-0.5">{{ titre|default:"Nouvelle ressource" }}</h1>
  </div>
</div>

{% if messages %}{% for msg in messages %}
<div class="mb-4 px-4 py-3 rounded-sm text-sm font-medium
  {% if msg.tags == 'error' %}bg-red-50 text-red-700 border border-red-200
  {% elif msg.tags == 'success' %}bg-emerald-50 text-emerald-700 border border-emerald-200
  {% else %}bg-sky-50 text-sky-700 border border-sky-200{% endif %}">{{ msg }}</div>
{% endfor %}{% endif %}

<div class="max-w-2xl">
<form method="post" enctype="multipart/form-data"
  action="{% if resource %}{% url 'resource_edit' resource.id %}{% else %}{% url 'resource_create' %}{% endif %}">
  {% csrf_token %}
  <div class="bg-white rounded-sm border border-gray-100 shadow-sm">
    <div class="flex items-center gap-2.5 px-5 py-3.5 border-b border-gray-100 bg-gray-50/60">
      {% lucide "file-plus" class="w-4 h-4 text-[#26b2bd]" %}
      <span class="text-xs font-semibold text-gray-600 uppercase tracking-wide">Informations de la ressource</span>
    </div>
    <div class="p-5 grid grid-cols-1 md:grid-cols-2 gap-4">
      {% for field in form %}
      <div {% if field.html_name in 'description,students,languages' %}class="md:col-span-2"{% endif %}>
        <label class="block text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1.5">{{ field.label }}{% if field.field.required %} <span class="text-red-500">*</span>{% endif %}</label>
        {{ field }}
        {% if field.errors %}{% for e in field.errors %}<p class="text-xs text-red-600 mt-1">{{ e }}</p>{% endfor %}{% endif %}
      </div>
      {% endfor %}
    </div>
  </div>
  <div class="sticky bottom-0 bg-white/95 backdrop-blur-sm border-t border-gray-100 py-4 flex justify-between items-center mt-6">
    <a href="{% url 'teacher_resources_dashboard' %}" class="inline-flex items-center gap-1.5 px-4 py-2.5 border border-gray-200 text-gray-600 text-sm font-medium rounded-sm hover:bg-gray-50 transition">Annuler</a>
    <button type="submit" class="inline-flex items-center gap-1.5 px-5 py-2.5 bg-[#056f77] text-white text-sm font-semibold rounded-sm hover:bg-[#045f66] transition">
      {% lucide "save" class="w-4 h-4" %} Enregistrer
    </button>
  </div>
</form>
</div>
{% endblock %}
```

- [ ] **Modifier `resource_create` view** pour qu'elle affiche le formulaire sur GET :

```python
@login_required
def resource_create(request):
    if request.user.role != "teacher":
        return redirect('dashboard')
    teacher = get_object_or_404(Teacher, user=request.user)
    if request.method == 'POST':
        form = ResourceForm(request.POST, request.FILES, teacher=teacher)
        if form.is_valid():
            resource = form.save(commit=False)
            resource.save()
            form.save_m2m()
            messages.success(request, "Ressource créée.")
            return redirect('teacher_resources_dashboard')
    else:
        form = ResourceForm(teacher=teacher)
    return render(request, 'dashboard/teacher/home/resource_form.html', {
        'form': form, 'titre': 'Nouvelle ressource',
    })
```

- [ ] **Modifier `resource_edit` view** pour afficher le formulaire sur GET :

```python
@login_required
def resource_edit(request, resource_id):
    if request.user.role != "teacher":
        return redirect('dashboard')
    resource = get_object_or_404(Resource, id=resource_id)
    teacher = get_object_or_404(Teacher, user=request.user)
    if request.method == 'POST':
        form = ResourceForm(request.POST, request.FILES, instance=resource)
        if form.is_valid():
            form.save()
            messages.success(request, "Ressource mise à jour.")
            return redirect('teacher_resources_dashboard')
    else:
        form = ResourceForm(instance=resource, teacher=teacher)
    return render(request, 'dashboard/teacher/home/resource_form.html', {
        'form': form, 'resource': resource, 'titre': f'Modifier — {resource.title}',
    })
```

- [ ] **Ajouter URL GET pour resource_create** dans urls.py (il existe peut-être déjà) :

```python
path('teacher/resources/creer/', resource_create, name='resource_create'),
path('teacher/resources/<int:resource_id>/modifier/', resource_edit, name='resource_edit'),
```

- [ ] **Mettre à jour `resources.html`** — supprimer les lignes incluant `resource_create_modal.html` et `resource_edit_modal.html`, remplacer le bouton create :

```html
<!-- Remplacer onclick="openCreateResourceModal()" -->
<a href="{% url 'resource_create' %}" class="inline-flex items-center gap-1.5 px-3 py-1.5 bg-[#26b2bd] text-white text-xs font-semibold rounded-sm hover:opacity-90 transition">
  {% lucide "plus" class="w-3.5 h-3.5" %} Ajouter
</a>
```

Et remplacer `onclick="openEditResourceModal({{ resource.id }})"` par `<a href="{% url 'resource_edit' resource.id %}">`.

- [ ] **Mettre à jour `evaluations.html`** — les modals sont readonly (détail). Remplacer chaque `onclick="openEvalModal({{ evaluation.id }})"` par un lien vers la page de détail d'évaluation existante, ou simplement supprimer le modal et afficher les données dans la liste directement. Supprimer tout le bloc `{% for evaluation in evaluations %}` de modals (lignes 78–138) et les fonctions JS correspondantes.

- [ ] **Mettre à jour `courses.html`** — supprimer le modal placeholder (aucun backend), supprimer le bouton "Nouveau Cours" ou le remplacer par un lien informatif.

- [ ] **Commit :**

```bash
git add dashboard/views.py dashboard/urls.py templates/dashboard/teacher/home/
git commit -m "refactor: teacher resources/evaluations/courses — remove modal, add dedicated resource form page"
```

---

## PARTIE E — Graphes dynamiques

### Task 14 : Corriger admin_dashboard view + ajouter données graphes

**Files:**
- Modify: `dashboard/views.py` — fonction `admin_dashboard` (ligne 1830)

- [ ] **Ajouter `marge_nette` et `revenue_data` dans le contexte** — remplacer le bloc graphes (lignes ~1911–1935) par :

```python
    # ── Graphes : séances sur 6 mois ─────────────────────────────
    labels = []
    completed_data = []
    scheduled_data = []
    revenue_data = []
    new_students_data = []

    for i in range(5, -1, -1):
        ref = today.replace(day=1)
        m = ref.month - i
        y = ref.year
        while m <= 0:
            m += 12
            y -= 1
        first_day = _date(y, m, 1)
        if m == 12:
            last_day = _date(y + 1, 1, 1)
        else:
            last_day = _date(y, m + 1, 1)

        labels.append(first_day.strftime('%b %Y'))
        completed_data.append(
            Session.objects.filter(status='completed', date__gte=first_day, date__lt=last_day).count()
        )
        scheduled_data.append(
            Session.objects.filter(status='scheduled', date__gte=first_day, date__lt=last_day).count()
        )
        rev = Payment.objects.filter(
            status='paid', payment_date__gte=first_day, payment_date__lt=last_day
        ).aggregate(total=Sum('amount'))['total'] or 0
        revenue_data.append(float(rev))

        ns = Student.objects.filter(
            date_joined__gte=first_day, date_joined__lt=last_day
        ).count()
        new_students_data.append(ns)

    marge_nette = float(revenue_total) - float(total_paiements_formateurs)
```

- [ ] **Ajouter dans le `context` dict** (après ligne ~1968) :

```python
        'marge_nette': round(marge_nette, 2),
        'revenue_labels': _json.dumps(labels),
        'revenue_data': _json.dumps(revenue_data),
        'new_students_labels': _json.dumps(labels),
        'new_students_data': _json.dumps(new_students_data),
```

- [ ] **Commit :**

```bash
git add dashboard/views.py
git commit -m "fix: admin_dashboard view — marge_nette Python-side, add revenue + students monthly data"
```

---

### Task 15 : Mettre à jour index.html — graphes

**Files:**
- Modify: `templates/dashboard/admin/home/index.html`

- [ ] **Corriger le calcul marge nette** (ligne ~120) — remplacer :

```html
<!-- Avant -->
<span class="font-bold text-emerald-600">{{ revenue_total|add:"-"|add:total_paiements_formateurs }} MAD</span>

<!-- Après -->
<span class="font-bold text-emerald-600">{{ marge_nette|floatformat:0 }} MAD</span>
```

- [ ] **Ajouter le graphe revenus mensuels** — après le bloc doughnut (après ligne ~124), avant `{% endblock %}` du contenu :

```html
<!-- Graphe revenus mensuels (bar) -->
<div class="bg-white rounded-sm shadow-sm border border-gray-100 mt-6">
  <div class="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
    <div>
      <h2 class="text-sm font-semibold text-gray-800">Revenus mensuels</h2>
      <p class="text-xs text-gray-400 mt-0.5">CA paiements étudiants — 6 derniers mois</p>
    </div>
  </div>
  <div class="p-4">
    <canvas id="revenueChart" height="100"></canvas>
  </div>
</div>
```

- [ ] **Mettre à jour le bloc `extra_js`** — ajouter le graphe revenus après le graphe séances :

```javascript
  // ── Graphe revenus mensuels (bar chart) ──────────────────────
  const revCtx = document.getElementById('revenueChart');
  if (revCtx) {
    new Chart(revCtx, {
      type: 'bar',
      data: {
        labels: {{ revenue_labels|safe }},
        datasets: [{
          label: 'Revenus (MAD)',
          data: {{ revenue_data|safe }},
          backgroundColor: 'rgba(16,185,129,0.15)',
          borderColor: '#10b981',
          borderWidth: 2,
          borderRadius: 3,
        }]
      },
      options: {
        responsive: true,
        plugins: { legend: { display: false } },
        scales: {
          y: { beginAtZero: true, grid: { color: 'rgba(0,0,0,0.04)' }, ticks: { font: { size: 11 } } },
          x: { grid: { display: false }, ticks: { font: { size: 11 } } }
        }
      }
    });
  }
```

- [ ] **Commit :**

```bash
git add templates/dashboard/admin/home/index.html
git commit -m "fix: admin dashboard — dynamic marge_nette, add monthly revenue bar chart"
```

---

## Vérification finale

- [ ] **Lancer tous les tests :**

```bash
python manage.py test dashboard -v 2
```

Expected : tous les tests passent, aucun `ERROR` ou `FAIL`.

- [ ] **Vérifier les URLs résolues :**

```bash
python manage.py check
python manage.py show_urls 2>/dev/null | grep "administrateur/seances/series" || echo "django-extensions non installé — OK"
```

- [ ] **Commit de clôture :**

```bash
git add -A
git status  # vérifier qu'aucun fichier sensible n'est inclus
git commit -m "feat: complete CRUD refonte — no modals, recurring sessions, dynamic graphs"
```
