import os
from pdf2image import convert_from_path

# --- CONFIGURATION ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Setup paths relative to the script location
PDF_PATH = os.path.join(BASE_DIR, "mustika_rasa.pdf")
OUTPUT_FOLDER = os.path.join(BASE_DIR, "book_pages")

# PAGE RANGE SETTINGS
START_PAGE = 1001      
END_PAGE = 1164      
POPPLER_PATH = None

if os.name != 'nt':
    POPPLER_PATH = None

def convert_pdf(pdf_path, output_folder):
    # Create output folder if it doesn't exist
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
        print(f"Created folder: {output_folder}")

    print(f"Starting conversion of {pdf_path}")
    print(f"Range: Page {START_PAGE} to {END_PAGE if END_PAGE else 'End'}")
    
    try:
        # We pass first_page and last_page here
        images = convert_from_path(
            pdf_path, 
            dpi=300, 
            first_page=START_PAGE, 
            last_page=END_PAGE, 
            poppler_path=POPPLER_PATH
        )
    except Exception as e:
        print(f"Error: {e}")
        return

    print(f"✅ Extracted {len(images)} pages. Saving files...")

    # Save each page as an image
    for i, image in enumerate(images):
        # Calculate actual page number based on start page
        current_page_num = START_PAGE + i
        
        # Format filename like: page_0001.jpg
        filename = f"page_{str(current_page_num).zfill(4)}.jpg"
        save_path = os.path.join(output_folder, filename)
        
        image.save(save_path, "JPEG")
        
        # Print progress
        print(f"Saved: {filename}")

    print("Conversion Complete!")

if __name__ == "__main__":
    convert_pdf(PDF_PATH, OUTPUT_FOLDER)