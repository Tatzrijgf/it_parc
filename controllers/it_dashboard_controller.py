# -*- coding: utf-8 -*-
from odoo import http, fields
from odoo.http import request
from dateutil.relativedelta import relativedelta


class ItDashboardController(http.Controller):

    @http.route('/it_parc/dashboard_data', type='json', auth='user')
    def get_dashboard_data(self):
        """Retourne les données KPI et graphique pour le dashboard OWL."""
        Equipment = request.env['it.equipment']
        Intervention = request.env['it.intervention']
        Contract = request.env['it.contract']
        Alerte = request.env['it.alerte']

        # ── KPIs ─────────────────────────────────────────────────────────────
        total_equipment = Equipment.search_count([])
        assigned_count = Equipment.search_count([('state', '=', 'assigned')])
        maintenance_count = Equipment.search_count([('state', '=', 'maintenance')])
        retired_count = Equipment.search_count([('state', '=', 'retired')])
        draft_count = Equipment.search_count([('state', '=', 'draft')])

        # Alertes ouvertes
        open_alerts = Alerte.search_count([('state', '=', 'open')])
        warranty_alerts = Alerte.search_count([
            ('state', '=', 'open'), ('alerte_type', '=', 'warranty')
        ])
        contract_alerts = Alerte.search_count([
            ('state', '=', 'open'), ('alerte_type', '=', 'contract')
        ])

        # Contrats expirant bientôt (< 30j)
        expiring_contracts = Contract.search_count([
            ('days_left', '>=', 0), ('days_left', '<=', 30)
        ])

        # Coût total maintenance
        all_interventions = Intervention.search([('state', '=', 'done')])
        total_maintenance_cost = sum(all_interventions.mapped('cost'))

        # Interventions ce mois
        today = fields.Date.today()
        month_start = today.replace(day=1)
        interventions_this_month = Intervention.search_count([
            ('date_start', '>=', str(month_start)),
            ('state', '=', 'done'),
        ])

        # ── Graphique : répartition par catégorie ────────────────────────────
        categories = request.env['it.equipment.category'].search([])
        category_data = []
        for cat in categories:
            count = Equipment.search_count([('category_id', '=', cat.id)])
            if count > 0:
                category_data.append({'label': cat.name, 'value': count})

        # Équipements sans catégorie
        no_cat = Equipment.search_count([('category_id', '=', False)])
        if no_cat > 0:
            category_data.append({'label': 'Non catégorisé', 'value': no_cat})

        # ── Graphique : évolution coûts maintenance par mois (6 derniers mois) ─
        monthly_costs = []
        for i in range(5, -1, -1):
            month_date = today - relativedelta(months=i)
            m_start = month_date.replace(day=1)
            m_end = (m_start + relativedelta(months=1))
            ints = Intervention.search([
                ('date_start', '>=', str(m_start)),
                ('date_start', '<', str(m_end)),
                ('state', '=', 'done'),
            ])
            monthly_costs.append({
                'label': m_start.strftime('%b %Y'),
                'value': sum(ints.mapped('cost')),
                'count': len(ints),
            })

        # ── Top 5 équipements les plus coûteux en maintenance ────────────────
        top_equipments = []
        equipments_with_cost = Equipment.search([
            ('total_maintenance_cost', '>', 0)
        ], order='total_maintenance_cost desc', limit=5)
        for eq in equipments_with_cost:
            top_equipments.append({
                'name': eq.name,
                'reference': eq.reference,
                'cost': eq.total_maintenance_cost,
                'interventions': eq.intervention_count,
            })

        return {
            'kpis': {
                'total_equipment': total_equipment,
                'assigned_count': assigned_count,
                'maintenance_count': maintenance_count,
                'retired_count': retired_count,
                'draft_count': draft_count,
                'open_alerts': open_alerts,
                'warranty_alerts': warranty_alerts,
                'contract_alerts': contract_alerts,
                'expiring_contracts': expiring_contracts,
                'total_maintenance_cost': total_maintenance_cost,
                'interventions_this_month': interventions_this_month,
            },
            'charts': {
                'by_category': category_data,
                'monthly_costs': monthly_costs,
            },
            'top_equipments': top_equipments,
        }
