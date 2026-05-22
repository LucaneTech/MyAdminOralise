# Reporting pédagogique — Séparation admin / formateur

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remplacer la vue unique `reporting_formateur` par 3 vues distinctes avec templates dédiés — liste formateurs (admin), détail formateur (admin), reporting personnel (teacher).

**Architecture:** Approche B — 3 vues indépendantes (`admin_reporting_list`, `admin_reporting_detail`, `teacher_reporting`), chacune avec son template et ses droits d'accès stricts. Les URLs sont reconfigurées et les deux sidenvs sont mis à jour.

**Tech Stack:** Django 4.x · Tailwind CSS (inline classes) · django-lucide · `{% widthratio %}` pour les barres de progression

---

## Fichiers créés / modifiés

| Fichier | Opération |
|---|---|
| `dashboard/views.py` | Remplacer `reporting_formateur` par 3 vues |
| `dashboard/urls.py` | 3 nouvelles routes, mise à jour des imports |
| `dashboard/tests.py` | Ajouter tests d'accès pour les 3 vues |
| `templates/dashboard/admin/home/reporting.html` | Créer (liste formateurs) |
| `templates/dashboard/admin/home/reporting_detail.html` | Créer (détail formateur) |
| `templates/dashboard/teacher/home/reporting.html` | Réécrire (redesign noble) |
| `templates/dashboard/admin/includes/sidenav.html` | Corriger le lien reporting |
| `templates/dashboard/teacher/includes/sidenav.html` | Ajouter le lien reporting |
| `templates/dashboard/teacher/home/index.html` | Corriger `reporting_formateur` → `teacher_reporting` |
| `templates/dashboard/admin/home/list_teachers.html` | Corriger `admin_reporting_formateur` → `admin_reporting_detail` |

---

## Task 1 : Remplacer la vue `reporting_formateur` par 3 vues

**Files:**
- Modify: `dashboard/views.py` (autour de la ligne 2208)

- [ ] **Step 1 : Localiser et supprimer `reporting_formateur`**

Dans `dashboard/views.py`, supprimer entièrement la fonction `reporting_formateur` (lignes ~2208–2293) et la remplacer par les 3 fonctions suivantes, sous le commentaire existant `# REPORTING BI-HEBDOMADAIRE` :

