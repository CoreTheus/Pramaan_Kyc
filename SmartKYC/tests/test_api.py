"""HTTP tests use a temporary case store and mock only the Ollama response."""
import base64
import json
import sys
import tempfile
import threading
import unittest
import urllib.request
import urllib.error
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import server
from settings import ROOT
from client import host_url, check_host


class APITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.storage = patch("cases.ROOT", Path(cls.temp.name))
        cls.storage.start()
        cls.http = server.ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        cls.url = f"http://127.0.0.1:{cls.http.server_port}"
        cls.thread = threading.Thread(target=cls.http.serve_forever, daemon=True)
        cls.thread.start()
        cls.demo = json.loads((ROOT / "data/demo/cases.json").read_text())["standard"]
        cls.image = base64.b64encode((ROOT / "data/demo/standard.png").read_bytes()).decode()

    @classmethod
    def tearDownClass(cls):
        cls.http.shutdown()
        cls.http.server_close()
        cls.thread.join()
        cls.storage.stop()
        cls.temp.cleanup()

    def call(self, path, data=None):
        request = urllib.request.Request(self.url + path, data=None if data is None else json.dumps(data).encode(), headers={"Content-Type":"application/json"})
        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                return response.status, json.load(response)
        except urllib.error.HTTPError as response:
            return response.code, json.load(response)

    def test_review_persists_and_reassessment_links(self):
        _, case = self.call('/api/rehearsal', {'scenario':'standard'})
        status, _ = self.call('/api/review', {'id':case['id'], 'action':'Approved','reviewer':'Test','note':''})
        self.assertEqual(status, 400)
        status, updated = self.call('/api/review', {'id':case['id'], 'action':'Approved','reviewer':'Test','note':'Checked fictional evidence.'})
        self.assertEqual(status, 200)
        _, stored = self.call('/api/cases/' + case['id'])
        self.assertEqual(stored['status'], 'Approved')
        self.assertEqual(len(stored['reviews']), 1)
        self.assertEqual(stored['risk'], case['risk'])
        with patch('server.extract', return_value=self.demo['fields']):
            status, linked = self.call('/verify', {**self.demo, 'image':self.image, 'parent_id':case['id']})
        self.assertEqual(status, 200)
        self.assertEqual(linked['parent_id'], case['id'])
        self.assertNotEqual(linked['id'], case['id'])
        self.assertEqual(linked['source'], 'live_ollama')

    def test_invalid_signals(self):
        status, data = self.call('/verify', {'image':self.image, 'applicant':self.demo['applicant'], 'signals':{'failed_attempts':-2}})
        self.assertEqual(status,400)
        status, data = self.call('/verify', {'image':self.image, 'applicant':self.demo['applicant'], 'signals':{'behavior_score':float('nan')}})
        self.assertEqual(status,400)
        status, data = self.call('/verify', {'image':self.image, 'applicant':self.demo['applicant'], 'signals':{'device_known':'false'}})
        self.assertEqual(status,400)

    def test_missing_applicant_and_bad_image(self):
        status, _ = self.call('/verify', {'image':self.image})
        self.assertEqual(status,400)
        status, _ = self.call('/api/ocr', {'image':base64.b64encode(b'not an image').decode()})
        self.assertEqual(status,422)

    def test_ocr_busy(self):
        server.OCR_LOCK.acquire()
        try:
            status, _ = self.call('/api/ocr', {'image':self.image})
            self.assertEqual(status,409)
        finally:
            server.OCR_LOCK.release()

    def test_client_connector(self):
        with patch('server.health', return_value={'ready':True, 'message':'test'}):
            url, data = check_host(self.url)
            self.assertEqual(url,self.url)
            self.assertEqual(data['app'],'Pramaan KYC')
        self.assertEqual(host_url('localhost'), 'http://localhost:8000')
        for value in ('', 'file:///test', 'http://user:password@host', 'http://host/path', 'http://host:99999'):
            with self.assertRaises(ValueError):
                host_url(value)

    def test_rehearsal_explicit_label(self):
        for key, route in [('standard','Standard'),('enhanced','Enhanced'),('manual','Manual')]:
            status, c = self.call('/api/rehearsal', {'scenario':key})
            self.assertEqual(status,200)
            self.assertEqual(c['risk']['route'],route)
            self.assertEqual(c['source'],'rehearsal_cached_fields')

    def test_unknown_routes_and_cases(self):
        self.assertEqual(self.call('/api/cases/missing')[0],404)
        self.assertEqual(self.call('/../config.json')[0],404)
        self.assertEqual(self.call('/api/rehearsal', {'scenario':'not-a-scenario'})[0],400)


if __name__ == '__main__':
    unittest.main()
