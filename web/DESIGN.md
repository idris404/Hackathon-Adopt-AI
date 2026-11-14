# Charte Graphique & Guide de Style — Greffe4IA (Page 3)

Ce document récapitule l'analyse visuelle et technique de la **Page 3** du projet Figma **Greffe4IA** (`node-id=6:246`), comprenant les écrans :
1. **Greffe rénale — Tableau de bord** (`node-id=8:2` — 1536 × 1160 px)
2. **Greffe rénale — Fiche patient** (`node-id=9:2` — 1536 × 1340 px)

Il détaille l'ensemble de la **palette chromatique**, les **tokens de design** et fournit des **prompts prêts à l'emploi** pour reproduire fidèlement cette identité visuelle sur n'importe quel générateur (v0, Lovable, Claude Artifacts, Figma AI, Midjourney).

---

## 1. Identité Visuelle & Principes de Style

L'interface adopte un style **Clinical HealthTech / Medical SaaS Premium** conçu pour les équipes de néphrologie et de coordination hospitalière :
- **Clarté et sobriété clinique** : Réduction maximale du bruit cognitif, hiérarchie stricte des données vitales et des statuts cliniques.
- **Palette chromatique rassurante et institutionnelle** :
  - **Teal & Vert forêt** : Évoque le soin, la précision médicale et la stabilité.
  - **Ardoise pétrole profond** (`#0d2328`) en barre latérale : Ancre visuellement l'application et renforce son caractère professionnel.
  - **Ambre chaud / Ocre médical** : Signale avec douceur mais fermeté les résultats douteux et les éléments nécessitant un contrôle biologique urgent.
  - **Fonds froids légèrement teintés** (`#f4f7f8`) : Réduit la fatigue visuelle des praticiens par rapport à un blanc pur.
- **Design quasi sans ombres (Flat + Hairline Borders)** : Les blocs sont délimités par des bordures subtiles de 1 px (`#e4ecee`), évitant les ombres portées lourdes pour privilégier une esthétique épurée et moderne.
- **Micro-badges compacts & Stepper linéaire** : Puces d'état colorées à fond pastel doux pour catégoriser instantanément les patients et les étapes du greffon.

---

## 2. Palette de Couleurs Complète

### 2.1. Couleurs Principales & Marque (Teal Médical)

| Nom du Token | Valeur HEX | Rôle & Usage dans l'UI |
| :--- | :--- | :--- |
| **Teal Primaire (Action)** | `#087f74` | Boutons d'action principaux (*Ajouter un patient*, *Modifier le dossier*, *Ouvrir la validation*), sur-titres en majuscules (*SUIVI DES GREFFES RÉNALES*), liens cliquables (*Ouvrir*, *Examiner*), étapes actives du stepper. |
| **Teal Foncé Institutionnel** | `#0d554f` | Couleur de la croix médicale `+` dans le logo supérieur gauche. |
| **Menthe Pastel Emblème** | `#c5f0d9` | Fond carré arrondi de l'icône logo médical. |
| **Menthe Active Navigation** | `#d9f8e6` | Texte de l'élément de navigation actuellement actif dans la sidebar. |
| **Teal Sélection Sidebar** | `#20433f` | Fond rectangulaire arrondi marquant l'onglet actif dans la barre latérale. |
| **Menthe Très Pâle (Surfaces)** | `#e9f5f1` | Fond des icônes de KPI (*Patients en attente*, *Dossiers à valider*), fond des pastilles d'étapes du parcours, badge de pagination active. |
| **Teal Glacé Doux** | `#eef7f3` | Fond du badge *Session sécurisée* dans la topbar. |
| **Vert Sauge Succès (Texte)** | `#24745a` | Texte du badge de statut *À jour*. |
| **Vert Sauge Succès (Fond)** | `#e8f5ef` | Fond pastel du badge de statut *À jour*. |
| **Bordure & Liaison Sarcelle** | `#cfe1de` | Bordure subtile des boutons secondaires (*Examiner*) et lignes de liaison entre étapes de greffe. |
| **Liaison Stepper** | `#caddd9` | Ligne horizontale reliant les étapes du parcours clinique. |

---

### 2.2. Barre Latérale Sombre (Petrol Slate / Dark Forest)

