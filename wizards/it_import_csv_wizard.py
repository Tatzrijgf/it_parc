# -*- coding: utf-8 -*-
import base64
import csv
import io
from datetime import datetime
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ItImportCsvWizard(models.TransientModel):
    _name = 'it.import.csv.wizard'
    _description = 'Wizard d\'import CSV d\'équipements'

    csv_file = fields.Binary(
        string='Fichier CSV', required=True,
        help="Format attendu : name,serial_number,category,brand,model,purchase_date,purchase_price,warranty_date,location"
    )
    csv_filename = fields.Char(string='Nom du fichier')
    delimiter = fields.Selection([
        (',', 'Virgule (,)'),
        (';', 'Point-virgule (;)'),
        ('\t', 'Tabulation'),
    ], string='Séparateur', default=';', required=True)

    # Résultats
    state = fields.Selection([
        ('draft', 'Prêt'),
        ('done', 'Résultats'),
    ], default='draft')
    result_created = fields.Integer(string='Lignes créées', readonly=True)
    result_ignored = fields.Integer(string='Lignes ignorées (doublons)', readonly=True)
    result_errors = fields.Integer(string='Lignes en erreur', readonly=True)
    result_details = fields.Text(string='Détails', readonly=True)

    def action_import(self):
        self.ensure_one()
        if not self.csv_file:
            raise UserError(_("Veuillez sélectionner un fichier CSV."))

        try:
            file_content = base64.b64decode(self.csv_file).decode('utf-8-sig')
        except Exception:
            raise UserError(_("Impossible de lire le fichier. Vérifiez l'encodage (UTF-8)."))

        reader = csv.DictReader(
            io.StringIO(file_content),
            delimiter=self.delimiter
        )

        created = 0
        ignored = 0
        errors = 0
        details = []

        # Colonnes obligatoires
        required_cols = ['name', 'serial_number']

        for i, row in enumerate(reader, start=2):  # ligne 2 = première data
            # Nettoyer les clés (espaces)
            row = {k.strip(): v.strip() for k, v in row.items() if k}

            # Vérifier colonnes obligatoires
            missing = [c for c in required_cols if not row.get(c)]
            if missing:
                errors += 1
                details.append(
                    _("Ligne %d : colonnes manquantes %s") % (i, ', '.join(missing))
                )
                continue

            # Détecter les doublons par numéro de série
            serial = row.get('serial_number', '').strip()
            if serial:
                existing = self.env['it.equipment'].search(
                    [('serial_number', '=', serial)], limit=1
                )
                if existing:
                    ignored += 1
                    details.append(
                        _("Ligne %d : doublon ignoré (n° série '%s' déjà existant - %s)") % (
                            i, serial, existing.name
                        )
                    )
                    continue

            # Construire les valeurs
            vals = {
                'name': row.get('name', ''),
                'serial_number': serial,
                'brand': row.get('brand', ''),
                'model': row.get('model', ''),
                'location': row.get('location', ''),
            }

            # Catégorie : trouver ou créer
            category_name = row.get('category', '').strip()
            if category_name:
                category = self.env['it.equipment.category'].search(
                    [('name', 'ilike', category_name)], limit=1
                )
                if not category:
                    category = self.env['it.equipment.category'].create(
                        {'name': category_name}
                    )
                vals['category_id'] = category.id

            # Prix d'achat
            price_str = row.get('purchase_price', '').replace(' ', '').replace(',', '.')
            if price_str:
                try:
                    vals['purchase_price'] = float(price_str)
                except ValueError:
                    pass

            # Dates
            for date_field, col in [('purchase_date', 'purchase_date'), ('warranty_date', 'warranty_date')]:
                date_str = row.get(col, '').strip()
                if date_str:
                    for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y'):
                        try:
                            vals[date_field] = datetime.strptime(date_str, fmt).date()
                            break
                        except ValueError:
                            continue

            try:
                self.env['it.equipment'].create(vals)
                created += 1
                details.append(_("Ligne %d : '%s' créé avec succès.") % (i, vals['name']))
            except Exception as e:
                errors += 1
                details.append(_("Ligne %d : erreur création - %s") % (i, str(e)))

        self.write({
            'state': 'done',
            'result_created': created,
            'result_ignored': ignored,
            'result_errors': errors,
            'result_details': '\n'.join(details),
        })

        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_download_template(self):
        """Télécharger un modèle CSV vide."""
        template = "name;serial_number;category;brand;model;purchase_date;purchase_price;warranty_date;location\n"
        template += "PC-Bureau-01;SN123456;Poste de travail;Dell;OptiPlex 7090;2023-01-15;850000;2026-01-15;Abidjan-Cocody\n"

        attachment = self.env['ir.attachment'].create({
            'name': 'template_import_equipements.csv',
            'type': 'binary',
            'datas': base64.b64encode(template.encode('utf-8')),
            'mimetype': 'text/csv',
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }
