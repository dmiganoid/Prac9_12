from datetime import UTC, datetime
from decimal import Decimal
from io import BytesIO
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def money(value: Any) -> str:
    amount = value if isinstance(value, Decimal) else Decimal(str(value or "0"))
    return f"{amount:.2f}"


def generate_sales_summary_pdf(report: dict[str, Any], data: dict[str, Any]) -> bytes:
    buffer = BytesIO()
    document = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()
    elements = [
        Paragraph("Sales Summary Report", styles["Title"]),
        Spacer(1, 12),
        Paragraph(
            f"Period: {data['period']['date_from']} - {data['period']['date_to']}",
            styles["Normal"],
        ),
        Paragraph(f"Generated at: {datetime.now(UTC).isoformat(timespec='seconds')}", styles["Normal"]),
        Spacer(1, 12),
        Paragraph(f"Orders count: {data['total_orders']}", styles["Normal"]),
        Paragraph(f"Total amount: {money(data['total_amount'])}", styles["Normal"]),
        Paragraph(f"Average check: {money(data['average_check'])}", styles["Normal"]),
        Spacer(1, 18),
        Paragraph("By Region", styles["Heading2"]),
    ]

    region_rows = [["Region", "Orders", "Total", "Average"]]
    for row in data["regions"]:
        region_rows.append(
            [
                row["region"],
                str(row["order_count"]),
                money(row["total_amount"]),
                money(row["average_amount"]),
            ]
        )
    if len(region_rows) == 1:
        region_rows.append(["No data", "0", "0.00", "0.00"])
    elements.append(_styled_table(region_rows, [150, 90, 120, 120]))
    elements.extend([Spacer(1, 18), Paragraph("Recent Orders", styles["Heading2"])])

    order_rows = [["Date", "Customer", "Region", "Amount", "Status"]]
    for row in data["recent_orders"]:
        created_at = row["created_at"]
        if hasattr(created_at, "strftime"):
            created_at = created_at.strftime("%Y-%m-%d")
        order_rows.append(
            [
                str(created_at),
                row["customer_name"],
                row["region"],
                money(row["amount"]),
                row["status"],
            ]
        )
    if len(order_rows) == 1:
        order_rows.append(["-", "No orders", "-", "0.00", "-"])
    elements.append(_styled_table(order_rows, [80, 170, 90, 90, 70]))

    document.build(elements)
    return buffer.getvalue()


def _styled_table(rows: list[list[str]], widths: list[int]) -> Table:
    table = Table(rows, colWidths=widths, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#234E70")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D8DEE9")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F7FA")]),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return table
