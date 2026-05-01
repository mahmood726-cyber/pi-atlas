# scripts/resume_invariant_test.ps1
# 1. Clear smoke dir
# 2. Seed 100 cells
# 3. Spawn worker, wait 2 sec, kill it
# 4. Check status
# 5. Spawn worker again, let it finish
# 6. Check all done, no duplicates

$ErrorActionPreference = "Stop"
$REPO_ROOT = (Get-Item -Path ".\").FullName
$SMOKE_ROOT = Join-Path $REPO_ROOT "smoke_resume"
$QUEUE_PATH = Join-Path $SMOKE_ROOT "queue.duckdb"
$RESULTS_ROOT = Join-Path $SMOKE_ROOT "results"

if (Test-Path $SMOKE_ROOT) { Remove-Item -Recurse -Force $SMOKE_ROOT }
New-Item -ItemType Directory -Path $SMOKE_ROOT | Out-Null

Write-Host "Seeding 100 cells..."
# Seed using a small python script
$seed_script = @"
import json
from pathlib import Path
from pi_atlas.queue import Queue
q = Queue(Path('$($QUEUE_PATH -replace '\\','/')'))
q.init_schema()
for i in range(100):
    q.insert_cell(f'res-{i:03d}', phase='resume', method='hts_dl', factor_json=json.dumps({'k':3, 'tau2':0.05, 'rep':i}))
q.close()
"@
python -c $seed_script

Write-Host "Starting worker and killing it after 2 seconds..."
$job = Start-Job -ScriptBlock {
    param($q, $r)
    cd $using:REPO_ROOT
    .\.venv\Scripts\activate
    python -m pi_atlas.worker_main --worker-id 1 --queue $q --results $r --max-cells 100
} -ArgumentList $QUEUE_PATH, $RESULTS_ROOT

Start-Sleep -Seconds 2
Stop-Job $job
Remove-Job $job

Write-Host "Checking for 'running' cells (should exist if kill worked mid-fit)..."
$check_script = @"
from pathlib import Path
from pi_atlas.queue import Queue
q = Queue(Path('$($QUEUE_PATH -replace '\\','/')'))
res = q._execute_with_retry(\"SELECT count(*) FROM cells WHERE status='running'\", fetchone=True)[0]
print(f'RUNNING_COUNT={res}')
q.close()
"@
$out = python -c $check_script
Write-Host $out

Write-Host "Running watchdog to reset stuck cells..."
python -m pi_atlas.watchdog_main --queue $QUEUE_PATH --results $RESULTS_ROOT

Write-Host "Finishing remaining cells..."
python -m pi_atlas.worker_main --worker-id 2 --queue $QUEUE_PATH --results $RESULTS_ROOT --max-cells 100

Write-Host "Verifying results..."
$final_script = @"
import pandas as pd
from pathlib import Path
from pi_atlas.storage import ResultStore
from pi_atlas.queue import Queue
q = Queue(Path('$($QUEUE_PATH -replace '\\','/')'))
store = ResultStore(Path('$($RESULTS_ROOT -replace '\\','/')'))
manifest = store.read_manifest()
print(f'TOTAL_FILES={len(manifest)}')
print(f'TOTAL_ROWS={manifest[\"rows\"].sum()}')
# check all done
done_count = q._execute_with_retry(\"SELECT count(*) FROM cells WHERE status='done'\", fetchone=True)[0]
print(f'DONE_COUNT={done_count}')
q.close()
"@
python -c $final_script

Write-Host "RESUME INVARIANT TEST COMPLETE"
