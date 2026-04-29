import csv
from io import BytesIO, StringIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from datetime import datetime
import openpyxl


def tickets_csv(tickets):
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Título", "Descrição", "Status", "Solicitante", "Criado em"])
    for t in tickets:
        writer.writerow(
            [
                t.id,
                t.titulo,
                t.descricao,
                t.status,
                t.solicitante.username if t.solicitante else "",
                t.criado_em.strftime("%Y-%m-%d %H:%M"),
            ]
        )
    return output.getvalue().encode("utf-8")


def tickets_pdf(tickets):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 50
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, y, "Relatório de Tickets")
    y -= 20
    c.setFont("Helvetica", 9)
    c.drawString(50, y, f"Gerado em: {datetime.utcnow().isoformat()} UTC")
    y -= 20
    c.setFont("Helvetica-Bold", 9)
    c.drawString(50, y, "ID  Título  Status  Solicitante")
    y -= 12
    c.setFont("Helvetica", 8)
    for t in tickets:
        solicitante = t.solicitante.username if t.solicitante else "N/A"
        linha = f"{t.id}  {t.titulo[:40]}  {t.status}  {solicitante}"
        c.drawString(50, y, linha[:120])
        y -= 12
        if y < 60:
            c.showPage()
            y = height - 50
    c.save()
    buffer.seek(0)
    return buffer.read()


def tickets_excel(tickets):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Tickets"
    ws.append(["ID", "Título", "Descrição", "Status", "Solicitante", "Criado em"])
    for t in tickets:
        ws.append(
            [
                t.id,
                t.titulo,
                t.descricao,
                t.status,
                t.solicitante.username if t.solicitante else "",
                str(t.criado_em),
            ]
        )
    stream = BytesIO()
    wb.save(stream)
    stream.seek(0)
    return stream.read()
