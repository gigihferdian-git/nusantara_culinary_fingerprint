Resep: OCR from page 187 - 1164

Kategori Masakan menurut jenis: 1165 - 1187

Kategori Masakan menurut bahan makanan: 1189 - 1215


*** STEP *** 
1_pdf_to_images 
required: pip install pdf2image
required: brew install poppler (terminal)


at json, there might be error on some pages 
to not get messed with it, remove the related-previous and the related-after json file 


dataset construction step: 
1. pdf to images (done)
2. images to json (done)
3. join and cleaning json (done)
4. data restructure json to tabular 
- table recipes: id, title_original, title_normalized, source_page, region, category, ingredient_json, instruction 
- table ingredient_recipes: id, recipe_id, ingredient_group, ingredient_original_name, ingredient_normalized_name, ingredient_quantity, ingredient_unit 
5. eda, cleaning data and grouping 
6. publish dataset 

