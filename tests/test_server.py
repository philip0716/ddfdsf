import json
import threading
import unittest
from urllib.request import urlopen, Request
from urllib.error import HTTPError
from http.server import ThreadingHTTPServer
import server
from catalog import slots_for

class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),server.Handler)
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
        cls.base=f'http://127.0.0.1:{cls.server.server_port}'
    @classmethod
    def tearDownClass(cls):cls.server.shutdown();cls.server.server_close();cls.thread.join()
    def request(self,path,payload=None,extra=None):
        headers={'Content-Type':'application/json','X-FM26-Client':'local',**(extra or {})}
        r=Request(self.base+path,data=json.dumps(payload).encode() if payload is not None else None,headers=headers)
        with urlopen(r) as response:return response.status,response.read()
    def test_demo_and_optimization_round_trip(self):
        status,raw=self.request('/api/demo',{})
        data=json.loads(raw);self.assertEqual(len(data['players']),28)
        _,raw=self.request('/api/optimize',dict(slots=slots_for('4-3-3 DM'),objective='potential'))
        self.assertEqual(len(json.loads(raw)['xi']),11)
    def test_invalid_json_import_preserves_previous_data(self):
        before=server.DATA
        with self.assertRaises(HTTPError) as e:self.request('/api/import-json',{'players':[]})
        self.assertEqual(e.exception.code,400);self.assertIs(before,server.DATA)
    def test_foreign_origin_blocked(self):
        with self.assertRaises(HTTPError) as e:self.request('/api/demo',{}, {'Origin':'https://example.com'})
        self.assertEqual(e.exception.code,403)
    def test_dns_rebinding_host_blocked(self):
        with self.assertRaises(HTTPError) as e:self.request('/api/data',extra={'Host':'attacker.example'})
        self.assertEqual(e.exception.code,403)
    def test_path_traversal_blocked(self):
        with self.assertRaises(HTTPError) as e:self.request('/../server.py')
        self.assertEqual(e.exception.code,404)
    def test_static_assets_exist(self):
        for p in ['/','/style.css','/app.js']:
            status,body=self.request(p);self.assertEqual(status,200);self.assertGreater(len(body),100)
    def test_invalid_save_is_rejected_and_not_saved(self):
        with self.assertRaises(HTTPError) as e:self.request('/api/import-save',{'not':'a save'})
        self.assertEqual(e.exception.code,422)
if __name__=='__main__':unittest.main()
