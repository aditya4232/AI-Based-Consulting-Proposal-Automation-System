"""Generate a formal multi-page proposal PDF with tables and charts."""

import os
import time
import tempfile
from uuid import uuid4

from fpdf import FPDF

# matplotlib is only imported inside chart helpers to keep startup fast.
import matplotlib
matplotlib.use("Agg")  # non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker


# ====================================================================== #
#                          CHART BUILDERS                                 #
# ====================================================================== #

def _chart_cost_pie(cost: dict, output_dir: str) -> str:
    """Create a cost-distribution pie chart and return the image path."""
    labels = []
    sizes = []

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

    colors = ["#14406E", "#2878C8", "#5BA0E0", "#A0C8F0"]
    fig, ax = plt.subplots(figsize=(3.8, 3.8))
    wedges, texts, autotexts = ax.pie(
        sizes,
        labels=labels,
        autopct="%1.1f%%",
        colors=colors[: len(sizes)],
        startangle=140,
        textprops={"fontsize": 8},
    )
    for t in autotexts:
        t.set_fontsize(7)
        t.set_color("white")
    ax.set_title("Cost Distribution", fontsize=10, fontweight="bold", color="#14406E")
    fig.tight_layout()

    path = os.path.join(output_dir, f"_chart_pie_{uuid4().hex[:6]}.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path


def _chart_timeline_bar(timeline_phases: list[dict], output_dir: str) -> str:
    """Create a horizontal bar chart showing timeline phases."""
    if not timeline_phases:
        return ""

    phases = [p.get("phase", f"Phase {i+1}") for i, p in enumerate(timeline_phases)]
    weeks = [p.get("weeks", 0) for p in timeline_phases]

    if not any(w > 0 for w in weeks):
        return ""

    # Compute start offsets for Gantt-style
    starts = []
    acc = 0
    for w in weeks:
        starts.append(acc)
        acc += w

    fig, ax = plt.subplots(figsize=(5.5, max(2.2, len(phases) * 0.55)))
    colors = ["#14406E", "#1E5A9E", "#2878C8", "#3C94DC", "#5BA0E0", "#80B8EC", "#A0C8F0"]
    bar_colors = [colors[i % len(colors)] for i in range(len(phases))]

    bars = ax.barh(phases, weeks, left=starts, color=bar_colors, height=0.5, edgecolor="white")

    # Add week labels on bars
    for bar, w, s in zip(bars, weeks, starts):
        if w > 0:
            ax.text(
                s + w / 2,
                bar.get_y() + bar.get_height() / 2,
                f"{w}w",
                ha="center",
                va="center",
                fontsize=7,
                color="white",
                fontweight="bold",
            )

    ax.set_xlabel("Weeks", fontsize=8, color="#333")
    ax.set_title("Project Timeline", fontsize=10, fontweight="bold", color="#14406E")
    ax.invert_yaxis()
    ax.tick_params(axis="y", labelsize=7)
    ax.tick_params(axis="x", labelsize=7)
    ax.xaxis.set_major_locator(mticker.MaxNLocator(integer=True))
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()

    path = os.path.join(output_dir, f"_chart_timeline_{uuid4().hex[:6]}.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path


# ====================================================================== #
#                          PDF CLASS                                      #
# ====================================================================== #

class ProposalPDF(FPDF):
    """Custom PDF with professional header, footer, tables, and chart support."""

    NAVY = (20, 60, 120)
    ACCENT = (40, 120, 200)
    TEXT_DARK = (40, 40, 40)
    TEXT_MID = (80, 80, 80)
    TEXT_LIGHT = (140, 140, 140)
    BG_LIGHT = (245, 248, 252)
    WHITE = (255, 255, 255)

    def __init__(self, project_title: str):
        super().__init__()
        self.project_title = project_title
        self.set_auto_page_break(auto=True, margin=25)

    # ----------------------------------------------------------------- #
    # Header / Footer
    # ----------------------------------------------------------------- #
    def header(self):
        self.set_fill_color(*self.NAVY)
        self.rect(0, 0, 210, 12, "F")
        self.set_y(16)
        self.set_font("Helvetica", "B", 18)
        self.set_text_color(*self.NAVY)
        self.cell(0, 10, self._safe(self.project_title), align="C", new_x="LMARGIN", new_y="NEXT")
        self.set_font("Helvetica", "I", 9)
        self.set_text_color(100, 100, 100)
        self.cell(0, 5, "Project Proposal Document", align="C", new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(*self.NAVY)
        self.set_line_width(0.4)
        self.line(15, self.get_y() + 2, 195, self.get_y() + 2)
        self.ln(8)

    def footer(self):
        self.set_y(-20)
        self.set_draw_color(200, 200, 200)
        self.set_line_width(0.2)
        self.line(15, self.get_y(), 195, self.get_y())
        self.ln(3)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(*self.TEXT_LIGHT)
        self.cell(0, 5, f"Page {self.page_no()}/{{nb}}", align="C")

    # ----------------------------------------------------------------- #
    # Helpers
    # ----------------------------------------------------------------- #
    @staticmethod
    def _safe(text: str) -> str:
        """Encode text to latin-1 safely."""
        return text.encode("latin-1", errors="replace").decode("latin-1")

    def section_heading(self, title: str):
        self.set_font("Helvetica", "B", 13)
        self.set_text_color(*self.NAVY)
        self.cell(0, 9, self._safe(title), new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(*self.ACCENT)
        self.set_line_width(0.6)
        self.line(15, self.get_y(), 85, self.get_y())
        self.ln(4)

    def body_text(self, text: str):
        self.set_font("Helvetica", "", 10)
        self.set_text_color(*self.TEXT_DARK)
        self.multi_cell(0, 6, self._safe(text))
        self.ln(3)

    # ----------------------------------------------------------------- #
    # Table: generic rows (with text wrapping)
    # ----------------------------------------------------------------- #
    def _lines_needed(self, text: str, col_width: float) -> int:
        """Calculate how many lines `text` needs inside a cell of `col_width`."""
        # Account for 2mm padding on each side
        effective_w = col_width - 2
        if effective_w <= 0:
            return 1
        str_width = self.get_string_width(self._safe(text))
        if str_width <= 0:
            return 1
        return max(1, int(str_width / effective_w) + 1)

    def _draw_wrapped_row(self, row: list[str], col_widths: list[float], line_h: float = 5):
        """Draw a single table row with proper text wrapping in each cell."""
        # Step 1: figure out the tallest cell
        self.set_font("Helvetica", "", 9)
        max_lines = 1
        for i, val in enumerate(row):
            n = self._lines_needed(str(val), col_widths[i])
            if n > max_lines:
                max_lines = n
        row_height = max(7, max_lines * line_h + 2)

        # Step 2: check if we need a page break
        if self.get_y() + row_height > self.h - self.b_margin:
            self.add_page()

        x_start = self.get_x()
        y_start = self.get_y()

        # Step 3: draw filled background rects + borders first
        for i, val in enumerate(row):
            self.rect(x_start + sum(col_widths[:i]), y_start, col_widths[i], row_height, "DF")

        # Step 4: draw text in each cell using multi_cell
        self.set_text_color(*self.TEXT_DARK)
        for i, val in enumerate(row):
            cell_x = x_start + sum(col_widths[:i]) + 1  # 1mm left padding
            self.set_xy(cell_x, y_start + 1)
            align = "L" if i == 0 else "L"
            self.multi_cell(col_widths[i] - 2, line_h, self._safe(str(val)), align=align)

        # Step 5: move cursor below the row
        self.set_xy(x_start, y_start + row_height)

    def data_table(self, headers: list[str], rows: list[list[str]], col_widths: list[float] | None = None):
        """Draw a bordered table with header row and wrapped text in data cells."""
        if col_widths is None:
            usable = 180
            col_widths = [usable / len(headers)] * len(headers)

        row_h = 7

        # Header row (single-line, centered)
        self.set_font("Helvetica", "B", 9)
        self.set_fill_color(*self.NAVY)
        self.set_text_color(*self.WHITE)
        self.set_draw_color(*self.NAVY)
        for i, h in enumerate(headers):
            self.cell(col_widths[i], row_h, self._safe(h), border=1, fill=True, align="C")
        self.ln(row_h)

        # Data rows (with text wrapping)
        self.set_draw_color(*self.NAVY)
        alt = False
        for row in rows:
            if alt:
                self.set_fill_color(*self.BG_LIGHT)
            else:
                self.set_fill_color(*self.WHITE)
            self._draw_wrapped_row(row, col_widths)
            alt = not alt

        self.ln(3)

    # ----------------------------------------------------------------- #
    # Table: cost breakdown with total row
    # ----------------------------------------------------------------- #
    def cost_table(self, cost: dict):
        """Render a professional cost breakdown table."""
        headers = ["Cost Item", "Amount (USD)"]
        col_widths = [100, 80]
        row_h = 8

        items = [
            ("Development Cost", cost.get("development_cost", 0)),
            ("Infrastructure Cost", cost.get("infrastructure_cost", 0)),
            ("Contingency (10%)", cost.get("contingency", 0)),
        ]
        if cost.get("discount", 0) > 0:
            items.append(("Discount", -cost["discount"]))

        # Header
        self.set_font("Helvetica", "B", 9)
        self.set_fill_color(*self.NAVY)
        self.set_text_color(*self.WHITE)
        self.set_draw_color(*self.NAVY)
        for i, h in enumerate(headers):
            self.cell(col_widths[i], row_h, h, border=1, fill=True, align="C")
        self.ln(row_h)

        # Rows
        self.set_font("Helvetica", "", 9)
        self.set_text_color(*self.TEXT_DARK)
        alt = False
        for label, amount in items:
            if alt:
                self.set_fill_color(*self.BG_LIGHT)
            else:
                self.set_fill_color(*self.WHITE)
            self.cell(col_widths[0], row_h, label, border=1, fill=True)
            self.cell(col_widths[1], row_h, f"${amount:,.2f}", border=1, fill=True, align="R")
            self.ln(row_h)
            alt = not alt

        # Total row
        self.set_font("Helvetica", "B", 10)
        self.set_fill_color(230, 240, 250)
        self.set_text_color(*self.NAVY)
        self.cell(col_widths[0], row_h + 1, "TOTAL ESTIMATED COST", border=1, fill=True)
        self.cell(
            col_widths[1], row_h + 1,
            f"${cost.get('total_estimated_cost', 0):,.2f}",
            border=1, fill=True, align="R",
        )
        self.ln(row_h + 1)

        # Monthly average note
        monthly = cost.get("monthly_average", 0)
        if monthly > 0:
            self.set_font("Helvetica", "I", 8)
            self.set_text_color(*self.TEXT_MID)
            self.cell(0, 6, f"Monthly average: ${monthly:,.2f}", new_x="LMARGIN", new_y="NEXT")

        self.ln(3)


# ====================================================================== #
#                     MAIN BUILD FUNCTION                                 #
# ====================================================================== #

def build_proposal_pdf(proposal_data: dict) -> str:
    """Build a formal proposal PDF with tables and charts.

    Expected keys in proposal_data:
        project_title, industry, duration_months, expected_users, tech_stack,
        executive_summary, technical_approach, timeline (list or str),
        estimated_cost (dict), risk_assessment (list or str),
        deliverables (list or str), team_composition (list of dicts)
    """
    title = proposal_data.get("project_title", "Project Proposal")
    output_dir = os.path.join(os.getcwd(), "outputs")
    os.makedirs(output_dir, exist_ok=True)

    # ---- Pre-generate chart images ---- #
    cost = proposal_data.get("estimated_cost", {})
    pie_path = _chart_cost_pie(cost, output_dir) if isinstance(cost, dict) else ""

    timeline_data = proposal_data.get("timeline", [])
    timeline_bar_path = ""
    if isinstance(timeline_data, list) and timeline_data:
        timeline_bar_path = _chart_timeline_bar(timeline_data, output_dir)

    pdf = ProposalPDF(project_title=title)
    pdf.alias_nb_pages()

    # ===================== PAGE 1 ===================== #
    pdf.add_page()

    # ---- Project Overview Table ---- #
    pdf.section_heading("1. Project Overview")
    overview_rows = [
        ["Project Title", title],
        ["Industry", str(proposal_data.get("industry", "N/A"))],
        ["Duration", f"{proposal_data.get('duration_months', 'N/A')} months"],
        ["Expected Users", f"{proposal_data.get('expected_users', 'N/A'):,}"],
        ["Tech Stack", ", ".join(proposal_data.get("tech_stack", []))],
    ]
    pdf.data_table(["Parameter", "Details"], overview_rows, col_widths=[60, 120])

    # ---- Executive Summary ---- #
    pdf.section_heading("2. Executive Summary")
    pdf.body_text(str(proposal_data.get("executive_summary", "N/A")))

    # ---- Technical Approach ---- #
    pdf.section_heading("3. Technical Approach")
    pdf.body_text(str(proposal_data.get("technical_approach", "N/A")))

    # ---- Deliverables ---- #
    deliverables = proposal_data.get("deliverables", [])
    if deliverables:
        pdf.section_heading("4. Key Deliverables")
        if isinstance(deliverables, list):
            for i, d in enumerate(deliverables, 1):
                pdf.set_font("Helvetica", "", 10)
                pdf.set_text_color(*ProposalPDF.TEXT_DARK)
                pdf.cell(0, 6, pdf._safe(f"  {i}. {d}"), new_x="LMARGIN", new_y="NEXT")
            pdf.ln(3)
        else:
            pdf.body_text(str(deliverables))

    # ===================== PAGE 2 ===================== #
    pdf.add_page()

    # ---- Timeline Table + Chart ---- #
    pdf.section_heading("5. Project Timeline")
    if isinstance(timeline_data, list) and timeline_data:
        headers = ["Phase", "Duration", "Description"]
        widths = [45, 15, 120]
        rows = []
        for p in timeline_data:
            rows.append([
                str(p.get("phase", "")),
                f"{p.get('weeks', '')}w",
                str(p.get("description", "")),
            ])
        pdf.data_table(headers, rows, widths)

        # Timeline bar chart
        if timeline_bar_path and os.path.isfile(timeline_bar_path):
            pdf.image(timeline_bar_path, x=25, w=160)
            pdf.ln(5)
    else:
        pdf.body_text(str(timeline_data))

    # ---- Cost Breakdown Table + Chart ---- #
    pdf.section_heading("6. Estimated Cost")
    if isinstance(cost, dict):
        pdf.cost_table(cost)

        # Pie chart
        if pie_path and os.path.isfile(pie_path):
            x_center = (210 - 80) / 2
            pdf.image(pie_path, x=x_center, w=80)
            pdf.ln(5)
    else:
        pdf.body_text(str(cost))

    # ===================== PAGE 3 (if needed, auto page break) ===================== #

    # ---- Team Composition Table ---- #
    team = proposal_data.get("team_composition", [])
    if team:
        pdf.section_heading("7. Recommended Team Composition")
        headers = ["Role", "Headcount", "Allocation"]
        widths = [80, 40, 60]
        rows = [[str(t.get("role", "")), str(t.get("count", "")), str(t.get("allocation", ""))] for t in team]
        pdf.data_table(headers, rows, widths)

    # ---- Risk Assessment Table ---- #
    risk_data = proposal_data.get("risk_assessment", [])
    section_num = 8 if team else 7
    pdf.section_heading(f"{section_num}. Risk Assessment")
    if isinstance(risk_data, list) and risk_data:
        headers = ["Risk", "Impact", "Mitigation"]
        widths = [40, 20, 120]
        rows = []
        for r in risk_data:
            rows.append([
                str(r.get("risk", "")),
                str(r.get("impact", "")),
                str(r.get("mitigation", "")),
            ])
        pdf.data_table(headers, rows, widths)
    else:
        pdf.body_text(str(risk_data))

    # ---- Confidentiality Notice ---- #
    pdf.ln(8)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(160, 160, 160)
    pdf.multi_cell(
        0, 5,
        "This document is confidential and intended solely for the use of the intended recipient(s). "
        "Unauthorized distribution or reproduction is prohibited.",
        align="C",
    )

    # ---- Save ---- #
    filename = f"proposal_{int(time.time())}_{uuid4().hex[:6]}.pdf"
    filepath = os.path.join(output_dir, filename)
    pdf.output(filepath)

    # Clean up chart images
    for p in [pie_path, timeline_bar_path]:
        if p and os.path.isfile(p):
            try:
                os.remove(p)
            except OSError:
                pass

    return os.path.abspath(filepath)
