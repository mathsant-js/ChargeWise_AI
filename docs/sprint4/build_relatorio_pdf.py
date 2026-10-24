"""Gera o PDF de evolução da Sprint 4 a partir do Markdown canônico.

Requer ReportLab. Exemplo: python docs/sprint4/build_relatorio_pdf.py
"""

from __future__ import annotations

import html
import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    HRFlowable, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "relatorio_evolucao_sprint4.md"
OUTPUT = HERE / "relatorio_evolucao_sprint4.pdf"
INK = colors.HexColor("#17344a")
TEAL = colors.HexColor("#168b83")
PALE = colors.HexColor("#edf7f5")


def inline(value: str) -> str:
    value = html.escape(value.strip())
    value = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", value)
    value = re.sub(r"`([^`]+)`", r'<font color="#126d67">\1</font>', value)
    return value


def footer(canvas, doc):
    canvas.saveState()
    width, _ = A4
    canvas.setStrokeColor(colors.HexColor("#cbd9db"))
    canvas.line(19 * mm, 18 * mm, width - 19 * mm, 18 * mm)
    canvas.setFont("DejaVu", 8)
    canvas.setFillColor(colors.HexColor("#667982"))
    canvas.drawString(19 * mm, 13 * mm, "ChargeWise AI  |  Sprint 4  |  23/10/2026")
    canvas.drawRightString(width - 19 * mm, 13 * mm, str(doc.page))
    canvas.restoreState()


def build():
    pdfmetrics.registerFont(TTFont("DejaVu", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"))
    pdfmetrics.registerFont(TTFont("DejaVu-Bold", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"))
    pdfmetrics.registerFontFamily("DejaVu", normal="DejaVu", bold="DejaVu-Bold")
    styles = getSampleStyleSheet()
    title = ParagraphStyle("TitleCW", parent=styles["Title"], fontName="DejaVu-Bold",
                           fontSize=19, leading=22, textColor=INK, spaceAfter=8)
    heading = ParagraphStyle("HeadingCW", parent=styles["Heading2"], fontName="DejaVu-Bold",
                             fontSize=11.5, leading=14, textColor=INK, spaceBefore=12, spaceAfter=5)
    body = ParagraphStyle("BodyCW", parent=styles["BodyText"], fontName="DejaVu",
                          fontSize=9, leading=12.6, textColor=INK, spaceAfter=7)
    small = ParagraphStyle("SmallCW", parent=body, fontSize=7.7, leading=10, spaceAfter=0)
    header = ParagraphStyle("HeaderCW", parent=small, fontName="DejaVu-Bold",
                            textColor=colors.white)
    story = []
    lines = SOURCE.read_text(encoding="utf-8").splitlines()
    idx = 0
    while idx < len(lines):
        line = lines[idx].strip()
        if not line:
            idx += 1
            continue
        if line.startswith("# "):
            story.append(Paragraph(inline(line[2:]), title))
            story.append(HRFlowable(width="100%", thickness=2, color=TEAL, spaceAfter=9))
            idx += 1
            continue
        if line.startswith("## "):
            story.append(Paragraph(inline(line[3:]), heading))
            idx += 1
            continue
        if line.startswith("| "):
            rows = []
            while idx < len(lines) and lines[idx].strip().startswith("|"):
                cells = [cell.strip() for cell in lines[idx].strip().strip("|").split("|")]
                if not all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells):
                    rows.append(cells)
                idx += 1
            if rows:
                col_count = len(rows[0])
                widths = ([70, 112, 139, 130] if col_count == 4 else
                          [177, 48, 226] if col_count == 3 else
                          [(A4[0] - 38 * mm) / col_count] * col_count)
                if col_count in (3, 4):
                    factor = (A4[0] - 38 * mm) / sum(widths)
                    widths = [w * factor for w in widths]
                content = [[Paragraph(inline(cell), header if r == 0 else small)
                            for cell in row] for r, row in enumerate(rows)]
                table = Table(content, colWidths=widths, repeatRows=1, hAlign="LEFT")
                table.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), INK),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PALE]),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ("LINEBELOW", (0, -1), (-1, -1), 0.4, colors.HexColor("#cbd9db")),
                ]))
                story.extend([Spacer(1, 3), table, Spacer(1, 7)])
            continue
        if re.match(r"^\d+\. ", line):
            story.append(Paragraph(inline(line), body))
            idx += 1
            continue
        paragraph = [line.rstrip(" ")]
        idx += 1
        while idx < len(lines) and lines[idx].strip() and not (
            lines[idx].startswith("#") or lines[idx].startswith("|")
            or re.match(r"^\d+\. ", lines[idx])
        ):
            paragraph.append(lines[idx].strip())
            idx += 1
        story.append(Paragraph(inline(" ".join(paragraph)), body))

    doc = SimpleDocTemplate(str(OUTPUT), pagesize=A4, leftMargin=19 * mm,
                            rightMargin=19 * mm, topMargin=17 * mm,
                            bottomMargin=23 * mm, title="ChargeWise AI - Evolução Sprint 4")
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    print(OUTPUT)


if __name__ == "__main__":
    build()
