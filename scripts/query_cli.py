import argparse
import json

import requests


def main() -> None:
    parser = argparse.ArgumentParser(description="Query Enterprise KnowledgeOps AI API")
    parser.add_argument("--url", default="http://127.0.0.1:8000/api/v1/query", help="Query endpoint URL")
    parser.add_argument("--question", required=True, help="Natural language question")
    parser.add_argument("--limit", type=int, default=5, help="Max chunks to retrieve")
    args = parser.parse_args()

    payload = {"question": args.question, "limit": args.limit}
    response = requests.post(args.url, json=payload, timeout=120)
    print(json.dumps(response.json(), indent=2))


if __name__ == "__main__":
    main()