```python
# ─────────────────────────────────────────────────────────────
#  REPORTING PÉDAGOGIQUE
# ─────────────────────────────────────────────────────────────

@login_required
def admin_reporting_list(request):
    if request.user.role != 'admin':
        raise Http404

    today = timezone.now().date()
    date_fin_default = today
    date_debut_default = today - timedelta(days=14)

    date_debut_str = request.GET.get('date_debut', str(date_debut_default))
    date_fin_str = request.GET.get('date_fin', str(date_fin_default))
    try:
        date_debut = datetime.strptime(date_debut_str, '%Y-%m-%d').date()
        date_fin = datetime.strptime(date_fin_str, '%Y-%m-%d').date()
    except ValueError:
        date_debut = date_debut_default
        date_fin = date_fin_default

    all_sessions = Session.objects.filter(
        date__gte=date_debut,
        date__lte=date_fin,
        seance_realisee=True,
    )

    teachers_stats = []
    for t in Teacher.objects.all().select_related('user'):
        t_sessions = all_sessions.filter(teacher=t)
        nb = t_sessions.count()
        if nb == 0:
            continue
        nb_validees = t_sessions.filter(statut_validation='validee').count()
        student_ids = t_sessions.values_list('students', flat=True).distinct()
        nb_students = student_ids.count()

        nb_en_difficulte = 0
        for s in Student.objects.filter(id__in=student_ids):
            s_sessions = t_sessions.filter(students=s)
            avg_p = s_sessions.aggregate(Avg('participation'))['participation__avg'] or 0
            avg_c = s_sessions.aggregate(Avg('comprehension_score'))['comprehension_score__avg'] or 0
            avg_e = s_sessions.aggregate(Avg('engagement'))['engagement__avg'] or 0
            if (avg_p + avg_c + avg_e) > 0 and (avg_p + avg_c + avg_e) / 3 < 2.5:
                nb_en_difficulte += 1

        comp_counts = {
            'Oral': t_sessions.filter(comp_oral=True).count(),
            'Compréhension': t_sessions.filter(comp_comprehension=True).count(),
            'Écrit': t_sessions.filter(comp_ecrit=True).count(),
            'Grammaire': t_sessions.filter(comp_grammaire=True).count(),
            'Vocabulaire': t_sessions.filter(comp_vocabulaire=True).count(),
        }
        top_comp = max(comp_counts, key=comp_counts.get) if any(comp_counts.values()) else None

        teachers_stats.append({
            'teacher': t,
            'nb_sessions': nb,
            'nb_sessions_validees': nb_validees,
            'nb_students': nb_students,
            'nb_en_difficulte': nb_en_difficulte,
            'top_comp_faible': top_comp,
        })

    return render(request, 'dashboard/admin/home/reporting.html', {
        'date_debut': date_debut,
        'date_fin': date_fin,
        'teachers_stats': teachers_stats,
        'total_sessions_global': sum(s['nb_sessions'] for s in teachers_stats),
        'total_teachers_actifs': len(teachers_stats),
        'total_students_global': all_sessions.values_list('students', flat=True).distinct().count(),
    })


@login_required
def admin_reporting_detail(request, teacher_id):
    if request.user.role != 'admin':
        raise Http404
    teacher = get_object_or_404(Teacher, id=teacher_id)

    today = timezone.now().date()
    date_fin_default = today
    date_debut_default = today - timedelta(days=14)

    date_debut_str = request.GET.get('date_debut', str(date_debut_default))
    date_fin_str = request.GET.get('date_fin', str(date_fin_default))
    try:
        date_debut = datetime.strptime(date_debut_str, '%Y-%m-%d').date()
        date_fin = datetime.strptime(date_fin_str, '%Y-%m-%d').date()
    except ValueError:
        date_debut = date_debut_default
        date_fin = date_fin_default

    sessions_qs = Session.objects.filter(
        teacher=teacher,
        date__gte=date_debut,
        date__lte=date_fin,
        seance_realisee=True,
    )

    total_sessions = sessions_qs.count()
    sessions_validees = sessions_qs.filter(statut_validation='validee').count()
    student_ids = sessions_qs.values_list('students', flat=True).distinct()
    students = Student.objects.filter(id__in=student_ids).select_related('user')

    student_stats = []
    students_en_difficulte = []
    for s in students:
        s_sessions = sessions_qs.filter(students=s)
        avg_participation = s_sessions.aggregate(Avg('participation'))['participation__avg']
        avg_comprehension = s_sessions.aggregate(Avg('comprehension_score'))['comprehension_score__avg']
        avg_engagement = s_sessions.aggregate(Avg('engagement'))['engagement__avg']
        stat = {
            'student': s,
            'nb_sessions': s_sessions.count(),
            'avg_participation': round(avg_participation, 1) if avg_participation else None,
            'avg_comprehension': round(avg_comprehension, 1) if avg_comprehension else None,
            'avg_engagement': round(avg_engagement, 1) if avg_engagement else None,
        }
        student_stats.append(stat)
        score = (avg_participation or 0) + (avg_comprehension or 0) + (avg_engagement or 0)
        if score > 0 and score / 3 < 2.5:
            students_en_difficulte.append(s)

    comp_faibles = {
        'Oral': sessions_qs.filter(comp_oral=True).count(),
        'Compréhension': sessions_qs.filter(comp_comprehension=True).count(),
        'Écrit': sessions_qs.filter(comp_ecrit=True).count(),
        'Grammaire': sessions_qs.filter(comp_grammaire=True).count(),
        'Vocabulaire': sessions_qs.filter(comp_vocabulaire=True).count(),
    }

    return render(request, 'dashboard/admin/home/reporting_detail.html', {
        'teacher': teacher,
        'date_debut': date_debut,
        'date_fin': date_fin,
        'total_sessions': total_sessions,
        'sessions_validees': sessions_validees,
        'student_stats': student_stats,
        'students_en_difficulte': students_en_difficulte,
        'comp_faibles': comp_faibles,
    })


@login_required
def teacher_reporting(request):
    if request.user.role != 'teacher':
        raise Http404
    teacher = get_object_or_404(Teacher, user=request.user)

    today = timezone.now().date()
    date_fin_default = today
    date_debut_default = today - timedelta(days=14)

    date_debut_str = request.GET.get('date_debut', str(date_debut_default))
    date_fin_str = request.GET.get('date_fin', str(date_fin_default))
    try:
        date_debut = datetime.strptime(date_debut_str, '%Y-%m-%d').date()
        date_fin = datetime.strptime(date_fin_str, '%Y-%m-%d').date()
    except ValueError:
        date_debut = date_debut_default
        date_fin = date_fin_default

    sessions_qs = Session.objects.filter(
        teacher=teacher,
        date__gte=date_debut,
        date__lte=date_fin,
        seance_realisee=True,
    )

    total_sessions = sessions_qs.count()
    sessions_validees = sessions_qs.filter(statut_validation='validee').count()
    student_ids = sessions_qs.values_list('students', flat=True).distinct()
    students = Student.objects.filter(id__in=student_ids).select_related('user')

    student_stats = []
    students_en_difficulte = []
    for s in students:
        s_sessions = sessions_qs.filter(students=s)
        avg_participation = s_sessions.aggregate(Avg('participation'))['participation__avg']
        avg_comprehension = s_sessions.aggregate(Avg('comprehension_score'))['comprehension_score__avg']
        avg_engagement = s_sessions.aggregate(Avg('engagement'))['engagement__avg']
        stat = {
            'student': s,
            'nb_sessions': s_sessions.count(),
            'avg_participation': round(avg_participation, 1) if avg_participation else None,
            'avg_comprehension': round(avg_comprehension, 1) if avg_comprehension else None,
            'avg_engagement': round(avg_engagement, 1) if avg_engagement else None,
        }
        student_stats.append(stat)
        score = (avg_participation or 0) + (avg_comprehension or 0) + (avg_engagement or 0)
        if score > 0 and score / 3 < 2.5:
            students_en_difficulte.append(s)

    comp_faibles = {
        'Oral': sessions_qs.filter(comp_oral=True).count(),
        'Compréhension': sessions_qs.filter(comp_comprehension=True).count(),
        'Écrit': sessions_qs.filter(comp_ecrit=True).count(),
        'Grammaire': sessions_qs.filter(comp_grammaire=True).count(),
        'Vocabulaire': sessions_qs.filter(comp_vocabulaire=True).count(),
    }

    return render(request, 'dashboard/teacher/home/reporting.html', {
        'teacher': teacher,
        'date_debut': date_debut,
        'date_fin': date_fin,
        'total_sessions': total_sessions,
        'sessions_validees': sessions_validees,
        'student_stats': student_stats,
        'students_en_difficulte': students_en_difficulte,
        'comp_faibles': comp_faibles,
    })
```