| Nom du Token | Valeur HEX | Rôle & Usage dans l'UI |
| :--- | :--- | :--- |
| **Fond Sidebar Principal** | `#0d2328` | Fond de la barre latérale gauche (232 px de large), créant un contraste statutaire fort avec l'espace de travail. |
| **Fond Bloc Aide & Support** | `#17353b` | Fond de la carte *Besoin d’aide ?* intégrée en bas de menu. |
| **Fond Pastille Compteur** | `#284249` | Fond des compteurs de dossiers neutres (*128*, *12*). |
| **Lignes Séparatrices Menu** | `#294047` | Lignes fines de séparation dans la navigation latérale. |
| **Texte Menu Inactif** | `#bcd0d1` | Libellés des pages inactives de la navigation. |
| **Texte Compteur Inactif** | `#cddedf` | Texte numérique dans les pastilles de compteur inactives. |
| **Texte Secondaire Sidebar** | `#8ea9ac` | Sous-titres techniques (*COORDINATION RÉNALE*, *Unité de greffe rénale*). |
| **Texte Établissement** | `#dcebe8` | Intitulé de l'hôpital (*CHU Saint-Louis*). |
| **Texte Lien Support** | `#9bb9b8` | Texte du lien externe *Contacter le support ↗*. |

---

### 2.3. Neutres, Surfaces de Données & Typographie

| Nom du Token | Valeur HEX | Rôle & Usage dans l'UI |
| :--- | :--- | :--- |
| **Fond de Page Global** | `#f4f7f8` | Fond d'écran global (gris brume clinique), très doux pour le contraste des cartes blanches. |
| **Blanc Pur (Surfaces)** | `#ffffff` | Cartes de statistiques, conteneurs, tableaux de patients, barre d'en-tête supérieure. |
| **Texte Primaire (Pétrole Noir)** | `#183b40` | Titres H1/H2, noms des patients (*Claire Martin*), grandes valeurs numériques KPI, libellés forts. |
| **Texte Secondaire (Ardoise Médicale)** | `#687d82` | Sous-titres, étiquettes de métriques (*Créatinine*, *DFGe*), dates, unités de mesure, mentions légales. |
| **Texte Placeholder / Grisé** | `#849599` | Placeholder des champs de formulaire (*Rechercher un identifiant patient…*). |
| **Bordure / Séparateur Principal** | `#e4ecee` | Lignes de bordure des cartes (1 px), traits de séparation de tableau, intercalaires verticaux. |
| **Fond En-têtes & Filtres** | `#f7fafa` | Bandeau d'en-tête des colonnes du tableau des patients. |
| **Fond Badges Neutres** | `#f0f5f5` | Fond des badges *Archivé*, *Exemple fictif*, compteur total patient. |
| **Fond Cartes Métriques** | `#f4f9f8` | Fond des tuiles individuelles de biologie (*Créatinine 138 µmol/L*, *DFGe 41*). |
| **Bordure Bouton Neutre** | `#d7e4e4` | Contour du bouton secondaire *Exporter le dossier*. |

---

### 2.4. Alertes, Vigilance & Résultats Douteux (Ambre Clinique)

| Nom du Token | Valeur HEX | Rôle & Usage dans l'UI |
| :--- | :--- | :--- |
| **Texte Alerte / Douteux** | `#9c601c` / `#935b1b` | Titre du bloc *Résultats douteux*, libellés des badges *À contrôler*, *À revoir*, bouton *Analyser*. |
| **Texte KPI Alerte** | `#ac661b` | Sous-texte du KPI critique (*À examiner en priorité*). |
| **Fond Pastille Alerte** | `#fff2df` | Fond des badges d'alerte biologique (*Résultat douteux*, *À contrôler*, *À revoir*). |
| **Fond Notification / Warning** | `#fff5e5` | Fond du bloc d'avertissement *Dosage résiduel en attente*. |
| **Fond Ligne Tableau Critique** | `#fffcf6` | Fond d'une ligne de patient présentant une anomalie dans la liste. |
| **Fond Bouton Alerte** | `#fff8ec` | Fond du bouton d'action *Analyser*. |
| **Bordure Alerte / Ambre** | `#eadfcf` / `#eedcbd` | Contour du bloc de résultats douteux et du bouton *Analyser*. |
| **Pastille Alerte Sidebar** | `#5f4932` | Fond du badge d'alerte dans la barre latérale sombre. |
| **Texte Alerte Sidebar** | `#ffdba7` | Chiffre de notification d'alerte dans la sidebar (*5*). |

---

### 2.5. Information & Validation Médicale (Bleu Médical)

| Nom du Token | Valeur HEX | Rôle & Usage dans l'UI |
| :--- | :--- | :--- |
| **Bleu Médical Acier (Texte)** | `#38688e` | Texte des badges d'attente d'approbation (*À valider*, *Compte rendu à signer*). |
| **Bleu Glace Pastel (Fond)** | `#eaf3fb` | Fond pastel des badges *À valider* et *Compte rendu à signer*. |

---

## 3. Typographie & Règles de Mise en Page

- **Famille de police** : `Inter`, sans-serif (remplaçable par Geist Sans ou SF Pro).
- **Graisses utilisées** :
  - `Regular` (400) : Paragraphes, valeurs secondaires, mentions légales, placeholders.
  - `Medium` (500) : Badges, données tabulaires, boutons secondaires, sous-titres de cartes.
  - `Semi-Bold` (600) : Titres H1/H2/H3, identifiants patients, grands chiffres KPI, boutons primaires.
