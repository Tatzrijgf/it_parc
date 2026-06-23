# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class ItAlerte(models.Model):
    _name = 'it.alerte'
    _description = 'Alerte de garantie ou contrat'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_echeance asc'

    name = fields.Char(string='Titre', required=True, tracking=True)
    alerte_type = fields.Selection([
        ('warranty', 'Garantie équipement'),
        ('contract', 'Contrat fournisseur'),
    ], string='Type d\'alerte', required=True, tracking=True)

    equipment_id = fields.Many2one(
        'it.equipment', string='Équipement', ondelete='cascade'
    )
    contract_id = fields.Many2one(
        'it.contract', string='Contrat', ondelete='cascade'
    )
    date_echeance = fields.Date(string='Date d\'échéance', required=True, tracking=True)
    days_left = fields.Integer(
        string='Jours restants',
        compute='_compute_days_left', store=True
    )
    state = fields.Selection([
        ('open', 'Ouverte'),
        ('acknowledged', 'Prise en compte'),
        ('closed', 'Fermée'),
    ], string='Statut', default='open', tracking=True)

    threshold_days = fields.Integer(
        string='Seuil déclenchement (jours)', default=30
    )
    notes = fields.Text(string='Notes')

    @api.depends('date_echeance')
    def _compute_days_left(self):
        today = fields.Date.today()
        for rec in self:
            if rec.date_echeance:
                rec.days_left = (rec.date_echeance - today).days
            else:
                rec.days_left = 0

    def action_acknowledge(self):
        for rec in self:
            rec.state = 'acknowledged'

    def action_close(self):
        for rec in self:
            rec.state = 'closed'

    def action_reopen(self):
        for rec in self:
            rec.state = 'open'

    @api.model
    def _cron_generate_alerts(self):
        """Tâche planifiée : génère les alertes pour garanties et contrats proches."""
        threshold = int(
            self.env['ir.config_parameter'].sudo().get_param(
                'it_parc.alert_threshold_days', default=30
            )
        )
        self._generate_warranty_alerts(threshold)
        self._generate_contract_alerts(threshold)

    @api.model
    def _generate_warranty_alerts(self, threshold):
        today = fields.Date.today()
        equipments = self.env['it.equipment'].search([
            ('warranty_date', '!=', False),
            ('state', 'not in', ['retired']),
        ])
        for eq in equipments:
            days = (eq.warranty_date - today).days
            if 0 <= days <= threshold:
                # Vérifier si une alerte ouverte existe déjà
                existing = self.search([
                    ('equipment_id', '=', eq.id),
                    ('alerte_type', '=', 'warranty'),
                    ('state', 'in', ['open', 'acknowledged']),
                ])
                if not existing:
                    self.create({
                        'name': _('Garantie expire dans %d jours : %s') % (days, eq.name),
                        'alerte_type': 'warranty',
                        'equipment_id': eq.id,
                        'date_echeance': eq.warranty_date,
                        'threshold_days': threshold,
                    })

    @api.model
    def _generate_contract_alerts(self, threshold):
        today = fields.Date.today()
        contracts = self.env['it.contract'].search([
            ('date_end', '!=', False),
            ('state', 'not in', ['expired', 'renewed']),
        ])
        for contract in contracts:
            days = (contract.date_end - today).days
            if 0 <= days <= threshold:
                existing = self.search([
                    ('contract_id', '=', contract.id),
                    ('alerte_type', '=', 'contract'),
                    ('state', 'in', ['open', 'acknowledged']),
                ])
                if not existing:
                    self.create({
                        'name': _('Contrat expire dans %d jours : %s') % (days, contract.name),
                        'alerte_type': 'contract',
                        'contract_id': contract.id,
                        'date_echeance': contract.date_end,
                        'threshold_days': threshold,
                    })

    def name_get(self):
        result = []
        for rec in self:
            result.append((rec.id, rec.name))
        return result
