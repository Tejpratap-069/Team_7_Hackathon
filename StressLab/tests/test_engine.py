import csv
import io
import time
import unittest
from unittest.mock import patch
from engine import Engine, validate, limits
from app import create_app

SETTINGS = dict(workers=1, memory_mib=0, duration=2, level='Low')

class ValidationTests(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(validate(SETTINGS)['workers'], 1)
    def test_rejects_invalid(self):
        for change in [dict(workers=-1),dict(workers=999),dict(workers=True),dict(duration=0),dict(duration=121),dict(duration=1.2),dict(memory_mib=999999),dict(level='Extreme'),dict(workers=0,memory_mib=0),dict(level='High')]:
            with self.subTest(change=change), self.assertRaises(ValueError):
                validate(dict(SETTINGS, **change))
    def test_high_confirmation(self):
        self.assertEqual(validate(dict(SETTINGS, level='High', confirm_high=True))['level'],'High')
    def test_memory_rechecks_budget(self):
        with patch('engine.limits',return_value=dict(max_workers=1,max_memory_mib=0)):
            with self.assertRaises(ValueError):validate(dict(SETTINGS,memory_mib=1))

class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.e=Engine(baseline=.3,recovery=.3,interval=.1)
    def tearDown(self):self.e.close()
    def finish(self):
        end=time.monotonic()+12
        while self.e.snapshot()['status'] in ('Baseline','Running','Stopping','Recovery') and time.monotonic()<end:time.sleep(.05)
        self.assertNotIn(self.e.snapshot()['status'],('Baseline','Running','Stopping','Recovery'))
    def test_complete_and_csv(self):
        self.e.start(SETTINGS)
        with self.assertRaises(RuntimeError):self.e.start(SETTINGS)
        with self.assertRaises(RuntimeError):self.e.reset()
        self.finish()
        s=self.e.snapshot();self.assertEqual(s['status'],'Completed');self.assertFalse(self.e.children)
        rows=list(csv.DictReader(io.StringIO(self.e.csv_text())))
        self.assertEqual(set(r['phase'] for r in rows),{'Baseline','Running','Recovery'})
        run=[float(r['cpu_percent']) for r in rows if r['phase']=='Running']
        self.assertEqual(max(run),s['summary']['peak_cpu_percent'])
        self.e.reset();self.assertEqual(self.e.snapshot()['status'],'Idle')
    def test_stop_and_memory_cleanup(self):
        self.e.start(dict(SETTINGS,workers=0,memory_mib=8,duration=8))
        end=time.monotonic()+6
        while time.monotonic()<end:
            s=self.e.snapshot()
            if any(r['allocated_mib']==8 for r in s['samples']):break
            time.sleep(.1)
        self.assertTrue(any(r['allocated_mib']==8 for r in self.e.snapshot()['samples']))
        self.e.stop();self.finish();self.assertEqual(self.e.snapshot()['status'],'Stopped');self.assertFalse(self.e.children)
        self.assertEqual(self.e.snapshot()['latest']['allocated_mib'],0)
    def test_stop_baseline(self):
        self.e.start(SETTINGS);self.e.stop();self.finish();self.assertEqual(self.e.snapshot()['status'],'Stopped')
    def test_http_validation_and_token(self):
        client=create_app(self.e).test_client()
        self.assertEqual(client.get('/').status_code,200)
        self.assertEqual(client.get('/api/status').status_code,200)
        self.assertEqual(client.post('/api/start',json=SETTINGS).status_code,403)
        import re
        token=re.search(r'name="stress-token" content="([^"]+)"',client.get('/').text).group(1)
        self.assertEqual(client.post('/api/start',json={},headers={'X-StressLab-Token':token}).status_code,400)
        self.assertEqual(client.get('/api/export').status_code,409)
        self.assertEqual(client.get('/api/status',headers={'Host':'attacker.example'}).status_code,403)

if __name__=='__main__':unittest.main()