- **Échelle typographique** :
  - **10 px** : Sur-titres en capitales (*SUIVI DES GREFFES RÉNALES*), mentions de confidentialité.
  - **11 px** : Textes de badges d'état, en-têtes de tableau, métriques secondaires, timestamps.
  - **12 px - 13 px** : Corps de texte, éléments de menu, données du tableau, boutons.
  - **14 px - 15 px** : Sous-titres d'introduction, éléments de formulaire.
  - **16 px - 18 px** : Titres de cartes et sections (*Validation*, *Résultats douteux*, *Données préopératoires*).
  - **23 px - 27 px** : Nom du patient (*Claire Martin*), titre de la page (*Fiche patient*).
  - **30 px** : Chiffres clés KPI (*128*, *12*, *5*, *111*), titre principal du dashboard.
- **Rayons de courbure (Border Radius)** :
  - Badges & Chips : `4px` à `5px`
  - Boutons & Champs : `6px` à `8px`
  - Cartes & Panneaux : `10px` à `12px`
  - Puces circulaires du stepper : `rounded-full` (diamètre `30px`)

---

## 4. Prompts Prêts à l'Emploi pour Générer ce Style

### Prompt 1 — Générateur d'Interface Code (v0, Lovable, Claude Artifacts, Cursor, Bolt)

> Copiez ce prompt directement dans un outil de génération de code front-end (React, Tailwind CSS, Vue) :

```markdown
Crée une interface web médicale et clinique de haute précision (CHU / Hôpital / Greffe d'organes) en React et Tailwind CSS en respectant STRICTEMENT la charte graphique suivante :

1. AMBIANCE & TONE :
- Style "Hospital Clinical HealthTech" : ultra-propre, rassurant, institutionnel, haute densité d'information sans surcharge visuelle.
- Pas d'ombres portées excessives (flat avec bordures fines hairline de 1px).

2. PALETTE DE COULEURS OBLIGATOIRE :
- Fond d'écran général : #f4f7f8 (gris clinique brumeux doux).
- Sidebar sombre (232px de large) : #0d2328 (ardoise pétrole profond), avec liens inactifs #bcd0d1, item actif sur fond #20433f avec texte #d9f8e6, et séparateurs #294047.
- Surfaces et cartes : blanc pur #ffffff avec bordure 1px #e4ecee et arrondi rounded-xl (12px).
- Couleur Primaire / Action : #087f74 (teal médical vif) pour boutons principaux, liens d'action, accents actifs et sur-titres en uppercase.
- Texte principal : #183b40 (pétrole très sombre, pas de noir pur).
- Texte secondaire : #687d82 (ardoise froide pour labels, unités, dates).
- Statut Succès / À jour : texte #24745a sur fond pastel #e8f5ef.
- Statut Alerte / Résultats Douteux : texte ambre #9c601c sur fond pastel #fff2df, avec cartes en bordure #eadfcf.
- Statut En Attente / À valider : texte bleu acier #38688e sur fond pastel #eaf3fb.

3. STRUCTURE DE PAGE :
- Barre latérale fixe à gauche avec logo médical (emblème vert menthe #c5f0d9 avec croix #0d554f), navigation avec badges numériques et carte support client en bas.
- Barre supérieure blanche (hauteur 80px) avec fil d'Ariane, badge "Session sécurisée" vert pâle, notifications et profil médecin.
- Contenu principal : 
  - Section d'en-tête avec titre épuré et bouton primaire #087f74.
  - Grille de 4 cartes KPI (Grand chiffre 30px #183b40, libellé, icône dans carré arrondi #e9f5f1).
  - Tableau de données ou fiches cliniques détaillées (tableaux à lignes alternées avec badge de statut compact et actions d'inspection).
- Typographie : Police Inter, contrastes nets, hiérarchie rigoureuse.
```

---

### Prompt 2 — Pour Générateur Figma / Outils Design AI

> Utilisez ce prompt dans des outils comme Figma AI, First Draft ou Uizard :

