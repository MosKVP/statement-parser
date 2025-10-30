import streamlit as st
import tempfile
import os
import io
import PyPDF2
from pdf2image import convert_from_bytes, convert_from_path
from PIL import Image, ImageDraw, ImageFont
import pandas as pd
from docling.datamodel.base_models import InputFormat
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions
from pdf_processor import (
    get_pdf_bytes,
    clean_columns,
    validate_transaction_table_columns,
    clean_transaction_data,
    convert_data_types,
    save_to_csv
)


def convert_pdf_to_images(pdf_bytes: bytes) -> list:
    """
    Convert PDF bytes to a list of PIL Images.
    
    Args:
        pdf_bytes (bytes): PDF file content as bytes
        
    Returns:
        list: List of PIL Image objects, one per page
    """
    try:
        images = convert_from_bytes(pdf_bytes, dpi=150)
        return images
    except Exception as e:
        st.error(f"Error converting PDF to images: {str(e)}")
        return []


def extract_tables_with_metadata(pdf_path: str) -> tuple:
    """
    Extract tables from PDF using docling with their metadata (bounding boxes, page numbers).
    
    Args:
        pdf_path (str): Path to the PDF file
        
    Returns:
        tuple: (list of tables, document object)
    """
    try:
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
        
        st.info(f"📄 Found {len(doc.tables)} tables in {len(doc.pages)} pages")
        
        return doc.tables, doc
        
    except Exception as e:
        st.error(f"Error extracting tables: {str(e)}")
        return [], None


def draw_table_boxes_on_page(image: Image.Image, tables: list, page_num: int) -> Image.Image:
    """
    Draw bounding boxes around tables on a specific page.
    
    Args:
        image (PIL.Image): Page image
        tables (list): List of table objects from docling
        page_num (int): Current page number (0-indexed)
        
    Returns:
        PIL.Image: Image with table boxes drawn
    """
    # Create a copy of the image to draw on
    img_with_boxes = image.copy()
    draw = ImageDraw.Draw(img_with_boxes, 'RGBA')
    
    # Try to find tables for this page
    tables_drawn = 0
    
    for table_idx, table in enumerate(tables):
        if not hasattr(table, 'prov') or not table.prov:
            continue
            
        try:
            for prov in table.prov:
                # Try to get page number
                prov_page = None
                try:
                    if hasattr(prov, 'page_no'):
                        prov_page = prov.page_no
                    elif hasattr(prov, 'page'):
                        prov_page = prov.page
                    elif hasattr(prov, 'bbox') and hasattr(prov.bbox, 'page'):
                        prov_page = prov.bbox.page
                except:
                    pass
                
                # If we can't determine page, or if it matches, draw the box
                # This ensures we show something even if page detection fails
                if prov_page is None or prov_page == page_num:
                    if hasattr(prov, 'bbox'):
                        bbox = prov.bbox
                        
                        # Scale bbox coordinates to image dimensions
                        # docling returns normalized coordinates (0-1)
                        try:
                            x1 = bbox.l * image.width
                            y1 = bbox.t * image.height
                            x2 = bbox.r * image.width
                            y2 = bbox.b * image.height
                            
                            # Draw semi-transparent rectangle
                            draw.rectangle([x1, y1, x2, y2], 
                                         outline='red', 
                                         width=3,
                                         fill=(255, 0, 0, 30))
                            
                            # Draw table label
                            try:
                                font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 24)
                            except:
                                font = ImageFont.load_default()
                            
                            label = f"Table {table_idx + 1}"
                            draw.text((x1 + 5, y1 + 5), label, fill='red', font=font)
                            
                            tables_drawn += 1
                        except Exception as e:
                            # Skip this box if coordinates are invalid
                            pass
                    
                    # Only process first matching provenance per table
                    if prov_page == page_num:
                        break
                    
        except Exception as e:
            # Continue to next table if this one fails
            continue
    
    return img_with_boxes


