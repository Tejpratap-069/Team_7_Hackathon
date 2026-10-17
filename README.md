# Team_7_OSSP_Hackathon
# StressLab — CPU and Memory Stress Testing Tool

**Batch 7 | Operating Systems Hackathon Project**

StressLab is a Python-based system testing and monitoring tool that generates controlled CPU and memory workloads and measures how the system responds. It provides a web-based dashboard for monitoring resource utilization, observing workload phases, and reviewing test results.

## 1. Problem Statement

System performance can change significantly under heavy CPU and memory workloads. Without a controlled testing tool, it can be difficult to observe resource utilization, understand system behavior under load, and monitor recovery after a workload stops.

## 2. Proposed Solution

StressLab provides a controlled environment for generating CPU and memory workloads while collecting system performance metrics.

The application allows users to configure workload settings, start and stop tests, monitor system resources through a web dashboard, and review test summaries.

## 3. Objectives

- Generate controlled CPU-intensive workloads.
- Allocate and access memory to simulate memory pressure.
- Monitor CPU and memory utilization.
- Observe baseline, running, and recovery phases.
- Display performance metrics through a web dashboard.
- Export test results for further analysis.
- Demonstrate operating-system concepts practically.

## 4. Technologies Used

| Technology | Purpose |
|---|---|
| Python | Core application and workload logic |
| Flask | Web server and dashboard backend |
| psutil | System resource monitoring |
| multiprocessing | Running workload processes |
| HTML | Dashboard structure |
| CSS | Dashboard styling |
| JavaScript | Dashboard interactions and live updates |
| CSV | Exporting test results |
| unittest | Automated testing |

## 5. Key Features

- **CPU stress testing:** Generates CPU-intensive calculations using worker processes.
- **Memory stress testing:** Allocates and accesses memory within configured limits.
- **Live monitoring:** Displays CPU and memory utilization.
- **Configurable workloads:** Supports adjustable duration, CPU workers, intensity, and memory allocation within application limits.
- **Test phases:** Observes baseline, active workload, and recovery behavior.
- **Results and export:** Reviews test summaries and exports available measurements to CSV.
- **Safety controls:** Validates settings, limits workload duration and resource use, and manages workload-process cleanup.

## 6. Project Architecture

The project follows a simple client-server architecture.

1. **Frontend:** HTML, CSS, and JavaScript provide the dashboard and user controls.
2. **Backend:** Flask handles web requests and connects the dashboard to the stress-testing engine.
3. **Stress engine:** Python and multiprocessing generate CPU and memory workloads.
4. **Monitoring:** psutil collects system resource statistics.
5. **Results:** Measurements and summaries can be reviewed and exported.

### Workflow

User Configuration → Flask Backend → Stress Engine → CPU/Memory Workload → System Monitoring → Dashboard and Results

## 7. Project Structure

```text
StressLab/
├── app.py
├── engine.py
├── collect_evidence.py
├── requirements.txt
├── run_windows.bat
├── README.md
├── templates/
│   └── index.html
├── static/
│   ├── app.js
│   └── style.css
└── tests/
    └── test_engine.py
```

## 8. System Requirements

- Python 3.12 recommended
- Windows or Linux environment
- A modern web browser
- Internet connection for initial dependency installation, if packages are not already available

The application is intended to run locally on the testing machine.

## 9. Installation and Execution

### Windows

Open Command Prompt or PowerShell and navigate to the project directory.

```powershell
cd StressLab
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe app.py
```

Alternatively, use the provided `run_windows.bat` launcher if its configuration matches your environment.

### Ubuntu/Linux

Navigate to the project directory and run:

```bash
cd StressLab
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

If your Linux distribution requires it, install the Python virtual-environment package through its package manager before creating the environment.

### Open the Dashboard

Once the server starts, open the following address in your browser:

http://127.0.0.1:5050

Keep the terminal running while using the application. Stop the server with `Ctrl+C` after the demonstration.

## 10. Demonstration Procedure

1. Start the StressLab application.
2. Open the local dashboard.
3. Configure a low-intensity CPU test with one worker, zero memory allocation, and a duration of 15 seconds.
4. Start the test and observe the dashboard.
5. Observe system measurements during the active workload.
6. Wait for the workload to finish and review the recovery phase.
7. Review the test summary and export the available results.
8. If system resources permit, demonstrate a separate, conservative memory workload.

Begin with low-intensity settings. Monitor the computer throughout testing and stop the workload if the system becomes unresponsive or excessively hot.

## 11. Operating-System Concepts Demonstrated

- **Process management:** Creating, monitoring, and terminating workload processes.
- **CPU scheduling:** Observing how the operating system schedules CPU-intensive processes.
- **Memory management:** Observing memory allocation and system memory utilization.
- **Resource utilization:** Measuring CPU and memory usage during different workload phases.
- **Process synchronization and coordination:** Coordinating workload execution and cleanup.
- **Performance monitoring:** Comparing resource behavior before, during, and after a test.

The operating system performs the actual scheduling and memory management; StressLab generates workloads and observes the resulting behavior.

## 12. Testing

Run the automated tests from the project directory.

### Windows

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

### Ubuntu/Linux

```bash
python -m unittest discover -s tests -v
```

The tests validate supported engine behavior and safety-related functionality. Actual system performance results depend on the host computer and its current workload.

## 13. Safety Considerations

- Run tests only on systems you are authorized to test.
- Start with conservative workload settings.
- Keep workload duration and resource allocation within the application's configured limits.
- Close unnecessary applications before more demanding tests.
- Do not run additional high-load tasks simultaneously.
- Stop testing if the computer becomes unstable or overheats.
- Use the application locally and avoid exposing the development server to untrusted networks.

StressLab is an educational performance-monitoring project. It is not a certification tool for hardware stability, cooling performance, or RAM integrity.

## 14. Expected Outcome

StressLab demonstrates how controlled CPU and memory workloads affect system resource utilization. Users can observe the system before, during, and after a test, review the resulting measurements, and use the exported data for performance analysis.

## 15. Future Enhancements

- Historical test comparisons and visual reports.
- Additional system metrics, such as temperature where supported.
- More detailed workload profiles.
- Automated performance benchmarking.
- Improved cross-platform monitoring and reporting.

## 16. Conclusion

StressLab combines workload generation, resource monitoring, and a web-based dashboard into a practical Operating Systems hackathon project. It demonstrates important concepts such as process management, CPU scheduling, memory management, and performance monitoring through controlled experiments.

---

**Project:** StressLab — CPU and Memory Stress Testing Tool  
**Batch:** 7  
**Subject:** Operating Systems  
**Repository:** https://github.com/Tejpratap-069/Team_7_OSSP_Hackathon