- [ ] **Step 2 : Commit**

```bash
git add dashboard/views.py
git commit -m "refactor: split reporting_formateur into 3 dedicated views"
```

---

## Task 2 : Mettre à jour `dashboard/urls.py`

**Files:**
- Modify: `dashboard/urls.py`

- [ ] **Step 1 : Mettre à jour l'import en ligne 20**

Remplacer :
```python
    reporting_formateur, paiements_formateurs_list,
```
Par :
```python
    admin_reporting_list, admin_reporting_detail, teacher_reporting,
    paiements_formateurs_list,
```

- [ ] **Step 2 : Remplacer les 2 anciennes routes reporting**

Remplacer :
```python
    path('reporting/', reporting_formateur, name='reporting_formateur'),
    path('administrateur/reporting/<int:teacher_id>/', reporting_formateur, name='admin_reporting_formateur'),
```
Par :
```python
    path('reporting/', teacher_reporting, name='teacher_reporting'),
    path('administrateur/reporting/', admin_reporting_list, name='admin_reporting_list'),
    path('administrateur/reporting/<int:teacher_id>/', admin_reporting_detail, name='admin_reporting_detail'),
```

- [ ] **Step 3 : Vérifier que Django démarre sans erreur**

```bash
python manage.py check
```

Résultat attendu : `System check identified no issues (0 silenced).`

- [ ] **Step 4 : Commit**

```bash
git add dashboard/urls.py
git commit -m "feat: add 3 reporting routes (admin list, admin detail, teacher)"
```

---

## Task 3 : Tests d'accès pour les 3 vues

**Files:**
- Modify: `dashboard/tests.py`

- [ ] **Step 1 : Ajouter la classe de test à la fin de `dashboard/tests.py`**

```python
from django.test import Client


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
        self.assertEqual(r.status_code, 404)

    def test_admin_reporting_detail_ok_for_admin(self):
        self.client.login(username='admin_rep', password='pass')
        r = self.client.get(f'/administrateur/reporting/{self.teacher.id}/')
        self.assertEqual(r.status_code, 200)

    def test_admin_reporting_detail_blocked_for_teacher(self):
        self.client.login(username='teacher_rep', password='pass')
        r = self.client.get(f'/administrateur/reporting/{self.teacher.id}/')
        self.assertEqual(r.status_code, 404)

    def test_teacher_reporting_ok_for_teacher(self):
        self.client.login(username='teacher_rep', password='pass')
        r = self.client.get('/reporting/')
        self.assertEqual(r.status_code, 200)

    def test_teacher_reporting_blocked_for_student(self):
        self.client.login(username='student_rep', password='pass')
        r = self.client.get('/reporting/')
        self.assertEqual(r.status_code, 404)
```

- [ ] **Step 2 : Lancer les tests**

```bash
python manage.py test dashboard.tests.ReportingAccessTest -v 2
```

Résultat attendu : `7 tests passed`

- [ ] **Step 3 : Commit**

```bash
git add dashboard/tests.py
git commit -m "test: access control for 3 reporting views"
```

---

## Task 4 : Template admin — liste des formateurs

**Files:**
- Create: `templates/dashboard/admin/home/reporting.html`

- [ ] **Step 1 : Créer le fichier**

