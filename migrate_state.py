import os
import json
from project_utils import migrate_json_states_to_sqlite

def main():
    # Ensure backend target is sqlite
    os.environ.setdefault("STATE_BACKEND", "sqlite")
    summary = migrate_json_states_to_sqlite()
    print(json.dumps(summary, indent=2))

if __name__ == "__main__":
    main()
