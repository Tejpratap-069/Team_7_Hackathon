# StressLab — CPU and Memory Stress Testing Tool

**Batch 7 hackathon project.** StressLab runs bounded CPU and memory workloads, samples system metrics, visualizes baseline/workload/recovery phases, and exports CSV results. The dashboard is local-only and needs no cloud service.

## Requirements
- Python 3.12 recommended (64-bit on Windows)
- Flask and psutil (installed from `requirements.txt`)

## Run on Windows
Open Command Prompt in this `StressLab` folder and run:

```bat
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe app.py
```

Open http://127.0.0.1:5050 and keep the terminal open. On later runs, use `.venv\Scripts\python.exe app.py` or `run_windows.bat`. Press Ctrl+C in the terminal to close the server. The workload has a maximum duration of 120 seconds and is stopped/cleaned up by the controller.

## Run on Ubuntu/Linux
```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python app.py
```
Then open http://127.0.0.1:5050.

## How to demonstrate
1. Start the app and wait for baseline metrics.
2. Choose Low intensity, 1 CPU worker, 0 MiB memory, and 15 seconds; click **Start test**.
3. Observe the live CPU/RAM graphs through Baseline, Running and Recovery.
4. Wait for completion, inspect phase means and sampled peaks, then click **Export CSV**.
5. Optionally run a memory-only experiment with 0 workers and a modest memory amount within the displayed safe limit.
6. High intensity requires explicit confirmation.

## Project structure
- `app.py` — Flask routes, local-only checks, control token, CSV export
- `engine.py` — workload workers, safety limits, controller, sampling and summaries
- `templates/index.html`, `static/` — offline dashboard and charts
- `collect_evidence.py`, `evidence/` — bounded sample experiment outputs
- `tests/test_engine.py` — unit and lifecycle tests
- `docs/` — report, presentation, architecture and demo/viva material

## Tests
```bash
python -m unittest discover -s tests -v
```

## Safety and interpretation
The application binds to localhost, validates settings, caps duration and memory, reserves RAM, asks for confirmation before High intensity, and cleans up only its own child processes. These controls reduce risk but cannot guarantee responsiveness on every computer. System metrics include unrelated applications; worker RSS includes Python overhead. CPU duty levels are approximate, and peaks are sampled rather than continuous maxima. This is a classroom workload generator, not a hardware benchmark or exhaustive RAM integrity test.
