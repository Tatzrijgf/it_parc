# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ItContract(models.Model):
    _name = 'it.contract'
    _description = 'Contrat fournisseur (maintenance / licence)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_end asc'

    name = fields.Char(string='Intitulé du contrat', required=True, tracking=True)
    reference = fields.Char(
        string='Référence', copy=False, readonly=True,
        default=lambda self: _('Nouveau')
    )
    contract_type = fields.Selection([
        ('maintenance', 'Maintenance'),
        ('license', 'Licence'),
        ('support', 'Support'),
        ('other', 'Autre'),
    ], string='Type de contrat', required=True, default='maintenance', tracking=True)

    supplier_id = fields.Many2one(
        'res.partner', string='Fournisseur', required=True, tracking=True
    )
    date_start = fields.Date(
        string='Date de début', required=True, tracking=True
    )
    date_end = fields.Date(
        string='Date d\'expiration', required=True, tracking=True
    )
    amount = fields.Float(string='Montant (FCFA)', tracking=True)
    description = fields.Text(string='Description')

    # Équipements couverts
    equipment_ids = fields.Many2many(
        'it.equipment',
        'it_contract_equipment_rel',
        'contract_id',
        'equipment_id',
        string='Équipements couverts'
    )
    equipment_count = fields.Integer(
        string='Nb équipements',
        compute='_compute_equipment_count'
    )

    # Calcul jours restants
    days_left = fields.Integer(
        string='Jours restants',
        compute='_compute_days_left', store=True
    )
    is_expired = fields.Boolean(
        string='Expiré',
        compute='_compute_days_left', store=True
    )
    state = fields.Selection([
        ('active', 'Actif'),
        ('expiring_soon', 'Expire bientôt'),
        ('expired', 'Expiré'),
        ('renewed', 'Renouvelé'),
    ], string='Statut', default='active', tracking=True)

    notes = fields.Html(string='Notes')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('reference', _('Nouveau')) == _('Nouveau'):
                vals['reference'] = self.env['ir.sequence'].next_by_code(
                    'it.contract'
                ) or _('Nouveau')
            if 'state' not in vals:
                vals['state'] = self._compute_state_from_dates(
                    vals.get('date_end')
                )
        return super().create(vals_list)

    def write(self, vals):
        res = super().write(vals)
        if 'date_end' in vals or 'state' in vals or 'days_left' in vals:
            for rec in self:
                if rec.state != 'renewed':
                    new_state = self._compute_state_from_dates(rec.date_end)
                    if new_state != rec.state:
                        rec.state = new_state
        return res

    @api.depends('date_end')
    def _compute_days_left(self):
        today = fields.Date.today()
        for rec in self:
            if rec.date_end:
                delta = (rec.date_end - today).days
                rec.days_left = delta
                rec.is_expired = delta < 0
            else:
                rec.days_left = 0
                rec.is_expired = False

    @api.model
    def _compute_state_from_dates(self, date_end):
        """Calcule le statut à partir de la date d'expiration."""
        if not date_end:
            return 'active'
        delta = (date_end - fields.Date.today()).days
        if delta < 0:
            return 'expired'
        if delta <= 30:
            return 'expiring_soon'
        return 'active'

    @api.model
    def _compute_state_cron(self):
        """Met à jour le statut de tous les contrats selon leur date d'expiration."""
        for rec in self.search([]):
            if rec.state == 'renewed':
                continue
            new_state = self._compute_state_from_dates(rec.date_end)
            if new_state != rec.state:
                rec.state = new_state

    def _compute_equipment_count(self):
        for rec in self:
            rec.equipment_count = len(rec.equipment_ids)

    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        for rec in self:
            if rec.date_start and rec.date_end and rec.date_end < rec.date_start:
                raise ValidationError(
                    _("La date d'expiration ne peut pas être avant la date de début.")
                )

    def action_renew(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Renouveler le contrat'),
            'res_model': 'it.contract.renew.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_contract_id': self.id},
        }

    def name_get(self):
        result = []
        for rec in self:
            name = f"[{rec.reference}] {rec.name}"
            result.append((rec.id, name))
        return result