def show_pdf_with_overlays(pdf_bytes: bytes, tables: list):
    """
    Display PDF pages with table overlays.
    
    Args:
        pdf_bytes (bytes): PDF content
        tables (list): List of table objects from docling
    """
    st.subheader("📑 PDF Preview with Table Detection")
    
    if not tables:
        st.warning("No tables detected in PDF")
        return
    
    # Debug info
    with st.expander("🔍 Debug: Table Detection Info", expanded=False):
        st.write(f"**Total tables detected:** {len(tables)}")
        for idx, table in enumerate(tables):
            st.write(f"**Table {idx + 1}:**")
            if hasattr(table, 'prov') and table.prov:
                for prov_idx, prov in enumerate(table.prov):
                    st.write(f"  Provenance {prov_idx + 1}:")
                    # Try to show all available attributes
                    prov_info = {}
                    for attr in ['page_no', 'page', 'bbox']:
                        if hasattr(prov, attr):
                            val = getattr(prov, attr)
                            prov_info[attr] = str(val)
                    st.json(prov_info)
            else:
                st.write("  No provenance data")
    
    # Convert PDF to images
    with st.spinner("Converting PDF to images..."):
        images = convert_pdf_to_images(pdf_bytes)
    
    if not images:
        st.error("Could not convert PDF to images. Make sure Poppler is installed.")
        st.info("To install Poppler:\n- macOS: `brew install poppler`\n- Ubuntu: `sudo apt-get install poppler-utils`")
        return
    
    st.success(f"✓ Loaded {len(images)} page(s)")
    
    # Show each page with overlays
    for page_num, image in enumerate(images):
        with st.expander(f"📄 Page {page_num + 1}", expanded=(page_num == 0)):
            # Draw table boxes
            image_with_boxes = draw_table_boxes_on_page(image, tables, page_num)
            
            # Display the image
            st.image(image_with_boxes, width='stretch')


def edit_table_interface(table_data: dict, table_idx: int) -> pd.DataFrame:
    """
    Display an editable interface for a single table.
    
    Args:
        table_data (dict): Dictionary containing table information
        table_idx (int): Index of the table
        
    Returns:
        pd.DataFrame: Edited dataframe
    """
    df = table_data['dataframe']
    
    st.markdown(f"### 📊 Table {table_idx + 1}")
    
    # Show table metadata
    col_meta1, col_meta2, col_meta3 = st.columns([1, 1, 2])
    with col_meta1:
        st.metric("Rows", len(df))
    with col_meta2:
        st.metric("Columns", len(df.columns))
    with col_meta3:
        st.metric("Page", table_data.get('page', 'Unknown'))
    
    # Column management - Quick menu style
    if len(df.columns) > 1:
        with st.expander("🗑️ Remove Columns", expanded=False):
            st.caption("Select columns to keep (uncheck to remove):")
            
            # Create checkboxes for each column
            cols_to_keep = []
            num_cols = 3  # Show 3 columns per row
            
            for i in range(0, len(df.columns), num_cols):
                cols = st.columns(num_cols)
                for j, col_name in enumerate(list(df.columns)[i:i+num_cols]):
                    with cols[j]:
                        # Convert column name to string and handle edge cases
                        col_str = str(col_name) if col_name is not None else ""
                        # Handle empty strings or whitespace-only strings
                        if not col_str or not col_str.strip():
                            col_label = f"Column {i+j+1}"
                        else:
                            col_label = col_str
                        
                        # Create a safe key by converting to string and replacing special chars
                        safe_key = col_str.replace(" ", "_").replace(".", "_").replace("(", "").replace(")", "")
                        if not safe_key.strip():
                            safe_key = f"col_{i}_{j}"
                        
                        if st.checkbox(
                            col_label,
                            value=True,
                            key=f"keep_col_{table_idx}_{i}_{j}_{safe_key}"
                        ):
                            cols_to_keep.append(col_name)
            
            # Update dataframe based on selection
            if len(cols_to_keep) < len(df.columns) and len(cols_to_keep) > 0:
                df = df[cols_to_keep]
                st.success(f"✓ Keeping {len(cols_to_keep)} column(s)")
    
    # Editable dataframe
    st.caption("💡 Click cells to edit • Use + to add rows • Use × to delete rows")
    edited_df = st.data_editor(
        df,
        num_rows="dynamic",  # Allow adding/removing rows
        width='stretch',
        key=f"table_editor_{table_idx}",
        hide_index=True
    )
    
    return edited_df


