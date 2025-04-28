import PyPDF2
import argparse
from docling.datamodel.base_models import InputFormat
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions
import os
import pandas as pd
from decimal import Decimal
import io
import tempfile
import re
from typing import Optional


def clean_amount(amount_str: str) -> Decimal:
    """Clean amount string by removing commas, handling negative values correctly, and removing any prefix text."""
    # Handle negative values with space after minus sign
    if amount_str.startswith('- '):
        amount_str = '-' + amount_str[2:]

    # Find the last number in the string (amount is always at the end)
    amount_match = re.search(r'([\d,-]+\.\d+)$', amount_str)
    if not amount_match:
        raise ValueError(f"Could not extract amount from string: {amount_str}")

    # Get the amount part and clean it
    amount_str = amount_match.group(1)

    # Remove commas and spaces
    amount_str = amount_str.replace(',', '').strip()

    return Decimal(amount_str)


def get_pdf_bytes(input_path: str, password: Optional[str] = None) -> Optional[bytes]:
    """
    Get PDF bytes, decrypting if necessary.

    Args:
        input_path (str): Path to the input PDF file
        password (str, optional): Password for encrypted PDF

    Returns:
        bytes: PDF content in bytes, or None if error occurs
    """
    try:
        # Open the PDF file in read binary mode
        with open(input_path, 'rb') as file:
            # Create PDF reader object
            pdf_reader = PyPDF2.PdfReader(file)

            # Check if the PDF is encrypted
            if pdf_reader.is_encrypted:
                if not password:
                    raise ValueError(
                        "PDF is encrypted but no password provided")

                # Try to decrypt with provided password
                if pdf_reader.decrypt(password):
                    print("Successfully decrypted the PDF")
                else:
                    raise ValueError("Incorrect password")

            # Create a PDF writer object for in-memory processing
            pdf_writer = PyPDF2.PdfWriter()

            # Add all pages to the writer
            for page in pdf_reader.pages:
                pdf_writer.add_page(page)

            # Write to bytes buffer instead of file
            output_buffer = io.BytesIO()
            pdf_writer.write(output_buffer)

            # Get the bytes content
            return output_buffer.getvalue()

    except FileNotFoundError:
        print(f"Error: The file {input_path} was not found.")
    except ValueError as e:
        print(f"Error: {str(e)}")
    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}")

    return None


def validate_transaction_table_columns(df: pd.DataFrame, table_index: int) -> bool:
    """
    Validate that the table has the expected number of columns and correct header names.
    """
    expected_columns = 4
    expected_keywords = [
        ['TRANS. DATE'],  # Transaction date column
        ['POSTING DATE'],  # Posting date column
        ['DESCRIPTION'],  # Description column
        ['AMOUNT', 'BAHT']  # Amount column
    ]

    # Check number of columns
    if len(df.columns) != expected_columns:
        print(
            f"Table {table_index} has {len(df.columns)} columns, expected {expected_columns}, skipping")
        return False

    # Check if each column contains its expected keywords
    for col_idx, (col_name, keywords) in enumerate(zip(df.columns, expected_keywords)):
        col_name_upper = col_name.upper()
        if not all(keyword in col_name_upper for keyword in keywords):
            print(
                f"Table {table_index} has incorrect header at column {col_idx + 1}:")
            print(f"Expected keywords: {keywords}")
            print(f"Column name: {col_name}")
            return False

    return True


