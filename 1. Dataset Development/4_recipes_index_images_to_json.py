import os
import json
import time
import io
import re
from PIL import Image
from google import genai
from google.genai import types

# --- CONFIGURATION ---
API_KEY = "[ENCRYPTION_KEY]" # ⚠️ PASTE KEY HERE
START_PAGE = 1166
END_PAGE = 1187
MODEL_ID = "gemini-flash-latest"

# --- PATHS ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_FOLDER = os.path.join(BASE_DIR, "images2_recipes_index")
OUTPUT_FOLDER = os.path.join(BASE_DIR, "json_output2_recipes_index")

client = genai.Client(api_key=API_KEY)

# --- STRICTER PROMPT ---
SYSTEM_PROMPT_TEMPLATE = """
You are a Data Engineer converting a book index.
The image is a multi-column index page from an Indonesian cookbook.

CONTEXT:
This page is a CONTINUATION. The previous page ended with the category: "{PREVIOUS_CATEGORY}".
Most likely, this page starts with recipes belonging to "{PREVIOUS_CATEGORY}".

YOUR TASK:
1. Extract every recipe name.
2. Assign a Category to each recipe.
   - If you see a NEW BOLD HEADER (e.g. "SAMBAL"), switch to that category.
   - If there is NO HEADER at the top, use "{PREVIOUS_CATEGORY}".

OUTPUT FORMAT (Strict JSON):
{
  "last_active_category": "The category valid at the very bottom of this page",
  "mappings": [
    { "recipes_original_name": "Recipe Name", "category": "Category Name" }
  ]
}
"""

def pil_to_bytes(img):
    buf = io.BytesIO()
    img.save(buf, format='JPEG')
    return buf.getvalue()

def process_page_with_state(image_path, page_num, previous_category):
    retries = 0
    max_retries = 3
    
    current_prompt = SYSTEM_PROMPT_TEMPLATE.replace("{PREVIOUS_CATEGORY}", previous_category)

    while retries < max_retries:
        try:
            print(f"   ...sending to Gemini (Attempt {retries+1})...")
            
            img = Image.open(image_path)
            image_bytes = pil_to_bytes(img)

            response = client.models.generate_content(
                model=MODEL_ID,
                contents=[
                    types.Content(
                        role="user",
                        parts=[
                            types.Part.from_text(text=current_prompt),
                            types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg") 
                        ]
                    )
                ]
            )
            
            # --- CLEANING ---
            raw_text = response.text
            if not raw_text:
                raise ValueError("Empty response")
                
            cleaned_text = raw_text.replace("```json", "").replace("```", "").strip()
            
            # Extract JSON block safely
            start = cleaned_text.find('{')
            end = cleaned_text.rfind('}')
            if start != -1 and end != -1:
                cleaned_text = cleaned_text[start:end+1]

            data = json.loads(cleaned_text)
            
            # --- PYTHON FALLBACK (The Fix) ---
            # If Gemini returned null/empty category, force the previous one
            for item in data.get('mappings', []):
                if not item.get('category'):
                    item['category'] = previous_category
            
            # Ensure last_active_category exists
            if not data.get('last_active_category'):
                 # If list is not empty, use the last item's category
                if data.get('mappings'):
                    data['last_active_category'] = data['mappings'][-1]['category']
                else:
                    # If page was empty, carry over previous
                    data['last_active_category'] = previous_category

            return data

        except Exception as e:
            print(f"   ⚠️ Error: {e}")
            retries += 1
            time.sleep(5)
    
    print(f"   ❌ Failed to process page {page_num}")
    return None

def main():
    if not os.path.exists(OUTPUT_FOLDER):
        os.makedirs(OUTPUT_FOLDER)

    all_files = sorted([f for f in os.listdir(INPUT_FOLDER) if f.endswith(('.jpg', '.png'))])
    
    # Sort files by page number to ensure order
    sorted_files = []
    for filename in all_files:
        match = re.search(r'page_(\d+)', filename)
        if match:
            p = int(match.group(1))
            if START_PAGE <= p <= END_PAGE:
                sorted_files.append((p, filename))
    sorted_files.sort(key=lambda x: x[0])

    # --- STATE TRACKING ---
    # Start with "Unknown" or explicitly set "MAKANAN UTAMA" if you know Page 1166 starts with it.
    current_state_category = "MAKANAN UTAMA" 

    print(f"🚀 Starting v3 Extraction: Page {START_PAGE} to {END_PAGE}...")

    for page_num, filename in sorted_files:
        json_filename = filename.replace(".jpg", ".json").replace(".png", ".json")
        save_path = os.path.join(OUTPUT_FOLDER, json_filename)

        print(f"📄 {filename} | Context: '{current_state_category}'")
        
        # If exists, load it to update state and skip
        if os.path.exists(save_path):
            try:
                with open(save_path, 'r') as f:
                    saved = json.load(f)
                    current_state_category = saved.get('last_active_category', current_state_category)
                print(f"   ⏩ Loaded state: '{current_state_category}'")
                continue
            except:
                pass 

        # Process
        data = process_page_with_state(
            os.path.join(INPUT_FOLDER, filename), 
            page_num, 
            current_state_category
        )
        
        if data:
            # Save
            with open(save_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            # Update State
            current_state_category = data['last_active_category']
            print(f"   ✅ Saved. New Context: '{current_state_category}'")
        
        time.sleep(2)

if __name__ == "__main__":
    main()