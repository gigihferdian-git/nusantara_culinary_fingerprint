import os
import json
import time
import io
import re
from PIL import Image
from google import genai
from google.genai import types

# --- CONFIGURATION ---
API_KEY = "[ENCRYPTION_KEY]"  # Paste your key here

# PAGE RANGE
START_PAGE = 824
END_PAGE = 1187

# --- PATH SETUP ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_FOLDER = os.path.join(BASE_DIR, "book_pages")
OUTPUT_FOLDER = os.path.join(BASE_DIR, "json_output")

# --- CLIENT SETUP ---
client = genai.Client(api_key=API_KEY)
MODEL_ID = "gemini-flash-latest" 

SYSTEM_PROMPT = """
You are an expert Data Engineer digitizing the "Mustika Rasa" Indonesian cookbook (1967).
Extract the recipe data from the image into valid JSON.

CRITICAL RULES:
1. Output a list of objects. One page may contain multiple recipes.
2. 'original_text': Keep exactly as seen.
3. 'item_normalized': Modernize spelling (e.g. "djagung" -> "jagung").
4. 'unit': Standardize units.
5. If page has no recipes, return empty list: [].

REQUIRED JSON FORMAT:
[
  {
    "recipe_id": "MR_{PAGE_NUMBER}_{INDEX}",
    "title_original": "AREM AREM",
    "title_normalized": "Arem Arem",
    "region": "Region Name or null",
    "page_number": 123,
    "category": "Inferred Category",
    "ingredient_groups": [
      {
        "group_name": "utama",
        "original_header": "Bahan",
        "ingredients": [
          {
            "original_text": "beras 1 lt.",
            "item_original": "beras",
            "item_normalized": "beras",
            "quantity": 1.0,
            "unit": "liter"
          }
        ]
      }
    ],
    "instructions": ["Step 1...", "Step 2..."]
  }
]
"""

def clean_json_string(text):
    text = text.replace("```json", "").replace("```", "")
    return text.strip()

# --- NEW HELPER FUNCTION ---
def pil_to_bytes(img):
    """Converts PIL Image to raw bytes for Gemini"""
    buf = io.BytesIO()
    img.save(buf, format='JPEG')
    return buf.getvalue()

def process_page_with_retry(image_path, page_num):
    retries = 0
    max_retries = 3
    
    while retries < max_retries:
        try:
            print(f"   ...sending to Gemini (Attempt {retries+1})...")
            
            # 1. Load Image
            img = Image.open(image_path)
            
            # 2. Convert to Bytes (The Fix)
            image_bytes = pil_to_bytes(img)

            # 3. Send Request using `from_bytes`
            response = client.models.generate_content(
                model=MODEL_ID,
                contents=[
                    types.Content(
                        role="user",
                        parts=[
                            types.Part.from_text(text=SYSTEM_PROMPT.replace("{PAGE_NUMBER}", str(page_num))),
                            types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg") 
                        ]
                    )
                ]
            )
            
            cleaned_text = clean_json_string(response.text)
            return json.loads(cleaned_text)

        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "Quota" in error_msg:
                wait_time = 20 * (retries + 1)
                print(f"   ⚠️ Rate Limit Hit. Waiting {wait_time} seconds...")
                time.sleep(wait_time)
                retries += 1
            else:
                print(f"   ❌ Fatal Error on page {page_num}: {e}")
                return None
    
    print(f"   ❌ Failed after {max_retries} attempts.")
    return None

def main():
    if not os.path.exists(OUTPUT_FOLDER):
        os.makedirs(OUTPUT_FOLDER)

    all_files = sorted([f for f in os.listdir(INPUT_FOLDER) if f.endswith(('.jpg', '.png'))])
    
    print(f"🚀 Starting Batch (Fixed Bytes Version): Page {START_PAGE} to {END_PAGE}...")

    for filename in all_files:
        try:
            match = re.search(r'page_(\d+)', filename)
            if not match: continue
            page_num = int(match.group(1))
            
            if page_num < START_PAGE: continue
            if END_PAGE and page_num > END_PAGE: break 
        except ValueError:
            continue

        json_filename = filename.replace(".jpg", ".json").replace(".png", ".json")
        save_path = os.path.join(OUTPUT_FOLDER, json_filename)

        if os.path.exists(save_path):
            print(f"⏩ Skipping {filename} (Exists)")
            continue

        print(f"📄 Processing: {filename}")
        
        data = process_page_with_retry(os.path.join(INPUT_FOLDER, filename), page_num)
        
        if data is not None:
            with open(save_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"   ✅ Saved to {json_filename}")
        
        time.sleep(2)

    print("\n✨ Batch Complete!")

if __name__ == "__main__":
    main()