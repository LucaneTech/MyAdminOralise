# Migration vers Tailwind CSS

## Vue d'ensemble

Ce projet a été migré de Bootstrap vers Tailwind CSS pour améliorer la cohérence visuelle et utiliser les couleurs personnalisées définies dans le fichier `input.css`.

## Couleurs personnalisées

Les couleurs principales du projet sont définies dans `tailwind.config.js` :

- **main-color**: `#26b2bc` (couleur principale)
- **main-color-hover**: `#1a8f96` (couleur principale au survol)
- **main-color-opacity**: `#26b2bc4d` (couleur principale avec transparence)
- **secondary-color**: `#c41e3a` (couleur secondaire)
- **secondary-color-hover**: `#a11b32b7` (couleur secondaire au survol)

## Structure des templates

### Templates de base

1. **`templates/dashboard/student/layouts/base.html`**
   - Template de base pour les étudiants
   - Utilise Tailwind CSS avec les couleurs personnalisées
   - Inclut la navigation latérale et la barre supérieure
   - Support du mode sombre

2. **`templates/dashboard/teacher/layouts/base.html`**
   - Template de base pour les enseignants
   - Même structure que celui des étudiants
   - Navigation adaptée aux fonctionnalités enseignants

### Pages converties

1. **Dashboard étudiant** (`templates/dashboard/student/home/index.html`)
   - Cartes de statistiques avec les couleurs personnalisées
   - Tableaux responsifs
   - Effets de survol et transitions

2. **Dashboard enseignant** (`templates/dashboard/teacher/home/index.html`)
   - Interface adaptée aux enseignants
   - Actions rapides avec les couleurs du thème
   - Statistiques et tableaux

## Classes Tailwind utilisées

### Couleurs
- `text-main-color` : Texte en couleur principale
- `bg-main-color` : Arrière-plan en couleur principale
- `text-secondary-color` : Texte en couleur secondaire
- `bg-secondary-color` : Arrière-plan en couleur secondaire

### Layout
- `grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4` : Grille responsive
- `flex items-center justify-between` : Flexbox pour alignement
- `space-y-4` : Espacement vertical

### Composants
- `bg-white rounded-lg shadow-lg` : Cartes avec ombre
- `hover:shadow-xl transition-shadow duration-300` : Effets de survol
- `text-3xl font-bold` : Titres en gras

### Responsive
- `hidden md:block` : Masquer sur mobile, afficher sur desktop
- `text-sm md:text-base` : Taille de texte responsive

## Mode sombre

Le support du mode sombre est intégré avec les classes `dark:` :
- `dark:bg-gray-900` : Arrière-plan sombre
- `dark:text-white` : Texte blanc en mode sombre
- `dark:border-gray-700` : Bordures sombres

## Compilation

Pour compiler Tailwind CSS :

```bash
cd SchoolManagement
npx tailwindcss -i ./static/css/input.css -o ./static/build/output.css --watch
```

## Avantages de la migration

1. **Cohérence** : Utilisation des couleurs définies dans `input.css`
2. **Performance** : CSS optimisé et purgé automatiquement
3. **Maintenabilité** : Classes utilitaires plus lisibles
4. **Responsive** : Meilleur support mobile
5. **Accessibilité** : Meilleure structure sémantique

## Prochaines étapes

1. Convertir les pages restantes (profil, paramètres, etc.)
2. Ajouter des animations personnalisées
3. Optimiser les performances
4. Tester sur différents navigateurs

## Notes importantes

- Les classes Bootstrap ont été remplacées par leurs équivalents Tailwind
- Les couleurs personnalisées sont utilisées de manière cohérente
- Le mode sombre est supporté nativement
- La responsivité est améliorée 