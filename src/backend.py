import json
from pathlib import Path

# check how backend Output should look like
"""
TEMPLATE = {
    "app_name": "app",
    "total_size_mb": 0.0,
    "folders": [
        # all dictionaries for each XDG folder found
        {
            "target_dir": "/home/user/.config/app",
             "dir_size_mb": 0.0,
             "files": [
                 {"path": "/home/user/.config/app/config", "size_kb": 14.5}
                ]
            }
    ]
}
"""
# to find the XDG folders for app
def map_xdg_paths(app_name: str) -> list[Path]:
    #/home/localusername
    home = Path.home()

    expected_paths = [
        home / ".config" / app_name,
        home / ".local" / "share" / app_name,
        home / ".cache" / app_name
    ]
    
    return expected_paths

# check if folder exists, calc folder size and retunrs a dictionary of the contents
def inspect_folder_tree(target_path: Path) -> dict | None:
    if not target_path.exists() or not target_path.is_dir():
        return None
        
    folder_data = {
        "target_dir": str(target_path),
        "dir_size_mb": 0.0,
        "files": []
    }
    
    total_bytes = 0
    
    # .rglob('*') rec func for findng all files
    for item in target_path.rglob('*'):
        if item.is_file():
            file_size_bytes = item.stat().st_size
            total_bytes += file_size_bytes
            size_kb = file_size_bytes / 1024
            folder_data["files"].append({
                "path": str(item),
                "size_kb": round(size_kb, 2)
            })
            
    # return in mb
    folder_data["dir_size_mb"] = round(total_bytes / (1024 * 1024), 2)
    
    return folder_data

# main function to return data for gui
def scan_app_leftovers(app_name: str) -> dict:
    final_data = {
        "app_name": app_name,
        "total_size_mb": 0.0,
        "folders": []
    }
    # get xdg paths
    paths_to_check = map_xdg_paths(app_name)
    for path in paths_to_check:
        folder_info = inspect_folder_tree(path)
        
        if folder_info:
            final_data["folders"].append(folder_info)
            final_data["total_size_mb"] += folder_info["dir_size_mb"]
            
    final_data["total_size_mb"] = round(final_data["total_size_mb"], 2)
    
    return final_data

# ====================================================
# TESTING BLOCK | Will be removed but works for now!!!
# ====================================================
if __name__ == "__main__":
    # test different apps
    test_app = "openttd" 
    
    print(f" Scanning system for '{test_app}' leftovers")
    
    results = scan_app_leftovers(test_app)
    
    print(json.dumps(results, indent=4))