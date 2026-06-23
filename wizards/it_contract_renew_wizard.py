# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta


class ItContractRenewWizard(models.TransientModel):
    _name = 'it.contract.renew.wizard'
    _description = 'Wizard de renouvellement de contrat'

    contract_id = fields.Many2one(
        'it.contract', string='Contrat', required=True, readonly=True
    )
    current_end_date = fields.Date(
        string='Date d\'expiration actuelle',
        related='contract_id.date_end', readonly=True
    )
    new_start_date = fields.Date(
        string='Nouvelle date de début', required=True,
        default=fields.Date.today
    )
    duration_months = fields.Integer(
        string='Durée (mois)', default=12, required=True
    )
    new_end_date = fields.Date(
        string='Nouvelle date de fin',
        compute='_compute_new_end_date', store=False
    )
    new_amount = fields.Float(string='Nouveau montant (FCFA)')
    notes = fields.Text(string='Notes de renouvellement')

    @api.depends('new_start_date', 'duration_months')
    def _compute_new_end_date(self):
        for rec in self:
            if rec.new_start_date and rec.duration_months:
                rec.new_end_date = rec.new_start_date + relativedelta(
                    months=rec.duration_months
                )
            else:
                rec.new_end_date = False

    def action_confirm(self):
        self.ensure_one()
        if not self.new_end_date:
            raise UserError(_("Impossible de calculer la nouvelle date de fin."))

        contract = self.contract_id
        contract.write({
            'date_start': self.new_start_date,
            'date_end': self.new_end_date,
            'amount': self.new_amount or contract.amount,
            'state': 'renewed',
        })

        contract.message_post(
            body=_("Contrat renouvelé du %s au %s. Montant : %s FCFA. %s") % (
                self.new_start_date,
                self.new_end_date,
                self.new_amount or contract.amount,
                self.notes or '',
            )
        )

        return {'type': 'ir.actions.act_window_close'}