```html
{% extends "dashboard/admin/layouts/base.html" %}
{% load static %}
{% load lucide %}

{% block title %}Reporting pédagogique{% endblock %}

{% block content %}
<!-- Header -->
<div class="flex items-start justify-between mb-6">
  <div>
    <h1 class="text-xl font-bold text-gray-900">Reporting pédagogique</h1>
    <p class="text-sm text-gray-400 mt-0.5">Synthèse de l'activité pédagogique par formateur</p>
  </div>
</div>

<!-- Filtre période -->
<div class="bg-white rounded-sm shadow-sm border border-gray-100 p-4 mb-6">
  <form method="get" class="flex flex-wrap items-end gap-3">
    <div>
      <label class="block text-xs font-semibold text-gray-400 mb-1 uppercase tracking-widest">Période du</label>
      <input type="date" name="date_debut" value="{{ date_debut|date:'Y-m-d' }}"
             class="px-3 py-2 border border-gray-200 rounded-sm text-sm focus:outline-none focus:ring-2 focus:ring-[#033050]/20 focus:border-[#033050] transition">
    </div>
    <div>
      <label class="block text-xs font-semibold text-gray-400 mb-1 uppercase tracking-widest">au</label>
      <input type="date" name="date_fin" value="{{ date_fin|date:'Y-m-d' }}"
             class="px-3 py-2 border border-gray-200 rounded-sm text-sm focus:outline-none focus:ring-2 focus:ring-[#033050]/20 focus:border-[#033050] transition">
    </div>
    <button type="submit"
            class="px-5 py-2 bg-[#033050] text-white text-sm font-semibold rounded-sm hover:bg-[#033050]/90 transition flex items-center gap-2">
      {% lucide "search" class="w-3.5 h-3.5" %}
      Analyser
    </button>
  </form>
</div>

<!-- KPIs globaux -->
<div class="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
  <div class="bg-white rounded-sm shadow-sm border border-gray-100 p-5">
    <div class="flex items-center justify-between mb-3">
      <p class="text-xs font-semibold text-gray-400 uppercase tracking-widest">Formateurs actifs</p>
      <span class="w-8 h-8 rounded-sm bg-[#033050]/10 flex items-center justify-center">
        {% lucide "users" class="w-4 h-4 text-[#033050]" %}
      </span>
    </div>
    <p class="text-3xl font-bold text-gray-900">{{ total_teachers_actifs }}</p>
  </div>
  <div class="bg-white rounded-sm shadow-sm border border-gray-100 p-5">
    <div class="flex items-center justify-between mb-3">
      <p class="text-xs font-semibold text-gray-400 uppercase tracking-widest">Séances réalisées</p>
      <span class="w-8 h-8 rounded-sm bg-sky-50 flex items-center justify-center">
        {% lucide "calendar-check" class="w-4 h-4 text-sky-500" %}
      </span>
    </div>
    <p class="text-3xl font-bold text-gray-900">{{ total_sessions_global }}</p>
  </div>
  <div class="bg-white rounded-sm shadow-sm border border-gray-100 p-5">
    <div class="flex items-center justify-between mb-3">
      <p class="text-xs font-semibold text-gray-400 uppercase tracking-widest">Étudiants suivis</p>
      <span class="w-8 h-8 rounded-sm bg-violet-50 flex items-center justify-center">
        {% lucide "graduation-cap" class="w-4 h-4 text-violet-500" %}
      </span>
    </div>
    <p class="text-3xl font-bold text-gray-900">{{ total_students_global }}</p>
  </div>
</div>

<!-- Table formateurs -->
<div class="bg-white rounded-sm shadow-sm border border-gray-100 overflow-hidden">
  <div class="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
    <h2 class="text-sm font-semibold text-gray-700">Activité par formateur</h2>
    <span class="text-xs text-gray-400 tabular-nums">{{ date_debut|date:"d/m/Y" }} → {{ date_fin|date:"d/m/Y" }}</span>
  </div>
  <div class="overflow-x-auto">
    <table class="w-full text-sm">
      <thead class="bg-[#033050] text-white">
        <tr>
          <th class="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wide">Formateur</th>
          <th class="px-5 py-3 text-center text-xs font-semibold uppercase tracking-wide">Séances</th>
          <th class="px-5 py-3 text-center text-xs font-semibold uppercase tracking-wide">Validées</th>
          <th class="px-5 py-3 text-center text-xs font-semibold uppercase tracking-wide">Étudiants</th>
          <th class="px-5 py-3 text-center text-xs font-semibold uppercase tracking-wide">En difficulté</th>
          <th class="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wide">Top faiblesse</th>
          <th class="px-5 py-3"></th>
        </tr>
      </thead>
      <tbody class="divide-y divide-gray-100">
        {% for stat in teachers_stats %}
        <tr class="hover:bg-gray-50 transition-colors">
          <td class="px-5 py-4">
            <div class="flex items-center gap-3">
              <img src="{{ stat.teacher.user.profile_picture_url }}" alt="avatar"
                   class="w-9 h-9 rounded-sm object-cover border border-gray-100 shrink-0">
              <div>
                <p class="text-sm font-semibold text-gray-800">{{ stat.teacher.user.get_full_name }}</p>
                <p class="text-xs text-gray-400">{{ stat.teacher.user.email }}</p>
              </div>
            </div>
          </td>
          <td class="px-5 py-4 text-center">
            <span class="text-sm font-bold text-gray-800">{{ stat.nb_sessions }}</span>
          </td>
          <td class="px-5 py-4 text-center">
            <span class="inline-flex items-center px-2 py-0.5 rounded-sm text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-100">
              {{ stat.nb_sessions_validees }}
            </span>
          </td>
          <td class="px-5 py-4 text-center text-sm font-medium text-gray-700">
            {{ stat.nb_students }}
          </td>
          <td class="px-5 py-4 text-center">
            {% if stat.nb_en_difficulte > 0 %}
            <span class="inline-flex items-center px-2 py-0.5 rounded-sm text-xs font-semibold bg-red-50 text-red-700 border border-red-100">
              {{ stat.nb_en_difficulte }}
            </span>
            {% else %}
            <span class="text-gray-200">—</span>
            {% endif %}
          </td>
          <td class="px-5 py-4">
            {% if stat.top_comp_faible %}
            <span class="inline-flex items-center px-2.5 py-1 rounded-sm text-xs font-medium bg-amber-50 text-amber-700 border border-amber-100">
              {{ stat.top_comp_faible }}
            </span>
            {% else %}
            <span class="text-xs text-gray-300">Aucune</span>
            {% endif %}
          </td>
          <td class="px-5 py-4 text-right">
            <a href="{% url 'admin_reporting_detail' stat.teacher.id %}"
               class="inline-flex items-center gap-1.5 px-3 py-1.5 bg-[#033050] text-white text-xs font-semibold rounded-sm hover:bg-[#033050]/90 transition">
              {% lucide "bar-chart-2" class="w-3.5 h-3.5" %}
              Voir
            </a>
          </td>
        </tr>
        {% empty %}
        <tr>
          <td colspan="7" class="px-5 py-14 text-center text-sm text-gray-400">
            Aucun formateur actif sur cette période.
          </td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
</div>
{% endblock %}
```

- [ ] **Step 2 : Vérifier la page dans le navigateur**

```bash
python manage.py runserver
```

Accéder à `http://localhost:8000/administrateur/reporting/` avec un compte admin. Vérifier que :
- Les KPIs s'affichent
- La table liste les formateurs ayant des séances sur la période
- Le lien "Voir" sur chaque ligne mène à la page détail

- [ ] **Step 3 : Commit**

```bash
git add templates/dashboard/admin/home/reporting.html
git commit -m "feat: admin reporting list template — teachers overview table"
```

---

## Task 5 : Template admin — détail formateur

