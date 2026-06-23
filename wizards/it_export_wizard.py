# -*- coding: utf-8 -*-
import base64
import io
from datetime import datetime, date
from odoo import models, fields, api, _
from odoo.exceptions import UserError

try:
    import xlsxwriter
except ImportError:
    xlsxwriter = None


def _date_to_datetime(d):
    """Convertit un objet date Python en datetime pour xlsxwriter."""
    if isinstance(d, datetime):
        return d
    if isinstance(d, date):
        return datetime(d.year, d.month, d.day)
    return None


class ItExportWizard(models.TransientModel):
    _name = 'it.export.wizard'
    _description = 'Wizard d\'export Excel'

    export_type = fields.Selection([
        ('inventory', 'Inventaire complet'),
        ('maintenance_costs', 'Coûts de maintenance'),
        ('expiring_contracts', 'Contrats expirant (60j)'),
    ], string='Type d\'export', required=True, default='inventory')

    department_id = fields.Many2one(
        'hr.department', string='Filtrer par département'
    )
    category_id = fields.Many2one(
        'it.equipment.category', string='Filtrer par catégorie'
    )
    date_from = fields.Date(string='Période du')
    date_to = fields.Date(string='Au')

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        # Capturer le type d'export depuis le contexte (bouton de la vue)
        export_type = (
            self.env.context.get('default_export_type') or
            self.env.context.get('export_type')
        )
        if export_type and 'export_type' in fields_list:
            res['export_type'] = export_type
        return res

    def action_export(self):
        self.ensure_one()
        if not xlsxwriter:
            raise UserError(
                _("La bibliothèque xlsxwriter n'est pas installée.\n"
                  "Exécutez : pip install xlsxwriter")
            )
        dispatch = {
            'inventory': self._export_inventory,
            'maintenance_costs': self._export_maintenance_costs,
            'expiring_contracts': self._export_expiring_contracts,
        }
        return dispatch[self.export_type]()

    # ── Export 1 : Inventaire complet ────────────────────────────────────────
    def _export_inventory(self):
        output = io.BytesIO()
        wb = xlsxwriter.Workbook(output, {'in_memory': True})
        ws = wb.add_worksheet('Inventaire')

        header_fmt = wb.add_format({
            'bold': True, 'bg_color': '#1F4E79', 'font_color': 'white',
            'border': 1, 'align': 'center', 'valign': 'vcenter', 'text_wrap': True,
        })
        cell_fmt = wb.add_format({'border': 1, 'valign': 'vcenter'})
        date_fmt = wb.add_format({'border': 1, 'num_format': 'dd/mm/yyyy'})
        money_fmt = wb.add_format({'border': 1, 'num_format': '#,##0', 'align': 'right'})
        warning_fmt = wb.add_format({'border': 1, 'bg_color': '#FFE0B2', 'font_color': '#E65100'})
        expired_fmt = wb.add_format({'border': 1, 'bg_color': '#FFCDD2', 'font_color': '#B71C1C', 'bold': True})
        ok_fmt = wb.add_format({'border': 1, 'bg_color': '#C8E6C9', 'font_color': '#1B5E20'})

        headers = [
            'Référence', 'Désignation', 'Catégorie', 'Marque', 'Modèle',
            'N° Série', 'État', 'Employé affecté', 'Département',
            'Localisation', 'Date achat', 'Valeur achat (FCFA)',
            'Fin garantie', 'Jours garantie', 'Fournisseur',
        ]
        col_widths = [13, 25, 18, 12, 16, 20, 13, 22, 18, 16, 13, 18, 13, 12, 22]

        ws.set_row(0, 28)
        for col, (header, width) in enumerate(zip(headers, col_widths)):
            ws.write(0, col, header, header_fmt)
            ws.set_column(col, col, width)

        domain = []
        if self.department_id:
            domain.append(('department_id', '=', self.department_id.id))
        if self.category_id:
            domain.append(('category_id', '=', self.category_id.id))

        equipments = self.env['it.equipment'].search(domain, order='reference')
        state_map = {
            'draft': 'Brouillon', 'assigned': 'Affecté',
            'maintenance': 'En maintenance', 'retired': 'Retiré',
        }

        for row_idx, eq in enumerate(equipments, start=1):
            if eq.warranty_expired:
                g_fmt = expired_fmt
            elif eq.warranty_days_left <= 30:
                g_fmt = warning_fmt
            else:
                g_fmt = ok_fmt

            ws.write(row_idx, 0, eq.reference or '', cell_fmt)
            ws.write(row_idx, 1, eq.name or '', cell_fmt)
            ws.write(row_idx, 2, eq.category_id.name or '', cell_fmt)
            ws.write(row_idx, 3, eq.brand or '', cell_fmt)
            ws.write(row_idx, 4, eq.model or '', cell_fmt)
            ws.write(row_idx, 5, eq.serial_number or '', cell_fmt)
            ws.write(row_idx, 6, state_map.get(eq.state, eq.state), cell_fmt)
            ws.write(row_idx, 7, eq.employee_id.name or '', cell_fmt)
            ws.write(row_idx, 8, eq.department_id.name or '', cell_fmt)
            ws.write(row_idx, 9, eq.location or '', cell_fmt)
            if eq.purchase_date:
                ws.write_datetime(row_idx, 10, _date_to_datetime(eq.purchase_date), date_fmt)
            else:
                ws.write(row_idx, 10, '', cell_fmt)
            ws.write(row_idx, 11, eq.purchase_price or 0, money_fmt)
            if eq.warranty_date:
                ws.write_datetime(row_idx, 12, _date_to_datetime(eq.warranty_date), date_fmt)
            else:
                ws.write(row_idx, 12, '', cell_fmt)
            ws.write(row_idx, 13, eq.warranty_days_left, g_fmt)
            ws.write(row_idx, 14, eq.supplier_id.name or '', cell_fmt)

        # Ligne totaux
        total_row = len(equipments) + 2
        total_fmt = wb.add_format({'bold': True, 'bg_color': '#E3F2FD', 'border': 1})
        ws.write(total_row, 0, f'TOTAL : {len(equipments)} équipement(s)', total_fmt)
        ws.write(total_row, 11, sum(equipments.mapped('purchase_price')), money_fmt)

        wb.close()
        output.seek(0)
        return self._create_download_action(
            base64.b64encode(output.read()),
            'inventaire_parc_informatique.xlsx'
        )

    # ── Export 2 : Coûts de maintenance ──────────────────────────────────────
    def _export_maintenance_costs(self):
        output = io.BytesIO()
        wb = xlsxwriter.Workbook(output, {'in_memory': True})
        ws = wb.add_worksheet('Coûts maintenance')

        header_fmt = wb.add_format({
            'bold': True, 'bg_color': '#1B5E20', 'font_color': 'white',
            'border': 1, 'align': 'center',
        })
        cell_fmt = wb.add_format({'border': 1})
        money_fmt = wb.add_format({'border': 1, 'num_format': '#,##0', 'align': 'right'})
        dt_fmt = wb.add_format({'border': 1, 'num_format': 'dd/mm/yyyy hh:mm'})
        month_fmt = wb.add_format({'border': 1, 'num_format': 'mmmm yyyy', 'bold': True})

        headers = [
            'Équipement', 'Référence', 'Catégorie', 'N° Intervention',
            'Type', 'Technicien', 'Date début', 'Durée (h)', 'Coût (FCFA)', 'Mois',
        ]
        widths = [25, 14, 16, 16, 14, 20, 18, 10, 16, 14]

        for col, (h, w) in enumerate(zip(headers, widths)):
            ws.write(0, col, h, header_fmt)
            ws.set_column(col, col, w)

        domain = []
        if self.date_from:
            domain.append(('date_start', '>=', str(self.date_from)))
        if self.date_to:
            domain.append(('date_start', '<=', str(self.date_to) + ' 23:59:59'))

        interventions = self.env['it.intervention'].search(domain, order='date_start')
        type_map = {'corrective': 'Corrective', 'preventive': 'Préventive'}

        for row_idx, inter in enumerate(interventions, start=1):
            ws.write(row_idx, 0, inter.equipment_id.name or '', cell_fmt)
            ws.write(row_idx, 1, inter.equipment_id.reference or '', cell_fmt)
            ws.write(row_idx, 2, inter.equipment_id.category_id.name or '', cell_fmt)
            ws.write(row_idx, 3, inter.name or '', cell_fmt)
            ws.write(row_idx, 4, type_map.get(inter.intervention_type, ''), cell_fmt)
            ws.write(row_idx, 5, inter.technician_id.name or '', cell_fmt)
            if inter.date_start:
                ws.write_datetime(row_idx, 6, inter.date_start, dt_fmt)
            else:
                ws.write(row_idx, 6, '', cell_fmt)
            ws.write(row_idx, 7, round(inter.duration, 2), cell_fmt)
            ws.write(row_idx, 8, inter.cost or 0, money_fmt)
            if inter.date_start:
                ws.write_datetime(row_idx, 9, inter.date_start, month_fmt)
            else:
                ws.write(row_idx, 9, '', cell_fmt)

        total_row = len(interventions) + 2
        total_fmt = wb.add_format({'bold': True, 'bg_color': '#F1F8E9', 'border': 1})
        ws.write(total_row, 7, f'TOTAL ({len(interventions)} interventions)', total_fmt)
        ws.write(total_row, 8, sum(interventions.mapped('cost')), money_fmt)

        wb.close()
        output.seek(0)
        return self._create_download_action(
            base64.b64encode(output.read()),
            'couts_maintenance.xlsx'
        )

    # ── Export 3 : Contrats expirant dans 60 jours ───────────────────────────
    def _export_expiring_contracts(self):
        output = io.BytesIO()
        wb = xlsxwriter.Workbook(output, {'in_memory': True})
        ws = wb.add_worksheet('Contrats expirants')

        header_fmt = wb.add_format({
            'bold': True, 'bg_color': '#BF360C', 'font_color': 'white',
            'border': 1, 'align': 'center',
        })
        cell_fmt = wb.add_format({'border': 1})
        money_fmt = wb.add_format({'border': 1, 'num_format': '#,##0', 'align': 'right'})
        date_fmt = wb.add_format({'border': 1, 'num_format': 'dd/mm/yyyy'})
        # Mise en couleur conditionnelle selon urgence
        expired_fmt = wb.add_format({
            'border': 1, 'bg_color': '#FFCDD2', 'font_color': '#B71C1C', 'bold': True,
        })
        urgent_fmt = wb.add_format({
            'border': 1, 'bg_color': '#FFE0B2', 'font_color': '#E65100',
        })
        soon_fmt = wb.add_format({
            'border': 1, 'bg_color': '#FFFDE7', 'font_color': '#F57F17',
        })

        headers = [
            'Référence', 'Intitulé', 'Type', 'Fournisseur',
            'Date début', 'Date expiration', 'Jours restants',
            'Montant (FCFA)', 'Statut', 'Équipements couverts',
        ]
        widths = [14, 30, 14, 22, 14, 16, 14, 18, 16, 35]

        for col, (h, w) in enumerate(zip(headers, widths)):
            ws.write(0, col, h, header_fmt)
            ws.set_column(col, col, w)

        contracts = self.env['it.contract'].search(
            [('days_left', '<=', 60), ('days_left', '>=', -30)],
            order='days_left asc'
        )
        type_map = {
            'maintenance': 'Maintenance', 'license': 'Licence',
            'support': 'Support', 'other': 'Autre',
        }

        for row_idx, contract in enumerate(contracts, start=1):
            if contract.days_left < 0:
                days_fmt = expired_fmt
            elif contract.days_left <= 15:
                days_fmt = urgent_fmt
            elif contract.days_left <= 30:
                days_fmt = urgent_fmt
            else:
                days_fmt = soon_fmt

            eq_names = ', '.join(contract.equipment_ids.mapped('name'))

            ws.write(row_idx, 0, contract.reference or '', cell_fmt)
            ws.write(row_idx, 1, contract.name or '', cell_fmt)
            ws.write(row_idx, 2, type_map.get(contract.contract_type, ''), cell_fmt)
            ws.write(row_idx, 3, contract.supplier_id.name or '', cell_fmt)
            if contract.date_start:
                ws.write_datetime(row_idx, 4, _date_to_datetime(contract.date_start), date_fmt)
            else:
                ws.write(row_idx, 4, '', cell_fmt)
            if contract.date_end:
                ws.write_datetime(row_idx, 5, _date_to_datetime(contract.date_end), date_fmt)
            else:
                ws.write(row_idx, 5, '', cell_fmt)
            ws.write(row_idx, 6, contract.days_left, days_fmt)
            ws.write(row_idx, 7, contract.amount or 0, money_fmt)
            ws.write(row_idx, 8, contract.state or '', cell_fmt)
            ws.write(row_idx, 9, eq_names, cell_fmt)

        wb.close()
        output.seek(0)
        return self._create_download_action(
            base64.b64encode(output.read()),
            'contrats_expirants.xlsx'
        )

    def _create_download_action(self, xlsx_b64, filename):
        """Crée une pièce jointe et retourne une action de téléchargement."""
        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'datas': xlsx_b64,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }
