#!/bin/bash

# Interactive PDF Table Processor Launcher
# This script launches the Streamlit-based interactive interface

echo "🚀 Starting Interactive PDF Table Processor..."
echo ""

# Check if Poppler is installed (required for pdf2image)
if ! command -v pdftoppm &> /dev/null; then
    echo "⚠️  Warning: Poppler is not installed!"
    echo "   Poppler is required for PDF to image conversion."
    echo ""
    echo "   Install it with:"
    echo "   - macOS:         brew install poppler"
    echo "   - Ubuntu/Debian: sudo apt-get install poppler-utils"
    echo ""
    read -p "   Do you want to continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check if streamlit is installed
if ! command -v streamlit &> /dev/null; then
    echo "📦 Streamlit is not installed. Installing dependencies..."
    pip install -r requirements.txt
fi

echo "✅ Starting Streamlit app..."
echo ""

# Run the Streamlit app
streamlit run src/interactive_processor.py