**Files:**
- Create: `templates/dashboard/admin/home/reporting_detail.html`

- [ ] **Step 1 : Créer le fichier**

```html
{% extends "dashboard/admin/layouts/base.html" %}
{% load static %}
{% load lucide %}

{% block title %}Reporting — {{ teacher.user.get_full_name }}{% endblock %}

{% block content %}
<!-- Breadcrumb -->
<div class="flex items-center gap-2 mb-5 text-sm">
  <a href="{% url 'admin_reporting_list' %}"
     class="flex items-center gap-1.5 text-gray-500 hover:text-[#033050] transition font-medium">
    {% lucide "arrow-left" class="w-3.5 h-3.5" %}
    Reporting
  </a>
  <span class="text-gray-300">/</span>
  <span class="text-gray-800 font-semibold">{{ teacher.user.get_full_name }}</span>
</div>

<!-- Header formateur + filtre -->
<div class="bg-white rounded-sm shadow-sm border border-gray-100 p-5 mb-6 flex flex-wrap items-center justify-between gap-4">
  <div class="flex items-center gap-4">
    <img src="{{ teacher.user.profile_picture_url }}" alt="avatar"
         class="w-12 h-12 rounded-sm object-cover border border-gray-100 shrink-0">
    <div>
      <h1 class="text-lg font-bold text-gray-900">{{ teacher.user.get_full_name }}</h1>
      <p class="text-sm text-gray-400">{{ teacher.user.email }}</p>
    </div>
  </div>
  <form method="get" class="flex items-end gap-3">
    <div>
      <label class="block text-xs font-semibold text-gray-400 mb-1 uppercase tracking-widest">Du</label>
      <input type="date" name="date_debut" value="{{ date_debut|date:'Y-m-d' }}"
             class="px-3 py-2 border border-gray-200 rounded-sm text-sm focus:outline-none focus:ring-2 focus:ring-[#033050]/20 focus:border-[#033050] transition">
    </div>
    <div>
      <label class="block text-xs font-semibold text-gray-400 mb-1 uppercase tracking-widest">au</label>
      <input type="date" name="date_fin" value="{{ date_fin|date:'Y-m-d' }}"
             class="px-3 py-2 border border-gray-200 rounded-sm text-sm focus:outline-none focus:ring-2 focus:ring-[#033050]/20 focus:border-[#033050] transition">
    </div>
    <button type="submit"
            class="px-4 py-2 bg-[#033050] text-white text-sm font-semibold rounded-sm hover:bg-[#033050]/90 transition">
      Analyser
    </button>
  </form>
</div>

<!-- KPIs -->
<div class="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
  <div class="bg-white rounded-sm shadow-sm border border-gray-100 p-5">
    <p class="text-xs font-semibold text-gray-400 uppercase tracking-widest mb-3">Séances réalisées</p>
    <p class="text-3xl font-bold text-gray-900">{{ total_sessions }}</p>
  </div>
  <div class="bg-white rounded-sm shadow-sm border border-gray-100 p-5">
    <p class="text-xs font-semibold text-gray-400 uppercase tracking-widest mb-3">Séances validées</p>
    <p class="text-3xl font-bold text-emerald-600">{{ sessions_validees }}</p>
  </div>
  <div class="bg-white rounded-sm shadow-sm border border-gray-100 p-5">
    <p class="text-xs font-semibold text-gray-400 uppercase tracking-widest mb-3">Étudiants suivis</p>
    <p class="text-3xl font-bold text-gray-900">{{ student_stats|length }}</p>
  </div>
</div>

<!-- Main grid -->
<div class="grid grid-cols-1 lg:grid-cols-3 gap-4">

  <!-- Table étudiants -->
  <div class="lg:col-span-2">
    <div class="bg-white rounded-sm shadow-sm border border-gray-100 overflow-hidden">
      <div class="px-5 py-4 border-b border-gray-100">
        <h2 class="text-sm font-semibold text-gray-700">Suivi individuel des étudiants</h2>
      </div>
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead class="bg-gray-50 border-b border-gray-100">
            <tr>
              <th class="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">Étudiant</th>
              <th class="px-5 py-3 text-center text-xs font-semibold text-gray-500 uppercase tracking-wide w-16">Séances</th>
              <th class="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">Participation</th>
              <th class="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">Compréhension</th>
              <th class="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">Engagement</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100">
            {% for stat in student_stats %}
            <tr class="hover:bg-gray-50 transition-colors">
              <td class="px-5 py-3 font-semibold text-gray-800">{{ stat.student }}</td>
              <td class="px-5 py-3 text-center text-gray-500 text-xs tabular-nums">{{ stat.nb_sessions }}</td>
              <td class="px-5 py-3">
                {% if stat.avg_participation %}
                <div class="flex items-center gap-2 min-w-[100px]">
                  <div class="flex-1 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                    <div class="h-full rounded-full transition-all
                      {% if stat.avg_participation >= 3 %}bg-emerald-500
                      {% elif stat.avg_participation >= 2 %}bg-amber-400
                      {% else %}bg-red-400{% endif %}"
                         style="width:{% widthratio stat.avg_participation 4 100 %}%"></div>
                  </div>
                  <span class="text-xs font-bold text-gray-500 shrink-0 tabular-nums w-7">{{ stat.avg_participation }}</span>
                </div>
                {% else %}<span class="text-gray-200 text-xs">—</span>{% endif %}
              </td>
              <td class="px-5 py-3">
                {% if stat.avg_comprehension %}
                <div class="flex items-center gap-2 min-w-[100px]">
                  <div class="flex-1 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                    <div class="h-full rounded-full transition-all
                      {% if stat.avg_comprehension >= 3 %}bg-emerald-500
                      {% elif stat.avg_comprehension >= 2 %}bg-amber-400
                      {% else %}bg-red-400{% endif %}"
                         style="width:{% widthratio stat.avg_comprehension 4 100 %}%"></div>
                  </div>
                  <span class="text-xs font-bold text-gray-500 shrink-0 tabular-nums w-7">{{ stat.avg_comprehension }}</span>
                </div>
                {% else %}<span class="text-gray-200 text-xs">—</span>{% endif %}
              </td>
              <td class="px-5 py-3">
                {% if stat.avg_engagement %}
                <div class="flex items-center gap-2 min-w-[100px]">
                  <div class="flex-1 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                    <div class="h-full rounded-full transition-all
                      {% if stat.avg_engagement >= 3 %}bg-emerald-500
                      {% elif stat.avg_engagement >= 2 %}bg-amber-400
                      {% else %}bg-red-400{% endif %}"
                         style="width:{% widthratio stat.avg_engagement 4 100 %}%"></div>
                  </div>
                  <span class="text-xs font-bold text-gray-500 shrink-0 tabular-nums w-7">{{ stat.avg_engagement }}</span>
                </div>
                {% else %}<span class="text-gray-200 text-xs">—</span>{% endif %}
              </td>
            </tr>
            {% empty %}
            <tr>
              <td colspan="5" class="px-5 py-14 text-center text-sm text-gray-400">
                Aucune donnée sur cette période.
              </td>
            </tr>
            {% endfor %}
          </tbody>
        </table>
      </div>
    </div>
  </div>

  <!-- Side panels -->
  <div class="space-y-4">
    {% if students_en_difficulte %}
    <div class="bg-white rounded-sm shadow-sm border border-red-100 overflow-hidden">
      <div class="px-5 py-4 border-b border-red-100 bg-red-50 flex items-center gap-2">
        {% lucide "alert-triangle" class="w-4 h-4 text-red-500 shrink-0" %}
        <h2 class="text-sm font-semibold text-red-700">Étudiants en difficulté</h2>
      </div>
      <ul class="divide-y divide-gray-100">
        {% for s in students_en_difficulte %}
        <li class="px-5 py-3 text-sm text-gray-700 flex items-center gap-2">
          {% lucide "user" class="w-3.5 h-3.5 text-gray-300 shrink-0" %}
          {{ s }}
        </li>
        {% endfor %}
      </ul>
    </div>
    {% endif %}

    <div class="bg-white rounded-sm shadow-sm border border-gray-100 overflow-hidden">
      <div class="px-5 py-4 border-b border-gray-100">
        <h2 class="text-sm font-semibold text-gray-700">Points faibles récurrents</h2>
      </div>
      <div class="p-5 space-y-3">
        {% for comp, count in comp_faibles.items %}
        <div>
          <div class="flex items-center justify-between mb-1.5">
            <span class="text-xs font-semibold text-gray-600">{{ comp }}</span>
            <span class="text-xs font-bold text-gray-400 tabular-nums">{{ count }}</span>
          </div>
          <div class="h-1.5 bg-gray-100 rounded-full overflow-hidden">
            {% if total_sessions %}
            <div class="h-full bg-[#033050]/50 rounded-full"
                 style="width:{% widthratio count total_sessions 100 %}%"></div>
            {% endif %}
          </div>
        </div>
        {% endfor %}
      </div>
    </div>
  </div>

</div>
{% endblock %}
```

