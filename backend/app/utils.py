# app/utils.py

def build_file_tree(flat_items):
    """
    Converts a flat list of GitHub paths into a nested tree structure 
    compatible with the frontend FileTree component.
    """
    tree = []
    
    for item in flat_items:
        path_parts = item["path"].split("/")
        current_level = tree
        
        for i, part in enumerate(path_parts):
            # Check if this part already exists in current_level
            existing_node = next((node for node in current_level if node["name"] == part), None)
            
            if existing_node:
                if "children" in existing_node:
                    current_level = existing_node["children"]
            else:
                # Determine if it's a file or folder based on the loop index
                is_last = (i == len(path_parts) - 1)
                new_node = {
                    "name": part,
                    "type": "file" if (is_last and item["type"] == "blob") else "folder"
                }
                
                if not is_last or item["type"] == "tree":
                    new_node["type"] = "folder"
                    new_node["children"] = []
                
                current_level.append(new_node)
                if "children" in new_node:
                    current_level = new_node["children"]
                    
    return tree