def convert_data_types(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convert data types for the DataFrame:
    - First column to datetime
    - Last column to decimal
    """
    # Convert both date columns to datetime
    df.iloc[:, 0] = df.iloc[:, 0].apply(
        pd.to_datetime, format='%d/%m/%y')
    # Convert last column to decimal
    df.iloc[:, -1] = df.iloc[:, -1].apply(clean_amount)
    return df


def validate_transaction_totals(df: pd.DataFrame, starting_balance: Decimal, ending_balance: Decimal) -> None:
    """Validate that starting balance + sum of transactions = ending balance"""
    total_amount = df.iloc[:, -1].sum()
    if starting_balance + total_amount != ending_balance:
        raise ValueError(
            f"Sanity check failed: Starting balance {starting_balance} + total amount {total_amount} != ending balance {ending_balance}")


def clean_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Check the columns header; if there are multiple adjacent columns with the same header, combine them into one by concatenating their text."""
    new_df = pd.DataFrame(index=df.index)

    col_iter = iter(range(len(df.columns)))
    for i in col_iter:
        col_name = df.columns[i]
        combined_col = df.iloc[:, i].astype(str)

        # Look ahead to combine adjacent columns with the same name
        j = i + 1
        while j < len(df.columns) and df.columns[j] == col_name:
            combined_col += " " + df.iloc[:, j].astype(str)
            j += 1

        new_df[col_name] = combined_col.replace('nan', '', regex=False)

        # Skip the columns we already processed
        for _ in range(i + 1, j):
            next(col_iter, None)

    return new_df


def clean_transaction_data(df: pd.DataFrame) -> pd.DataFrame:
    """Clean and filter transaction data."""
    # Drop rows with any null values
    df = df[df.notna().all(axis=1)]

    # Drop the second column
    df = df.drop(df.columns[[1]], axis=1)

    # Filter out rows where dates don't match expected format
    def is_valid_date(date_str):
        return pd.to_datetime(date_str, format='%d/%m/%y', errors='coerce') is not pd.NaT

    # Filter out rows where amounts can't be converted
    def is_valid_amount(amount_str):
        try:
            clean_amount(str(amount_str))
            return True
        except:
            return False

    # Apply date validation to first column
    date_mask = df.iloc[:, 0].apply(is_valid_date)
    # Apply amount validation to last column
    amount_mask = df.iloc[:, -1].apply(is_valid_amount)

    # Keep only rows that pass both validations
    df = df[date_mask & amount_mask]

    return df


def filter_payment_transactions(df: pd.DataFrame) -> pd.DataFrame:
    """
    Filter out transactions that have a negative amount and description starting with 'Payment'.

    Args:
        df (pd.DataFrame): DataFrame containing transaction data

    Returns:
        pd.DataFrame: Filtered DataFrame with payment transactions removed
    """
    return df[~((df.iloc[:, -1] < 0) & (df.iloc[:, 1].str.startswith('Payment')))]


def flip_amount_sign(df: pd.DataFrame) -> pd.DataFrame:
    """
    Flip positive amount to negative and vice versa
    """
    df.iloc[:, -1] = df.iloc[:, -1].apply(lambda x: -x)
    return df


def save_to_csv(df: pd.DataFrame, output_dir: str, original_filename: str) -> None:
    """
    Save DataFrame to CSV file using the original filename.

    Args:
        df: DataFrame to save
        output_dir: Directory to save the CSV file
        original_filename: Original PDF filename to base the CSV filename on
    """
    # Remove .pdf extension if present and add .csv
    base_name = os.path.splitext(os.path.basename(original_filename))[0]
    csv_path = os.path.join(output_dir, f"{base_name}.csv")
    df.to_csv(csv_path, index=False, encoding='utf-8-sig')
    print(f"Saved result to: {csv_path}")


def process_pdf(pdf_path: str, output_dir: str, original_path: str) -> None:
    """
    Process a PDF using docling's document converter to extract and process tables.

    Args:
        pdf_path (str): Path to the PDF file to process
        output_dir (str): Directory where output files will be saved
        original_path (str): Original input path for naming the output file
    """
    try:
        # Create a document converter and convert the PDF
        pipeline_options = PdfPipelineOptions()
        pipeline_options.do_ocr = False
        pipeline_options.do_table_structure = True

        converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(
                    pipeline_options=pipeline_options
                )
            }
        )

        result = converter.convert(pdf_path)
        doc = result.document

        print("\nDocument Information:")
        print("-" * 50)
        print(f"Number of pages: {len(doc.pages)}")
        print(f"Document name: {doc.name}")
        print(f"Document origin: {doc.origin}")
        print(f"Document version: {doc.version}")

        # Process tables if present
        if not doc.tables:
            print("\nNo tables found in the document")
            return

        print("\nTables Found:")
        print(f"Number of tables: {len(doc.tables)}")

        # Process and combine all transaction tables
        transaction_dfs = []
        for i, table in enumerate(doc.tables, 1):
            print(f"\nProcessing table {i}...")
            df = table.export_to_dataframe()
            df = clean_columns(df)
            if not validate_transaction_table_columns(df, i):
                continue

            transaction_dfs.append(df)

        if not transaction_dfs:
            print("No transaction tables found in the document")
            return

        # Combine all transaction tables
        combined_transaction_df = pd.concat(transaction_dfs)

        starting_balance = clean_amount(combined_transaction_df.iloc[0, -1])
        ending_balance = clean_amount(combined_transaction_df.iloc[-1, -1])

        combined_transaction_df = clean_transaction_data(
            combined_transaction_df)
        combined_transaction_df = convert_data_types(
            combined_transaction_df)
        validate_transaction_totals(
            combined_transaction_df, starting_balance, ending_balance)

        # Filter out payment transactions
        combined_transaction_df = filter_payment_transactions(
            combined_transaction_df)
        combined_transaction_df = flip_amount_sign(combined_transaction_df)

        # Get just the filename from the original path
        input_filename = os.path.basename(original_path)
        # Save the transaction data with original filename
        save_to_csv(combined_transaction_df, output_dir, input_filename)

    except Exception as e:
        print(f"\nError processing document: {str(e)}")
        print("Full error details:")
        import traceback
        traceback.print_exc()


def main() -> None:
    """Main function to handle command line arguments and process PDF files."""
    parser = argparse.ArgumentParser(
        description='Process PDF files: decrypt if needed and extract tables')

    parser.add_argument('input', help='Path to the input PDF file')
    parser.add_argument(
        '--password', help='Password for the PDF file (if encrypted)')
    parser.add_argument(
        '--output-dir', default='output',
        help='Directory where output files will be saved (default: output)')

    args = parser.parse_args()

    # Get PDF bytes (decrypted if necessary)
    pdf_bytes = get_pdf_bytes(args.input, args.password)
    if pdf_bytes is None:
        return

    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)

    # Create a temporary file for processing
    temp_pdf = None
    try:
        # Create and write to temporary file
        temp_pdf = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
        temp_pdf.write(pdf_bytes)
        temp_pdf.close()  # Close the file to ensure all data is written

        # Process the temporary PDF file but use original input path for naming
        process_pdf(temp_pdf.name, args.output_dir, original_path=args.input)

    finally:
        # Clean up the temporary file
        if temp_pdf and os.path.exists(temp_pdf.name):
            os.unlink(temp_pdf.name)


if __name__ == '__main__':
    main()
