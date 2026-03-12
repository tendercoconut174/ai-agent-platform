"""Delivery Service: formats and delivers results to user."""

import base64
import io
import uuid
from typing import Any, Dict, Optional

from shared.models import OrchestratorResponse


def _wrap_line(text: str, width: int = 90) -> list[str]:
    """Wrap long lines to avoid fpdf 'not enough horizontal space' errors."""
    words = text.split()
    lines = []
    current = []
    current_len = 0
    for w in words:
        if current_len + len(w) + 1 <= width:
            current.append(w)
            current_len += len(w) + 1
        else:
            if current:
                lines.append(" ".join(current))
            current = [w]
            current_len = len(w)
    if current:
        lines.append(" ".join(current))
    return lines


def _text_to_pdf(content: str) -> bytes:
    """Convert text/markdown to PDF bytes."""
    from fpdf import FPDF

    pdf = FPDF()
    pdf.set_auto_page_break(True, margin=15)
    pdf.set_margins(left=15, top=15, right=15)
    pdf.add_page()
    pdf.set_font("Helvetica", size=10)
    # Use explicit width (A4 ~210mm - margins) to avoid "Not enough horizontal space"
    w = pdf.epw  # effective page width after margins
    for block in content.split("\n"):
        for line in _wrap_line(block):
            pdf.multi_cell(w=w, h=6, txt=line)
    buf = io.BytesIO()
    pdf.output(buf)
    return buf.getvalue()


def _text_to_excel(content: str) -> bytes:
    """Convert text/markdown table to Excel bytes."""
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font

        wb = Workbook()
        ws = wb.active
        ws.title = "Result"

        # Try to parse markdown table (| col1 | col2 |)
        lines = [l.strip() for l in content.split("\n") if l.strip()]
        rows = []
        for line in lines:
            if "|" in line:
                cells = [c.strip() for c in line.split("|") if c.strip()]
                if cells and not all(c.replace("-", "").replace(":", "").strip() == "" for c in cells):
                    rows.append(cells)
            else:
                rows.append([line])

        if not rows:
            ws["A1"] = content[:50000]  # Fallback: plain text in A1
        else:
            for r, row in enumerate(rows, 1):
                for c, val in enumerate(row, 1):
                    cell = ws.cell(row=r, column=c, value=val)
                    if r == 1:
                        cell.font = Font(bold=True)

        buf = io.BytesIO()
        wb.save(buf)
        return buf.getvalue()
    except ImportError:
        raise ImportError("Install openpyxl for Excel export: pip install openpyxl")


def deliver(
    result: Optional[Dict[str, Any]],
    workflow_id: Optional[str] = None,
    output_format: str = "json",
) -> Dict[str, Any]:
    """Format result for delivery to user.

    Args:
        result: Result dict from Task Graph Engine.
        workflow_id: Optional workflow identifier.
        output_format: json (default), pdf, or xl (Excel).

    Returns:
        Formatted response for user.
    """
    if result is None:
        return {"status": "timeout", "result": "Request timed out"}
    text = result.get("result", "")

    if output_format == "pdf":
        try:
            pdf_bytes = _text_to_pdf(text)
            return OrchestratorResponse(
                result=text,
                workflow_id=workflow_id,
                content_base64=base64.b64encode(pdf_bytes).decode("ascii"),
                content_type="application/pdf",
                filename=f"result_{workflow_id or uuid.uuid4()}.pdf",
            ).model_dump()
        except Exception as e:
            return OrchestratorResponse(
                result=text,
                workflow_id=workflow_id,
            ).model_dump() | {"status": "error", "detail": f"PDF export failed: {e}"}

    if output_format == "xl":
        try:
            xl_bytes = _text_to_excel(text)
            return OrchestratorResponse(
                result=text,
                workflow_id=workflow_id,
                content_base64=base64.b64encode(xl_bytes).decode("ascii"),
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                filename=f"result_{workflow_id or uuid.uuid4()}.xlsx",
            ).model_dump()
        except Exception as e:
            return OrchestratorResponse(
                result=text,
                workflow_id=workflow_id,
            ).model_dump() | {"status": "error", "detail": f"Excel export failed: {e}"}

    return OrchestratorResponse(
        result=text,
        workflow_id=workflow_id,
    ).model_dump()
