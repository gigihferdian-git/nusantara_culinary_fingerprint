import os
import json
import re

# --- CONFIGURATION ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_FOLDER = os.path.join(BASE_DIR, "json_output1_recipes_detail")
OUTPUT_FILE = os.path.join(BASE_DIR, "mustika_rasa_full.json")

def get_page_number(filename):
    match = re.search(r'page_(\d+)', filename)
    return int(match.group(1)) if match else 99999

def load_and_fix_ids(folder_path):
    """
    Loads all JSONs, sorts them by page number, and 
    REWRITES the recipe_id based on the filename to ensure accuracy.
    """
    all_files = sorted(
        [f for f in os.listdir(folder_path) if f.endswith(".json")],
        key=get_page_number
    )
    
    linear_recipes = []
    
    print(f"📚 Reading {len(all_files)} files...")

    for filename in all_files:
        page_num = get_page_number(filename)
        file_path = os.path.join(folder_path, filename)
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                # REWRITE ID LOGIC
                # We trust the filename (page_203.json) more than the AI's internal guess
                for index, recipe in enumerate(data):
                    # Create ID like: MR_203_01, MR_203_02
                    new_id = f"MR_{page_num}_{str(index + 1).zfill(2)}"
                    recipe['recipe_id'] = new_id
                    recipe['_source_page'] = page_num # Keep track for debugging
                    
                    linear_recipes.append(recipe)
                    
        except Exception as e:
            print(f"❌ Error reading {filename}: {e}")

    return linear_recipes

def is_continuation(prev, curr):
    """
    FORCE MERGE LOGIC:
    If 'curr' says "Lanjutan" and 'prev' is incomplete, merge them 
    regardless of what 'prev' is named.
    """
    if not prev or not curr:
        return False

    # 1. Check if previous recipe is incomplete (No instructions)
    prev_instructions = prev.get('instructions', [])
    prev_incomplete = not prev_instructions or len(prev_instructions) == 0
    
    # 2. Safe Title Access (Handle None)
    curr_title = (curr.get('title_normalized') or "").lower()
    prev_title = (prev.get('title_normalized') or "").lower()

    # 3. Detect "Continued" Keywords
    # These are the "Magic Words" that trigger a forced merge
    force_merge_keywords = ["lanjutan", "continued", "sambungan", "(continued)", "(lanjutan)"]
    is_explicit_continuation = any(keyword in curr_title for keyword in force_merge_keywords)

    # 4. Check Page Adjacency (Must be next page or same page)
    try:
        page_diff = curr.get('_source_page', 999) - prev.get('_source_page', 0)
        is_next_page = page_diff == 1 or page_diff == 0
    except:
        is_next_page = False 

    # --- DECISION LOGIC ---
    if prev_incomplete and is_next_page:
        # RULE: If the new title explicitly says "Lanjutan", WE MERGE.
        # We ignore the fact that 'Kintuk' != 'Ayam Masak Santan'.
        if is_explicit_continuation:
            print(f"   ⚠️ Force Merging: '{prev_title}' -> '{curr_title}' (Detected 'Lanjutan')")
            return True
            
        # Fallback: If titles happen to match anyway
        clean_curr = curr_title.replace("(lanjutan)", "").replace("(continued)", "").strip()
        if clean_curr and (clean_curr in prev_title or prev_title in clean_curr):
            return True

    return False

def merge_recipes(head, tail):
    """
    Merges 'tail' into 'head'.
    Handles cases where lists might be None (null) instead of empty [].
    """
    print(f"   🧵 Stitching: {head.get('title_normalized')} + {tail.get('title_normalized')}")
    
    # 1. Merge Ingredients
    # Check if tail has ingredients to add
    if tail.get('ingredient_groups'):
        # Ensure head has a valid list to append to
        if head.get('ingredient_groups') is None:
            head['ingredient_groups'] = []
        
        head['ingredient_groups'].extend(tail['ingredient_groups'])
        
    # 2. Merge Instructions
    # Check if tail has instructions to add
    if tail.get('instructions'):
        # Ensure head has a valid list to append to
        if head.get('instructions') is None:
            head['instructions'] = []
            
        head['instructions'].extend(tail['instructions'])
        
    return head

def main():
    # 1. Load everything into one long list with corrected IDs
    raw_list = load_and_fix_ids(INPUT_FOLDER)
    
    if not raw_list:
        print("❌ No data found.")
        return

    final_recipes = []
    
    # 2. The Stitching Loop
    # We hold the 'current' recipe in a buffer. If the next one is a continuation,
    # we merge it into buffer. If not, we save buffer and move on.
    
    buffer = raw_list[0]
    
    for i in range(1, len(raw_list)):
        next_recipe = raw_list[i]
        
        if is_continuation(buffer, next_recipe):
            # MERGE
            buffer = merge_recipes(buffer, next_recipe)
        else:
            # SAVE & RESET
            final_recipes.append(buffer)
            buffer = next_recipe
            
    # Save the last one remaining in buffer
    final_recipes.append(buffer)
    
    # 3. Write to Disk
    print(f"\n✨ Processed {len(raw_list)} raw fragments.")
    print(f"✅ Final Dataset: {len(final_recipes)} unique recipes.")
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(final_recipes, f, indent=2, ensure_ascii=False)
        
    print(f"💾 Saved to: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()