import json
import os

def show():
    target_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    json_path = os.path.join(target_dir, "Outputs", "static_analysis_bugs.json")
    if not os.path.exists(json_path):
        print("Json not found.")
        return
        
    with open(json_path, "r", encoding="utf-8") as f:
        bugs = json.load(f)
        
    by_type = {}
    for bug in bugs:
        by_type.setdefault(bug["type"], []).append(bug)
        
    for t, items in by_type.items():
        print(f"\n=================== {t} ({len(items)} items) ===================")
        # Show first 5 items of each type as example
        for item in items[:5]:
            print(f"File: {item['file']}:{item['line']}")
            print(f"Code: {item['code']}")
            print(f"Desc: {item['description']}")
            print("-" * 40)

if __name__ == "__main__":
    show()
