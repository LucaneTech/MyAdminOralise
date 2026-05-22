# Spec — Reporting pédagogique : séparation admin / formateur

**Date** : 2026-05-22  
**Statut** : approuvé

---

## Contexte

La vue `reporting_formateur` gère actuellement les rôles admin et teacher dans une seule fonction et rend systématiquement le template teacher. Le lien admin sidenav pointe vers une URL qui requiert un `teacher_id` et cause un 404 sans paramètre. Le sidenav teacher n'a pas de lien reporting. L'objectif est de séparer proprement les deux espaces et d'améliorer le design.

---

## Architecture cible

### Vues (`dashboard/views.py`)

| Vue | Rôle | Accès |
|---|---|---|
| `admin_reporting_list` | Liste de tous les formateurs avec stats de période | admin uniquement |
| `admin_reporting_detail(teacher_id)` | Reporting détaillé d'un formateur | admin uniquement |
| `teacher_reporting` | Propre reporting du formateur connecté | teacher uniquement |

La vue `reporting_formateur` est supprimée et remplacée par ces 3 vues.

### URLs (`dashboard/urls.py`)

```
administrateur/reporting/                  → admin_reporting_list     (name: admin_reporting_list)
administrateur/reporting/<int:teacher_id>/ → admin_reporting_detail   (name: admin_reporting_detail)
reporting/                                 → teacher_reporting         (name: teacher_reporting)
```

Les 2 anciennes routes (`reporting/` et `administrateur/reporting/<id>/`) sont remplacées.

---

## Données transmises aux templates

### `admin_reporting_list`

- `date_debut`, `date_fin` — période filtrée
- `teachers_stats` — liste de dicts par formateur :
  ```python
  {
      'teacher': <Teacher>,
      'nb_sessions': int,
      'nb_sessions_validees': int,
      'nb_students': int,
      'nb_en_difficulte': int,
      'top_comp_faible': str | None,  # compétence la plus fréquente
  }
  ```
- `total_sessions_global`, `total_teachers_actifs`, `total_students_global` — KPIs globaux

### `admin_reporting_detail`

- `teacher` — objet Teacher
- `date_debut`, `date_fin`
- `total_sessions`, `sessions_validees`
- `student_stats` — liste de dicts : `student`, `nb_sessions`, `avg_participation`, `avg_comprehension`, `avg_engagement`
- `students_en_difficulte` — liste de Students
- `comp_faibles` — dict `{oral, comprehension, ecrit, grammaire, vocabulaire: int}`

### `teacher_reporting`

Même données que `admin_reporting_detail` (sans `teacher` qui est toujours le user courant).

---

## Templates

### `templates/dashboard/admin/home/reporting.html` — Liste formateurs

Extends `dashboard/admin/layouts/base.html`.

Structure :
1. Header page + filtre période (form GET : `date_debut`, `date_fin`)
2. 3 KPI cards globaux : formateurs actifs, séances réalisées, étudiants suivis
3. Table noble : colonnes Formateur / Séances / Validées / Étudiants / En difficulté / Top faiblesse / Action
4. Chaque ligne a un bouton "Voir le reporting →" → `admin_reporting_detail` avec `teacher_id`
5. État vide si aucun formateur actif sur la période

### `templates/dashboard/admin/home/reporting_detail.html` — Détail formateur (admin)

Extends `dashboard/admin/layouts/base.html`.

Structure :
1. Breadcrumb : "Reporting / [Nom formateur]" + bouton retour → `admin_reporting_list`
2. Filtre période
3. 3 KPI cards : séances, validées, étudiants
4. Grille 2 colonnes :
   - Gauche (2/3) : table étudiants avec barres de progression visuelles (participation, compréhension, engagement sur /4)
   - Droite (1/3) : panel "Étudiants en difficulté" + panel "Points faibles récurrents" avec barres horizontales

### `templates/dashboard/teacher/home/reporting.html` — Reporting formateur (redesign)

Extends `dashboard/teacher/layouts/base.html`.

Structure identique au détail admin mais dans le layout teacher. Améliorations design :
- Typographie plus affirmée pour les KPIs (taille et couleur)
- Barres de progression horizontales colorées (vert/jaune/rouge) à la place des badges
- Section "Points faibles" avec barres proportionnelles (width % du max)
- En-tête avec nom du formateur et sous-titre période analysée

---

## Changements sidenav

### Admin sidenav (`templates/dashboard/admin/includes/sidenav.html`)
- Lien "Reporting" : `admin_reporting_formateur` → `admin_reporting_list`
- Condition active : `'reporting' in request.path` (inchangé)

### Teacher sidenav (`templates/dashboard/teacher/includes/sidenav.html`)
- Ajouter un lien "Reporting" après "Évaluations" :
  - URL : `teacher_reporting`
  - Icône lucide : `trending-up`
  - Couleur accent : lime

---

## Contraintes

- Tous les accès sont protégés par `@login_required` et vérification du rôle (Http404 sinon)
- Le filtre de période utilise des GET params (`date_debut`, `date_fin`) au format `YYYY-MM-DD`
- Valeur par défaut : 14 derniers jours
- Les sessions filtrées ont `seance_realisee=True`
- Seuil "en difficulté" : score moyen des 3 métriques < 2.5 (sur 4)

---

## Fichiers modifiés

| Fichier | Nature |
|---|---|
| `dashboard/views.py` | Supprimer `reporting_formateur`, ajouter 3 vues |
| `dashboard/urls.py` | Remplacer 2 routes, ajouter 1, mettre à jour les imports |
| `templates/dashboard/admin/includes/sidenav.html` | Corriger le lien reporting |
| `templates/dashboard/teacher/includes/sidenav.html` | Ajouter lien reporting |
| `templates/dashboard/admin/home/reporting.html` | Créer |
| `templates/dashboard/admin/home/reporting_detail.html` | Créer |
| `templates/dashboard/teacher/home/reporting.html` | Réécrire |
| `templates/dashboard/teacher/home/index.html` | Ligne 168 : `reporting_formateur` → `teacher_reporting` |
| `templates/dashboard/admin/home/list_teachers.html` | Ligne 96 : `admin_reporting_formateur teacher.id` → `admin_reporting_detail teacher.id` |
