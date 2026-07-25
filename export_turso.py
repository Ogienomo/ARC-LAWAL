import os
import sys
from libsql_client import create_client_sync


def main() -> None:
    db_url = os.getenv("TURSO_DATABASE_URL") or "libsql://turso-db-create-inclusive-research-ogienomo.aws-eu-west-1.turso.io"
    auth_token = os.getenv("TURSO_AUTH_TOKEN")

    if not db_url or not auth_token:
        print("Missing TURSO_DATABASE_URL or TURSO_AUTH_TOKEN environment variables.")
        sys.exit(1)

    print(f"Connecting to {db_url}")
    client = create_client_sync(url=db_url, auth_token=auth_token)

    try:
        result = client.execute("SELECT 1 AS ok")
        print(result)
    except Exception as exc:
        print(f"Connection failed: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
