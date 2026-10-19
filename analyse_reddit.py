import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone


def parse_date(date_str: str) -> datetime:
    """Parse YYYY-MM-DD input into a UTC datetime object."""
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return dt.replace(tzinfo=timezone.utc)
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"Invalid date format: '{date_str}'. Use YYYY-MM-DD."
        )


def load_data(filepath: str) -> list:
    """Load JSON file and extract structured posts/comments with timestamps and subreddits."""
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    records = []

    for category in ["comments", "submissions"]:
        for item in data.get(category, []):
            utc_ts = item.get("created_utc")
            subreddit = item.get("subreddit") or item.get(
                "subreddit_name_prefixed", "Unknown"
            )

            # Strip leading r/ if present for consistent subreddit naming
            if subreddit.startswith("r/"):
                subreddit = subreddit[2:]

            if utc_ts:
                records.append({
                    "timestamp": float(utc_ts),
                    "type": category,
                    "subreddit": subreddit,
                })

    return records


def filter_records(
    records: list,
    from_date: datetime = None,
    to_date: datetime = None,
    day_filter: str = "all",
    utc_offset: int = 0,
) -> list:
    """Filter records based on date range, weekday/weekend, and timezone offset."""
    filtered = []

    for item in records:
        ts = item["timestamp"]
        dt_utc = datetime.fromtimestamp(ts, tz=timezone.utc)

        # Date range filtering (evaluated in UTC)
        if from_date and dt_utc < from_date:
            continue
        if to_date and dt_utc > to_date:
            continue

        # Local time evaluation for weekday/weekend classification
        dt_local = datetime.fromtimestamp(
            ts + (utc_offset * 3600), tz=timezone.utc
        )
        weekday = dt_local.weekday()  # Mon=0 ... Sun=6

        if day_filter == "weekdays" and weekday >= 5:
            continue
        if day_filter == "weekends" and weekday < 5:
            continue

        # Attach local datetime object to item
        item["dt_local"] = dt_local
        filtered.append(item)

    return filtered


def print_yearly_breakdown(records: list):
    """Display activity totals grouped by Year, Month, and Day of Week."""
    yearly_counts = Counter()
    monthly_counts = Counter()
    day_of_week_counts = Counter()

    days_map = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ]

    for item in records:
        dt = item["dt_local"]
        yearly_counts[dt.year] += 1
        monthly_counts[f"{dt.year}-{dt.month:02d}"] += 1
        day_of_week_counts[days_map[dt.weekday()]] += 1

    print("\n" + "=" * 50)
    print("=== YEARLY ACTIVITY BREAKDOWN ===")
    print("=" * 50)
    for year in sorted(yearly_counts.keys()):
        print(f"  {year}: {yearly_counts[year]:5d} posts/comments")

    print("\n--- Top 10 Active Months ---")
    for year_month, count in sorted(
        monthly_counts.items(), key=lambda x: x[1], reverse=True
    )[:10]:
        print(f"  {year_month}: {count:4d} items")

    print("\n--- Day-of-Week Distribution ---")
    for day in days_map:
        count = day_of_week_counts.get(day, 0)
        print(f"  {day:<10}: {count:4d} items")


def print_top_subreddits(records: list, top_n: int = 10):
    """Display most active subreddits broken down by comments vs submissions."""
    sub_counts = defaultdict(lambda: {"comments": 0, "submissions": 0})

    for item in records:
        sub = item["subreddit"]
        cat = item["type"]
        sub_counts[sub][cat] += 1

    # Sort subreddits by total activity
    sorted_subs = sorted(
        sub_counts.items(),
        key=lambda x: (x[1]["comments"] + x[1]["submissions"]),
        reverse=True,
    )

    print("\n" + "=" * 50)
    print(f"=== TOP {top_n} MOST ACTIVE SUBREDDITS ===")
    print("=" * 50)
    print(
        f"{'Subreddit':<25} | {'Comments':<10} | {'Submissions':<12} | {'Total':<6}"
    )
    print("-" * 62)

    for sub, counts in sorted_subs[:top_n]:
        comments = counts["comments"]
        submissions = counts["submissions"]
        total = comments + submissions
        print(
            f"r/{sub:<23} | {comments:<10} | {submissions:<12} | {total:<6}"
        )