- [ ] **Step 2 : Vérifier la page dans le navigateur**

Accéder à `http://localhost:8000/administrateur/reporting/<id_formateur>/` avec un compte admin. Vérifier :
- Breadcrumb fonctionnel (retour vers la liste)
- Table étudiants avec barres de progression colorées
- Panels latéraux (étudiants en difficulté + points faibles)

- [ ] **Step 3 : Commit**

```bash
git add templates/dashboard/admin/home/reporting_detail.html
git commit -m "feat: admin reporting detail template — student progress bars, side panels"
```

---

## Task 6 : Redesign du template teacher

**Files:**
- Modify: `templates/dashboard/teacher/home/reporting.html`

- [ ] **Step 1 : Remplacer intégralement le contenu du fichier**

```html
{% extends 'dashboard/teacher/layouts/base.html' %}
{% load lucide %}

{% block title %}Mon reporting{% endblock %}

{% block content %}
<!-- Header -->
<div class="mb-6">
  <h1 class="text-xl font-bold text-gray-900">Mon reporting pédagogique</h1>
  <p class="text-sm text-gray-400 mt-0.5">
    Analyse de votre activité — {{ date_debut|date:"d/m/Y" }} au {{ date_fin|date:"d/m/Y" }}
  </p>
</div>

<!-- Filtre période -->
<div class="bg-white rounded-sm shadow-sm border border-gray-100 p-4 mb-6">
  <form method="get" class="flex flex-wrap items-end gap-3">
    <div>
      <label class="block text-xs font-semibold text-gray-400 mb-1 uppercase tracking-widest">Du</label>
      <input type="date" name="date_debut" value="{{ date_debut|date:'Y-m-d' }}"
             class="px-3 py-2 border border-gray-200 rounded-sm text-sm focus:outline-none focus:ring-2 focus:ring-sky-500/20 focus:border-sky-500 transition">
    </div>
    <div>
      <label class="block text-xs font-semibold text-gray-400 mb-1 uppercase tracking-widest">au</label>
      <input type="date" name="date_fin" value="{{ date_fin|date:'Y-m-d' }}"
             class="px-3 py-2 border border-gray-200 rounded-sm text-sm focus:outline-none focus:ring-2 focus:ring-sky-500/20 focus:border-sky-500 transition">
    </div>
    <button type="submit"
            class="px-5 py-2 bg-[#0c1e35] text-white text-sm font-semibold rounded-sm hover:bg-[#0c1e35]/90 transition flex items-center gap-2">
      {% lucide "search" class="w-3.5 h-3.5" %}
      Analyser
    </button>
  </form>
</div>

<!-- KPIs -->
<div class="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
  <div class="bg-white rounded-sm shadow-sm border border-gray-100 p-5">
    <div class="flex items-center justify-between mb-3">
      <p class="text-xs font-semibold text-gray-400 uppercase tracking-widest">Séances réalisées</p>
      <span class="w-8 h-8 rounded-sm bg-sky-50 flex items-center justify-center shrink-0">
        {% lucide "calendar-check" class="w-4 h-4 text-sky-500" %}
      </span>
    </div>
    <p class="text-3xl font-bold text-gray-900">{{ total_sessions }}</p>
  </div>
  <div class="bg-white rounded-sm shadow-sm border border-gray-100 p-5">
    <div class="flex items-center justify-between mb-3">
      <p class="text-xs font-semibold text-gray-400 uppercase tracking-widest">Séances validées</p>
      <span class="w-8 h-8 rounded-sm bg-emerald-50 flex items-center justify-center shrink-0">
        {% lucide "check-circle" class="w-4 h-4 text-emerald-500" %}
      </span>
    </div>
    <p class="text-3xl font-bold text-emerald-600">{{ sessions_validees }}</p>
  </div>
  <div class="bg-white rounded-sm shadow-sm border border-gray-100 p-5">
    <div class="flex items-center justify-between mb-3">
      <p class="text-xs font-semibold text-gray-400 uppercase tracking-widest">Étudiants suivis</p>
      <span class="w-8 h-8 rounded-sm bg-violet-50 flex items-center justify-center shrink-0">
        {% lucide "graduation-cap" class="w-4 h-4 text-violet-500" %}
      </span>
    </div>
    <p class="text-3xl font-bold text-gray-900">{{ student_stats|length }}</p>
  </div>
</div>

<!-- Main grid -->
<div class="grid grid-cols-1 lg:grid-cols-3 gap-4">

  <!-- Table étudiants -->
  <div class="lg:col-span-2">
    <div class="bg-white rounded-sm shadow-sm border border-gray-100 overflow-hidden">
      <div class="px-5 py-4 border-b border-gray-100">
        <h2 class="text-sm font-semibold text-gray-700">Suivi individuel des étudiants</h2>
      </div>
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead class="bg-gray-50 border-b border-gray-100">
            <tr>
              <th class="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">Étudiant</th>
              <th class="px-5 py-3 text-center text-xs font-semibold text-gray-500 uppercase tracking-wide w-16">Séances</th>
              <th class="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">Participation</th>
              <th class="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">Compréhension</th>
              <th class="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">Engagement</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100">
            {% for stat in student_stats %}
            <tr class="hover:bg-gray-50 transition-colors">
              <td class="px-5 py-3 font-semibold text-gray-800">{{ stat.student }}</td>
              <td class="px-5 py-3 text-center text-gray-500 text-xs tabular-nums">{{ stat.nb_sessions }}</td>
              <td class="px-5 py-3">
                {% if stat.avg_participation %}
                <div class="flex items-center gap-2 min-w-[100px]">
                  <div class="flex-1 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                    <div class="h-full rounded-full
                      {% if stat.avg_participation >= 3 %}bg-emerald-500
                      {% elif stat.avg_participation >= 2 %}bg-amber-400
                      {% else %}bg-red-400{% endif %}"
                         style="width:{% widthratio stat.avg_participation 4 100 %}%"></div>
                  </div>
                  <span class="text-xs font-bold text-gray-500 shrink-0 tabular-nums w-7">{{ stat.avg_participation }}</span>
                </div>
                {% else %}<span class="text-gray-200 text-xs">—</span>{% endif %}
              </td>
              <td class="px-5 py-3">
                {% if stat.avg_comprehension %}
                <div class="flex items-center gap-2 min-w-[100px]">
                  <div class="flex-1 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                    <div class="h-full rounded-full
                      {% if stat.avg_comprehension >= 3 %}bg-emerald-500
                      {% elif stat.avg_comprehension >= 2 %}bg-amber-400
                      {% else %}bg-red-400{% endif %}"
                         style="width:{% widthratio stat.avg_comprehension 4 100 %}%"></div>
                  </div>
                  <span class="text-xs font-bold text-gray-500 shrink-0 tabular-nums w-7">{{ stat.avg_comprehension }}</span>
                </div>
                {% else %}<span class="text-gray-200 text-xs">—</span>{% endif %}
              </td>
              <td class="px-5 py-3">
                {% if stat.avg_engagement %}
                <div class="flex items-center gap-2 min-w-[100px]">
                  <div class="flex-1 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                    <div class="h-full rounded-full
                      {% if stat.avg_engagement >= 3 %}bg-emerald-500
                      {% elif stat.avg_engagement >= 2 %}bg-amber-400
                      {% else %}bg-red-400{% endif %}"
                         style="width:{% widthratio stat.avg_engagement 4 100 %}%"></div>
                  </div>
                  <span class="text-xs font-bold text-gray-500 shrink-0 tabular-nums w-7">{{ stat.avg_engagement }}</span>
                </div>
                {% else %}<span class="text-gray-200 text-xs">—</span>{% endif %}
              </td>
            </tr>
            {% empty %}
            <tr>
              <td colspan="5" class="px-5 py-14 text-center text-sm text-gray-400">
                Aucune donnée sur cette période.
              </td>
            </tr>
            {% endfor %}
          </tbody>
        </table>
      </div>
    </div>
  </div>

  <!-- Side panels -->
  <div class="space-y-4">
    {% if students_en_difficulte %}
    <div class="bg-white rounded-sm shadow-sm border border-red-100 overflow-hidden">
      <div class="px-5 py-4 border-b border-red-100 bg-red-50 flex items-center gap-2">
        {% lucide "alert-triangle" class="w-4 h-4 text-red-500 shrink-0" %}
        <h2 class="text-sm font-semibold text-red-700">Étudiants en difficulté</h2>
      </div>
      <ul class="divide-y divide-gray-100">
        {% for s in students_en_difficulte %}
        <li class="px-5 py-3 text-sm text-gray-700 flex items-center gap-2">
          {% lucide "user" class="w-3.5 h-3.5 text-gray-300 shrink-0" %}
          {{ s }}
        </li>
        {% endfor %}
      </ul>
    </div>
    {% endif %}

    <div class="bg-white rounded-sm shadow-sm border border-gray-100 overflow-hidden">
      <div class="px-5 py-4 border-b border-gray-100">
        <h2 class="text-sm font-semibold text-gray-700">Points faibles récurrents</h2>
      </div>
      <div class="p-5 space-y-3">
        {% for comp, count in comp_faibles.items %}
        <div>
          <div class="flex items-center justify-between mb-1.5">
            <span class="text-xs font-semibold text-gray-600">{{ comp }}</span>
            <span class="text-xs font-bold text-gray-400 tabular-nums">{{ count }}</span>
          </div>
          <div class="h-1.5 bg-gray-100 rounded-full overflow-hidden">
            {% if total_sessions %}
            <div class="h-full bg-[#0c1e35]/50 rounded-full"
                 style="width:{% widthratio count total_sessions 100 %}%"></div>
            {% endif %}
          </div>
        </div>
        {% endfor %}
      </div>
    </div>
  </div>

</div>
{% endblock %}
```

