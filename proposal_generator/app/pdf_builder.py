"""Generate a formal multi-page proposal PDF with a cover page, tables, and charts."""

import os
import time
import re
from uuid import uuid4

from fpdf import FPDF

import matplotlib
matplotlib.use("Agg")  # non-interactive backend — must be before pyplot import
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import matplotlib.patches as mpatches


# ====================================================================== #
#                          CHART BUILDERS                                 #
# ====================================================================== #

def _chart_cost_pie(cost: dict, output_dir: str) -> str:
    """Vibrant donut chart for cost distribution."""
    labels, sizes = [], []
    for key, label in [
        ("development_cost", "Development"),
        ("infrastructure_cost", "Infrastructure"),
        ("contingency", "Contingency"),
    ]:
        val = cost.get(key, 0)
        if val > 0:
            labels.append(label)
            sizes.append(val)
    if cost.get("discount", 0) > 0:
        labels.append("Discount")
        sizes.append(cost["discount"])
    if not sizes:
        return ""

    COLORS = ["#1e40af", "#2563eb", "#60a5fa", "#93c5fd"]
    fig, ax = plt.subplots(figsize=(3.6, 3.2))
    wedges, texts, autotexts = ax.pie(
        sizes, labels=None, autopct="%1.1f%%",
        colors=COLORS[: len(sizes)], startangle=140,
        wedgeprops={"width": 0.65, "edgecolor": "white", "linewidth": 2},
        pctdistance=0.75,
    )
    for at in autotexts:
        at.set_fontsize(8)
        at.set_color("white")
        at.set_fontweight("bold")

    patches = [mpatches.Patch(color=COLORS[i], label=labels[i]) for i in range(len(labels))]
    ax.legend(handles=patches, loc="lower center", bbox_to_anchor=(0.5, -0.14),
              ncol=2, fontsize=7, frameon=False)
    ax.set_title("Cost Distribution", fontsize=9.5, fontweight="bold", color="#1e3a5f", pad=6)
    fig.tight_layout()

    path = os.path.join(output_dir, f"_chart_pie_{uuid4().hex[:6]}.png")
    fig.savefig(path, dpi=160, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path


def _chart_timeline_bar(timeline_phases: list, output_dir: str) -> str:
    """Gantt-style horizontal bar chart for the timeline."""
    if not timeline_phases:
        return ""
    phases = [p.get("phase", f"Phase {i+1}") for i, p in enumerate(timeline_phases)]
    weeks = [p.get("weeks", 0) for p in timeline_phases]
    if not any(w > 0 for w in weeks):
        return ""

    starts = []
    acc = 0
    for w in weeks:
        starts.append(acc)
        acc += w

    COLS = ["#1e40af", "#1d4ed8", "#2563eb", "#3b82f6", "#60a5fa", "#93c5fd"]
    bar_colors = [COLS[i % len(COLS)] for i in range(len(phases))]

    fig_h = max(2.2, len(phases) * 0.52 + 0.6)
    fig, ax = plt.subplots(figsize=(5.5, fig_h))

    bars = ax.barh(phases, weeks, left=starts, color=bar_colors,
                   height=0.55, edgecolor="white", linewidth=1.2)
    for bar, w, s in zip(bars, weeks, starts):
        if w > 0:
            ax.text(s + w / 2, bar.get_y() + bar.get_height() / 2,
                    f"{w}w", ha="center", va="center",
                    fontsize=7.5, color="white", fontweight="bold")

    ax.set_xlabel("Weeks", fontsize=8, color="#374151")
    ax.set_title("Project Timeline (Gantt)", fontsize=9, fontweight="bold", color="#1e3a5f")
    ax.invert_yaxis()
    ax.tick_params(axis="y", labelsize=7.5)
    ax.tick_params(axis="x", labelsize=7.5)
    ax.xaxis.set_major_locator(mticker.MaxNLocator(integer=True))
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.set_facecolor("#f8fafc")
    fig.patch.set_facecolor("white")
    fig.tight_layout()

    path = os.path.join(output_dir, f"_chart_timeline_{uuid4().hex[:6]}.png")
    fig.savefig(path, dpi=160, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path


def _chart_team_bar(team: list, output_dir: str) -> str:
    """Horizontal bar chart for team composition headcount."""
    if not team:
        return ""
    roles = [t.get("role", "Unknown") for t in team]
    counts = [int(str(t.get("count", 1)).split("-")[0]) for t in team]  # handle "2-3" ranges
    if not any(c > 0 for c in counts):
        return ""

    COLS = plt.cm.get_cmap("Blues")(
        [0.4 + 0.55 * i / max(len(roles) - 1, 1) for i in range(len(roles))]
    )

    fig_h = max(1.8, len(roles) * 0.48 + 0.5)
    fig, ax = plt.subplots(figsize=(3.6, fig_h))
    bars = ax.barh(roles, counts, color=COLS, height=0.55, edgecolor="white", linewidth=1.0)
    for bar, c in zip(bars, counts):
        ax.text(bar.get_width() + 0.05, bar.get_y() + bar.get_height() / 2,
                str(c), va="center", ha="left", fontsize=7.5, color="#1e3a5f", fontweight="bold")

    ax.set_xlabel("Headcount", fontsize=8, color="#374151")
    ax.set_title("Team Composition", fontsize=9, fontweight="bold", color="#1e3a5f")
    ax.invert_yaxis()
    ax.tick_params(axis="y", labelsize=7.5)
    ax.tick_params(axis="x", labelsize=7.5)
    ax.xaxis.set_major_locator(mticker.MaxNLocator(integer=True))
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.set_facecolor("#f8fafc")
    fig.patch.set_facecolor("white")
    fig.tight_layout()

    path = os.path.join(output_dir, f"_chart_team_{uuid4().hex[:6]}.png")
    fig.savefig(path, dpi=160, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path


def _chart_risk_matrix(risks: list, output_dir: str) -> str:
    """Bubble scatter chart mapping risks by probability vs impact severity."""
    if not risks:
        return ""

    LEVEL = {"High": 3, "Medium": 2, "Low": 1}
    COLOR = {"High": "#ef4444", "Medium": "#f59e0b", "Low": "#22c55e"}

    xs, ys, sizes_plot, colors_plot, labels = [], [], [], [], []
    for r in risks:
        impact = r.get("impact", "Medium")
        prob = r.get("probability", "Medium")
        xs.append(LEVEL.get(prob, 2))
        ys.append(LEVEL.get(impact, 2))
        sizes_plot.append(500)
        colors_plot.append(COLOR.get(impact, "#6366f1"))
        lbl = r.get("risk", "")
        labels.append(lbl[:28] + "…" if len(lbl) > 28 else lbl)

    fig, ax = plt.subplots(figsize=(5.0, 3.2))
    ax.scatter(xs, ys, s=sizes_plot, c=colors_plot, alpha=0.7, edgecolors="white", linewidths=1.5, zorder=5)

    for i, (x, y, lbl) in enumerate(zip(xs, ys, labels)):
        ax.annotate(lbl, (x, y), textcoords="offset points", xytext=(6, 4),
                    fontsize=6.5, color="#1f2937", zorder=6)

    ax.set_xlim(0.5, 3.5)
    ax.set_ylim(0.5, 3.5)
    ax.set_xticks([1, 2, 3]); ax.set_xticklabels(["Low", "Medium", "High"], fontsize=8)
    ax.set_yticks([1, 2, 3]); ax.set_yticklabels(["Low", "Medium", "High"], fontsize=8)
    ax.set_xlabel("Probability", fontsize=8.5, color="#374151")
    ax.set_ylabel("Impact", fontsize=8.5, color="#374151")
    ax.set_title("Risk Matrix", fontsize=10, fontweight="bold", color="#1e3a5f")
    ax.set_facecolor("#f8fafc")
    fig.patch.set_facecolor("white")

    # Background quadrant shading
    ax.axhspan(2.5, 3.5, alpha=0.08, color="#ef4444")
    ax.axhspan(0.5, 1.5, alpha=0.08, color="#22c55e")

    legend_patches = [
        mpatches.Patch(color="#ef4444", label="High impact"),
        mpatches.Patch(color="#f59e0b", label="Medium impact"),
        mpatches.Patch(color="#22c55e", label="Low impact"),
    ]
    ax.legend(handles=legend_patches, fontsize=7, loc="lower right", frameon=True, framealpha=0.85)

    fig.tight_layout()
    path = os.path.join(output_dir, f"_chart_risk_{uuid4().hex[:6]}.png")
    fig.savefig(path, dpi=160, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path


# ====================================================================== #
#                          PDF CLASS                                      #
# ====================================================================== #

class ProposalPDF(FPDF):
    """Custom FPDF2 subclass with professional cover page, header, footer, tables, and charts."""

    NAVY    = (20, 58, 95)
    ACCENT  = (37, 99, 235)
    LIGHT   = (96, 165, 250)
    TEAL    = (5, 150, 105)
    TTEXT   = (30, 30, 30)
    TMID    = (80, 80, 80)
    TLIGHT  = (140, 140, 140)
    BGLIGHT = (245, 248, 252)
    WHITE   = (255, 255, 255)

    def __init__(self, project_title: str):
        super().__init__()
        self.project_title = project_title
        self.set_auto_page_break(auto=True, margin=28)

    # ── Safety ────────────────────────────────────────────────────────────
    # Common non-latin-1 Unicode chars pre-mapped to ASCII equivalents
    _UNICODE_MAP = str.maketrans({
        '\u2014': '-',    # em dash
        '\u2013': '-',    # en dash
        '\u2012': '-',    # figure dash
        '\u2011': '-',    # non-breaking hyphen
        '\u2019': "'",    # right single quote
        '\u2018': "'",    # left single quote
        '\u201c': '"',    # left double quote
        '\u201d': '"',    # right double quote
        '\u2026': '...',  # ellipsis
        '\u20b9': 'Rs.',  # Indian Rupee sign
        '\u00a0': ' ',    # non-breaking space
        '\u2022': '-',    # bullet point
        '\u2192': '->',   # right arrow
        '\u00e2': 'a',    # a with circumflex (common mojibake artifact)
    })

    @staticmethod
    def _safe(text: str) -> str:
        """Sanitise string for FPDF latin-1 output — maps common Unicode to ASCII first."""
        text = str(text).translate(ProposalPDF._UNICODE_MAP)
        text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
        return text.encode("latin-1", errors="replace").decode("latin-1")

    # ── Header / Footer (skipped on cover) ────────────────────────────────
    def header(self):
        if self.page_no() == 1:
            return  # cover page has its own design
        self.set_fill_color(*self.NAVY)
        self.rect(0, 0, 210, 8, "F")
        self.set_y(10)
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(*self.NAVY)
        self.cell(0, 6, self._safe(self.project_title), align="C", new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(*self.LIGHT)
        self.set_line_width(0.3)
        self.line(15, self.get_y() + 0.5, 195, self.get_y() + 0.5)
        self.ln(4)

    def footer(self):
        if self.page_no() == 1:
            return
        self.set_y(-18)
        self.set_draw_color(210, 210, 210)
        self.set_line_width(0.2)
        self.line(15, self.get_y(), 195, self.get_y())
        self.ln(2)
        self.set_font("Helvetica", "I", 7.5)
        self.set_text_color(*self.TLIGHT)
        self.cell(0, 5, self._safe(f"Page {self.page_no()}/{{nb}}  |  Confidential"), align="C")

    # ── Cover Page ─────────────────────────────────────────────────────────
    def cover_page(self, proposal_data: dict):
        """Full-bleed cover page with branding and key metadata."""
        self.add_page()

        # Deep navy background (full page)
        self.set_fill_color(*self.NAVY)
        self.rect(0, 0, 210, 297, "F")

        # Accent stripe
        self.set_fill_color(*self.ACCENT)
        self.rect(0, 115, 210, 6, "F")

        # LOGO / TITLE AREA
        self.set_xy(20, 45)
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(96, 165, 250)
        self.cell(0, 7, "CONSULTING PROPOSAL", new_x="LMARGIN", new_y="NEXT")

        self.set_x(20)
        self.set_font("Helvetica", "B", 26)
        self.set_text_color(*self.WHITE)
        self.multi_cell(170, 14, self._safe(proposal_data.get("project_title", "Project Proposal")))

        # Client name
        client = proposal_data.get("client_name", "")
        if client:
            self.set_x(20)
            self.set_font("Helvetica", "", 14)
            self.set_text_color(147, 197, 253)
            self.cell(0, 9, f"Prepared for: {self._safe(client)}", new_x="LMARGIN", new_y="NEXT")

        # Meta info block
        from datetime import date
        meta_y = 140
        meta = [
            ("Industry",    proposal_data.get("industry", "")),
            ("Duration",    f"{proposal_data.get('duration_months', '')} months"),
            ("Users",       f"{int(proposal_data.get('expected_users', 0)):,}+"),
            ("Tech Stack",  ", ".join(proposal_data.get("tech_stack", [])[:4])),
            ("Date",        date.today().strftime("%B %d, %Y")),
        ]
        self.set_font("Helvetica", "", 10)
        for label, value in meta:
            self.set_xy(25, meta_y)
            self.set_text_color(147, 197, 253)
            self.cell(38, 8, self._safe(label + ":"))
            self.set_text_color(*self.WHITE)
            self.cell(130, 8, self._safe(str(value)))
            meta_y += 12

        # Branding footer on cover
        self.set_xy(0, 265)
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(96, 165, 250)
        self.cell(210, 8, self._safe("ProposalStudio  —  Confidential & Proprietary"), align="C")

    # ── Section heading ────────────────────────────────────────────────────
    def section_heading(self, title: str):
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(*self.NAVY)
        self.cell(0, 7, self._safe(title), new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(*self.ACCENT)
        self.set_line_width(0.6)
        self.line(15, self.get_y(), 75, self.get_y())
        self.ln(2.5)

    # ── Body text ──────────────────────────────────────────────────────────
    def body_text(self, text: str):
        self.set_font("Helvetica", "", 9)
        self.set_text_color(*self.TTEXT)
        self.multi_cell(0, 4.8, self._safe(str(text)))
        self.ln(2)

    # ── Table helpers ──────────────────────────────────────────────────────
    def _lines_needed(self, text: str, col_width: float) -> int:
        eff = col_width - 3
        if eff <= 0:
            return 1
        w = self.get_string_width(self._safe(str(text)))
        return max(1, int(w / eff) + 1)

    def _draw_wrapped_row(self, row: list, col_widths: list, line_h: float = 4.5):
        self.set_font("Helvetica", "", 8.5)
        max_lines = max(self._lines_needed(str(v), col_widths[i]) for i, v in enumerate(row))
        row_height = max(6.5, max_lines * line_h + 2)

        if self.get_y() + row_height > self.h - self.b_margin:
            self.add_page()

        x0 = self.get_x()
        y0 = self.get_y()

        for i in range(len(row)):
            self.rect(x0 + sum(col_widths[:i]), y0, col_widths[i], row_height, "DF")

        self.set_text_color(*self.TTEXT)
        for i, val in enumerate(row):
            self.set_xy(x0 + sum(col_widths[:i]) + 1.5, y0 + 1.5)
            self.multi_cell(col_widths[i] - 3, line_h, self._safe(str(val)), align="L")

        self.set_xy(x0, y0 + row_height)

    def data_table(self, headers: list, rows: list, col_widths: list = None):
        if col_widths is None:
            col_widths = [180 / len(headers)] * len(headers)
        row_h = 6

        self.set_font("Helvetica", "B", 8)
        self.set_fill_color(*self.NAVY)
        self.set_text_color(*self.WHITE)
        self.set_draw_color(*self.NAVY)
        for i, h in enumerate(headers):
            self.cell(col_widths[i], row_h, self._safe(h), border=1, fill=True, align="C")
        self.ln(row_h)

        self.set_draw_color(180, 180, 180)
        alt = False
        for row in rows:
            self.set_fill_color(*(self.BGLIGHT if alt else self.WHITE))
            self._draw_wrapped_row(row, col_widths)
            alt = not alt
        self.ln(2)

    def cost_table(self, cost: dict):
        currency = cost.get("currency", "INR")
        symbol = "Rs." if currency == "INR" else "$"
        headers = ["Cost Item", f"Amount ({currency})"]
        col_widths = [100, 80]
        row_h = 8

        row_h = 6.5
        items = [
            ("Development Cost",   cost.get("development_cost", 0)),
            ("Infrastructure Cost", cost.get("infrastructure_cost", 0)),
            ("Contingency (10%)",  cost.get("contingency", 0)),
        ]
        if cost.get("discount", 0) > 0:
            items.append(("Discount Applied", -cost["discount"]))

        self.set_font("Helvetica", "B", 8)
        self.set_fill_color(*self.NAVY)
        self.set_text_color(*self.WHITE)
        self.set_draw_color(*self.NAVY)
        for i, h in enumerate(headers):
            self.cell(col_widths[i], row_h, h, border=1, fill=True, align="C")
        self.ln(row_h)

        self.set_draw_color(180, 180, 180)
        alt = False
        for label, amount in items:
            self.set_fill_color(*(self.BGLIGHT if alt else self.WHITE))
            self.set_font("Helvetica", "", 8)
            self.set_text_color(*self.TTEXT)
            self.cell(col_widths[0], row_h, label, border=1, fill=True)
            self.cell(col_widths[1], row_h, f"{symbol} {abs(amount):,.2f}", border=1, fill=True, align="R")
            self.ln(row_h)
            alt = not alt

        # Total
        self.set_font("Helvetica", "B", 9.5)
        self.set_fill_color(220, 233, 250)
        self.set_text_color(*self.NAVY)
        self.cell(col_widths[0], row_h, "TOTAL ESTIMATED COST", border=1, fill=True)
        self.cell(col_widths[1], row_h,
                  f"{symbol} {cost.get('total_estimated_cost', 0):,.2f}",
                  border=1, fill=True, align="R")
        self.ln(row_h)

        monthly = cost.get("monthly_average", 0)
        if monthly > 0:
            self.set_font("Helvetica", "I", 7.5)
            self.set_text_color(*self.TMID)
            self.cell(0, 5, f"Monthly average: {symbol} {monthly:,.2f}", new_x="LMARGIN", new_y="NEXT")
        self.ln(2)


# ====================================================================== #
#                     MAIN BUILD FUNCTION                                 #
# ====================================================================== #

def build_proposal_pdf(proposal_data: dict) -> str:
    """Build and return the absolute path of the generated PDF."""
    title = proposal_data.get("project_title", "Project Proposal")
    output_dir = os.path.join(os.getcwd(), "outputs")
    os.makedirs(output_dir, exist_ok=True)

    # ── Pre-generate chart images ──────────────────────────────────────── #
    cost = proposal_data.get("estimated_cost", {})
    pie_path      = _chart_cost_pie(cost, output_dir) if isinstance(cost, dict) else ""

    timeline_data = proposal_data.get("timeline", [])
    tl_bar_path   = ""
    if isinstance(timeline_data, list) and timeline_data:
        tl_bar_path = _chart_timeline_bar(timeline_data, output_dir)

    team = proposal_data.get("team_composition", [])
    team_bar_path = _chart_team_bar(team, output_dir) if team else ""

    risk_data = proposal_data.get("risk_assessment", [])
    risk_matrix_path = _chart_risk_matrix(risk_data if isinstance(risk_data, list) else [], output_dir)

    # ── Build PDF ─────────────────────────────────────────────────────── #
    pdf = ProposalPDF(project_title=title)
    pdf.alias_nb_pages()

    # ─────────── COVER PAGE ─────────────────────────────────────────────
    pdf.cover_page(proposal_data)

    # ─────────── PAGE 2: Overview + Summary + Approach ──────────────────
    pdf.add_page()

    pdf.section_heading("1. Project Overview")
    overview_rows = [
        ["Project Title",   title],
        ["Client",          proposal_data.get("client_name", "-") or "-"],
        ["Industry",        str(proposal_data.get("industry", ""))],
        ["Duration",        f"{proposal_data.get('duration_months', '')} months"],
        ["Expected Users",  f"{int(proposal_data.get('expected_users', 0)):,}"],
        ["Tech Stack",      ", ".join(proposal_data.get("tech_stack", []))],
    ]
    pdf.data_table(["Parameter", "Details"], overview_rows, col_widths=[55, 125])

    pdf.section_heading("2. Executive Summary")
    pdf.body_text(proposal_data.get("executive_summary", "N/A"))

    pdf.section_heading("3. Technical Approach")
    pdf.body_text(proposal_data.get("technical_approach", "N/A"))

    # ─────────── PAGE 3: Deliverables + Timeline ────────────────────────
    pdf.add_page()

    deliverables = proposal_data.get("deliverables", [])
    if deliverables:
        pdf.section_heading("4. Key Deliverables")
        if isinstance(deliverables, list):
            d_rows = [[f"{i + 1}.", str(d)] for i, d in enumerate(deliverables)]
            pdf.data_table(["#", "Deliverable"], d_rows, col_widths=[12, 168])
        else:
            pdf.body_text(str(deliverables))

    pdf.section_heading("5. Project Timeline")
    if isinstance(timeline_data, list) and timeline_data:
        tl_rows = [
            [str(p.get("phase", "")), f"{p.get('weeks', '')}w", str(p.get("description", ""))]
            for p in timeline_data
        ]
        pdf.data_table(["Phase", "Dur.", "Description"], tl_rows, col_widths=[45, 12, 123])

        if tl_bar_path and os.path.isfile(tl_bar_path):
            # Check if enough space remains
            if pdf.get_y() + 52 > pdf.h - pdf.b_margin:
                pdf.add_page()
            pdf.image(tl_bar_path, x=15, w=170)
            pdf.ln(3)
    else:
        pdf.body_text(str(timeline_data))

    # ─────────── PAGE 4: Cost + Team ────────────────────────────────────
    pdf.add_page()

    pdf.section_heading("6. Estimated Cost Breakdown")
    if isinstance(cost, dict):
        pdf.cost_table(cost)
    else:
        pdf.body_text(str(cost))

    if team:
        pdf.section_heading("7. Recommended Team Composition")
        t_rows = [
            [str(t.get("role", "")), str(t.get("count", "")), str(t.get("allocation", ""))]
            for t in team
        ]
        pdf.data_table(["Role", "Headcount", "Allocation"], t_rows, col_widths=[80, 35, 65])

    # Place cost pie + team bar side by side at bottom of page 4
    has_pie  = pie_path and os.path.isfile(pie_path)
    has_team = team_bar_path and os.path.isfile(team_bar_path)
    if has_pie or has_team:
        chart_h = 58
        if pdf.get_y() + chart_h > pdf.h - pdf.b_margin:
            pdf.add_page()
        y_charts = pdf.get_y()
        if has_pie and has_team:
            pdf.image(pie_path, x=15, y=y_charts, w=84)
            pdf.image(team_bar_path, x=110, y=y_charts, w=84)
        elif has_pie:
            pdf.image(pie_path, x=(210 - 84) / 2, y=y_charts, w=84)
        else:
            pdf.image(team_bar_path, x=15, y=y_charts, w=155)
        pdf.set_y(y_charts + chart_h)
        pdf.ln(3)

    # ─────────── PAGE 5: Risk Assessment ────────────────────────────────
    pdf.add_page()

    section_num = 8 if team else 7
    pdf.section_heading(f"{section_num}. Risk Assessment")
    if isinstance(risk_data, list) and risk_data:
        headers = ["Risk", "Impact", "Probability", "Mitigation"]
        widths  = [40, 18, 22, 100]
        risk_rows = []
        for r in risk_data:
            risk_rows.append([
                str(r.get("risk", "")),
                str(r.get("impact", "")),
                str(r.get("probability", "—")),
                str(r.get("mitigation", "")),
            ])
        pdf.data_table(headers, risk_rows, widths)

        if risk_matrix_path and os.path.isfile(risk_matrix_path):
            if pdf.get_y() + 58 > pdf.h - pdf.b_margin:
                pdf.add_page()
            x_c = (210 - 130) / 2
            pdf.image(risk_matrix_path, x=x_c, w=130)
            pdf.ln(3)
    else:
        pdf.body_text(str(risk_data))

    # ─────────── CONFIDENTIALITY NOTICE ─────────────────────────────────
    pdf.ln(8)
    pdf.set_font("Helvetica", "I", 7.5)
    pdf.set_text_color(160, 160, 160)
    pdf.multi_cell(
        0, 5,
        "This document is CONFIDENTIAL and intended solely for the named recipient(s). "
        "Unauthorised reproduction or distribution is strictly prohibited. "
        "Prepared on " + __import__("datetime").date.today().strftime("%B %d, %Y") + ".",
        align="C",
    )

    # ─────────── SAVE ────────────────────────────────────────────────────
    filename = f"proposal_{int(time.time())}_{uuid4().hex[:6]}.pdf"
    filepath = os.path.join(output_dir, filename)
    pdf.output(filepath)

    # Clean up chart temp files
    for p in [pie_path, tl_bar_path, team_bar_path, risk_matrix_path]:
        if p and os.path.isfile(p):
            try:
                os.remove(p)
            except OSError:
                pass

    return os.path.abspath(filepath)
