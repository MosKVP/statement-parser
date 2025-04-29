# Statement Parser

A Python utility for processing PDF bank statements, extracting transaction tables, and converting them to CSV format with data validation and cleaning.

## Features

- PDF decryption support for password-protected files
- Automatic table detection and extraction
- Transaction data validation and cleaning
- Payment transaction filtering
- Data type conversion (dates and amounts)
- Balance validation
- CSV output generation

## Requirements

- Python 3.6+
- Dependencies:
  - PyPDF2
  - pandas
  - docling
  - decimal

## Installation

1. Clone the repository:

```bash
git clone <repository-url>
cd pdf-processor
```

2. Install the required dependencies:

```bash
pip install -r requirements.txt
```

## Virtual Environment Setup

It's recommended to use a virtual environment to avoid conflicts with other Python projects. Here's how to set it up:

### On macOS/Linux:

1. Create a virtual environment:

```bash
python3 -m venv venv
```

2. Activate the virtual environment:

```bash
source venv/bin/activate
```

3. Install dependencies in the virtual environment:

```bash
pip install -r requirements.txt
```

4. To deactivate the virtual environment when you're done:

```bash
deactivate
```

### On Windows:

1. Create a virtual environment:

```bash
python -m venv venv
```

2. Activate the virtual environment:

```bash
.\venv\Scripts\activate
```

3. Install dependencies in the virtual environment:

```bash
pip install -r requirements.txt
```

4. To deactivate the virtual environment when you're done:

```bash
deactivate
```

## Testing

The project includes a comprehensive test suite to ensure the functionality of the PDF processor. Here's how to run the tests:

1. Make sure you're in the virtual environment:

```bash
source venv/bin/activate
```

2. Run the test suite:

```bash
python -m pytest tests/ -v
```

The test suite includes:

- Unit tests for individual functions
- Integration tests for PDF processing
- Tests for encrypted PDF handling
- Data validation tests

### Test Data

The test suite uses sample PDFs generated with test data. These PDFs are automatically created when running the tests. The test data includes:

- Sample transaction tables
- Encrypted PDFs
- Various transaction scenarios

To manually generate test PDFs:

1. Make sure you're in the virtual environment:

```bash
source venv/bin/activate
```

2. Run the test PDF generator:

```bash
python tests/test_data/create_test_pdf.py
```

This will create a sample PDF with test transaction data in the `tests/test_data` directory. 

To generate an encrypted test PDF:

```bash
python tests/test_data/create_encrypted_pdf.py
```

This will create an encrypted PDF with the same test data, using the password 'test123'.

### Test Coverage

To check test coverage:

```bash
python -m pytest --cov=src tests/ -v
```

This will show you the percentage of code covered by tests.

## Usage

### Basic Usage

```bash
python src/pdf_processor.py input.pdf
```

### With Password (for encrypted PDFs)

```bash
python src/pdf_processor.py input.pdf --password your_password
```

### Custom Output Directory

```bash
python src/pdf_processor.py input.pdf --output-dir custom_directory
```

## Command Line Arguments

- `input`: Path to the input PDF file (required)
- `--password`: Password for encrypted PDF files (optional)
- `--output-dir`: Directory for output files (default: 'output')

## Processing Steps

1. **PDF Decryption**: If the PDF is encrypted, it's decrypted using the provided password.
2. **Table Extraction**: Tables are automatically detected and extracted from the PDF.
3. **Data Validation**:
   - Validates table structure and column headers
   - Checks for correct date formats
   - Validates amount formats
   - Verifies transaction totals against starting and ending balances
4. **Data Cleaning**:
   - Removes rows with null values
   - Filters out invalid dates and amounts
   - Removes payment transactions (negative amounts with descriptions starting with 'Payment')
5. **Data Type Conversion**:
   - Converts dates to datetime format
   - Converts amounts to Decimal type
6. **Output Generation**: Saves processed data to CSV format in the specified output directory

## Output Format

The generated CSV file contains the following columns:

1. Transaction Date (datetime)
2. Description (text)
3. Amount (decimal)

## Error Handling

The processor includes comprehensive error handling for:

- File not found errors
- Incorrect PDF passwords
- Invalid table formats
- Data validation failures
- Balance verification errors

## Functions Reference

### Main Functions

- `main()`: Entry point, handles command line arguments and orchestrates processing
- `process_pdf(pdf_path, output_dir, original_path)`: Main processing function for PDF files
- `get_pdf_bytes(input_path, password)`: Handles PDF decryption and reading

### Data Processing Functions

- `clean_amount(amount_str)`: Cleans and formats amount strings
- `validate_transaction_table_columns(df, table_index)`: Validates table structure
- `convert_data_types(df)`: Converts column data types
- `validate_transaction_totals(df, starting_balance, ending_balance)`: Validates transaction totals
- `clean_transaction_data(df)`: Cleans and filters transaction data
- `filter_payment_transactions(df)`: Filters out payment transactions
- `save_to_csv(df, output_dir, original_filename)`: Saves results to CSV

## Example

```bash
# Process an encrypted PDF and save to custom directory
python src/pdf_processor.py statement.pdf --password mypass123 --output-dir processed_statements
```

## Limitations

- Only processes PDFs with consistent table formats
- Requires specific column headers in transaction tables
- Payment transactions are filtered out by default
- All amounts must be in the same currency (BAHT)

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

[Add your license information here]

## Author

[Add author information here]
