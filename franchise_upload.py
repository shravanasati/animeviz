import pandas as pd
from collections import defaultdict
from qdrant_client import QdrantClient

qc = QdrantClient(url="http://localhost:6333")

df = pd.read_csv("./anime_data_cleaned.csv")

batch_size = 500
update_data = df[["id", "franchise_id"]].dropna().to_dict(orient="records")

print(f"Starting payload sync for {len(update_data)} points...")
total_batches = len(update_data) // batch_size + 1
batch_counter = 1

for i in range(0, len(update_data), batch_size):
    print(f"Batch {batch_counter}/{total_batches}...")
    batch = update_data[i : i + batch_size]

    franchise_groups = defaultdict(list)
    for record in batch:
        franchise_groups[int(record["franchise_id"])].append(int(record["id"]))

    # Execute payload updates per unique franchise in this batch
    for f_id, point_ids in franchise_groups.items():
        qc.set_payload(
            collection_name="anime",
            payload={"franchise_id": f_id},
            points=point_ids,
            wait=False,
        )

    batch_counter += 1

print("Qdrant payloads successfully updated with franchise_ids.")