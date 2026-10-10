import json
import os

def list_sql():
    target_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    json_path = os.path.join(target_dir, "Outputs", "static_analysis_bugs.json")
    if not os.path.exists(json_path):
        print("Not found.")
        return
    with open(json_path, "r", encoding="utf-8") as f:
        bugs = json.load(f)
    sql_bugs = [b for b in bugs if b["type"] == "SQL Injection Risk / Query Formatting"]
    print(f"Total SQL bugs: {len(sql_bugs)}")
    for b in sql_bugs:
        print(f"{b['file']}:{b['line']} -> {b['code']}")
        print(f"  {b['description']}\n")

if __name__ == "__main__":
    list_sql()
