from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
import os


def create_test_pdf(output_path):
    # Create a PDF document
    doc = SimpleDocTemplate(output_path, pagesize=letter)

    # Sample transaction data with correct column names and totals
    data = [
        ['TRANS. DATE', 'POSTING DATE', 'DESCRIPTION', 'AMOUNT BAHT'],
        ['', '', 'Starting Balance', '1,000.00'],
        ['02/01/23', '02/01/23', 'Purchase 1', '2,000.00'],
        ['03/01/23', '03/01/23', 'Payment 1', '-1,000.00'],
        ['04/01/23', '04/01/23', 'Purchase 2', '3,000.00'],
        ['05/01/23', '05/01/23', 'Purchase 3', '4,000.00'],
        ['', '', 'Ending Balance', '9,000.00']
    ]

    # Create table
    table = Table(data)

    # Add style
    style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 14),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 12),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('SPAN', (0, 0), (0, 0)),  # Ensure header cells are not merged
        ('SPAN', (1, 0), (1, 0)),
        ('SPAN', (2, 0), (2, 0)),
        ('SPAN', (3, 0), (3, 0)),
        # Make header text black for better visibility
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        # Make header background white
        ('BACKGROUND', (0, 0), (-1, 0), colors.white)
    ])
    table.setStyle(style)

    # Build PDF
    doc.build([table])


if __name__ == '__main__':
    # Create test PDFs directory if it doesn't exist
    os.makedirs('tests/test_data', exist_ok=True)

    # Create regular test PDF
    create_test_pdf('tests/test_data/sample_transactions.pdf')

    print("Test PDFs created successfully!")
