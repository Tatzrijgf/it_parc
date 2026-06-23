/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, onWillStart, useRef, onMounted, onPatched } from "@odoo/owl";

/**
 * Composant OWL - Dashboard IT Parc - TECHPARK CI
 * KPIs + graphiques SVG natifs via contrôleur JSON-RPC
 */
class ItParcDashboard extends Component {
    static template = "it_parc.Dashboard";

    setup() {
        this.rpc = useService("rpc");
        this.action = useService("action");
        this.notification = useService("notification");

        this.state = useState({
            loading: true,
            kpis: {},
            charts: { by_category: [], monthly_costs: [] },
            top_equipments: [],
            error: null,
            chartsReady: false,
        });

        this.pieChartRef = useRef("pieChart");
        this.barChartRef = useRef("barChart");

        // Chargement initial des données avant le rendu
        onWillStart(async () => {
            await this._loadData();
        });

        // Premier rendu : tracer les graphiques une fois le DOM disponible
        onMounted(() => {
            if (!this.state.loading && !this.state.error) {
                this._renderCharts();
            }
        });

        // Re-tracer si les données ont changé après un refresh
        onPatched(() => {
            if (this.state.chartsReady) {
                this.state.chartsReady = false;  // reset avant render pour éviter boucle
                this._renderCharts();
            }
        });
    }

    // ── Chargement des données via JSON-RPC ─────────────────────────────────
    async _loadData() {
        try {
            const data = await this.rpc("/it_parc/dashboard_data", {});
            this.state.kpis = data.kpis || {};
            this.state.charts = data.charts || { by_category: [], monthly_costs: [] };
            this.state.top_equipments = data.top_equipments || [];
            this.state.loading = false;
            this.state.chartsReady = true;
        } catch (error) {
            this.state.error = "Impossible de charger les données du tableau de bord.";
            this.state.loading = false;
            console.error("Dashboard IT Parc - Erreur chargement:", error);
        }
    }

    // ── Rendu des graphiques SVG natifs ─────────────────────────────────────
    _renderCharts() {
        this._renderPieChart();
        this._renderBarChart();
    }

    /**
     * Graphique camembert SVG - Répartition par catégorie d'équipements
     */
    _renderPieChart() {
        const el = this.pieChartRef.el;
        if (!el) return;

        const data = this.state.charts.by_category;
        if (!data || data.length === 0) {
            el.innerHTML = `<text x="50%" y="50%" text-anchor="middle"
                fill="#aaa" font-size="12">Aucune donnée disponible</text>`;
            return;
        }

        const total = data.reduce((s, d) => s + d.value, 0);
        if (total === 0) return;

        const cx = 110, cy = 105, r = 85;
        const colors = [
            "#1F4E79", "#2E86AB", "#A23B72", "#F18F01", "#C73E1D",
            "#3B1F2B", "#44BBA4", "#E94F37", "#393E41", "#F5A623",
        ];

        let paths = "";
        let legend = "";
        let startAngle = -Math.PI / 2;

        data.forEach((item, i) => {
            const slice = (item.value / total) * 2 * Math.PI;
            const endAngle = startAngle + slice;
            const x1 = cx + r * Math.cos(startAngle);
            const y1 = cy + r * Math.sin(startAngle);
            const x2 = cx + r * Math.cos(endAngle);
            const y2 = cy + r * Math.sin(endAngle);
            const largeArc = slice > Math.PI ? 1 : 0;
            const pct = Math.round((item.value / total) * 100);
            const color = colors[i % colors.length];

            paths += `<path d="M${cx},${cy} L${x1.toFixed(2)},${y1.toFixed(2)} A${r},${r} 0 ${largeArc},1 ${x2.toFixed(2)},${y2.toFixed(2)} Z"
                           fill="${color}" opacity="0.9" stroke="white" stroke-width="2">
                        <title>${item.label}: ${item.value} équipement(s) (${pct}%)</title>
                      </path>`;

            if (pct >= 7) {
                const midAngle = startAngle + slice / 2;
                const lx = cx + (r * 0.62) * Math.cos(midAngle);
                const ly = cy + (r * 0.62) * Math.sin(midAngle);
                paths += `<text x="${lx.toFixed(2)}" y="${ly.toFixed(2)}"
                               text-anchor="middle" dominant-baseline="middle"
                               fill="white" font-size="11" font-weight="bold">${pct}%</text>`;
            }

            const ly = 18 + i * 22;
            const label = item.label.length > 22 ? item.label.substring(0, 22) + "…" : item.label;
            legend += `<rect x="240" y="${ly - 9}" width="13" height="13" fill="${color}" rx="2"/>
                       <text x="258" y="${ly}" font-size="11" fill="#333" dominant-baseline="middle">
                         ${label} (${item.value})
                       </text>`;

            startAngle = endAngle;
        });

        el.innerHTML = paths + legend;
    }

