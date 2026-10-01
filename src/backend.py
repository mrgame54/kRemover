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

# ====================================================
# TESTING BLOCK | Will be removed but works for now!!!
# ====================================================
if __name__ == "__main__":
    test_app = "app"
    print(f"Testing '{test_app}'")
    
    paths_to_check = map_xdg_paths(test_app)
    
    for path in paths_to_check:
        print(f"Generated Path: {path}")