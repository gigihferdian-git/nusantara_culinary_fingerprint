import pandas as pd
import glob
import json
import os

# --- CONFIGURATION ---
# We use the exact folder name from your screenshot
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_FOLDER = os.path.join(BASE_DIR, "json_output2_recipes_index")
OUTPUT_FILE = os.path.join(BASE_DIR, "food_index.csv")

def main():
    # 1. Get all JSON files from the specific folder
    search_path = os.path.join(INPUT_FOLDER, "*.json")
    files = glob.glob(search_path)
    
    if not files:
        print(f"❌ No files found in: {INPUT_FOLDER}")
        print("   -> Please check if the folder exists and contains .json files.")
        return

    all_recipes = []
    print(f"📂 Found {len(files)} JSON files in '{INPUT_FOLDER}'. Processing...")

    for f in files:
        try:
            with open(f, 'r', encoding='utf-8') as file:
                content = json.load(file)
                
                # LOGIC: Handle different JSON structures (V3 vs V1)
                
                # Case A: Structure is { "last_active_category": "...", "mappings": [...] }
                if isinstance(content, dict) and "mappings" in content:
                    all_recipes.extend(content["mappings"])
                
                # Case B: Structure is just a list [...]
                elif isinstance(content, list):
                    all_recipes.extend(content)
                    
        except Exception as e:
            print(f"⚠️ Skipping {os.path.basename(f)} due to error: {e}")

    # 2. Save to CSV
    if all_recipes:
        df = pd.DataFrame(all_recipes)
        
        # Optional: Ensure we only keep relevant columns
        if 'recipes_original_name' in df.columns and 'category' in df.columns:
            df = df[['recipes_original_name', 'category']]
            
        # Optional: Remove duplicates
        df.drop_duplicates(subset=['recipes_original_name'], inplace=True)
        
        df.to_csv(OUTPUT_FILE, index=False)
        print(f"\n✅ Success! Saved {len(df)} rows to '{OUTPUT_FILE}'.")
        print(df.head())
    else:
        print("❌ No recipe data extracted. The JSON files might be empty.")

if __name__ == "__main__":
    main()