def process_selected_tables(selected_tables: list, output_dir: str, filename: str, 
                           date_format: str = "%d/%m/%y", flip_sign: bool = False, 
                           remove_commas: bool = True, show_sum: bool = True):
    """
    Process the selected and edited tables and save to CSV.
    
    Args:
        selected_tables (list): List of edited dataframes
        output_dir (str): Output directory
        filename (str): Output filename
        date_format (str): Date format string for parsing dates
        flip_sign (bool): Whether to multiply numeric columns by -1
        remove_commas (bool): Whether to remove commas from numeric output
        show_sum (bool): Whether to display sum of numeric columns
    """
    if not selected_tables:
        st.warning("No tables selected for processing")
        return
    
    try:
        # Use first table's columns as the standard for all tables
        reference_columns = list(selected_tables[0].columns)
        num_cols = len(reference_columns)
        
        # Select only the first N columns from each table and standardize column names
        aligned_tables = []
        for df in selected_tables:
            # Take first N columns (or pad if fewer)
            temp_df = df.iloc[:, :num_cols].copy() if len(df.columns) >= num_cols else df.copy()
            
            # If table has fewer columns, pad with empty columns
            if len(temp_df.columns) < num_cols:
                for i in range(len(temp_df.columns), num_cols):
                    temp_df.insert(i, f'_temp_col_{i}', '')
            
            # Rename all columns to match first table
            temp_df.columns = reference_columns
            aligned_tables.append(temp_df)
        
        # Combine all selected tables (they now all have the same column names)
        combined_df = pd.concat(aligned_tables, ignore_index=True)
        
        # Process date columns - try to parse ALL columns that look like dates
        date_columns_parsed = []
        for col in combined_df.columns:
            try:
                # Try to parse this column as date
                parsed = pd.to_datetime(
                    combined_df[col], 
                    format=date_format,
                    errors='coerce'
                )
                # If at least 50% of non-null values parsed successfully, treat as date column
                if parsed.notna().sum() / max(combined_df[col].notna().sum(), 1) > 0.5:
                    combined_df[col] = parsed
                    date_columns_parsed.append(col)
            except:
                pass
        
        if date_columns_parsed:
            st.info(f"✓ Parsed {len(date_columns_parsed)} date column(s): {', '.join(date_columns_parsed)}")
        
        # Convert string columns to numeric where possible (remove commas first)
        for col in combined_df.columns:
            if col not in date_columns_parsed:  # Don't process date columns
                try:
                    # Try to convert to numeric, removing commas first
                    cleaned = combined_df[col].astype(str).str.replace(',', '').str.strip()
                    numeric_values = pd.to_numeric(cleaned, errors='coerce')
                    # If at least 50% converted successfully, treat as numeric
                    if numeric_values.notna().sum() / max(cleaned.notna().sum(), 1) > 0.5:
                        combined_df[col] = numeric_values
                except:
                    pass
        
        # Get numeric columns (after conversion)
        numeric_columns = combined_df.select_dtypes(include=['number']).columns.tolist()
        
        # Flip signs if requested
        if flip_sign and len(numeric_columns) > 0:
            for col in numeric_columns:
                combined_df[col] = combined_df[col] * -1
            st.info(f"✓ Flipped signs for {len(numeric_columns)} numeric column(s): {', '.join(numeric_columns)}")
        
        # Show preview
        st.subheader("📋 Final Combined Data Preview")
        st.dataframe(combined_df, width='stretch')
        
        # Show sums if requested
        if show_sum and len(numeric_columns) > 0:
            st.markdown("#### 📊 Column Totals")
            cols = st.columns(len(numeric_columns))
            for idx, col in enumerate(numeric_columns):
                with cols[idx]:
                    total = combined_df[col].sum()
                    st.metric(str(col), f"{total:,.2f}")
        
        # Prepare for CSV export
        export_df = combined_df.copy()
        
        # Format numeric columns for CSV
        if len(numeric_columns) > 0:
            for col in numeric_columns:
                if remove_commas:
                    # Convert to string without thousand separators
                    export_df[col] = export_df[col].apply(lambda x: f"{x:.2f}" if pd.notna(x) else "")
                else:
                    # Keep as number (pandas will handle formatting)
                    pass
        
        # Save to CSV
        os.makedirs(output_dir, exist_ok=True)
        csv_path = os.path.join(output_dir, f"{os.path.splitext(filename)[0]}.csv")
        
        if remove_commas:
            # If removing commas, save as-is (already formatted as strings)
            export_df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        else:
            # If keeping numbers, let pandas format them
            export_df.to_csv(csv_path, index=False, encoding='utf-8-sig', float_format='%.2f')
        
        st.success(f"✅ Saved processed data to {csv_path}")
        
    except Exception as e:
        st.error(f"Error processing tables: {str(e)}")
        import traceback
        st.error(traceback.format_exc())


