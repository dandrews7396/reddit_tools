# Reddit User Data Tools

This repository contains two command-line Python scripts for fetching Reddit
user activity through the PullPush API and summarizing the resulting data.

## Requirements

- Python 3.6 or newer
- The `requests` package (used by the data-fetching script)
- Network access to the PullPush API

Install the dependency with:

```bash
python3 -m pip install requests
```

## 1. Fetch user data

Run `reddit.py` with a Reddit username, without the `u/` prefix:

```bash
python3 reddit.py spez
```

The script requests comments and submissions from PullPush, in batches of 100
by default. It paginates from newer to older records, removes duplicate items
by ID, and pauses briefly between full batches. The result is written to
`<username>_reddit_data.json` in the current directory.

Options:

```text
  -b, --batch-size N   Number of items requested per API batch (default: 100)
  -o, --output FILE    Output JSON filename (default: <username>_reddit_data.json)
```

For example, to request batches of 250 and choose the output path:

```bash
python3 reddit.py spez --batch-size 250 --output spez.json
```

The JSON file contains the username, counts for comments and submissions, and
the returned submission and comment objects:

```json
{
  "username": "spez",
  "data_counts": {
    "comments": 0,
    "submissions": 0,
    "total": 0
  },
  "submissions": [],
  "comments": []
}
```

The counts and arrays above are illustrative; actual contents depend on the
API response. If an HTTP request raises a request exception or the API returns
a non-200 status, fetching stops for that data type; the script can still save
the records collected so far.

## 2. Analyze an export

Pass the JSON file created by `reddit.py` to `analyse_reddit.py`:

```bash
python3 analyse_reddit.py spez_reddit_data.json
```

The analyzer prints:

- Activity totals by year, the ten most active months, and activity by day of
  the week
- The most active subreddits, with comment and submission counts
- An hourly activity histogram and the quietest rolling six-hour block, labeled
  as a likely sleep window

Options:

```text
  -f, --from-date YYYY-MM-DD   Include activity on or after this UTC date
  -t, --to-date YYYY-MM-DD     Set the end bound to 23:59:59 UTC on this date
  --weekdays                   Include Monday through Friday only
  --weekends                   Include Saturday and Sunday only
  --offset HOURS               UTC offset used for weekday and hour calculations
                               (default: 0)
  --top-subs N                 Number of subreddits to display (default: 10)
```

Date bounds are evaluated in UTC. The end-date bound is set to 23:59:59 UTC on
the specified date. The offset changes local weekday and hour calculations;
it does not change date-range filtering. For example:

```bash
python3 analyse_reddit.py spez_reddit_data.json \
  --from-date 2024-01-01 --to-date 2024-12-31 \
  --weekends --offset -5 --top-subs 15
```

The sleep-window output is an inference from the least-active consecutive
six-hour period in the filtered records, not a determination of actual sleep
times. The analyzer expects the export's `comments` and `submissions` arrays
and uses each item's `created_utc` timestamp and subreddit field.
