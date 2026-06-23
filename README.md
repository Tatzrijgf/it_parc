# IT Parc — Module Odoo 18 de gestion de parc informatique

Module développé pour **TECHPARK CI** permettant la gestion complète du parc informatique interne.

---

## Installation

### Prérequis

- Odoo 18 Enterprise
- Python 3.11+
- Bibliothèque `xlsxwriter` :
  ```bash
  pip install xlsxwriter
  ```

### Déploiement

1. Copier le dossier `it_parc` dans votre dossier `custom_addons`.

2. Ajouter le chemin dans `odoo.conf` :
   ```ini
   addons_path = .../odoo/addons,.../custom_addons
   ```

3. Redémarrer le serveur Odoo :
   ```bash
   python odoo-bin -u it_parc -d <votre_base>
   ```

4. Dans Odoo → **Apps** → Rechercher `IT Parc` → Installer.

---

## Fonctionnalités

### 01 — Gestion des équipements
- Enregistrement avec caractéristiques techniques complètes (marque, modèle, n° série)
- Workflow : **Brouillon → Affecté → En maintenance → Retiré**
- Calcul automatique des jours de garantie restants
- Codes couleur : rouge (garantie expirée), orange (< 30j)

### 02 — Affectations
- Liaison employé / département / localisation
- Historique complet de toutes les mutations
- **Wizard de réaffectation** avec saisie de motif obligatoire

### 03 — Interventions
- Types : corrective et préventive
- Durée calculée automatiquement (date début → date fin)
- **Vue calendrier** des interventions planifiées
- Rapport d'intervention en HTML

### 04 — Contrats fournisseurs
- Maintenance, licences, support
- Calcul automatique des jours restants avant expiration
- **Wizard de renouvellement** avec calcul de date automatique

### 05 — Alertes automatiques
- Modèle `it.alerte` avec type garantie/contrat
- **Tâche planifiée** (`ir.cron`) quotidienne — 08h00
- **Wizard de scan manuel** pour déclencher à la demande
- Seuil paramétrable via `ir.config_parameter`

### 06 — Import CSV
- Upload fichier CSV avec choix du séparateur
- Détection des doublons par **numéro de série**
- Rapport détaillé : lignes créées / ignorées / en erreur
- Téléchargement d'un modèle CSV vide

### 07 — Rapports PDF (QWeb)
| Rapport | Déclencheur |
|---|---|
| Fiche individuelle d'équipement | Bouton dans la vue formulaire |
| Rapport d'inventaire complet | Menu Rapports |
| Historique des maintenances | Depuis la liste des interventions |

### 08 — Exports Excel (xlsxwriter)
| Export | Contenu |
|---|---|
| Inventaire complet | Toutes colonnes, mise en couleur garantie |
| Coûts maintenance | Par asset et par mois |
| Contrats expirants | < 60j, mise en couleur selon urgence |

### 09 — Dashboard OWL
- Composant OWL 2 natif (aucun framework tiers)
- Données chargées via contrôleur JSON-RPC `/it_parc/dashboard_data`
- **6 KPIs** : total, affectés, maintenance, alertes, contrats, coût
- **2 graphiques SVG natifs** : répartition par catégorie + coûts mensuels
- Top 5 équipements les plus coûteux en maintenance
- Résumé alertes cliquable

---

## Sécurité

| Groupe | Droits |
|---|---|
| `IT Technicien` | Lecture équipements/contrats/alertes, CRUD interventions |
| `IT Manager` | Accès complet + imports + exports + rapports |

---

## Structure du module

```
it_parc/
├── __manifest__.py
├── __init__.py
├── models/
│   ├── it_equipment.py       # Équipements + catégories
│   ├── it_assignment.py      # Historique affectations
│   ├── it_intervention.py    # Interventions maintenance
│   ├── it_contract.py        # Contrats fournisseurs
│   └── it_alerte.py          # Alertes + cron
├── wizards/
│   ├── it_reassign_wizard.py
│   ├── it_contract_renew_wizard.py
│   ├── it_alert_scan_wizard.py
│   ├── it_import_csv_wizard.py
│   └── it_export_wizard.py
├── controllers/
│   └── it_dashboard_controller.py
├── views/
│   ├── it_equipment_views.xml
│   ├── it_assignment_views.xml
│   ├── it_intervention_views.xml
│   ├── it_contract_views.xml
│   ├── it_alerte_views.xml
│   ├── it_dashboard_views.xml
│   └── it_parc_menus.xml
├── report/
│   ├── it_equipment_report.xml
│   ├── it_inventory_report.xml
│   └── it_maintenance_report.xml
├── security/
│   ├── it_parc_groups.xml
│   ├── ir.model.access.csv
│   └── it_parc_rules.xml
├── data/
│   ├── it_parc_sequence.xml
│   ├── it_parc_cron.xml
│   └── it_parc_demo.xml      # 10 équipements, 3 contrats, 5 interventions
├── static/
│   ├── description/icon.svg
│   └── src/
│       ├── js/dashboard.js
│       ├── xml/dashboard.xml
│       └── css/it_parc.css
└── README.md
```

---

## Données de démo

Le fichier `data/it_parc_demo.xml` contient :
- **10 équipements** (postes de travail, serveurs, imprimantes, réseau, téléphonie)
- **3 contrats** fournisseurs (maintenance, licence, support)
- **5 interventions** (correctives et préventives)

---

## Auteur

TECHPARK CI — Abidjan, Côte d'Ivoire  
Version : 18.0.1.0.0
