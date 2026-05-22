# Spec — Refonte CRUD + Séances Récurrentes + Graphes Dynamiques

**Date :** 2026-05-22  
**Projet :** MyAdminOralise (monespace.oralise.pro)  
**Scope :** Admin dashboard + Teacher dashboard

---

## 1. Suppression modals → pages directes

### Problème
Le système `loadModal()` / AJAX injecte du HTML dans un panel flottant. Il crée des UX cassées (pas d'URL propre, pas de back-button, erreurs silencieuses) et complique la maintenance.

### Solution
Remplacer chaque appel modal par une redirection vers la page de formulaire dédiée.

### Changements admin (8 templates)
| Template | Éléments à modifier |
|---|---|
| `assignments_list.html` | `onclick="loadModal(...)"` → `<a href="{% url 'admin_assignment_create' %}">` |
| `evaluations_list.html` | idem → `admin_evaluation_create` / `admin_evaluation_edit` |
| `languages_list.html` | idem → `admin_language_create` / `admin_language_edit` |
| `list_students.html` | idem → `admin_student_create` |
| `list_teachers.html` | idem → `admin_teacher_create` / `admin_teacher_edit` |
| `payments_list.html` | idem → `admin_payment_create` / `admin_payment_edit` |
| `notifications_list.html` | idem → `admin_notification_create` |
| `sessions_list.html` | modal session inline → supprimer, liens directs |

### Nettoyage infrastructure
- `templates/dashboard/admin/includes/scripts.html` : supprimer `openModal`, `closeModal`, `loadModal`, `buildSessionForm`, `openSessionModal`
- `templates/dashboard/admin/layouts/base.html` : supprimer `#modal-backdrop`, `#modal-panel`, `#modal-content`
- `templates/dashboard/admin/includes/scripts.html` : supprimer les `gsap` calls liés aux modals (garder notifications polling)

### Changements teacher (4 templates)
| Template | Action |
|---|---|
| `assignments.html` | Supprimer `addAssignmentModal`, créer page `teacher_assignment_create.html` + vue + URL |
| `courses.html` | Supprimer `addCourseModal`, créer page `teacher_course_create.html` + vue + URL |
| `resources.html` | Supprimer `createResourceModal` + `editResourceModal`, créer pages dédiées |
| `evaluations.html` | Supprimer `evalModal`, créer page `teacher_evaluation_detail.html` |

### Vues backend
Les vues `_create` et `_edit` existantes retournent déjà des `redirect()` sur succès — aucun changement backend nécessaire pour le côté admin. Pour les vues teacher à créer, même pattern : `redirect()` vers la liste après POST.

---

## 2. Redesign formulaires

### Principes
- **Layout** : page entière, pas de modal, pas de sidebar collapse
- **Structure** : header breadcrumb → card sections → footer actions fixe
- **Grid** : 2 colonnes sur desktop, 1 colonne mobile
- **Tokens visuels** : `#056f77` primary, `#26b2bd` accent, `gray-200` borders, `gray-50` bg sections
- **Inputs** : `h-10`, `rounded-sm`, `border-gray-200`, `focus:ring-1 focus:ring-[#26b2bd]`
- **Labels** : au-dessus du champ, `text-xs font-semibold text-gray-600 uppercase tracking-wide`
- **Sections** : séparateur + icône lucide + titre section + grid champs
- **Footer** : `sticky bottom-0 bg-white border-t border-gray-100 px-6 py-3 flex justify-end gap-3`
  - Annuler : `border border-gray-200 text-gray-600 hover:bg-gray-50`
  - Enregistrer : `bg-[#056f77] text-white hover:bg-[#045f66]`

### Templates à refondre
- `admin_form.html` — formulaire générique simple
- `student_form.html` — double form User + Student (sections : Compte / Profil étudiant / Statut)
- `teacher_form.html` — double form User + Teacher (sections : Compte / Profil formateur / Rémunération)
- `session_form.html` — multi-sections (Identification / Horaires / Participants / Pédagogie / Récurrence)
- `paiement_formateur_form.html` — sections Formateur / Période / Montant
- `certificate_form.html` — sections Étudiant / Formation / Compétences

---

## 3. Séances récurrentes

### Nouveau modèle `SessionSeries`

```python
class SessionSeries(models.Model):
    teacher = ForeignKey(Teacher, CASCADE, related_name='series')
    language = ForeignKey(Language, CASCADE)
    students = ManyToManyField(Student, blank=True)
    day_of_week = IntegerField()          # 0=lundi … 6=dimanche
    start_time = TimeField()
    end_time = TimeField()
    recurrence_start = DateField()         # date de la 1ère occurrence
    recurrence_end = DateField(null=True)  # null = générer 12 mois
    type_seance = CharField(choices=TYPE_SEANCE_CHOICES, default='individuelle')
    meeting_link = URLField(blank=True, null=True)
    notes = TextField(blank=True)
    created_at = DateTimeField(auto_now_add=True)
```

### Champ ajouté à `Session`

```python
series = ForeignKey(SessionSeries, null=True, blank=True, on_delete=SET_NULL, related_name='occurrences')
series_index = PositiveIntegerField(null=True, blank=True)  # ordre dans la série
```

### Logique de génération (`dashboard/services.py`)

```python
def generate_series_occurrences(series: SessionSeries) -> list[Session]:
    """Génère toutes les Session à partir d'une SessionSeries."""
    # Itère semaine par semaine depuis recurrence_start
    # jusqu'à recurrence_end (ou recurrence_start + 365 jours)
    # Crée une Session par semaine, status='scheduled'

def apply_series_edit(session: Session, scope: str, updated_data: dict):
    """
    scope: 'this' | 'this_and_future' | 'all'
    - 'this': met à jour seulement cette Session
    - 'this_and_future': met à jour session + toutes les occurrences avec series_index >= session.series_index
    - 'all': met à jour toutes les occurrences de la série + la SessionSeries elle-même
    """

def apply_series_delete(session: Session, scope: str):
    """Même logique de scope pour la suppression."""
```

### Vues admin

| URL | Vue | Description |
|---|---|---|
| `/administrateur/seances/series/` | `admin_session_series_list` | Liste des séries actives |
| `/administrateur/seances/series/creer/` | `admin_session_series_create` | Création série + génération occurrences |
| `/administrateur/seances/series/<id>/modifier/` | `admin_session_series_edit` | Modifier la série (scope dialog) |
| `/administrateur/seances/series/<id>/supprimer/` | `admin_session_series_delete` | Supprimer série (scope dialog) |

### Formulaire session — champ récurrence

Dans `session_form.html`, section **Récurrence** :
- Toggle `is_recurring` (checkbox)
- Si activé : affiche `recurrence_end` (date picker) + note sur les jours générés
- Submit crée `SessionSeries` + appelle `generate_series_occurrences()`

### Page scope (édition/suppression d'une occurrence de série)

Template `session_scope_choice.html` — page intermédiaire après soumission d'un formulaire edit/delete sur une occurrence d'une série :
```
Cette séance fait partie d'une série récurrente.
Quelle portée souhaitez-vous appliquer ?
○ Seulement cette séance
○ Cette séance et les suivantes
○ Toutes les séances de la série
[Confirmer]
```

---

## 4. Graphes dynamiques

### Problèmes identifiés
1. Marge nette calculée en template (`|add:"-"|add:...`) — casse sur les décimaux
2. Pas de graphe revenus mensuels
3. Taux de présence affiché en texte seul, pas de chart

### Corrections view (`admin_dashboard`)
- Calculer `marge_nette = revenue_total - total_paiements_formateurs` côté Python
- Ajouter `revenue_labels`, `revenue_data` : CA mensuel sur 6 mois depuis `Payment.objects.filter(status='paid')`
- Ajouter `new_students_labels`, `new_students_data` : nouveaux étudiants par mois sur 6 mois

### Nouveaux graphes (template `index.html`)
1. **Bar chart revenus** (6 mois) — remplace l'espace vide à droite du doughnut
2. **Ring attendance** — petit gauge `attendance_rate` dans les KPIs secondaires (remplace texte seul)
3. **Sparkline étudiants** — `new_students_data` en mini line chart dans la stat card

### Données hardcodées à corriger
- Marge nette dans le template → passer `marge_nette` depuis la view
- `attendance_rate` affiché comme chiffre seul → ajouter chart.js doughnut mini

---

## Migrations

```
0003_sessionseries.py         — crée SessionSeries
0004_session_series_fk.py     — ajoute Session.series + Session.series_index
```

## Ordre d'implémentation recommandé

1. **Modèle + migration** SessionSeries → `services.py`
2. **Forms on pages** : nettoyage modals admin + teacher
3. **Redesign formulaires** : templates refondus
4. **Vues séances récurrentes** : create/edit/delete avec scope
5. **Graphes** : corrections view + template

---

## Non inclus dans ce scope
- Envoi d'emails de rappel sur séances récurrentes
- Interface mobile native
- Synchronisation Google Calendar API
- Séances bi-hebdomadaires ou mensuelles (uniquement hebdomadaire pour l'instant)
