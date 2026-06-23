# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ItReassignWizard(models.TransientModel):
    _name = 'it.reassign.wizard'
    _description = 'Wizard de réaffectation d\'équipement'

    equipment_id = fields.Many2one(
        'it.equipment', string='Équipement', required=True, readonly=True
    )
    current_employee_id = fields.Many2one(
        'hr.employee', string='Employé actuel', readonly=True
    )
    new_employee_id = fields.Many2one(
        'hr.employee', string='Nouvel employé', required=True
    )
    new_department_id = fields.Many2one(
        'hr.department', string='Nouveau département'
    )
    new_location = fields.Char(string='Nouvelle localisation')
    motif = fields.Text(string='Motif de réaffectation', required=True)
    date_reassign = fields.Date(
        string='Date de réaffectation',
        default=fields.Date.today, required=True
    )

    @api.onchange('new_employee_id')
    def _onchange_new_employee(self):
        if self.new_employee_id:
            self.new_department_id = self.new_employee_id.department_id

    def action_confirm(self):
        self.ensure_one()
        equipment = self.equipment_id

        if self.new_employee_id == equipment.employee_id:
            raise UserError(
                _("Le nouvel employé est identique à l'employé actuel.")
            )

        # Clôturer l'affectation courante
        current_assignment = self.env['it.assignment'].search([
            ('equipment_id', '=', equipment.id),
            ('date_to', '=', False),
            ('active', '=', True),
        ], limit=1)
        if current_assignment:
            current_assignment.write({
                'date_to': self.date_reassign,
                'active': False,
            })

        # Créer la nouvelle affectation
        self.env['it.assignment'].create({
            'equipment_id': equipment.id,
            'employee_id': self.new_employee_id.id,
            'department_id': self.new_department_id.id if self.new_department_id else False,
            'date_from': self.date_reassign,
            'motif': self.motif,
        })

        # Mettre à jour l'équipement
        vals = {
            'employee_id': self.new_employee_id.id,
            'department_id': self.new_department_id.id if self.new_department_id else False,
        }
        if self.new_location:
            vals['location'] = self.new_location
        equipment.write(vals)

        # Message dans le chatter
        equipment.message_post(
            body=_("Réaffectation : %s → %s. Motif : %s") % (
                self.current_employee_id.name if self.current_employee_id else _('N/A'),
                self.new_employee_id.name,
                self.motif,
            )
        )

        return {'type': 'ir.actions.act_window_close'}
