# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class ItAlertScanWizard(models.TransientModel):
    _name = 'it.alert.scan.wizard'
    _description = 'Wizard de scan manuel des alertes'

    threshold_days = fields.Integer(
        string='Seuil d\'alerte (jours)',
        default=lambda self: int(
            self.env['ir.config_parameter'].sudo().get_param(
                'it_parc.alert_threshold_days', default=30
            )
        ),
        required=True,
        help="Générer des alertes pour les garanties/contrats expirant dans ce nombre de jours."
    )
    scan_warranties = fields.Boolean(
        string='Scanner les garanties équipements', default=True
    )
    scan_contracts = fields.Boolean(
        string='Scanner les contrats fournisseurs', default=True
    )

    # Résultats
    result_message = fields.Text(
        string='Résultat', readonly=True
    )
    state = fields.Selection([
        ('draft', 'Prêt'),
        ('done', 'Terminé'),
    ], default='draft')

    def action_scan(self):
        self.ensure_one()
        alerte_model = self.env['it.alerte']
        created = 0

        if self.scan_warranties:
            before = alerte_model.search_count([])
            alerte_model._generate_warranty_alerts(self.threshold_days)
            after = alerte_model.search_count([])
            created += (after - before)

        if self.scan_contracts:
            before = alerte_model.search_count([])
            alerte_model._generate_contract_alerts(self.threshold_days)
            after = alerte_model.search_count([])
            created += (after - before)

        self.write({
            'result_message': _(
                "Scan terminé.\n%d nouvelle(s) alerte(s) créée(s) avec un seuil de %d jours."
            ) % (created, self.threshold_days),
            'state': 'done',
        })

        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_view_alerts(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Alertes'),
            'res_model': 'it.alerte',
            'view_mode': 'list,form',
            'domain': [('state', '=', 'open')],
        }