```markdown
Design a modern, clinical hospital coordination web application (desktop resolution 1536x1160px) named "Greffe4IA - Coordination Rénale".

Design characteristics:
- Left Navigation Sidebar (width 232px): Deep dark petroleum slate (#0d2328), hospital logo with mint green medical emblem (+), navigation links (Overview, Patient List, Validation, Doubtful Results, History, Settings) with soft cyan-gray text (#bcd0d1) and active state indicator in dark pine teal (#20433f).
- Main Background: Very light clinical cool gray mist (#f4f7f8).
- White flat cards with crisp 1px borders in #e4ecee, rounded corners at 10px-12px, zero drop shadows.
- Primary Accent: Clinical deep teal (#087f74) used for primary call-to-actions, category overlines, and progression step indicators.
- Typography: Clean Inter font. Primary headers in #183b40, secondary body and labels in muted slate gray #687d82.
- Dashboard Components:
  1. Top navigation bar with breadcrumb, secure session pill tag, and coordinator doctor profile avatar.
  2. 4 Metric KPI cards: "Patients en attente (128)", "Dossiers à valider (12)", "Résultats douteux (5)" with amber highlight (#fff2df background, #9c601c text), and "Dossiers à jour (111)".
  3. Patient records table with columns: Patient ID, Organ support modality, Blood type, Registration date, and colored status chips ("À valider" in soft blue #eaf3fb, "À jour" in soft sage #e8f5ef, "Résultat douteux" in warm peach amber #fff2df).
  4. Clinical patient pathway timeline stepper with numbered circles (1, 2, 3, 4) connected by subtle horizontal lines.
```

---

### Prompt 3 — Pour Générateurs d'Images (Midjourney v6 / DALL-E 3)

> Utilisez ce prompt en anglais pour générer des maquettes de présentation ou des visuels conceptuels :

```text
High-fidelity modern UI/UX desktop dashboard design mockup of a specialized nephrology and kidney transplant hospital portal called Greffe4IA, clean professional medical interface, 1536x1160 layout, dark deep petrol slate left sidebar (#0d2328) with mint green medical cross emblem, main workspace in light clinical gray mist background (#f4f7f8), pristine white flat metric cards with 1px hairline borders, clinical teal primary accents (#087f74), sophisticated patient monitoring table, biological lab metrics (Creatinine, eGFR, Blood group A+), warm amber alert chips for doubtful lab results, Inter typography, Apple Health and Epic Systems inspired aesthetics, 8k resolution, minimalist, ultra-sharp detail, Figma UI showcase --ar 16:10 --v 6.1
```

---

### Prompt 4 — Prompt Système pour Agent ou Développeur Front-End

> À ajouter dans les instructions système d'un projet pour garantir la continuité du style :

```text
Tu es le Lead UI Designer et Développeur Front-End de l'application médicale Greffe4IA.
Pour toute nouvelle vue ou composant que tu développes :
1. Respecte strictement les classes de couleur définies :
   - bg-[#f4f7f8] pour le fond global
   - bg-white avec border border-[#e4ecee] pour toutes les cartes
   - text-[#183b40] pour les titres et textes prioritaires
   - text-[#687d82] pour les labels secondaires
   - bg-[#087f74] hover:bg-[#06655c] pour les boutons primaires
   - Pour les statuts critiques (résultats douteux) : utiliser uniquement la gamme ambre (bg-[#fff2df], text-[#9c601c], border-[#eadfcf]).
   - Pour les statuts en attente de signature : utiliser la gamme bleu acier (bg-[#eaf3fb], text-[#38688e]).
   - Pour les statuts conformes : utiliser la gamme sauge (bg-[#e8f5ef], text-[#24745a]).
2. Maintiens un style clinique épuré : aucun dégradé criard, aucune ombre 3D lourde, bordures fines de 1px, typographie Inter ou system-ui.
```

---

## 5. Configuration Tailwind CSS Prête à l'Emploi

Pour intégrer directement cette charte dans votre projet `tailwind.config.js` :

```javascript
/** @type {import('tailwindcss').Config} */
module.exports = {
  theme: {
    extend: {
      colors: {
        clinical: {
          bg: '#f4f7f8',
          card: '#ffffff',
          border: '#e4ecee',
          text: {
            primary: '#183b40',
            secondary: '#687d82',
            muted: '#849599',
          },
        },
        sidebar: {
          bg: '#0d2328',
          card: '#17353b',
          badge: '#284249',
          border: '#294047',
          active: '#20433f',
          textActive: '#d9f8e6',
          text: '#bcd0d1',
          textMuted: '#8ea9ac',
        },
        medical: {
          primary: '#087f74',
          dark: '#0d554f',
          mint: '#c5f0d9',
          surface: '#e9f5f1',
          light: '#eef7f3',
          border: '#cfe1de',
        },
        alert: {
          text: '#9c601c',
          badge: '#fff2df',
          notice: '#fff5e5',
          row: '#fffcf6',
          border: '#eadfcf',
          sidebarBadge: '#5f4932',
          sidebarText: '#ffdba7',
        },
        approval: {
          text: '#38688e',
          badge: '#eaf3fb',
        },
        success: {
          text: '#24745a',
          badge: '#e8f5ef',
        },
      },
      fontFamily: {
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'sans-serif'],
      },
    },
  },
};
```
