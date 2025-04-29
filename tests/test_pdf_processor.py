import pytest
import pandas as pd
from decimal import Decimal
from pathlib import Path
from src.pdf_processor import (
    clean_amount,
    get_pdf_bytes,
    validate_transaction_table_columns,
    convert_data_types,
    validate_transaction_totals,
    clean_columns,
    clean_transaction_data,
    filter_payment_transactions,
    flip_amount_sign,
    save_to_csv,
    read_pdf_tables,
    process_transaction_tables,
    process_pdf
)
import tempfile
import os

# Test data fixtures


@pytest.fixture
def sample_transaction_df():
    return pd.DataFrame({
        'TRANS. DATE': ['01/01/23', '02/01/23', '03/01/23'],
        'POSTING DATE': ['01/01/23', '02/01/23', '03/01/23'],
        'DESCRIPTION': ['Purchase 1', 'Purchase 2', 'Payment 1'],
        'AMOUNT BAHT': ['1,000.00', '2,000.00', '-3,000.00']
    })


@pytest.fixture
def sample_duplicate_columns_df():
    return pd.DataFrame({
        'DESCRIPTION': ['A', 'B', 'C'],
        'DESCRIPTION': ['1', '2', '3'],
        'AMOUNT': ['100.00', '200.00', '300.00']
    })


@pytest.fixture
def test_pdf_path():
    """Fixture to ensure test PDF exists and return its path."""
    pdf_path = Path('tests/test_data/sample_transactions.pdf')
    if not pdf_path.exists():
        # Create the test PDF if it doesn't exist
        from tests.test_data.create_test_pdf import create_test_pdf
        create_test_pdf(str(pdf_path))
    return str(pdf_path)


@pytest.fixture
def encrypted_pdf_path():
    """Fixture to ensure encrypted test PDF exists and return its path."""
    pdf_path = Path('tests/test_data/encrypted_transactions.pdf')
    if not pdf_path.exists():
        # Create the encrypted PDF if it doesn't exist
        from tests.test_data.create_encrypted_pdf import create_encrypted_pdf
        input_path = 'tests/test_data/sample_transactions.pdf'
        create_encrypted_pdf(input_path, str(pdf_path), 'test123')
    return str(pdf_path)

# Test cases for clean_amount


def test_clean_amount_positive():
    assert clean_amount('1,000.00') == Decimal('1000.00')


def test_clean_amount_negative():
    assert clean_amount('- 1,000.00') == Decimal('-1000.00')


def test_clean_amount_with_text():
    assert clean_amount('Total: 1,000.00') == Decimal('1000.00')


def test_clean_amount_invalid():
    with pytest.raises(ValueError):
        clean_amount('invalid')

# Test cases for validate_transaction_table_columns


def test_validate_transaction_table_columns_valid(sample_transaction_df):
    assert validate_transaction_table_columns(sample_transaction_df, 1) is True


def test_validate_transaction_table_columns_invalid_columns():
    df = pd.DataFrame({
        'TRANS. DATE': ['01/01/23'],
        'POSTING DATE': ['01/01/23'],
        'DESCRIPTION': ['Test']
    })
    assert validate_transaction_table_columns(df, 1) is False


def test_validate_transaction_table_columns_invalid_headers():
    df = pd.DataFrame({
        'DATE': ['01/01/23'],
        'POST DATE': ['01/01/23'],
        'DESC': ['Test'],
        'VALUE': ['100.00']
    })
    assert validate_transaction_table_columns(df, 1) is False

# Test cases for convert_data_types


def test_convert_data_types(sample_transaction_df):
    df = convert_data_types(sample_transaction_df)
    # The first column should be datetime type
    assert isinstance(df.iloc[0, 0], pd.Timestamp)
    # The last column should be Decimal type
    assert isinstance(df.iloc[0, -1], Decimal)

# Test cases for validate_transaction_totals


def test_validate_transaction_totals_valid():
    df = pd.DataFrame({
        'AMOUNT': [Decimal('1000.00'), Decimal('2000.00')]
    })
    validate_transaction_totals(df, Decimal('0.00'), Decimal('3000.00'))


def test_validate_transaction_totals_invalid():
    df = pd.DataFrame({
        'AMOUNT': [Decimal('1000.00'), Decimal('2000.00')]
    })
    with pytest.raises(ValueError):
        validate_transaction_totals(df, Decimal('0.00'), Decimal('4000.00'))

# Test cases for clean_columns


def test_clean_columns(sample_duplicate_columns_df):
    df = clean_columns(sample_duplicate_columns_df)
    assert len(df.columns) == 2  # Should combine duplicate columns

# Test cases for clean_transaction_data


def test_clean_transaction_data(sample_transaction_df):
    df = clean_transaction_data(sample_transaction_df)
    assert len(df.columns) == 3  # Should drop one column
    assert df.notna().all().all()  # Should have no null values

# Test cases for filter_payment_transactions


def test_filter_payment_transactions():
    df = pd.DataFrame({
        'TRANS. DATE': ['01/01/23', '02/01/23', '03/01/23'],
        'POSTING DATE': ['01/01/23', '02/01/23', '03/01/23'],
        'DESCRIPTION': ['Purchase', 'Payment', 'Purchase'],
        'AMOUNT BAHT': [Decimal('100.00'), Decimal('-200.00'), Decimal('300.00')]
    })
    # Convert the DataFrame to match the expected format
    # Drop the second column as per clean_transaction_data
    df = df.drop('POSTING DATE', axis=1)
    filtered_df = filter_payment_transactions(df)
    assert len(filtered_df) == 2  # Should remove payment transaction
    assert 'Payment' not in filtered_df['DESCRIPTION'].values

