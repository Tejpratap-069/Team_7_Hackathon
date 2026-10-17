"""Bounded local workloads. Only the controller thread owns child processes."""
import csv
import io
import math
import multiprocessing as mp
import os
import threading
import time
from collections import deque
from datetime import datetime, timezone

import psutil

MIB = 1024 * 1024
LEVELS = {'Low': .20, 'Medium': .45, 'High': .70}
ACTIVE = {'Baseline', 'Running', 'Stopping', 'Recovery'}


def memory_budget():
    """Conservative host budget, also respecting Linux cgroup v2/v1 limits."""
    vm = psutil.virtual_memory()
    total, available = vm.total, vm.available
    for limit_path, used_path in [('/sys/fs/cgroup/memory.max', '/sys/fs/cgroup/memory.current'),
                                  ('/sys/fs/cgroup/memory/memory.limit_in_bytes', '/sys/fs/cgroup/memory/memory.usage_in_bytes')]:
        try:
            with open(limit_path) as f:
                limit = int(f.read())
            with open(used_path) as f:
                used = int(f.read())
            if 0 < limit < total:
                total, available = limit, min(available, max(0, limit - used))
        except (OSError, ValueError):
            pass
    reserve = max(512 * MIB, int(total * .15))
    cap = max(0, min(512 * MIB, int(available * .20), available - reserve)) // MIB
    return int(total), int(available), int(reserve), int(cap)


def limits(max_duration=120):
    try:
        cpus = len(psutil.Process().cpu_affinity())
    except (AttributeError, psutil.Error):
        cpus = psutil.cpu_count() or 1
    total, available, reserve, cap = memory_budget()
    return dict(max_workers=min(4, max(1, cpus - 1)), logical_cpus=cpus,
                max_memory_mib=cap, effective_total_mib=round(total / MIB),
                effective_available_mib=round(available / MIB), reserve_mib=round(reserve / MIB),
                max_duration=max_duration)


def validate(data, maximum=120):
    if not isinstance(data, dict):
        raise ValueError('Settings must be a JSON object.')
    result = {}
    for name in ('workers', 'memory_mib', 'duration'):
        value = data.get(name)
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f'{name} must be a whole number.')
        result[name] = value
    lim = limits(maximum)
    if not 0 <= result['workers'] <= lim['max_workers']:
        raise ValueError(f"Workers must be 0 to {lim['max_workers']}.")
    if not 0 <= result['memory_mib'] <= lim['max_memory_mib']:
        raise ValueError(f"Memory must be 0 to {lim['max_memory_mib']} MiB at present.")
    if result['workers'] == 0 and result['memory_mib'] == 0:
        raise ValueError('Select at least one CPU worker or some memory.')
    if not 1 <= result['duration'] <= maximum:
        raise ValueError(f'Duration must be 1 to {maximum} seconds.')
    result['level'] = data.get('level')
    if result['level'] not in LEVELS:
        raise ValueError('Choose Low, Medium or High.')
    if result['workers'] and result['level'] == 'High' and data.get('confirm_high') is not True:
        raise ValueError('Confirm the high intensity warning before starting.')
    return result


def permitted(stop, deadline, parent):
    return not stop.is_set() and time.monotonic() < deadline and (mp.parent_process() is None or mp.parent_process().is_alive())


def cpu_worker(stop, duty, deadline, parent):
    """100 ms cycles: arithmetic while busy, interruptible wait while resting."""
    x = 1.0
    while permitted(stop, deadline, parent):
        begin = time.monotonic()
        while time.monotonic() - begin < .1 * duty:
            for _ in range(150):
                x = math.sqrt(x + 1.234567)
        stop.wait(max(0, .1 - (time.monotonic() - begin)))


def memory_worker(stop, size, deadline, parent, allocated):
    blocks = []
    try:
        for _ in range(size):
            if not permitted(stop, deadline, parent):
                return
            _, available, reserve, _ = memory_budget()
            if available < reserve + 2 * MIB:
                raise MemoryError('Safety reserve reached')
            block = bytearray(MIB)
            # Touch every page with nonzero data, avoiding lazy untouched allocation.
            for offset in range(0, MIB, 4096):
                block[offset] = 165
            blocks.append(block)
            allocated.value = len(blocks)
        index = 0
        while permitted(stop, deadline, parent):
            if blocks:
                blocks[index % len(blocks)][0] ^= 1
                index += 1
            stop.wait(.05)
    finally:
        blocks.clear()
        allocated.value = 0