- [ ] **Step 2 : Vérifier la page teacher**

Accéder à `http://localhost:8000/reporting/` avec un compte teacher. Vérifier :
- KPIs avec icônes
- Barres de progression dans la table étudiants
- Section points faibles avec barres proportionnelles

- [ ] **Step 3 : Commit**

```bash
git add templates/dashboard/teacher/home/reporting.html
git commit -m "feat: teacher reporting redesign — progress bars, KPI icons, noble layout"
```

---

## Task 7 : Mettre à jour les sidenvs

**Files:**
- Modify: `templates/dashboard/admin/includes/sidenav.html`
- Modify: `templates/dashboard/teacher/includes/sidenav.html`

- [ ] **Step 1 : Admin sidenav — corriger le lien**

Dans `templates/dashboard/admin/includes/sidenav.html`, remplacer le href du lien Reporting :

Remplacer :
```html
    <a href="{% url 'reporting_formateur' %}"
```
Par :
```html
    <a href="{% url 'admin_reporting_list' %}"
```

- [ ] **Step 2 : Teacher sidenav — ajouter le lien Reporting**

Dans `templates/dashboard/teacher/includes/sidenav.html`, après le lien `teacher_evaluations_add`, ajouter :

```html
    <a href="{% url 'teacher_reporting' %}"
       class="flex items-center gap-3 px-3 py-2.5 rounded-sm text-sm font-medium transition-all hover:bg-white/10 {% if 'reporting' in request.path %}bg-lime-500/20 border-l-2 border-lime-400{% endif %}">
      <span class="w-7 h-7 rounded-sm bg-lime-500/20 flex items-center justify-center shrink-0">
        {% lucide "trending-up" class="w-3.5 h-3.5 text-lime-400" %}
      </span>
      <span class="text-white/90">Reporting</span>
    </a>
```

