"""
Export Service (Phase 2 Core)

Handles exporting patient data (Health Metrics, Chat History) into structured formats
like CSV (built-in FastAPI) or PDF (using reportlab). 
Provides a standardized report format for local doctors or CHWs.
"""
import io
import csv
from typing import List, Dict, Any

from backend.utils.logger import get_logger

logger = get_logger(__name__)

class ExportService:
    def export_metrics_csv(self, metrics: List[Dict[str, Any]]) -> io.StringIO:
        """Export health metrics to CSV format."""
        logger.debug(f"Exporting {len(metrics)} metrics to CSV")
        output = io.StringIO()
        if not metrics:
            return output
            
        fieldnames = metrics[0].keys()
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(metrics)
        output.seek(0)
        return output
        
    def export_clinical_report_pdf(self, patient_info: dict, metrics: List[Dict], summary: str) -> io.BytesIO:
        """Export a readable, valid PDF clinical report."""
        output = io.BytesIO()
        from textwrap import wrap

        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.pdfgen import canvas
        except ImportError:
            # Keep PDF export functional in the lightweight frontend/test
            # environment. Production installs reportlab from requirements;
            # this standards-compliant one-page fallback has no extra runtime
            # dependency.
            lines = [
                "AfriHealth Assistant - Clinical Report",
                f"Patient: {patient_info.get('name') or patient_info.get('mrn') or 'Unknown'}",
                f"MRN: {patient_info.get('mrn', 'Not recorded')}",
                "Summary",
                summary or "No summary recorded.",
                "Health metrics",
            ]
            lines.extend(
                " | ".join(f"{key}: {value}" for key, value in metric.items())
                for metric in metrics
            )
            if not metrics:
                lines.append("No health metrics recorded.")
            return self._minimal_pdf(lines)

        pdf = canvas.Canvas(output, pagesize=A4)
        width, height = A4
        y = height - 48

        def line(text, size=10, leading=14):
            nonlocal y
            if y < 48:
                pdf.showPage()
                y = height - 48
            pdf.setFont("Helvetica", size)
            for part in wrap(str(text or ""), width=100):
                pdf.drawString(42, y, part)
                y -= leading

        pdf.setTitle("AfriHealth Clinical Report")
        line("AfriHealth Assistant - Clinical Report", 16, 22)
        line(f"Patient: {patient_info.get('name') or patient_info.get('mrn') or 'Unknown'}", 11)
        line(f"MRN: {patient_info.get('mrn', 'Not recorded')}")
        y -= 8
        line("Summary", 12, 16)
        line(summary or "No summary recorded.")
        y -= 8
        line("Health metrics", 12, 16)
        if metrics:
            for metric in metrics:
                line(" | ".join(f"{key}: {value}" for key, value in metric.items()))
        else:
            line("No health metrics recorded.")
        pdf.save()
        output.seek(0)
        return output

    @staticmethod
    def _minimal_pdf(lines: List[str]) -> io.BytesIO:
        """Create a small valid PDF without depending on a PDF package."""
        def escape(value: str) -> str:
            return str(value).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

        commands = ["BT", "/F1 10 Tf", "42 780 Td"]
        for index, line in enumerate(lines[:45]):
            if index:
                commands.append("0 -14 Td")
            commands.append(f"({escape(line)}) Tj")
        commands.append("ET")
        stream = "\n".join(commands).encode("latin-1", errors="replace")
        objects = [
            b"<< /Type /Catalog /Pages 2 0 R >>",
            b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
            b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream",
        ]
        pdf = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        offsets = [0]
        for number, obj in enumerate(objects, start=1):
            offsets.append(len(pdf))
            pdf.extend(f"{number} 0 obj\n".encode("ascii"))
            pdf.extend(obj)
            pdf.extend(b"\nendobj\n")
        xref = len(pdf)
        pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
        pdf.extend(b"0000000000 65535 f \n")
        for offset in offsets[1:]:
            pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
        pdf.extend(
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode("ascii")
        )
        return io.BytesIO(bytes(pdf))

export_service = ExportService()