def print_sleep_analysis(records: list, utc_offset: int, window_size: int = 6):
    """Display 24-hour histogram and quietest rolling window."""
    hours_counter = Counter(item["dt_local"].hour for item in records)

    min_activity = float("inf")
    best_window = (0, 0)

    for start_hour in range(24):
        total_activity = sum(
            hours_counter.get((start_hour + i) % 24, 0)
            for i in range(window_size)
        )
        if total_activity < min_activity:
            min_activity = total_activity
            best_window = (start_hour, (start_hour + window_size) % 24)

    print("\n" + "=" * 50)
    print(
        f"=== HOURLY POST DISTRIBUTION & SLEEP ANALYSIS (Offset: {utc_offset:+}h) ==="
    )
    print("=" * 50)

    max_count = max(hours_counter.values()) if hours_counter else 1
    for hour in range(24):
        count = hours_counter.get(hour, 0)
        bar = "█" * int((count / max_count) * 25) if count > 0 else ""
        print(f"  {hour:02d}:00 - {count:4d} posts | {bar}")

    start, end = best_window
    total_records = len(records)
    pct = (min_activity / total_records * 100) if total_records > 0 else 0

    print("\n--- Sleep Window Inference ---")
    print(
        f"  Likely Sleep Window (Quietest {window_size}-Hour Block): {start:02d}:00 to {end:02d}:00"
    )
    print(
        f"  Total posts during this block: {min_activity} ({pct:.1f}% of analyzed records)"
    )


def main():
    parser = argparse.ArgumentParser(
        description="Comprehensive Reddit user activity and sleep window analyzer."
    )
    parser.add_argument(
        "json_file", type=str, help="Path to the JSON output file"
    )

    # Date Range Flags
    parser.add_argument(
        "-f",
        "--from-date",
        type=parse_date,
        default=None,
        help="Start date filter (YYYY-MM-DD)",
    )
    parser.add_argument(
        "-t",
        "--to-date",
        type=parse_date,
        default=None,
        help="End date filter (YYYY-MM-DD)",
    )

    # Day Filter Group
    day_group = parser.add_mutually_exclusive_group()
    day_group.add_argument(
        "--weekdays",
        action="store_true",
        help="Filter Monday to Friday only",
    )
    day_group.add_argument(
        "--weekends",
        action="store_true",
        help="Filter Saturday and Sunday only",
    )

    # Display Options
    parser.add_argument(
        "--offset",
        type=int,
        default=0,
        help="UTC offset in hours (default: 0)",
    )
    parser.add_argument(
        "--top-subs",
        type=int,
        default=10,
        help="Number of top subreddits to display (default: 10)",
    )

    args = parser.parse_args()

    raw_records = load_data(args.json_file)
    if not raw_records:
        print("No valid user records found in the input JSON file.")
        return

    day_filter = (
        "weekdays"
        if args.weekdays
        else ("weekends" if args.weekends else "all")
    )
    to_date_adj = (
        args.to_date.replace(hour=23, minute=59, second=59)
        if args.to_date
        else None
    )

    filtered_records = filter_records(
        raw_records,
        from_date=args.from_date,
        to_date=to_date_adj,
        day_filter=day_filter,
        utc_offset=args.offset,
    )

    print(f"Loaded {len(raw_records)} total items from file.")
    print(f"Analyzing {len(filtered_records)} records after applying filters.\n")

    if not filtered_records:
        print("No records matched your search filters.")
        return

    # Run Analysis Modules
    print_yearly_breakdown(filtered_records)
    print_top_subreddits(filtered_records, top_n=args.top_subs)
    print_sleep_analysis(filtered_records, utc_offset=args.offset)


if __name__ == "__main__":
    main()