class Engine:
    def __init__(self, max_duration=120, baseline=5, recovery=5, interval=1):
        self.maximum = max(1, min(120, int(max_duration)))
        self.baseline, self.recovery, self.interval = baseline, recovery, interval
        self.lock = threading.RLock()
        self.quit = threading.Event()
        self.cancel = threading.Event()
        self.ctx = mp.get_context('spawn')
        self.state = 'Idle'
        self.pending = None
        self.settings = None
        self.rows = []
        self.history = deque(maxlen=180)
        self.summary = None
        self.latest = None
        self.reason = ''
        self.children = []
        self.actual_start = None
        self.elapsed = 0
        self.thread = threading.Thread(target=self._loop, name='stress-controller', daemon=True)
        self.thread.start()

    def start(self, data):
        settings = validate(data, self.maximum)
        with self.lock:
            if self.state in ACTIVE:
                raise RuntimeError('A test is already active.')
            self.settings = settings
            self.pending = settings.copy()
            self.rows, self.summary, self.reason = [], None, ''
            self.cancel.clear()
            self.elapsed = 0
            self.state = 'Baseline'

    def stop(self):
        with self.lock:
            if self.state in ACTIVE:
                self.cancel.set()
                self.reason = 'Stopped by user'
                self.state = 'Stopping'

    def reset(self):
        with self.lock:
            if self.state in ACTIVE:
                raise RuntimeError('Stop and wait for recovery before resetting.')
            self.state, self.rows, self.summary = 'Idle', [], None
            self.settings, self.reason, self.elapsed = None, '', 0

    def snapshot(self):
        with self.lock:
            return dict(status=self.state, settings=self.settings, summary=self.summary,
                        latest=self.latest, elapsed=round(self.elapsed, 2), reason=self.reason,
                        samples=list(self.rows if self.settings else self.history), limits=limits(self.maximum))

    def _sample(self, phase, origin=None, allocated=0):
        vm = psutil.virtual_memory()
        total, available, _, _ = memory_budget()
        rss = 0
        rss_observable = True
        for child in self.children:
            try:
                rss += psutil.Process(child.pid).memory_info().rss
            except (psutil.Error, TypeError):
                rss_observable = False
        row = dict(timestamp_utc=datetime.now(timezone.utc).isoformat(timespec='milliseconds'),
                   seconds=round(time.monotonic() - origin, 3) if origin else 0,
                   phase=phase, cpu_percent=psutil.cpu_percent(interval=None),
                   ram_percent=vm.percent, ram_used_mib=round(vm.used / MIB, 2),
                   ram_total_mib=round(vm.total / MIB, 2), ram_available_mib=round(vm.available / MIB, 2),
                   effective_available_mib=round(available / MIB, 2),
                   effective_total_mib=round(total / MIB, 2), worker_rss_mib=round(rss / MIB, 2) if rss_observable else None,
                   allocated_mib=allocated)
        with self.lock:
            self.latest = row
            self.history.append(row)
            if origin is not None:
                self.rows.append(row)
        return row

    def _wait_phase(self, seconds, phase, origin, cancellable):
        end = time.monotonic() + seconds
        while time.monotonic() < end and not self.quit.is_set():
            if cancellable and self.cancel.is_set():
                break
            self._sample(phase, origin)
            self.quit.wait(min(self.interval, max(0, end - time.monotonic())))

    def _cleanup(self, stop):
        stop.set()
        # One overall graceful deadline, then terminate and join owned workers only.
        deadline = time.monotonic() + 2
        for child in self.children:
            child.join(max(0, deadline - time.monotonic()))
        for child in self.children:
            if child.is_alive():
                child.terminate()
                child.join(1)
            if child.is_alive():
                child.kill()
                child.join(1)
        if any(c.is_alive() for c in self.children):
            raise RuntimeError('Worker cleanup failed; close the server.')
        self.children.clear()

    def _run(self, settings):
        origin = time.monotonic()
        stop = self.ctx.Event()
        allocated = self.ctx.Value('i', 0, lock=False)
        outcome = 'Completed'
        self.actual_start = None
        try:
            self._wait_phase(self.baseline, 'Baseline', origin, True)
            if self.cancel.is_set() or self.quit.is_set():
                outcome = 'Stopped'
            else:
                # Recheck dynamic memory cap after baseline, immediately before spawn.
                validate(dict(settings, confirm_high=True), self.maximum)
                self.actual_start = time.monotonic()
                deadline = self.actual_start + settings['duration']
                with self.lock:
                    self.state = 'Running'
                for _ in range(settings['workers']):
                    child = self.ctx.Process(target=cpu_worker, args=(stop, LEVELS[settings['level']], deadline, os.getpid()), daemon=True)
                    child.start()
                    self.children.append(child)
                if settings['memory_mib']:
                    child = self.ctx.Process(target=memory_worker, args=(stop, settings['memory_mib'], deadline, os.getpid(), allocated), daemon=True)
                    child.start()
                    self.children.append(child)
                while time.monotonic() < deadline:
                    if self.cancel.is_set() or self.quit.is_set():
                        outcome = 'Stopped'
                        break
                    if any(c.exitcode is not None for c in self.children):
                        # Children may naturally finish at the deadline.
                        if time.monotonic() < deadline - .1:
                            raise RuntimeError('A worker exited early. Check memory reserve and terminal output.')
                        break
                    _, available, reserve, _ = memory_budget()
                    if available < reserve:
                        raise MemoryError('Available memory fell below the safety reserve.')
                    with self.lock:
                        self.elapsed = time.monotonic() - self.actual_start
                    self._sample('Running', origin, allocated.value)
                    self.quit.wait(min(self.interval, max(0, deadline - time.monotonic())))
        except Exception as exc:
            outcome = 'Error'
            with self.lock:
                self.reason = str(exc)
        finally:
            with self.lock:
                if self.actual_start:
                    self.elapsed = min(settings['duration'], time.monotonic() - self.actual_start)
            try:
                self._cleanup(stop)
            except Exception as exc:
                outcome = 'Error'
                self.reason = str(exc)
            with self.lock:
                self.state = 'Recovery'
            self._wait_phase(self.recovery, 'Recovery', origin, False)
            with self.lock:
                self.summary = self._summarize(settings, outcome)
                self.state = outcome

    def _summarize(self, settings, outcome):
        def stats(phase):
            rows = [r for r in self.rows if r['phase'] == phase]
            return dict(samples=len(rows), mean_cpu_percent=round(sum(r['cpu_percent'] for r in rows) / len(rows), 2) if rows else None,
                        mean_ram_used_mib=round(sum(r['ram_used_mib'] for r in rows) / len(rows), 2) if rows else None)
        running = [r for r in self.rows if r['phase'] == 'Running']
        return dict(outcome=outcome, reason=self.reason, settings=settings, workload_seconds=round(self.elapsed, 3),
                    peak_cpu_percent=max((r['cpu_percent'] for r in running), default=None),
                    peak_ram_used_mib=max((r['ram_used_mib'] for r in running), default=None),
                    peak_worker_rss_mib=max((r['worker_rss_mib'] for r in running if r['worker_rss_mib'] is not None), default=None),
                    peak_allocated_mib=max((r['allocated_mib'] for r in running), default=None),
                    phases={p: stats(p) for p in ('Baseline', 'Running', 'Recovery')})

    def csv_text(self):
        with self.lock:
            if self.summary is None:
                raise RuntimeError('Finish a test before exporting.')
            settings, summary, rows = self.settings.copy(), self.summary.copy(), [r.copy() for r in self.rows]
        output = io.StringIO(newline='')
        extras = dict(selected_workers=settings['workers'], selected_level=settings['level'], selected_memory_mib=settings['memory_mib'],
                      selected_duration_seconds=settings['duration'], outcome=summary['outcome'], reason=summary['reason'],
                      actual_workload_seconds=summary['workload_seconds'], peak_cpu_percent=summary['peak_cpu_percent'],
                      peak_ram_used_mib=summary['peak_ram_used_mib'])
        writer = csv.DictWriter(output, fieldnames=list(rows[0]) + list(extras) if rows else list(extras))
        writer.writeheader()
        for row in rows:
            writer.writerow(dict(row, **extras))
        return output.getvalue()

    def _loop(self):
        psutil.cpu_percent(None)  # prime this thread's interval sampler
        while not self.quit.is_set():
            with self.lock:
                settings, self.pending = self.pending, None
            if settings:
                self._run(settings)
            else:
                self._sample('Idle')
                self.quit.wait(self.interval)

    def close(self):
        self.cancel.set()
        self.quit.set()
        self.thread.join(10)
