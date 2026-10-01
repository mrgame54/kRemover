import json
from pathlib import Path
import send2trash
import subprocess

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
# format helper funtion
def format_size(size_in_bytes: int) -> str:
    if size_in_bytes < 1024:
        return f"{size_in_bytes} B"
    elif size_in_bytes < 1024 * 1024:
        return f"{round(size_in_bytes / 1024, 2)} KB"
    elif size_in_bytes < 1024 * 1024 * 1024:
        return f"{round(size_in_bytes / (1024 * 1024), 2)} MB"
    else:
        return f"{round(size_in_bytes / (1024 * 1024 * 1024), 2)} GB"

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
        "size_str": "0 B",
        "raw_bytes": 0, 
        "files": []
    }
    
    total_bytes = 0

    # .rglob to rec find file size
    if target_path.is_file():
        try:
            file_size = target_path.stat().st_size
            total_bytes += file_size
            path_data["files"].append({
                "path": str(target_path),
                "size_str": format_size(file_size)
            })
        except PermissionError:
            pass 
    else:
        for item in target_path.rglob('*'):
            if item.is_file(): 
                try:
                    file_size = item.stat().st_size
                    total_bytes += file_size
                    path_data["files"].append({
                        "path": str(item),
                        "size_str": format_size(file_size)
                    })
                except PermissionError:
                    pass
            
    path_data["size_str"] = format_size(total_bytes)
    path_data["raw_bytes"] = total_bytes
    return path_data

# main function to return data for gui
def scan_app_leftovers(app_name: str) -> dict:
    final_data = {
        "app_name": app_name,
        "total_size_str": "0 B", 
        "paths": [] 
    }
    
    total_app_bytes = 0
    paths_to_check = map_xdg_paths(app_name)
    
    for path in paths_to_check:
        path_info = inspect_folder_tree(path)
        
        if path_info:
            final_data["paths"].append(path_info)
            total_app_bytes += path_info["raw_bytes"]
            
    # return with helper fnc
    final_data["total_size_str"] = format_size(total_app_bytes)
    return final_data

# move to trash, returns summary of succes and fail to gui
def move_to_trash(paths_to_delete: list) -> dict:
    results = {
        "success": [],
        "failed": []
    }
    
    for path in paths_to_delete:
        p = Path(path) if isinstance(path, str) else path
        
        if not p.exists():
            results["failed"].append({"path": str(p), "reason": "File already gone"})
            continue
            
        try:
            send2trash.send2trash(p)
            results["success"].append(str(p))
        except Exception as e:
            results["failed"].append({"path": str(p), "reason": str(e)})
        
    return results

# dnf remove via polkit, returns dictionary with termial output and succes status
def remove_rpm_package(app_name: str) -> dict:
    # sudo dnf remove -y app_name
    command = ["pkexec", "dnf", "remove", "-y", app_name]
    
    try:
        result = subprocess.run(command, capture_output=True, text=True)
        
        # 0 means it worked
        if result.returncode == 0:
            return {
                "success": True, 
                "message": f"Successfully removed {app_name}.", 
                "details": result.stdout
            }
        else:
            # user clicks cancle or DNF fails
            return {
                "success": False, 
                "message": "Uninstallation failed or was cancelled.", 
                "details": result.stderr
            }
            
    except FileNotFoundError:
        return {"success": False, "message": "Polkit (pkexec) is not installed.", "details": ""}
    except Exception as e:
        return {"success": False, "message": "An unexpected error occurred.", "details": str(e)}

# fetch installed packages 
def get_installed_packages() -> list:
    try:
        # rpm -qa lists all packages. --queryformat '%{NAME}\n' outputs just the names
        result = subprocess.run(["rpm", "-qa", "--queryformat", "%{NAME}\n"], 
                                capture_output=True, text=True)
        
        if result.returncode == 0:
            packages = result.stdout.splitlines()

            # filter 
            clean_list = [
                p for p in packages 
                if not p.startswith("lib") 
                and not p.endswith("-libs") 
                and not p.endswith("-devel")
                and not p.endswith("-common")
            ]
            
            return sorted(clean_list)
        return []
    except Exception:
        return []

# ====================================================
# TESTING BLOCK | Will be removed but works for now!!!
# ====================================================
if __name__ == "__main__":
    # test different apps
    test_app = "openttd" 
    
    print(f" Scanning system for '{test_app}' leftovers")
    
    results = scan_app_leftovers(test_app)
    
    print(json.dumps(results, indent=4))