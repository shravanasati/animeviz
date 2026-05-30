import argparse
import os
import time
from collections import deque
from threading import Lock

import pandas as pd
import niquests
from concurrent.futures import ThreadPoolExecutor, as_completed

MAX_ID = 65000
MAX_WORKERS = 10
OUTPUT_CSV = "anime_data.csv"
NOT_FOUND_FILE = "anime_404.txt"
BATCH_SIZE = 50
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


def _join_names(items: list[dict] | None, key: str = "name") -> str | None:
    if not items:
        return None
    names = [item.get(key) for item in items if item.get(key)]
    return "|".join(names) if names else None


def _format_season(season: str | None, year: int | None) -> str | None:
    if not season or not year:
        return None
    return f"{str(season).capitalize()} {year}"


def _format_relations(items: list[dict] | None) -> str | None:
    if not items:
        return None
    parts = []
    for relation in items:
        relation_type = relation.get("relation")
        for entry in relation.get("entry", []) or []:
            anime_id = entry.get("mal_id")
            title = entry.get("name")
            if anime_id and title:
                if relation_type:
                    parts.append(f"{anime_id}|{title}|{relation_type}")
                else:
                    parts.append(f"{anime_id}|{title}")
    return " ; ".join(parts) if parts else None


def _normalize_row(anime_id: int, data: dict) -> dict:
    aired = data.get("aired") or {}
    row = {
        "id": data.get("mal_id", anime_id),
        "title": data.get("title"),
        "alt_title_en": data.get("title_english"),
        "alt_title_jp": data.get("title_japanese"),
        "start_date": aired.get("from"),
        "end_date": aired.get("to"),
        "synopsis": _clean_synopsis(data.get("synopsis")),
        "mean": data.get("score"),
        "rank": data.get("rank"),
        "popularity": data.get("popularity"),
        "num_list_users": data.get("members"),
        "num_scoring_users": data.get("scored_by"),
        "nsfw": None,
        "media_type": data.get("type"),
        "status": data.get("status"),
        "genres": _join_names(data.get("genres")),
        "explicit_genres": _join_names(data.get("explicit_genres")),
        "themes": _join_names(data.get("themes")),
        "demographics": _join_names(data.get("demographics")),
        "num_episodes": data.get("episodes"),
        "start_season": _format_season(data.get("season"), data.get("year")),
        "average_episode_duration": data.get("duration"),
        "rating": data.get("rating"),
        "related_anime": _format_relations(data.get("relations")),
        "studios": _join_names(data.get("studios")),
    }
    return row


def anime_info(anime_id: int, max_retries: int = 2):
    url = f"https://api.jikan.moe/v4/anime/{anime_id}/full"
    for attempt in range(max_retries + 1):
        try:
            _throttle()
            response = niquests.get(url, timeout=15)
        except Exception:
            if attempt == max_retries:
                return anime_id, None, "error"
            time.sleep(1 + attempt)
            continue

        if response.status_code == 200:
            try:
                payload = response.json()
            except Exception:
                return anime_id, None, "bad_json"
            data = payload.get("data") if isinstance(payload, dict) else None
            if not data:
                return anime_id, None, "bad_json"
            return anime_id, _normalize_row(anime_id, data), "ok"

        if response.status_code == 404:
            return anime_id, None, "not_found"

        if response.status_code in {429, 500, 502, 503, 504} and attempt < max_retries:
            time.sleep(1 + attempt)
            continue

        return anime_id, None, f"http_{response.status_code}"

    return anime_id, None, "error"


def _load_existing() -> pd.DataFrame:
    if os.path.exists(OUTPUT_CSV):
        df = pd.read_csv(OUTPUT_CSV, encoding="utf-8")
        return df.reindex(columns=OUTPUT_COLUMNS)
    return pd.DataFrame(columns=OUTPUT_COLUMNS)


def _load_not_found() -> set[int]:
    if not os.path.exists(NOT_FOUND_FILE):
        return set()
    with open(NOT_FOUND_FILE, "r", encoding="utf-8") as handle:
        return {int(line.strip()) for line in handle if line.strip().isdigit()}


def _save_not_found(not_found: set[int]) -> None:
    with open(NOT_FOUND_FILE, "w", encoding="utf-8") as handle:
        handle.write("\n".join(str(anime_id) for anime_id in sorted(not_found)))


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Jikan anime scraper with sharding")
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
        df = _load_existing()
    except Exception as exc:
        print(f"Failed to load existing CSV: {exc}")
        return
    existing_ids = set(int(value) for value in df.get("id", []) if pd.notna(value))
    not_found = _load_not_found()

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
                    df = pd.concat([df, pd.DataFrame(buffer)], ignore_index=True)
                    df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8")
                    buffer.clear()
                    _save_not_found(not_found)
                    print(f"Wrote batch. Rows={len(df)} 404s={len(not_found)}")
    except Exception as exc:
        print(f"Main loop error: {exc}")
    finally:
        if buffer:
            df = pd.concat([df, pd.DataFrame(buffer)], ignore_index=True)
        try:
            df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8")
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
