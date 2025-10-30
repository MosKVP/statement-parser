# Quick Start Guide - Interactive PDF Processor

This guide will help you get started with the interactive PDF table processor in just a few minutes.

## Prerequisites Check

Before starting, make sure you have:

1. ✅ Python 3.6 or higher installed
2. ✅ Poppler installed (required for PDF to image conversion)

### Check if Poppler is installed:

```bash
# On macOS/Linux
which pdftoppm

# If nothing appears, install Poppler:
# macOS:
brew install poppler

# Ubuntu/Debian:
sudo apt-get install poppler-utils
```

## Quick Setup (5 minutes)

### Step 1: Install Dependencies

```bash
# Make sure you're in the project directory
cd statement-parser

# Install Python dependencies
pip install -r requirements.txt
```

### Step 2: Launch the Interactive UI

```bash
# Make the launcher executable (first time only)
chmod +x run_interactive.sh

# Launch the interactive interface
./run_interactive.sh
```

Or run directly:

```bash
streamlit run src/interactive_processor.py
```

This will open your default web browser with the interactive interface.

## Using the Interface

### 1️⃣ Upload Your PDF

- Click "Browse files" in the sidebar
- Select your PDF file
- If encrypted, enter the password in the sidebar

### 2️⃣ Process the PDF

- Click the "🔄 Process PDF" button
- Wait a few seconds while docling extracts tables

### 3️⃣ Review Table Detection

Go to the **"📑 PDF Preview"** tab to:

- See your PDF pages
- View red boxes showing where tables were detected
- Verify that all tables were found correctly

### 4️⃣ Select & Edit Tables

Go to the **"✏️ Select & Edit Tables"** tab to:

**Select Tables:**

- Check the boxes next to tables you want to keep
- Uncheck tables you want to ignore

**Edit Table Data:**

- Click any cell to edit its content
- Click the **"+"** button to add new rows
- Click the **"×"** button next to a row to delete it
- Use the dropdown to select and remove columns

### 5️⃣ Save Results

Go to the **"💾 Save Results"** tab to:

- Preview the combined data from all selected tables
- Click "💾 Save to CSV" to save the processed data
- Find your CSV file in the output directory

## Example Workflow

Here's a typical workflow:

1. **Upload**: Upload your bank statement PDF
2. **Review**: Check that all transaction tables are detected
3. **Clean**: Remove any incorrectly detected "tables" (headers, footers, etc.)
4. **Edit**: Fix any OCR errors or formatting issues
5. **Save**: Export clean data to CSV

## Troubleshooting

### "Error converting PDF to images"

**Solution**: Make sure Poppler is installed

```bash
# macOS
brew install poppler

# Ubuntu/Debian
sudo apt-get install poppler-utils
```

### "Streamlit is not installed"

**Solution**: Install dependencies

```bash
pip install -r requirements.txt
```

### Tables not detected correctly

**Solution**:

1. Try adjusting the PDF quality (scan resolution)
2. Use the interactive mode to manually select and edit tables
3. If tables are complex, you may need to edit the data manually

### Browser doesn't open automatically

**Solution**: Manually open the URL shown in the terminal (usually `http://localhost:8501`)

## Tips & Tricks

💡 **Tip 1**: Use the checkbox to quickly select/deselect all tables

💡 **Tip 2**: You can edit cells directly by clicking on them - great for fixing OCR errors

💡 **Tip 3**: The data editor supports keyboard navigation - use Tab, Arrow keys, and Enter

💡 **Tip 4**: If you make a mistake, just uncheck and re-check the table to reset it

💡 **Tip 5**: The interface auto-saves your selections - you can navigate between tabs freely

## What's Next?

- Try processing different types of PDFs
- Experiment with editing capabilities
- Check the full README.md for advanced features
- Use command-line mode for automated batch processing

## Need Help?

- Check the main [README.md](README.md) for detailed documentation
- Review error messages in the Streamlit interface
- Check terminal output for detailed error logs

## Going Back to Command Line Mode

If you prefer automated processing without manual review:

```bash
python src/pdf_processor.py input.pdf --output-dir output
```

See README.md for more command-line options.

---

**Happy Processing! 🎉**
