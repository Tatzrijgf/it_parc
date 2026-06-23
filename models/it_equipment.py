# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ItEquipmentCategory(models.Model):
    _name = 'it.equipment.category'
    _description = 'Catégorie d\'équipement'
    _order = 'name'

    name = fields.Char(string='Catégorie', required=True)
    description = fields.Text(string='Description')
    equipment_count = fields.Integer(
        string='Nb équipements',
        compute='_compute_equipment_count'
    )

    def _compute_equipment_count(self):
        for cat in self:
            cat.equipment_count = self.env['it.equipment'].search_count(
                [('category_id', '=', cat.id)]
            )


class ItEquipment(models.Model):
    _name = 'it.equipment'
    _description = 'Équipement informatique'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'
    _rec_name = 'name'

    # ── Identification ──────────────────────────────────────────────────────
    name = fields.Char(
        string='Nom / Désignation', required=True, tracking=True
    )
    reference = fields.Char(
        string='Référence interne', copy=False, readonly=True,
        default=lambda self: _('Nouveau')
    )
    serial_number = fields.Char(
        string='Numéro de série', copy=False, tracking=True
    )
    category_id = fields.Many2one(
        'it.equipment.category', string='Catégorie', tracking=True
    )
    brand = fields.Char(string='Marque', tracking=True)
    model = fields.Char(string='Modèle', tracking=True)
    description = fields.Text(string='Description technique')

    # ── Acquisition ──────────────────────────────────────────────────────────
    purchase_date = fields.Date(string='Date d\'achat', tracking=True)
    purchase_price = fields.Float(string='Valeur d\'achat (FCFA)', tracking=True)
    supplier_id = fields.Many2one('res.partner', string='Fournisseur')
    invoice_ref = fields.Char(string='Référence facture')

    # ── Garantie ────────────────────────────────────────────────────────────
    warranty_date = fields.Date(string='Fin de garantie', tracking=True)
    warranty_days_left = fields.Integer(
        string='Jours de garantie restants',
        compute='_compute_warranty_days_left', store=True
    )
    warranty_expired = fields.Boolean(
        string='Garantie expirée',
        compute='_compute_warranty_days_left', store=True
    )

    # ── Affectation courante ─────────────────────────────────────────────────
    employee_id = fields.Many2one(
        'hr.employee', string='Employé affecté', tracking=True
    )
    department_id = fields.Many2one(
        'hr.department', string='Département', tracking=True
    )
    location = fields.Char(string='Localisation / Site', tracking=True)

    # ── État / workflow ──────────────────────────────────────────────────────
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('assigned', 'Affecté'),
        ('maintenance', 'En maintenance'),
        ('retired', 'Retiré'),
    ], string='État', default='draft', required=True, tracking=True)

    # ── Relations ────────────────────────────────────────────────────────────
    assignment_ids = fields.One2many(
        'it.assignment', 'equipment_id', string='Historique affectations'
    )
    intervention_ids = fields.One2many(
        'it.intervention', 'equipment_id', string='Interventions'
    )
    contract_ids = fields.Many2many(
        'it.contract',
        'it_contract_equipment_rel',
        'equipment_id',
        'contract_id',
        string='Contrats associés'
    )
    alerte_ids = fields.One2many(
        'it.alerte', 'equipment_id', string='Alertes'
    )

    # ── Compteurs ────────────────────────────────────────────────────────────
    intervention_count = fields.Integer(
        string='Nb interventions',
        compute='_compute_intervention_count'
    )
    total_maintenance_cost = fields.Float(
        string='Coût total maintenance',
        compute='_compute_total_maintenance_cost', store=True
    )
    assignment_count = fields.Integer(
        string='Nb affectations',
        compute='_compute_assignment_count'
    )

    # ── Image ────────────────────────────────────────────────────────────────
    image = fields.Binary(string='Photo', attachment=True)

    # ── Notes ────────────────────────────────────────────────────────────────
    notes = fields.Html(string='Notes internes')

    # ────────────────────────────────────────────────────────────────────────
    # Sequence
    # ────────────────────────────────────────────────────────────────────────
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('reference', _('Nouveau')) == _('Nouveau'):
                vals['reference'] = self.env['ir.sequence'].next_by_code(
                    'it.equipment'
                ) or _('Nouveau')
        return super().create(vals_list)

    # ────────────────────────────────────────────────────────────────────────
    # Computed fields
    # ────────────────────────────────────────────────────────────────────────
    @api.depends('warranty_date')
    def _compute_warranty_days_left(self):
        today = fields.Date.today()
        for rec in self:
            if rec.warranty_date:
                delta = (rec.warranty_date - today).days
                rec.warranty_days_left = delta
                rec.warranty_expired = delta < 0
            else:
                rec.warranty_days_left = 0
                rec.warranty_expired = False

    @api.depends('intervention_ids')
    def _compute_intervention_count(self):
        for rec in self:
            rec.intervention_count = len(rec.intervention_ids)

    @api.depends('intervention_ids.cost')
    def _compute_total_maintenance_cost(self):
        for rec in self:
            rec.total_maintenance_cost = sum(
                rec.intervention_ids.mapped('cost')
            )

    @api.depends('assignment_ids')
    def _compute_assignment_count(self):
        for rec in self:
            rec.assignment_count = len(rec.assignment_ids)

    # ────────────────────────────────────────────────────────────────────────
    # Workflow actions
    # ────────────────────────────────────────────────────────────────────────
    def action_assign(self):
        """Passe en état Affecté."""
        for rec in self:
            if rec.state not in ('draft',):
                raise UserError(
                    _("Seuls les équipements en brouillon peuvent être affectés.")
                )
            if not rec.employee_id:
                raise UserError(
                    _("Veuillez affecter un employé avant de valider.")
                )
            rec.state = 'assigned'
            # Créer une ligne d'historique d'affectation
            self.env['it.assignment'].create({
                'equipment_id': rec.id,
                'employee_id': rec.employee_id.id,
                'department_id': rec.department_id.id if rec.department_id else False,
                'date_from': fields.Date.today(),
                'motif': _('Affectation initiale'),
            })

    def action_set_maintenance(self):
        """Passe en état En maintenance."""
        for rec in self:
            if rec.state not in ('assigned',):
                raise UserError(
                    _("Seul un équipement affecté peut passer en maintenance.")
                )
            rec.state = 'maintenance'

    def action_return_from_maintenance(self):
        """Retour en Affecté depuis maintenance."""
        for rec in self:
            if rec.state != 'maintenance':
                raise UserError(_("L'équipement n'est pas en maintenance."))
            rec.state = 'assigned'

    def action_retire(self):
        """Met au rebut."""
        for rec in self:
            if rec.state == 'retired':
                raise UserError(_("L'équipement est déjà retiré."))
            rec.state = 'retired'

    def action_reset_draft(self):
        """Remet en brouillon."""
        for rec in self:
            rec.state = 'draft'

    # ────────────────────────────────────────────────────────────────────────
    # Smart buttons
    # ────────────────────────────────────────────────────────────────────────
    def action_view_interventions(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Interventions'),
            'res_model': 'it.intervention',
            'view_mode': 'list,form',
            'domain': [('equipment_id', '=', self.id)],
            'context': {'default_equipment_id': self.id},
        }

    def action_view_assignments(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Historique affectations'),
            'res_model': 'it.assignment',
            'view_mode': 'list,form',
            'domain': [('equipment_id', '=', self.id)],
            'context': {'default_equipment_id': self.id},
        }

    def action_open_reassign_wizard(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Réaffecter l\'équipement'),
            'res_model': 'it.reassign.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_equipment_id': self.id,
                'default_current_employee_id': self.employee_id.id,
            },
        }

    # ────────────────────────────────────────────────────────────────────────
    # Export Excel
    # ────────────────────────────────────────────────────────────────────────
    def action_export_excel_inventory(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Export Excel Inventaire'),
            'res_model': 'it.export.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'export_type': 'inventory'},
        }

    # ────────────────────────────────────────────────────────────────────────
    # Couleur Kanban
    # ────────────────────────────────────────────────────────────────────────
    def _get_kanban_state_label(self):
        mapping = {
            'draft': 'Brouillon',
            'assigned': 'Affecté',
            'maintenance': 'En maintenance',
            'retired': 'Retiré',
        }
        return mapping.get(self.state, '')
