import argparse
import json
import time
import requests

COMMENT_URL = "https://api.pullpush.io/comment"
SUBMISSION_URL = "https://api.pullpush.io/topic"


def fetch_user_data(
    session: requests.Session,
    endpoint_url: str,
    username: str,
    batch_size: int = 100,
) -> list:
    items = []
    seen_ids = set()
    before = None

    print(f"Fetching data from {endpoint_url} (batch size: {batch_size})...")

    while True:
        params = {
            "author": username,
            "size": batch_size,
            "sort": "desc",
            "sort_type": "created_utc",
        }

        if before is not None:
            params["before"] = before

        if seen_ids:
            # Exclude recently seen IDs to avoid overlap at boundary timestamps
            recent_ids = list(seen_ids)[-50:]
            params["exclude_ids"] = ",".join(recent_ids)

        try:
            response = session.get(endpoint_url, params=params, timeout=15)

            if response.status_code != 200:
                print(
                    f"Warning: API returned status code {response.status_code}. Stopping fetch."
                )
                break

            payload = response.json()
            data = payload.get("data", [])

            # End of records
            if not data:
                break

            # Deduplicate by ID
            new_items = []
            for item in data:
                item_id = item.get("id")
                if item_id and item_id not in seen_ids:
                    seen_ids.add(item_id)
                    new_items.append(item)

            if not new_items:
                break

            items.extend(new_items)
            print(f"  Retrieved {len(items)} unique items so far...")

            # Check if we reached the last page (partial batch returned)
            if len(data) < batch_size:
                print("  Reached end of available records (batch size < requested).")
                break

            # Set 'before' to the timestamp of the oldest record in the batch
            oldest_utc = data[-1].get("created_utc")
            if oldest_utc is not None:
                before = int(oldest_utc)

            time.sleep(0.3)

        except requests.exceptions.RequestException as err:
            print(f"Request error occurred: {err}")
            break

    return items


def main():
    parser = argparse.ArgumentParser(
        description="Fetch Reddit user data via PullPush API."
    )
    parser.add_argument("username", type=str, help="Reddit username (without u/)")
    parser.add_argument(
        "-b",
        "--batch-size",
        type=int,
        default=100,
        help="Batch size (default: 100)",
    )
    parser.add_argument(
        "-o", "--output", type=str, default=None, help="Output JSON file name"
    )

    args = parser.parse_args()
    username = args.username.strip()
    batch_size = args.batch_size
    output_filename = args.output or f"{username}_reddit_data.json"

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) RedditDataExporter/1.0"
    })

    print(f"Starting data collection for user: '{username}'")

    comments = fetch_user_data(session, COMMENT_URL, username, batch_size=batch_size)
    submissions = fetch_user_data(
        session, SUBMISSION_URL, username, batch_size=batch_size
    )

    user_data = {
        "username": username,
        "data_counts": {
            "comments": len(comments),
            "submissions": len(submissions),
            "total": len(comments) + len(submissions),
        },
        "submissions": submissions,
        "comments": comments,
    }

    with open(output_filename, "w", encoding="utf-8") as f:
        json.dump(user_data, f, ensure_ascii=False, indent=2)

    print(
        f"\nDone! Total unique items: {user_data['data_counts']['total']} "
        f"({len(submissions)} submissions, {len(comments)} comments)."
    )
    print(f"Saved to: {output_filename}")


if __name__ == "__main__":
    main()
