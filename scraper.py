import argparse
import os
import time
from datetime import datetime
from collections import deque
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

from animec import Anime
import pandas as pd

MAX_ID = 65000
MAX_WORKERS = 10
OUTPUT_CSV = "anime_data.csv"
NOT_FOUND_FILE = "anime_404.txt"
BATCH_SIZE = 10
REQS_PER_SEC = 3
REQS_PER_MIN = 60

OUTPUT_COLUMNS = [
    "id",
    "title",
    "alt_title_en",
    "alt_title_jp",
    "start_date",
    "end_date",
    "synopsis",
    "mean",
    "rank",
    "popularity",
    "num_list_users",
    "num_scoring_users",
    "nsfw",
    "media_type",
    "status",
    "genres",
    "explicit_genres",
    "themes",
    "demographics",
    "num_episodes",
    "start_season",
    "average_episode_duration",
    "rating",
    "related_anime",
    "studios",
]

_rate_lock = Lock()
_per_sec = deque()
_per_min = deque()


def _throttle() -> None:
    while True:
        now = time.monotonic()
        with _rate_lock:
            while _per_sec and now - _per_sec[0] >= 1:
                _per_sec.popleft()
            while _per_min and now - _per_min[0] >= 60:
                _per_min.popleft()

            if len(_per_sec) < REQS_PER_SEC and len(_per_min) < REQS_PER_MIN:
                _per_sec.append(now)
                _per_min.append(now)
                return

            wait_sec = 0.0
            if len(_per_sec) >= REQS_PER_SEC:
                wait_sec = max(wait_sec, 1 - (now - _per_sec[0]))
            if len(_per_min) >= REQS_PER_MIN:
                wait_sec = max(wait_sec, 60 - (now - _per_min[0]))

        time.sleep(max(wait_sec, 0.01))


def _clean_synopsis(text: str | None) -> str | None:
    if not text:
        return None
    return " ".join(str(text).split())


def _join_list(values: list[str] | None) -> str | None:
    if not values:
        return None
    items = [str(value).strip() for value in values if value]
    return "|".join(items) if items else None


def _parse_date(text: str | None) -> str | None:
    if not text:
        return None
    value = str(text).strip()
    if not value or value in {"?", "Unknown"}:
        return None
    for fmt in ("%b %d, %Y", "%b %Y", "%Y"):
        try:
            parsed = datetime.strptime(value, fmt)
            return parsed.date().isoformat()
        except ValueError:
            continue
    return value


def _split_aired(aired: str | None) -> tuple[str | None, str | None]:
    if not aired:
        return None, None
    text = str(aired).strip()
    if not text:
        return None, None
    if " to " in text:
        start, end = text.split(" to ", 1)
        return _parse_date(start), _parse_date(end)
    if "to" in text:
        start, end = text.split("to", 1)
        return _parse_date(start), _parse_date(end)
    return _parse_date(text), None


def _parse_int(value) -> int | None:
    if value is None:
        return None
    try:
        return int(str(value).replace("#", "").replace(",", "").strip())
    except (TypeError, ValueError):
        return None


def _parse_relation_id(url: str | None) -> int | None:
    if not url:
        return None
    parts = str(url).split("/anime/")
    if len(parts) < 2:
        return None
    tail = parts[1].split("/", 1)[0]
    return _parse_int(tail)


def _clean_relation(text: str | None) -> str | None:
    if not text:
        return None
    value = str(text).strip()
    if "(" in value and value.endswith(")"):
        value = value.split("(", 1)[0].strip()
    return value or None


def _format_related(entries: list[dict] | None) -> str | None:
    if not entries:
        return None
    parts: list[str] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        url = entry.get("url")
        if not url or "/anime/" not in str(url):
            continue
        anime_id = _parse_relation_id(url)
        title = entry.get("title") or entry.get("name")
        relation = _clean_relation(entry.get("relation"))
        if anime_id and title:
            if relation:
                parts.append(f"{anime_id}|{title}|{relation}")
            else:
                parts.append(f"{anime_id}|{title}")
    return " ; ".join(parts) if parts else None


def _normalize_row(anime: Anime, fallback_id: int) -> dict:
    start_date, end_date = _split_aired(getattr(anime, "aired", None))
    row = {
        "id": getattr(anime, "id", None) or fallback_id,
        "title": getattr(anime, "name", None),
        "alt_title_en": getattr(anime, "title_english", None),
        "alt_title_jp": getattr(anime, "title_jp", None),
        "start_date": start_date,
        "end_date": end_date,
        "synopsis": _clean_synopsis(getattr(anime, "description", None)),
        "mean": getattr(anime, "score", None),
        "rank": _parse_int(getattr(anime, "ranked", None)),
        "popularity": _parse_int(getattr(anime, "popularity", None)),
        "num_list_users": getattr(anime, "num_list_users", None),
        "num_scoring_users": getattr(anime, "num_scoring_users", None),
        "nsfw": None,
        "media_type": getattr(anime, "type", None),
        "status": getattr(anime, "status", None),
        "genres": _join_list(getattr(anime, "genres", None)),
        "explicit_genres": _join_list(getattr(anime, "explicit_genres", None)),
        "themes": _join_list(getattr(anime, "themes", None)),
        "demographics": _join_list(getattr(anime, "demographics", None)),
        "num_episodes": _parse_int(getattr(anime, "episodes", None)),
        "start_season": getattr(anime, "premiered", None),
        "average_episode_duration": getattr(anime, "avg_episode_duration", None),
        "rating": getattr(anime, "rating", None),
        "related_anime": _format_related(getattr(anime, "related_entries", None)),
        "studios": _join_list(getattr(anime, "producers", None)),
    }
    return row


