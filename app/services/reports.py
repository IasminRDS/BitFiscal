import csv
from io import BytesIO, StringIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from datetime import datetime
import openpyxl


def tickets_csv(tickets):
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "id",
            "cliente",
            "assunto",
            "canal",
            "prioridade",
            "status",
            "responsavel",
            "criado_em",
        ]
    )
    for t in tickets:
        writer.writerow(
            [
                t.id,
                t.cliente,
                t.assunto,
                t.canal,
                t.prioridade,
                t.status,
                t.responsavel,
                t.criado_em,
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
    c.drawString(50, y, "ID  Cliente  Assunto  Canal  Prioridade  Status  Responsável")
    y -= 12
    c.setFont("Helvetica", 8)

    for t in tickets:
        linha = f"{t.id}  {t.cliente}  {t.assunto}  {t.canal}  {t.prioridade}  {t.status}  {t.responsavel}"
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
    ws.append(
        [
            "ID",
            "Cliente",
            "Assunto",
            "Canal",
            "Prioridade",
            "Status",
            "Responsável",
            "Criado em",
        ]
    )
    for t in tickets:
        ws.append(
            [
                t.id,
                t.cliente,
                t.assunto,
                t.canal,
                t.prioridade,
                t.status,
                t.responsavel,
                str(t.criado_em),
            ]
        )
    stream = BytesIO()
    wb.save(stream)
    stream.seek(0)
    return stream.read()
