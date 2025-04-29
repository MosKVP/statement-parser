import PyPDF2
import os


def create_encrypted_pdf(input_path, output_path, password):
    # Read the input PDF
    with open(input_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        writer = PyPDF2.PdfWriter()

        # Add all pages to the writer
        for page in reader.pages:
            writer.add_page(page)

        # Encrypt the PDF with the password
        writer.encrypt(password)

        # Write the encrypted PDF to file
        with open(output_path, 'wb') as output_file:
            writer.write(output_file)


if __name__ == '__main__':
    # Create encrypted version of the sample PDF
    input_path = 'tests/test_data/sample_transactions.pdf'
    output_path = 'tests/test_data/encrypted_transactions.pdf'
    password = 'test123'  # Test password

    create_encrypted_pdf(input_path, output_path, password)
    print("Encrypted PDF created successfully!")
