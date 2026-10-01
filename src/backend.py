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
# to find the XDG folders for app, inclduding weird ones like app, apprc, app.conf
def map_xdg_paths(app_name: str) -> list[Path]:
    #/home/localusername
    home = Path.home()

    base_dirs = [
        home / ".config",
        home / ".local" / "share",
        home / ".cache"
    ]
    
    found_paths = []
    for base in base_dirs:
        if not base.exists():
            continue
        for item in base.iterdir():
            name = item.name.lower()
            target = app_name.lower()
            
            # guideline for matches:
            # app, apprc, app.conf, app.ini, app-server, app_data
            if name == target or \
               name == f"{target}rc" or \
               name.startswith(f"{target}.") or \
               name.startswith(f"{target}-") or \
               name.startswith(f"{target}_"):
                
                found_paths.append(item)
                
    return found_paths

# check if folder exists, calc folder size and retunrs a dictionary of the contents
def inspect_folder_tree(target_path: Path) -> dict | None:
    if not target_path.exists():
        return None
        
    path_data = {
        "target_path": str(target_path),
        "is_directory": target_path.is_dir(),
        "size_mb": 0.0,
        "files": []
    }
    
    total_bytes = 0
    
    # .rglob('*') rec func for findng all files
    if target_path.is_file():
        # files like ~/.config/elisarc
        file_size = target_path.stat().st_size
        total_bytes += file_size
        path_data["files"].append({
            "path": str(target_path),
            "size_kb": round(file_size / 1024, 2)
        })
    else:
        # folders like ~/.cache/elisa
        for item in target_path.rglob('*'):
            if item.is_file(): 
                file_size = item.stat().st_size
                total_bytes += file_size
                path_data["files"].append({
                    "path": str(item),
                    "size_kb": round(file_size / 1024, 2)
                })
            
    # return in mb
    path_data["dir_size_mb"] = round(total_bytes / (1024 * 1024), 2)
    
    return path_data

# main function to return data for gui
def scan_app_leftovers(app_name: str) -> dict:
    final_data = {
        "app_name": app_name,
        "total_size_mb": 0.0,
        "paths": []
    }
    # get xdg paths
    paths_to_check = map_xdg_paths(app_name)
    for path in paths_to_check:
        path_info = inspect_folder_tree(path)
        
        if path_info:
            final_data["paths"].append(path_info)
            final_data["total_size_mb"] += path_info["dir_size_mb"]
            
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