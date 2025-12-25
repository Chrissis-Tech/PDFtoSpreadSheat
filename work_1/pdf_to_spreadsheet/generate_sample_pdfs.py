"""
Script para generar PDFs de ejemplo
===================================

Genera PDFs de prueba con datos ficticios para testing.
Requiere: reportlab (pip install reportlab)
"""

import os
import sys
from pathlib import Path

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    print("reportlab no disponible. Instala con: pip install reportlab")


def create_invoice_pdf(output_path: str, invoice_num: int) -> None:
    """Crea un PDF de factura de ejemplo."""
    doc = SimpleDocTemplate(output_path, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()
    
    # Titulo
    title_style = ParagraphStyle(
        'Title',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30,
        alignment=1  # Center
    )
    elements.append(Paragraph("FACTURA", title_style))
    elements.append(Spacer(1, 20))
    
    # Info de factura
    info_data = [
        ["Numero de Factura:", f"INV-2024-{invoice_num:03d}"],
        ["Fecha:", f"15/0{invoice_num}/2024"],
        ["", ""],
        ["Proveedor:", "TechCorp Solutions S.A. de C.V."],
        ["RFC:", "TCS123456ABC"],
        ["Direccion:", "Av. Tecnologia 1234, CDMX"],
        ["", ""],
        ["Cliente:", f"Empresa Cliente {invoice_num} SA"],
        ["RFC Cliente:", f"ECL{invoice_num}87654XYZ"],
    ]
    
    info_table = Table(info_data, colWidths=[2*inch, 4*inch])
    info_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 30))
    
    # Tabla de items
    items_header = ["Cant.", "Descripcion", "Precio Unit.", "Total"]
    items_data = [items_header]
    
    products = [
        (5, "Licencia Software Enterprise", 1500.00),
        (10, "Horas de Consultoria", 150.00),
        (3, "Modulo Adicional Premium", 800.00),
        (1, "Soporte Anual", 2000.00),
        (20, "Capacitacion (horas)", 75.00),
    ]
    
    subtotal = 0
    for qty, desc, price in products[:3 + invoice_num % 3]:
        total = qty * price
        subtotal += total
        items_data.append([
            str(qty),
            desc,
            f"${price:,.2f}",
            f"${total:,.2f}"
        ])
    
    items_table = Table(items_data, colWidths=[0.7*inch, 3.5*inch, 1.2*inch, 1.2*inch])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (1, 1), (1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    elements.append(items_table)
    elements.append(Spacer(1, 20))
    
    # Totales
    iva = subtotal * 0.16
    total = subtotal + iva
    
    totals_data = [
        ["", "", "Subtotal:", f"${subtotal:,.2f}"],
        ["", "", "IVA (16%):", f"${iva:,.2f}"],
        ["", "", "TOTAL:", f"${total:,.2f}"],
    ]
    
    totals_table = Table(totals_data, colWidths=[2*inch, 2*inch, 1.2*inch, 1.2*inch])
    totals_table.setStyle(TableStyle([
        ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (2, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('LINEABOVE', (2, -1), (-1, -1), 2, colors.black),
    ]))
    elements.append(totals_table)
    
    doc.build(elements)
    print(f"Creado: {output_path}")


def create_report_pdf(output_path: str) -> None:
    """Crea un PDF de reporte tabular de ejemplo."""
    doc = SimpleDocTemplate(output_path, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()
    
    # Titulo
    title_style = ParagraphStyle(
        'Title',
        parent=styles['Heading1'],
        fontSize=20,
        spaceAfter=20,
        alignment=1
    )
    elements.append(Paragraph("REPORTE DE VENTAS MENSUAL", title_style))
    elements.append(Paragraph("Periodo: Enero 2024", styles['Normal']))
    elements.append(Spacer(1, 30))
    
    # Tabla de datos
    header = ["ID", "Vendedor", "Region", "Ventas", "Comision", "Fecha"]
    data = [header]
    
    sales_data = [
        ("V001", "Juan Perez", "Norte", 45000.00, 4500.00, "05/01/2024"),
        ("V002", "Maria Garcia", "Sur", 38000.00, 3800.00, "08/01/2024"),
        ("V003", "Carlos Lopez", "Centro", 52000.00, 5200.00, "12/01/2024"),
        ("V004", "Ana Martinez", "Este", 41000.00, 4100.00, "15/01/2024"),
        ("V005", "Roberto Sanchez", "Oeste", 35000.00, 3500.00, "18/01/2024"),
        ("V006", "Laura Hernandez", "Norte", 48000.00, 4800.00, "22/01/2024"),
        ("V007", "Pedro Gomez", "Sur", 39500.00, 3950.00, "25/01/2024"),
        ("V008", "Sofia Ruiz", "Centro", 55000.00, 5500.00, "28/01/2024"),
    ]
    
    for row in sales_data:
        data.append([
            row[0],
            row[1],
            row[2],
            f"${row[3]:,.2f}",
            f"${row[4]:,.2f}",
            row[5]
        ])
    
    # Fila de totales
    total_ventas = sum(row[3] for row in sales_data)
    total_comision = sum(row[4] for row in sales_data)
    data.append(["", "TOTAL", "", f"${total_ventas:,.2f}", f"${total_comision:,.2f}", ""])
    
    table = Table(data, colWidths=[0.6*inch, 1.5*inch, 0.8*inch, 1.1*inch, 1*inch, 1*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (1, 1), (1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 30))
    
    # Notas
    elements.append(Paragraph("Notas:", styles['Heading3']))
    elements.append(Paragraph("- Comision calculada al 10% de ventas", styles['Normal']))
    elements.append(Paragraph("- Datos correspondientes a Enero 2024", styles['Normal']))
    
    doc.build(elements)
    print(f"Creado: {output_path}")


def main():
    """Genera todos los PDFs de ejemplo."""
    if not REPORTLAB_AVAILABLE:
        print("Error: reportlab es requerido para generar PDFs")
        print("Instala con: pip install reportlab")
        sys.exit(1)
    
    # Directorio de salida
    script_dir = Path(__file__).parent
    input_dir = script_dir / "input"
    input_dir.mkdir(exist_ok=True)
    
    # Generar facturas de ejemplo
    for i in range(1, 4):
        pdf_path = input_dir / f"factura_ejemplo_{i:03d}.pdf"
        create_invoice_pdf(str(pdf_path), i)
    
    # Generar reporte de ejemplo
    report_path = input_dir / "reporte_ventas_ejemplo.pdf"
    create_report_pdf(str(report_path))
    
    print("\nPDFs de ejemplo generados en:", input_dir)


if __name__ == "__main__":
    main()
