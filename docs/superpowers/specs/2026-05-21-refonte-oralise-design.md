# Spec — Refonte Oralise (Session, Stats, UI)
_Date : 2026-05-21_

---

## Contexte

Application Django 5.2 mono-app (`dashboard`) de gestion d'école de langues (Oralise).  
Trois rôles : **Admin**, **Teacher**, **Student**.  
Stack actuelle : Argon CSS (Bootstrap) pour les dashboards, Tailwind CLI v4 + DaisyUI v5 pour la page login, allauth, sqlite en dev / PostgreSQL en prod (Railway).

---

## AXE 1 — Refonte Architecture Backend (Système de Réservation)

### 1.1 Suppression du modèle `Schedule`

- Supprimer le modèle `Schedule` et sa migration associée.
- Supprimer toutes ses FK, vues, URLs, et templates liés :
  - Vues : `add_schedule`, `edit_schedule`, `delete_schedule`, `load_schedule_week`, `filter_schedule`, `quick_add_schedule`, `schedule_view`, `teacher_schedule_view`, `admin_schedules_list`, `admin_schedule_create`, `admin_schedule_edit`, `admin_schedule_delete`
  - URLs : tous les patterns `teacher/schedule/`, `student/schedule`, `administrateur/plannings/`
  - Templates : `dashboard/teacher/home/schedule.html`, `dashboard/student/home/schedule.html`, `dashboard/teacher/includes/schedule_modals.html`, `dashboard/admin/home/schedules_list.html`
- Créer une migration de suppression propre (ne pas toucher aux données Session existantes).

### 1.2 Modification du modèle `Session`

**Changement principal :**
```python
# AVANT
student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='sessions')

# APRÈS
students = models.ManyToManyField(Student, related_name='sessions', verbose_name="étudiants")
```

- Le champ `type_seance` (individuelle/groupe) reste inchangé.
- Tous les filtres `session.student` dans `views.py`, `models.py`, et `signals.py` sont mis à jour vers `session.students`.
- `Session.recent_sessions` et `Session.upcoming_sessions` dans `Student` utilisent `Session.objects.filter(students=self)`.
- `Teacher.today_sessions` et `Teacher.weekly_sessions` restent filtrés par `teacher=self`.

### 1.3 Trigger — Notification d'évaluation

Quand `Session.status` passe à `'completed'` :

