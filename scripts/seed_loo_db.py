"""Seed LOO tasks into DuckDB from the JSONL manifest."""
import json
from pathlib import Path
from pi_atlas.queue import Queue

REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFEST = REPO_ROOT / "loo_manifest.jsonl"
QUEUE_PATH = REPO_ROOT / "pi-atlas-queue.duckdb"

def main():
    q = Queue(QUEUE_PATH)
    q.init_schema()
    
    count = 0
    with open(MANIFEST, "r") as f:
        for line in f:
            data = json.loads(line)
            ma_id = data["ma_id"]
            analysis_id = data["analysis_id"]
            y = data["y"]
            v = data["v"]
            k = data["k"]
            
            for j in range(k):
                cell_id = f"loo-{ma_id}-{analysis_id}-{j:03d}"
                cfg = {
                    "ma_id": ma_id,
                    "analysis_id": analysis_id,
                    "held_out_index": j,
                    "y": y,
                    "v": v,
                    "k_total": k
                }
                # method is hts_dl for now
                q.insert_cell(
                    cell_id, 
                    phase="loo", 
                    method="hts_dl", 
                    factor_json=json.dumps(cfg)
                )
                count += 1
                if count % 5000 == 0:
                    print(f"Seeded {count} tasks...")

    print(f"Total seeded: {count} LOO tasks.")
    q.close()

if __name__ == "__main__":
    main()
