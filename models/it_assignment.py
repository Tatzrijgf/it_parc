# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ItAssignment(models.Model):
    _name = 'it.assignment'
    _description = 'Historique d\'affectation d\'équipement'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_from desc'

    equipment_id = fields.Many2one(
        'it.equipment', string='Équipement',
        required=True, ondelete='cascade', tracking=True
    )
    employee_id = fields.Many2one(
        'hr.employee', string='Employé',
        required=True, tracking=True
    )
    department_id = fields.Many2one(
        'hr.department', string='Département', tracking=True
    )
    date_from = fields.Date(
        string='Date de début', required=True,
        default=fields.Date.today, tracking=True
    )
    date_to = fields.Date(string='Date de fin', tracking=True)
    motif = fields.Char(string='Motif', tracking=True)
    active = fields.Boolean(string='Active', default=True)
    duration_days = fields.Integer(
        string='Durée (jours)',
        compute='_compute_duration', store=True
    )
    notes = fields.Text(string='Notes')

    @api.depends('date_from', 'date_to')
    def _compute_duration(self):
        today = fields.Date.today()
        for rec in self:
            end = rec.date_to or today
            if rec.date_from and end >= rec.date_from:
                rec.duration_days = (end - rec.date_from).days
            else:
                rec.duration_days = 0

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for rec in self:
            if rec.date_to and rec.date_from and rec.date_to < rec.date_from:
                raise ValidationError(
                    _("La date de fin ne peut pas être antérieure à la date de début.")
                )

    def name_get(self):
        result = []
        for rec in self:
            name = f"{rec.equipment_id.name} → {rec.employee_id.name} ({rec.date_from})"
            result.append((rec.id, name))
        return result
