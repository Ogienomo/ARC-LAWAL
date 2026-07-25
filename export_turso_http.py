import json
import os
import sys
from pathlib import Path

import requests


def main() -> None:
    db_host = os.getenv("TURSO_DATABASE_URL")
    auth_token = os.getenv("TURSO_AUTH_TOKEN")

    if not db_host or not auth_token:
        print("Missing TURSO_DATABASE_URL or TURSO_AUTH_TOKEN environment variables.")
        sys.exit(1)

    url = f"https://{db_host}/v1/execute"
    headers = {
        "Authorization": f"Bearer {auth_token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    payload = {
        "stmt": {
            "sql": "SELECT 1 AS ok",
            "args": [],
        }
    }

    print(f"Requesting {url}")
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        print(f"Status: {response.status_code}")

        output_path = Path(__file__).with_name("exported_data.json")
        output_path.write_text(response.text, encoding="utf-8")
        print(f"Saved response to {output_path}")
        print(response.text[:2000])
    except Exception as exc:
        print(f"Request failed: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