def main():
    """Main Streamlit application."""
    st.set_page_config(
        page_title="PDF Table Processor - Interactive",
        page_icon="📄",
        layout="wide"
    )
    
    st.title("📄 Interactive PDF Table Processor")
    st.markdown("Upload a PDF, review detected tables, select and edit them, then save the results.")
    
    # Sidebar for file upload and settings
    with st.sidebar:
        st.header("⚙️ Settings")
        
        uploaded_file = st.file_uploader(
            "Upload PDF",
            type=['pdf'],
            help="Upload a PDF file to process"
        )
        
        password = st.text_input(
            "Password (if encrypted)",
            type="password",
            help="Leave empty if PDF is not encrypted"
        )
        
        output_dir = st.text_input(
            "Output Directory",
            value="output",
            help="Directory where processed files will be saved"
        )
        
        st.divider()
        st.subheader("📊 Data Processing Options")
        
        # Date format configuration
        date_format = st.text_input(
            "Date Format",
            value="%d/%m/%y",
            help="Format of dates in the PDF (e.g., %d/%m/%y for 31/12/24, %Y-%m-%d for 2024-12-31)"
        )
        
        # Number column options
        st.markdown("**Number Columns:**")
        
        flip_sign = st.checkbox(
            "Flip signs (multiply by -1)",
            value=True,
            help="Convert positive to negative and vice versa"
        )
        
        remove_commas = st.checkbox(
            "Remove commas in output",
            value=True,
            help="Export numbers without thousand separators"
        )
        
        show_sum = st.checkbox(
            "Show column totals",
            value=True,
            help="Display sum of numeric columns"
        )
    
    # Initialize session state
    if 'pdf_processed' not in st.session_state:
        st.session_state.pdf_processed = False
    if 'tables_data' not in st.session_state:
        st.session_state.tables_data = []
    if 'edited_tables' not in st.session_state:
        st.session_state.edited_tables = {}
    
    # Main content area
    if uploaded_file is None:
        st.info("👈 Please upload a PDF file from the sidebar to begin")
        return
    
    # Show currently uploaded file
    st.info(f"📄 Selected file: **{uploaded_file.name}**")
    
    # Check if a different file was uploaded
    if 'current_filename' in st.session_state and st.session_state.current_filename != uploaded_file.name:
        st.warning(f"⚠️ New file detected! Previously processed: **{st.session_state.current_filename}**. Click 'Process PDF' to load the new file.")
    
    # Process PDF button
    if st.button("🔄 Process PDF", type="primary"):
        # Clear previous session state for new file
        st.session_state.edited_tables = {}
        st.session_state.tables_data = []
        st.session_state.pdf_processed = False
        if 'initial_selection_done' in st.session_state:
            del st.session_state.initial_selection_done
        
        with st.spinner("Processing PDF..."):
            # Get PDF bytes
            pdf_bytes = uploaded_file.read()
            
            # Check if PDF is encrypted
            try:
                pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes))
                is_encrypted = pdf_reader.is_encrypted
            except:
                is_encrypted = False
            
            # If encrypted but no password provided
            if is_encrypted and not password:
                st.error("🔒 **This PDF is encrypted!**")
                st.warning("Please enter the password in the sidebar and try again.")
                st.info("💡 Tip: Look for the 'Password (if encrypted)' field in the sidebar.")
                return
            
            # Handle encrypted PDFs
            if password:
                # Create a temporary file to check encryption
                with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_check:
                    tmp_check.write(pdf_bytes)
                    tmp_check.flush()
                    check_path = tmp_check.name
                
                # Decrypt the PDF
                pdf_bytes = get_pdf_bytes(check_path, password)
                os.unlink(check_path)  # Clean up check file
                
                if pdf_bytes is None:
                    st.error("Failed to decrypt PDF. Please check the password.")
                    return
                
                st.success("✅ PDF decrypted successfully")
            
            # Save the final PDF bytes to a clean temp file for docling
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
                tmp_file.write(pdf_bytes)
                tmp_file.flush()
                
                # Extract tables
                tables, doc = extract_tables_with_metadata(tmp_file.name)
                
                if tables:
                    # Store in session state
                    st.session_state.pdf_bytes = pdf_bytes
                    st.session_state.tables = tables
                    st.session_state.doc = doc
                    st.session_state.pdf_processed = True
                    st.session_state.temp_file = tmp_file.name
                    st.session_state.original_filename = uploaded_file.name
                    st.session_state.current_filename = uploaded_file.name  # Track current file
                    
                    # Prepare table data
                    st.session_state.tables_data = []
                    for idx, table in enumerate(tables):
                        df = table.export_to_dataframe(doc=doc)
                        df = clean_columns(df)
                        
                        # Get page number from provenance
                        page = idx  # Default to table index as page
                        if hasattr(table, 'prov') and table.prov:
                            try:
                                prov = table.prov[0]
                                # Try different attribute names for page
                                if hasattr(prov, 'page_no'):
                                    page = prov.page_no
                                elif hasattr(prov, 'page'):
                                    page = prov.page
                                elif hasattr(prov, 'bbox') and hasattr(prov.bbox, 'page'):
                                    page = prov.bbox.page
                                else:
                                    # Debug: print available attributes
                                    st.info(f"Table {idx + 1} provenance attributes: {dir(prov)}")
                            except Exception as e:
                                st.warning(f"Could not get page for table {idx + 1}: {str(e)}")
                        
                        st.session_state.tables_data.append({
                            'dataframe': df,
                            'page': page + 1,  # Convert to 1-indexed
                            'original_table': table
                        })
                    
                    st.success(f"✅ Extracted {len(tables)} tables from PDF")
                else:
                    st.warning("No tables found in the PDF")
                
                # Don't delete temp file yet, we need it for image conversion
    
    # Show results if processed
    if st.session_state.pdf_processed:
        # Show currently processed file
        st.success(f"✅ Currently processing: **{st.session_state.get('current_filename', 'Unknown file')}**")
        
        # Create tabs
        tab1, tab2, tab3 = st.tabs(["✏️ Select & Edit Tables", "📑 PDF Preview", "💾 Save Results"])
        
        with tab1:
            st.subheader("Select Tables to Process")
            
            if not st.session_state.tables_data:
                st.warning("No tables available")
            else:
                # Table selection
                selected_indices = []
                
                # Show each table with selection checkbox
                for idx, table_data in enumerate(st.session_state.tables_data):
                    with st.container():
                        col1, col2 = st.columns([0.1, 0.9])
                        
                        with col1:
                            # Check if table was previously selected
                            default_selected = idx in st.session_state.edited_tables
                            if 'initial_selection_done' not in st.session_state:
                                default_selected = True  # First time, select all
                            
                            selected = st.checkbox(
                                "Select",
                                key=f"select_{idx}",
                                value=default_selected
                            )
                        
                        with col2:
                            if selected:
                                selected_indices.append(idx)
                                edited_df = edit_table_interface(table_data, idx)
                                st.session_state.edited_tables[idx] = edited_df
                            else:
                                # Remove from edited tables if unselected
                                if idx in st.session_state.edited_tables:
                                    del st.session_state.edited_tables[idx]
                                
                                st.markdown(f"### 📊 Table {idx + 1} (Not Selected)")
                                st.dataframe(table_data['dataframe'], width='stretch')
                        
                        st.divider()
                
                # Mark that initial selection has been done
                st.session_state.initial_selection_done = True
                
                st.info(f"📊 {len(selected_indices)} table(s) selected for processing")
        
        with tab2:
            show_pdf_with_overlays(st.session_state.pdf_bytes, st.session_state.tables)
        
        with tab3:
            st.subheader("Save Processed Data")
            
            # Get only the edited tables (which means they were selected in tab2)
            if not st.session_state.edited_tables:
                st.warning("⚠️ No tables selected. Please select tables in the '✏️ Select & Edit Tables' tab.")
            else:
                # Show preview of what will be saved
                st.info(f"📊 {len(st.session_state.edited_tables)} table(s) ready to save")
                
                # Preview combined data
                selected_dfs = list(st.session_state.edited_tables.values())
                
                # Use first table's columns as the standard
                if selected_dfs:
                    reference_columns = list(selected_dfs[0].columns)
                    num_cols = len(reference_columns)
                    
                    # Select only the first N columns from each table and standardize column names
                    aligned_dfs = []
                    for df in selected_dfs:
                        # Take first N columns (or pad if fewer)
                        temp_df = df.iloc[:, :num_cols].copy() if len(df.columns) >= num_cols else df.copy()
                        
                        # If table has fewer columns, pad with empty columns
                        if len(temp_df.columns) < num_cols:
                            for i in range(len(temp_df.columns), num_cols):
                                temp_df.insert(i, f'_temp_col_{i}', '')
                        
                        # Rename all columns to match first table
                        temp_df.columns = reference_columns
                        aligned_dfs.append(temp_df)
                    
                    # Combine all tables (they now all have the same column names)
                    combined_preview = pd.concat(aligned_dfs, ignore_index=True)
                else:
                    combined_preview = pd.DataFrame()
                
                # Process preview data to show with transformations
                preview_df = combined_preview.copy()
                
                # Convert numeric columns (same logic as in save)
                date_columns_parsed = []
                for col in preview_df.columns:
                    try:
                        parsed = pd.to_datetime(preview_df[col], format=date_format, errors='coerce')
                        if parsed.notna().sum() / max(preview_df[col].notna().sum(), 1) > 0.5:
                            preview_df[col] = parsed
                            date_columns_parsed.append(col)
                    except:
                        pass
                
                # Convert strings to numeric
                for col in preview_df.columns:
                    if col not in date_columns_parsed:
                        try:
                            cleaned = preview_df[col].astype(str).str.replace(',', '').str.strip()
                            numeric_values = pd.to_numeric(cleaned, errors='coerce')
                            if numeric_values.notna().sum() / max(cleaned.notna().sum(), 1) > 0.5:
                                preview_df[col] = numeric_values
                        except:
                            pass
                
                # Get numeric columns and apply flip if enabled
                numeric_columns = preview_df.select_dtypes(include=['number']).columns.tolist()
                if flip_sign and len(numeric_columns) > 0:
                    for col in numeric_columns:
                        preview_df[col] = preview_df[col] * -1
                
                st.markdown("#### Preview of Combined Data")
                st.caption(f"Showing all {len(preview_df)} rows")
                st.dataframe(preview_df, width='stretch', height=400)
                
                # Show sums if enabled
                if show_sum and len(numeric_columns) > 0:
                    st.markdown("#### 📊 Column Totals (Preview)")
                    cols = st.columns(len(numeric_columns))
                    for idx, col in enumerate(numeric_columns):
                        with cols[idx]:
                            total = preview_df[col].sum()
                            st.metric(str(col), f"{total:,.2f}")
                
                if st.button("💾 Save to CSV", type="primary"):
                    process_selected_tables(
                        selected_dfs,
                        output_dir,
                        st.session_state.original_filename,
                        date_format=date_format,
                        flip_sign=flip_sign,
                        remove_commas=remove_commas,
                        show_sum=show_sum
                    )


if __name__ == '__main__':
    main()