    /**
     * Graphique barres SVG - Coûts de maintenance 6 derniers mois
     */
    _renderBarChart() {
        const el = this.barChartRef.el;
        if (!el) return;

        const data = this.state.charts.monthly_costs;
        if (!data || data.length === 0) {
            el.innerHTML = `<text x="50%" y="50%" text-anchor="middle"
                fill="#aaa" font-size="12">Aucune donnée disponible</text>`;
            return;
        }

        const W = 500, H = 190;
        const pl = 68, pb = 38, pt = 12;
        const chartW = W - pl - 10;
        const chartH = H - pb - pt;
        const maxVal = Math.max(...data.map(d => d.value), 1);
        const barW = (chartW / data.length) * 0.55;
        const step = chartW / data.length;

        let svg = "";

        // Grille horizontale (5 niveaux)
        for (let i = 0; i <= 4; i++) {
            const y = pt + chartH - (i / 4) * chartH;
            const val = (maxVal * i) / 4;
            svg += `<line x1="${pl}" y1="${y.toFixed(1)}" x2="${W - 5}" y2="${y.toFixed(1)}"
                          stroke="#e8e8e8" stroke-width="1" stroke-dasharray="4,3"/>`;
            svg += `<text x="${pl - 4}" y="${y.toFixed(1)}" text-anchor="end"
                          dominant-baseline="middle" font-size="9" fill="#888">
                      ${this._formatAmount(Math.round(val))}
                    </text>`;
        }

        // Barres
        data.forEach((item, i) => {
            const barH = maxVal > 0 ? (item.value / maxVal) * chartH : 0;
            const x = pl + i * step + (step - barW) / 2;
            const y = pt + chartH - barH;
            const color = item.value > 0 ? "#1F4E79" : "#d0d0d0";
            const hoverColor = item.value > 0 ? "#2E86AB" : "#d0d0d0";

            svg += `<rect x="${x.toFixed(2)}" y="${y.toFixed(2)}"
                         width="${barW.toFixed(2)}" height="${Math.max(barH, 1).toFixed(2)}"
                         fill="${color}" rx="3" opacity="0.85"
                         onmouseover="this.setAttribute('fill','${hoverColor}')"
                         onmouseout="this.setAttribute('fill','${color}')">
                      <title>${item.label}: ${item.value.toLocaleString("fr-FR")} FCFA (${item.count} intervention(s))</title>
                    </rect>`;

            if (item.value > 0) {
                svg += `<text x="${(x + barW / 2).toFixed(2)}" y="${(y - 4).toFixed(2)}"
                              text-anchor="middle" font-size="9" fill="#444" font-weight="bold">
                          ${this._formatAmount(item.value)}
                        </text>`;
            }

            svg += `<text x="${(x + barW / 2).toFixed(2)}" y="${H - pb + 14}"
                          text-anchor="middle" font-size="9" fill="#666">
                      ${item.label}
                    </text>`;
        });

        // Axes
        svg += `<line x1="${pl}" y1="${pt}" x2="${pl}" y2="${pt + chartH}"
                      stroke="#bbb" stroke-width="1.5"/>`;
        svg += `<line x1="${pl}" y1="${pt + chartH}" x2="${W - 5}" y2="${pt + chartH}"
                      stroke="#bbb" stroke-width="1.5"/>`;

        el.innerHTML = svg;
    }

    _formatAmount(val) {
        if (val >= 1000000) return (val / 1000000).toFixed(1) + "M";
        if (val >= 1000) return (val / 1000).toFixed(0) + "K";
        return String(val);
    }

    // ── Rafraîchissement ────────────────────────────────────────────────────
    async onRefresh() {
        this.state.loading = true;
        this.state.error = null;
        await this._loadData();
        this.notification.add("Tableau de bord actualisé", {
            type: "success",
            sticky: false,
        });
    }

    // ── Navigations ────────────────────────────────────────────────────────
    openEquipments(state = null) {
        const domain = state ? [["state", "=", state]] : [];
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Équipements",
            res_model: "it.equipment",
            view_mode: "list,kanban,form",
            domain,
        });
    }

    openAlerts() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Alertes ouvertes",
            res_model: "it.alerte",
            view_mode: "list,form",
            domain: [["state", "=", "open"]],
        });
    }

    openExpiringContracts() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Contrats expirant bientôt",
            res_model: "it.contract",
            view_mode: "list,form",
            domain: [["days_left", "<=", 30], ["days_left", ">=", 0]],
        });
    }

    openInterventions() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Interventions",
            res_model: "it.intervention",
            view_mode: "list,calendar,form",
        });
    }
}

registry.category("actions").add("it_parc.Dashboard", ItParcDashboard);