1. Signal `post_save` sur `Session` détecte le changement de statut (`pre_save` stocke l'ancien statut).
2. Pour chaque `student` dans `session.students.all()` : crée une `Notification` :
   - `notification_type = 'evaluation_request'`
   - `title = "Votre cours est terminé — donnez votre avis"`
   - `message = f"Votre séance de {session.language} avec {session.teacher} du {session.date} est terminée. Cliquez pour évaluer."`
   - `user = student.user`
3. Nouveau type ajouté dans `Notification.NOTIFICATION_TYPES` : `('evaluation_request', 'Demande d\'évaluation')`.

### 1.4 API JSON Sessions (nouvelles URLs sous `/api/`)

| URL | Méthode | Accès | Description |
|---|---|---|---|
| `/api/sessions/` | GET | Tous | Feed FullCalendar. Params: `start`, `end` (ISO). Filtre par rôle automatique. |
| `/api/sessions/create/` | POST | Admin, Teacher | Créer une session. Retourne JSON `{success, session_id}`. |
| `/api/sessions/<id>/` | GET | Tous | Détail session en JSON (pour pré-remplir modale). |
| `/api/sessions/<id>/update/` | POST | Admin, Teacher | Modifier session (données form ou drag-drop). |
| `/api/sessions/<id>/delete/` | POST | Admin, Teacher | Supprimer session. |
| `/api/sessions/<id>/status/` | POST | Teacher, Admin | Changer statut. Déclenche notification si `completed`. |
| `/api/notifications/unread/` | GET | Tous | Retourne `{"count": N}`. Utilisé par le polling JS toutes les 30s. |

**Format réponse Feed FullCalendar :**
```json
[
  {
    "id": 1,
    "title": "Anglais — Dupont, Martin",
    "start": "2026-05-21T10:00:00",
    "end": "2026-05-21T11:00:00",
    "color": "#26b2bd",
    "extendedProps": {
      "status": "scheduled",
      "teacher": "M. Alami",
      "language": "Anglais",
      "students": ["Dupont", "Martin"],
      "session_id": 1
    }
  }
]
```

**Couleurs événements FullCalendar par statut :**
- `scheduled` → `#3b82f6` (bleu)
- `completed` → `#22c55e` (vert)
- `cancelled` → `#ef4444` (rouge)
- `rescheduled` → `#f59e0b` (ambre)
- `absent` → `#f97316` (orange)

**Filtrage par rôle :**
- Admin : toutes les sessions. Query params optionnels : `?teacher_id=X`, `?student_id=Y`, `?language_id=Z`.
- Teacher : `Session.objects.filter(teacher=request.user.teacher)`.
- Student : `Session.objects.filter(students=request.user.student)`.

### 1.5 Pages Calendrier (3 dashboards)

Chaque dashboard dispose d'une page `/sessions/` remplaçant les vues tabulaires actuelles :

- **Vue par défaut** : `timeGridWeek` (semaine).
- **Switcher** : Mois / Semaine / Jour / Liste.
- **Teacher & Admin** : clic sur créneau vide → modale GSAP "Créer session".
- **Student** : lecture seule.
- **Clic sur événement** → modale GSAP "Détail / Éditer session".
- **Drag & drop** (Teacher/Admin) → `POST /api/sessions/<id>/update/` avec `{date, start_time, end_time}`.

---

## AXE 2 — Audit et Correction des Statistiques

### 2.1 Bugs corrigés

| Fichier | Ligne | Bug | Fix |
|---|---|---|---|
| `models.py` | `Teacher.total_students` | `filter(current_teacher=self)` — champ inexistant | `filter(current_teachers=self).count()` |
| `models.py` | `Student.total_hours_used` | Champ entier manuel non synchronisé | Propriété calculée dynamiquement |
| `models.py` | `Student.hours_remaining` | Dépend de `total_hours_used` erroné | Corrigé en cascade |
| `models.py` | `PaiementFormateur.calculer_montant()` | `s.student` (FK supprimé) | `s.students.all()` |
| `views.py` | Dashboard admin | Comptages incohérents | Toujours via `Model.objects.count()` direct |

### 2.2 Nouvelles propriétés

```python
# Teacher
@property
def total_students(self):
    return Student.objects.filter(current_teachers=self).count()

# Student
@property
def total_hours_used(self):
    sessions = Session.objects.filter(students=self, status='completed')
    return round(sum(s.duration_hours for s in sessions), 1)

@property
def hours_remaining(self):
    return self.total_hours_purchased - self.total_hours_used
```

### 2.3 Optimisations

- `select_related('user', 'user__user_profile')` sur toutes les querysets de listes.
- `prefetch_related('students', 'teacher__user')` sur les vues sessions.
- Aucune requête N+1 dans les templates.

---

## AXE 3 — Refonte Frontend & UI/UX

### 3.1 Stack technique

| Outil | Source | Note |
|---|---|---|
| Tailwind CSS v4 | npm existant | Compile → `static/assets/css/output.css` |
| DaisyUI v5 | npm existant | Composants UI de base |
| `django-lucide` | `pip install django-lucide` | `{% load lucide %}` dans templates |
| GSAP 3 | CDN (jsDelivr) | Animations modales |
| FullCalendar 6 | CDN | Pages calendrier uniquement |

**Suppression :** Argon CSS (`argon.css`), Nucleo CSS, tous les CSS Bootstrap hérités dans les dashboards. Conservé uniquement pour la page `/admin/` Django (jazzmin).

### 3.2 Design System

| Règle | Valeur |
|---|---|
| Arrondi maximum | `rounded-md` |
| Ombre maximum | `shadow-xl` |
| Dégradés | Interdits |
| Couleur Student | `#d9a505` |
| Couleur Teacher | `#033050` |
| Couleur Admin | `#26b2bd` |
| Police | Inter (Google Fonts) |

### 3.3 Structure Templates

```
templates/
├── account/
│   └── login.html              ← refonte split-screen
├── dashboard/
│   ├── admin/
│   │   ├── layouts/base.html   ← nouveau, Tailwind pur
│   │   ├── includes/
│   │   │   ├── sidenav.html    ← restyled, couleur #26b2bd
│   │   │   ├── navigation.html ← restyled, polling notifs
│   │   │   └── scripts.html    ← GSAP + FullCalendar CDN
│   │   └── home/*.html         ← contenu modernisé
│   ├── teacher/
│   │   ├── layouts/base.html   ← nouveau, couleur #033050
│   │   └── ...
│   └── student/
│       ├── layouts/base.html   ← nouveau, couleur #d9a505
│       └── ...
```

### 3.4 Modales GSAP — Comportement Uniforme

Tous les formulaires CRUD s'ouvrent en modale :

**Animation :**
```javascript
// Ouverture
const tl = gsap.timeline();
tl.to('#modal-backdrop', { opacity: 1, duration: 0.2, display: 'flex' })
  .fromTo('#modal-panel', { y: 60, opacity: 0 }, { y: 0, opacity: 1, duration: 0.3, ease: 'power2.out' });

// Fermeture (reverse ou explicit)
tl.reverse();
```

**Règles :**
- Une seule modale par page, contenu injecté via `fetch`.
- Fermeture : clic backdrop, touche `ESC`, ou bouton "Annuler".
- Formulaires soumis via `fetch POST` → rechargement FullCalendar ou liste.
- Pas de `page reload` après CRUD.

### 3.5 Page Login — Split-screen

**Gauche (50%) :**
- `background-image` cover, overlay `bg-black/50`
- Logo `w-10` positionné en haut à gauche (`absolute top-6 left-6`)
- Tagline centré verticalement : `"Gérez votre école en toute clarté."`
- Sous-titre : `"La plateforme tout-en-un d'Oralise."`

**Droite (50%) :**
- Fond blanc (`bg-white`)
- Formulaire centré verticalement (flexbox)
- Champs : email, mot de passe
- Bouton couleur neutre (`bg-gray-900 text-white`)
- Lien "Mot de passe oublié ?"

**Responsive :** colonne unique sur `< md`, côté gauche masqué (`hidden md:block`).

### 3.6 Page Profil — Refonte totale

**Header :**
- Avatar circulaire (`w-24 h-24`), outline couleur rôle
- Nom complet, badge rôle coloré, matricule (si student)
- Ville · Pays · Téléphone en ligne

**Stats cards (3 colonnes) :**
- Student : Séances totales / Heures restantes / Note moyenne reçue
- Teacher : Étudiants actifs / Séances ce mois / Taux horaire
- Admin : sans stats

**Corps :**
- Section "À propos" (champ `about`)
- Section "Langues" (badges)
- Section "Objectif de formation" (si student)
- Bouton "Modifier le profil" → modale GSAP

### 3.7 Notifications Polling (UI type WhatsApp/Facebook)

**Badge navbar :**
- `fetch('/api/notifications/unread/', {credentials: 'same-origin'})` toutes les 30s
- Badge rouge avec compteur sur l'icône cloche
- Badge disparaît si `count === 0`

**Panneau notifications :**
- Dropdown slide-down sur clic cloche
- Liste des 5 dernières notifications, icône par type, timestamp relatif
- Lien "Voir tout" → `/notifications/`
- Clic notification `evaluation_request` → redirige vers `/evaluations/` (page où le student laisse son avis)

### 3.8 Tailwind Build Pipeline

**Commande de développement :**
```bash
npx @tailwindcss/cli -i ./static/assets/css/input.css -o ./static/assets/css/output.css --watch
```

**Fichier `static/assets/css/input.css` :**
```css
@import "tailwindcss";
@plugin "daisyui";
```

**Inclusion dans les base templates :**
```html
<link rel="stylesheet" href="{% static 'assets/css/output.css' %}">
```

---

## Migration de données — Session.student → Session.students

Le passage FK→M2M nécessite une migration de données explicite en 3 étapes :

1. Créer le champ `students (M2M)` en gardant temporairement `student (FK)`.
2. Migration de données : `for s in Session.objects.all(): s.students.add(s.student)`.
3. Supprimer le champ `student (FK)` dans une migration séparée.

Cette approche préserve toutes les données existantes.

---

## Ordre d'implémentation recommandé

1. **Migration modèle** : supprimer Schedule, M2M Session.students (avec migration données), nouveau type Notification.
2. **Corrections modèles** : propriétés stats fixes, signal notification.
3. **API JSON** : 7 endpoints sessions + 1 notifications.
4. **Tailwind build** : `input.css`, compiler `output.css`, vérifier.
5. **Base templates** : refonte des 3 `base.html` (admin, teacher, student).
6. **Login** : split-screen.
7. **Sidenav + Navbar** : restyled Tailwind + polling JS.
8. **Profil** : refonte totale.
9. **Pages calendrier** : FullCalendar + modales GSAP.
10. **Toutes les pages CRUD** : modales GSAP sur formulaires existants.
11. **Tests manuels** : vérifier les 3 dashboards end-to-end.

---

## Contraintes et exclusions

- **Jazzmin** (`/admin/`) non touché — reste Bootstrap.
- **Allauth** templates (`/account/`) : login refait, reste identique pour signup/reset.
- **PostgreSQL** (prod) : les migrations doivent être réversibles.
- **`django-compressor`** : désactivé pour les fichiers Tailwind (output.css déjà compilé).
- Aucune régression sur l'authentification allauth / OAuth GitHub / Google.
