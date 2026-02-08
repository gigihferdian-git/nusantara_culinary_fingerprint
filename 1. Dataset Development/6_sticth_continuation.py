import os
import json
import re
import pandas as pd

# --- CONFIGURATION ---
# Use os.getcwd() for compatibility with Jupyter (.ipynb)
try:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
except NameError:
    BASE_DIR = os.getcwd()

RAW_INPUT = os.path.join(BASE_DIR, "raw_mustika_rasa_full.json")
FINAL_OUTPUT = os.path.join(BASE_DIR, "mustika_rasa_full_cleaned.json")

def is_continuation(prev, curr):
    """
    Detects if 'curr' is a tail fragment of 'prev'.
    Triggers on 'lanjut', 'continu', or when previous instructions are missing.
    """
    if not prev or not curr:
        return False, None

    # Metadata extraction
    curr_title_orig = (curr.get('title_original') or "").lower()
    curr_title_norm = (curr.get('title_normalized') or "").lower()
    
    # Page sequence check
    page_diff = curr.get('_source_page', 999) - prev.get('_source_page', 0)
    is_adjacent = (0 <= page_diff <= 2)
    
    if not is_adjacent:
        return False, None

    # Trigger 1: Keywords in title
    fragment_keywords = ["continu", "lanjut", "sambung", "untitled",'fragment', 'cont.']
    is_explicit_fragment = any(kw in curr_title_orig or kw in curr_title_norm for kw in fragment_keywords)

    # Trigger 2: Previous state check (Empty or placeholder instructions)
    prev_instr_list = prev.get('instructions') or []
    prev_instr_text = " ".join(map(str, prev_instr_list)).lower()
    is_prev_incomplete = (
        len(prev_instr_list) == 0 or 
        "incomplete" in prev_instr_text or 
        "missing" in prev_instr_text or
        "continue" in prev_instr_text
    )
    list_id_to_stitch = ['MR_201_01','MR_276_01','MR_300_01','MR_310_01','MR_348_01','MR_432_01','MR_434_01','MR_561_01','MR_613_01','MR_715_01','MR_740_01','MR_748_01','MR_857_01','MR_861_01','MR_893_01','MR_980_01','MR_1098_01']

    if is_explicit_fragment and is_prev_incomplete:
        return True, "Keyword + Empty Instructions"
    if is_explicit_fragment:
        return True, "Explicit Keyword"
    if curr.get('recipe_id', '') in list_id_to_stitch:
        return True, "Force Stich"
    #if is_prev_incomplete and curr.get('recipe_id', '').endswith('_01'):
    #    return True, "First item on page after incomplete"
        
    return False, None

def merge_recipes(head, tail):
    """
    Surgically stitches tail into head.
    - Filters out 'inferred' ingredients.
    - Merges bumbu/utama groups if they exist in both.
    - Replaces placeholders with real instructions.
    """
    # Create a deep copy to avoid mutating original list during processing
    head = json.loads(json.dumps(head))
    
    # 1. Ingredient Merging & Filtering
    head_groups = head.get('ingredient_groups', []) or []
    tail_groups = tail.get('ingredient_groups', []) or []

    for t_group in tail_groups:
        g_name = (t_group.get('group_name') or "").lower()
        
        # RULE: Skip if group_name contains 'inferred'
        if "inferred" in g_name:
            continue
            
        # RULE: Skip individual ingredients containing 'inferred'
        t_ingredients = [
            ing for ing in t_group.get('ingredients', [])
            if "inferred" not in (ing.get('original_text') or "").lower()
        ]
        
        if not t_ingredients:
            continue

        # Check for existing group to merge into
        target_group = None
        if any(name in g_name for name in ["utama", "bumbu"]):
            for h_group in head_groups:
                if h_group.get('group_name', '').lower() == g_name:
                    target_group = h_group
                    break
        
        if target_group:
            target_group['ingredients'].extend(t_ingredients)
        else:
            # Add as a new group
            new_group = t_group.copy()
            new_group['ingredients'] = t_ingredients
            head_groups.append(new_group)

    head['ingredient_groups'] = head_groups

    # 2. Instruction Replacement
    t_instructions = tail.get('instructions', []) or []
    h_instructions = head.get('instructions', []) or []
    
    # Check if head instruction is a placeholder
    is_placeholder = any("continue" in str(line).lower() for line in h_instructions)
    
    if t_instructions:
        if not h_instructions or is_placeholder:
            head['instructions'] = t_instructions
        else:
            # If both have content, we append tail to head
            head['instructions'].extend(t_instructions)

    return head

def main():
    if not os.path.exists(RAW_INPUT):
        print(f"❌ File not found: {RAW_INPUT}")
        return

    with open(RAW_INPUT, 'r', encoding='utf-8') as f:
        raw_list = json.load(f)

    if not raw_list:
        print("❌ Raw list is empty.")
        return

    final_recipes = []
    stitch_log = []
    
    # Start with the first recipe
    buffer = raw_list[0]

    for i in range(1, len(raw_list)):
        next_item = raw_list[i]
        
        should_stitch, reason = is_continuation(buffer, next_item)
        
        if should_stitch:
            # LOGGING FOR DATAFRAME
            stitch_log.append({
                "Head_ID": buffer['recipe_id'],
                "Tail_ID": next_item['recipe_id'],
                "Reason": reason
            })
            # PERFORM STITCH
            buffer = merge_recipes(buffer, next_item)
        else:
            # SAVE CURRENT BUFFER AND MOVE TO NEXT
            final_recipes.append(buffer)
            buffer = next_item
            
    # Don't forget the final buffer
    final_recipes.append(buffer)

    # OUTPUT RESULTS
    with open(FINAL_OUTPUT, 'w', encoding='utf-8') as f:
        json.dump(final_recipes, f, indent=2, ensure_ascii=False)
    
    # PRINT SUMMARY
    df_log = pd.DataFrame(stitch_log)
    print(f"✅ Processed {len(raw_list)} fragments into {len(final_recipes)} recipes.")
    print(f"🧵 Total Stitches: {len(stitch_log)}")
    
    if not df_log.empty:
        print("\n--- Stitching Preview ---")
        print(df_log.head(10).to_string(index=False))

if __name__ == "__main__":
    main()