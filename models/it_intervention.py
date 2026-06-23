# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ItIntervention(models.Model):
    _name = 'it.intervention'
    _description = 'Intervention / Maintenance'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_start desc'

    name = fields.Char(
        string='Référence', copy=False, readonly=True,
        default=lambda self: _('Nouveau')
    )
    equipment_id = fields.Many2one(
        'it.equipment', string='Équipement',
        required=True, tracking=True, ondelete='cascade'
    )
    intervention_type = fields.Selection([
        ('corrective', 'Corrective'),
        ('preventive', 'Préventive'),
    ], string='Type', required=True, default='corrective', tracking=True)

    technician_id = fields.Many2one(
        'hr.employee', string='Technicien', tracking=True
    )
    date_start = fields.Datetime(
        string='Début', required=True,
        default=fields.Datetime.now, tracking=True
    )
    date_end = fields.Datetime(string='Fin', tracking=True)
    duration = fields.Float(
        string='Durée (heures)',
        compute='_compute_duration', store=True
    )
    cost = fields.Float(string='Coût (FCFA)', tracking=True)
    description = fields.Text(string='Description du problème')
    report = fields.Html(string='Rapport d\'intervention')
    state = fields.Selection([
        ('planned', 'Planifiée'),
        ('in_progress', 'En cours'),
        ('done', 'Terminée'),
        ('cancelled', 'Annulée'),
    ], string='État', default='planned', tracking=True)

    # Pour la vue calendrier
    date_start_date = fields.Date(
        string='Date début', compute='_compute_dates', store=True
    )
    date_end_date = fields.Date(
        string='Date fin', compute='_compute_dates', store=True
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('Nouveau')) == _('Nouveau'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'it.intervention'
                ) or _('Nouveau')
        return super().create(vals_list)

    @api.depends('date_start', 'date_end')
    def _compute_duration(self):
        for rec in self:
            if rec.date_start and rec.date_end:
                delta = rec.date_end - rec.date_start
                rec.duration = delta.total_seconds() / 3600.0
            else:
                rec.duration = 0.0

    @api.depends('date_start', 'date_end')
    def _compute_dates(self):
        for rec in self:
            rec.date_start_date = rec.date_start.date() if rec.date_start else False
            rec.date_end_date = rec.date_end.date() if rec.date_end else False

    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        for rec in self:
            if rec.date_end and rec.date_start and rec.date_end < rec.date_start:
                raise ValidationError(
                    _("La date de fin ne peut pas être avant la date de début.")
                )

    def action_start(self):
        for rec in self:
            rec.state = 'in_progress'
            # Mettre l'équipement en maintenance
            if rec.equipment_id.state == 'assigned':
                rec.equipment_id.state = 'maintenance'

    def action_done(self):
        for rec in self:
            if not rec.date_end:
                rec.date_end = fields.Datetime.now()
            rec.state = 'done'
            # Remettre l'équipement en affecté
            if rec.equipment_id.state == 'maintenance':
                rec.equipment_id.state = 'assigned'

    def action_cancel(self):
        for rec in self:
            rec.state = 'cancelled'

    def name_get(self):
        result = []
        for rec in self:
            name = f"[{rec.name}] {rec.equipment_id.name}"
            result.append((rec.id, name))
        return result