def anime_info(anime_id: int, max_retries: int = 2):
    for attempt in range(max_retries + 1):
        try:
            # _throttle()
            anime = Anime.from_id(anime_id)
            if not anime:
                return anime_id, None, "not_found"
            return anime_id, _normalize_row(anime, anime_id), "ok"
        except Exception:
            if attempt == max_retries:
                return anime_id, None, "error"
            time.sleep(1 + attempt)
            continue


def _load_existing_ids() -> set[int]:
    if not os.path.exists(OUTPUT_CSV):
        return set()
    try:
        df = pd.read_csv(OUTPUT_CSV, usecols=["id"], encoding="utf-8")
    except Exception:
        df = pd.read_csv(OUTPUT_CSV, encoding="utf-8")
        if "id" not in df.columns:
            return set()
        df = df[["id"]]
    return set(int(value) for value in df["id"].dropna())


def _load_not_found() -> set[int]:
    if not os.path.exists(NOT_FOUND_FILE):
        return set()
    with open(NOT_FOUND_FILE, "r", encoding="utf-8") as handle:
        return {int(line.strip()) for line in handle if line.strip().isdigit()}


def _save_not_found(not_found: set[int]) -> None:
    with open(NOT_FOUND_FILE, "w", encoding="utf-8") as handle:
        handle.write("\n".join(str(anime_id) for anime_id in sorted(not_found)))


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Animec MAL scraper with sharding")
    parser.add_argument("--start", type=int, default=1, help="Start MAL id")
    parser.add_argument("--end", type=int, default=MAX_ID, help="End MAL id")
    parser.add_argument(
        "--shard-index",
        type=int,
        default=0,
        help="Zero-based shard index",
    )
    parser.add_argument(
        "--shard-count",
        type=int,
        default=1,
        help="Total number of shards",
    )
    return parser.parse_args()


def _build_ids(
    start_id: int, end_id: int, shard_index: int, shard_count: int
) -> list[int]:
    if shard_count < 1:
        raise ValueError("shard-count must be >= 1")
    if shard_index < 0 or shard_index >= shard_count:
        raise ValueError("shard-index must be in [0, shard-count)")
    if end_id < start_id:
        return []

    ids = list(range(start_id, end_id + 1))
    if shard_count == 1:
        return ids
    return [
        anime_id
        for anime_id in ids
        if (anime_id - start_id) % shard_count == shard_index
    ]


def main() -> None:
    args = _parse_args()
    try:
        existing_ids = _load_existing_ids()
    except Exception as exc:
        print(f"Failed to load existing CSV: {exc}")
        return
    not_found = _load_not_found()
    write_header = not os.path.exists(OUTPUT_CSV)

    try:
        id_pool = _build_ids(args.start, args.end, args.shard_index, args.shard_count)
    except ValueError as exc:
        print(f"Invalid sharding args: {exc}")
        return

    ids_to_fetch = [
        anime_id
        for anime_id in id_pool
        if anime_id not in existing_ids and anime_id not in not_found
    ]

    if not ids_to_fetch:
        print("No new IDs to fetch.")
        return

    total = len(ids_to_fetch)
    processed = 0
    ok_count = 0
    not_found_count = 0
    error_count = 0
    written = 0
    last_log = time.time()
    start_time = last_log
    log_every = 200
    print(f"Starting fetch for {total} IDs (workers={MAX_WORKERS}).")

    buffer: list[dict] = []
    try:
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = [
                executor.submit(anime_info, anime_id) for anime_id in ids_to_fetch
            ]
            for future in as_completed(futures):
                try:
                    anime_id, row, status = future.result()
                except Exception as exc:
                    error_count += 1
                    processed += 1
                    print(f"Worker error: {exc}")
                    continue

                if status == "ok" and row:
                    buffer.append(row)
                    ok_count += 1
                elif status == "not_found":
                    not_found.add(anime_id)
                    not_found_count += 1
                else:
                    error_count += 1

                processed += 1
                if processed % log_every == 0 or (time.time() - last_log) >= 10:
                    elapsed = max(time.time() - start_time, 1e-6)
                    rate = processed / elapsed
                    print(
                        "Processed "
                        f"{processed}/{total} | ok={ok_count} "
                        f"404={not_found_count} error={error_count} "
                        f"rate={rate:.2f}/s"
                    )
                    last_log = time.time()

                if len(buffer) >= BATCH_SIZE:
                    pd.DataFrame(buffer, columns=OUTPUT_COLUMNS).to_csv(
                        OUTPUT_CSV,
                        mode="a",
                        header=write_header,
                        index=False,
                        encoding="utf-8",
                    )
                    write_header = False
                    written += len(buffer)
                    buffer.clear()
                    _save_not_found(not_found)
                    print(f"Wrote batch. Rows={written} 404s={len(not_found)}")
    except Exception as exc:
        print(f"Main loop error: {exc}")
    finally:
        if buffer:
            try:
                pd.DataFrame(buffer, columns=OUTPUT_COLUMNS).to_csv(
                    OUTPUT_CSV,
                    mode="a",
                    header=write_header,
                    index=False,
                    encoding="utf-8",
                )
                write_header = False
                written += len(buffer)
            except Exception as exc:
                print(f"Failed to save output: {exc}")
        try:
            _save_not_found(not_found)
        except Exception as exc:
            print(f"Failed to save output: {exc}")

        elapsed = max(time.time() - start_time, 1e-6)
        print(
            "Done. "
            f"Processed={processed} ok={ok_count} 404={not_found_count} "
            f"error={error_count} time={elapsed:.1f}s"
        )


if __name__ == "__main__":
    main()