# Test cases for flip_amount_sign


def test_flip_amount_sign():
    df = pd.DataFrame({
        'AMOUNT': [100.00, -200.00, 300.00]
    })
    flipped_df = flip_amount_sign(df)
    assert (flipped_df['AMOUNT'] == [-100.00, 200.00, -300.00]).all()

# Test cases for save_to_csv


def test_save_to_csv(sample_transaction_df, tmp_path):
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    save_to_csv(sample_transaction_df, str(output_dir), "test.pdf")
    assert (output_dir / "test.csv").exists()

# Test cases for process_pdf


def test_process_pdf_invalid_file(tmp_path):
    # The function should not raise an exception but return None
    process_pdf("nonexistent.pdf", str(tmp_path), "nonexistent.pdf")
    # Verify no output file was created
    assert not (tmp_path / "nonexistent.csv").exists()


def test_process_pdf_valid_file(test_pdf_path, tmp_path):
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    process_pdf(test_pdf_path, str(output_dir), test_pdf_path)
    assert (output_dir / "sample_transactions.csv").exists()


def test_process_pdf_encrypted_file(encrypted_pdf_path, tmp_path):
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    # First try without password - should fail
    process_pdf(encrypted_pdf_path, str(output_dir), encrypted_pdf_path)
    assert not (output_dir / "encrypted_transactions.csv").exists()

    # Get the decrypted PDF bytes
    pdf_bytes = get_pdf_bytes(encrypted_pdf_path, 'test123')
    assert pdf_bytes is not None

    # Create a temporary file for the decrypted PDF
    temp_pdf = None
    try:
        # Create and write to temporary file
        temp_pdf = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
        temp_pdf.write(pdf_bytes)
        temp_pdf.close()  # Close the file to ensure all data is written

        # Process the decrypted PDF
        process_pdf(temp_pdf.name, str(output_dir), encrypted_pdf_path)
        assert (output_dir / "encrypted_transactions.csv").exists()

        # Verify CSV contents
        df = pd.read_csv(output_dir / "encrypted_transactions.csv")
        assert len(df) > 0
        assert 'TRANS. DATE' in df.columns
        assert 'DESCRIPTION' in df.columns
        assert 'AMOUNT BAHT' in df.columns

    finally:
        # Clean up the temporary file
        if temp_pdf and os.path.exists(temp_pdf.name):
            os.unlink(temp_pdf.name)

# Test cases for get_pdf_bytes


def test_get_pdf_bytes_nonexistent_file():
    assert get_pdf_bytes("nonexistent.pdf") is None


def test_get_pdf_bytes_valid_file(test_pdf_path):
    pdf_bytes = get_pdf_bytes(test_pdf_path)
    assert pdf_bytes is not None
    assert len(pdf_bytes) > 0


def test_get_pdf_bytes_encrypted_file(encrypted_pdf_path):
    # Test without password
    assert get_pdf_bytes(encrypted_pdf_path) is None

    # Test with incorrect password
    assert get_pdf_bytes(encrypted_pdf_path, 'wrongpass') is None

    # Test with correct password
    pdf_bytes = get_pdf_bytes(encrypted_pdf_path, 'test123')
    assert pdf_bytes is not None
    assert len(pdf_bytes) > 0

# Test cases for read_pdf_tables


def test_read_pdf_tables_invalid_file():
    assert read_pdf_tables("nonexistent.pdf") == []


def test_read_pdf_tables_valid_file(test_pdf_path):
    tables = read_pdf_tables(test_pdf_path)
    assert len(tables) > 0
    # Verify table structure
    df = tables[0].export_to_dataframe()
    assert len(df.columns) == 4
    # Convert column names to strings for comparison
    col_names = [str(col).upper() for col in df.columns]
    # Check if any column contains the expected keywords
    assert any('TRANS' in col or 'DATE' in col for col in col_names)
    assert any('DESCRIPTION' in col for col in col_names)
    assert any('AMOUNT' in col and 'BAHT' in col for col in col_names)

# Test cases for process_transaction_tables


def test_process_transaction_tables_empty(tmp_path):
    process_transaction_tables([], str(tmp_path), "test.pdf")
    # Should not raise any exceptions


def test_process_transaction_tables_invalid_data(tmp_path):
    invalid_df = pd.DataFrame({
        'INVALID': ['1', '2', '3']
    })
    process_transaction_tables([invalid_df], str(tmp_path), "test.pdf")
    # Should handle invalid data gracefully


def test_process_transaction_tables_valid_data(test_pdf_path, tmp_path):
    tables = read_pdf_tables(test_pdf_path)
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    process_transaction_tables(tables, str(output_dir), test_pdf_path)
    assert (output_dir / "sample_transactions.csv").exists()

    # Verify CSV contents
    df = pd.read_csv(output_dir / "sample_transactions.csv")
    assert len(df) > 0
    assert 'TRANS. DATE' in df.columns
    assert 'DESCRIPTION' in df.columns
    assert 'AMOUNT BAHT' in df.columns