- [ ] **Step 3 : Commit**

```bash
git add templates/dashboard/admin/includes/sidenav.html
git add templates/dashboard/teacher/includes/sidenav.html
git commit -m "feat: update sidenavs — fix admin reporting link, add teacher reporting link"
```

---

## Task 8 : Corriger les anciennes références URL

**Files:**
- Modify: `templates/dashboard/teacher/home/index.html` (ligne 168)
- Modify: `templates/dashboard/admin/home/list_teachers.html` (ligne 96)

- [ ] **Step 1 : Corriger `teacher/home/index.html`**

Remplacer :
```html
        <a href="{% url 'reporting_formateur' %}"
```
Par :
```html
        <a href="{% url 'teacher_reporting' %}"
```

- [ ] **Step 2 : Corriger `admin/home/list_teachers.html`**

Remplacer :
```html
              <a href="{% url 'admin_reporting_formateur' teacher.id %}"
```
Par :
```html
              <a href="{% url 'admin_reporting_detail' teacher.id %}"
```

- [ ] **Step 3 : Lancer tous les tests**

```bash
python manage.py test dashboard -v 2
```

Résultat attendu : tous les tests passent.

- [ ] **Step 4 : Commit final**

```bash
git add templates/dashboard/teacher/home/index.html
git add templates/dashboard/admin/home/list_teachers.html
git commit -m "fix: update stale reporting URL references in templates"
```
