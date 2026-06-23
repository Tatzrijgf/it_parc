# -*- coding: utf-8 -*-
{
    'name': 'IT Parc - Gestion de Parc Informatique',
    'version': '18.0.1.0.0',
    'category': 'IT Management',
    'summary': 'Gestion complète du parc informatique : équipements, affectations, maintenances, contrats et alertes.',
    'description': """
        Module de gestion du parc informatique pour TECHPARK CI.
        
        Fonctionnalités :
        - Gestion des équipements avec workflow (Brouillon → Affecté → En maintenance → Retiré)
        - Affectation aux employés avec historique complet
        - Suivi des interventions et maintenances
        - Gestion des contrats fournisseurs
        - Alertes automatiques (garanties, contrats)
        - Import en masse via CSV
        - Rapports PDF QWeb
        - Exports Excel (xlsxwriter)
        - Dashboard OWL avec KPIs en temps réel
    """,
    'author': 'TECHPARK CI',
    'website': 'https://www.techparkci.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'mail',
        'hr',
        'web',
    ],
    'data': [
        # Sécurité
        'security/it_parc_groups.xml',
        'security/ir.model.access.csv',
        'security/it_parc_rules.xml',

        # Données
        'data/it_parc_sequence.xml',
        'data/it_parc_cron.xml',

        # Vues - modèles principaux
        'views/it_equipment_views.xml',
        'views/it_assignment_views.xml',
        'views/it_intervention_views.xml',
        'views/it_contract_views.xml',
        'views/it_alerte_views.xml',

        # Wizards
        'wizards/it_reassign_wizard_views.xml',
        'wizards/it_contract_renew_wizard_views.xml',
        'wizards/it_alert_scan_wizard_views.xml',
        'wizards/it_import_csv_wizard_views.xml',
        'wizards/it_export_wizard_views.xml',

        # Rapports PDF
        'report/it_equipment_report.xml',
        'report/it_inventory_report.xml',
        'report/it_maintenance_report.xml',

        # Menus (contient aussi l'action dashboard)
        'views/it_parc_menus.xml',

    ],
    'demo': [
        'data/it_parc_demo.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'it_parc/static/src/css/it_parc.css',
            'it_parc/static/src/js/dashboard.js',
            'it_parc/static/src/xml/dashboard.xml',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'images': ['static/description/9360672.png'],
}
