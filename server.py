"""Local-only browser app. No remote service, save mutation, or persistent upload storage."""
import argparse
import json
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Lock
from urllib.parse import urlparse
import webbrowser
from catalog import ROLES, FORMATIONS, POSITIONS, slots_for
from demo import demo
from engine import validate, optimize
from importer import from_save
from planning import run_action

ROOT=Path(__file__).parent/'web'
DATA=demo()
LOCK=Lock()
MAX_SAVE=2*1024**3

def encode(obj): return json.dumps(obj,ensure_ascii=False,allow_nan=False).encode()

class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args): pass
    def send(self,status,body,kind='application/json; charset=utf-8'):
        self.send_response(status); self.send_header('Content-Type',kind)
        self.send_header('Content-Length',str(len(body)))
        self.send_header('Cache-Control','no-store'); self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Content-Security-Policy',"default-src 'self'; style-src 'self'; script-src 'self'; connect-src 'self'; img-src 'self' data:; frame-ancestors 'none'")
        self.end_headers(); self.wfile.write(body)
    def valid_host(self):
        return self.headers.get('Host') in [f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}']
    def do_GET(self):
        if not self.valid_host(): return self.send(403,encode({'error':'Ungültiger Host.'}))
        path=urlparse(self.path).path
        if path=='/api/catalog':
            return self.send(200,encode(dict(roles=ROLES,formations={k:slots_for(k) for k in FORMATIONS},positions=POSITIONS)))
        if path=='/api/data':
            with LOCK: data=DATA
            return self.send(200,encode(data))
        files={'/':('index.html','text/html; charset=utf-8'),'/app.js':('app.js','text/javascript; charset=utf-8'),'/manager.js':('manager.js','text/javascript; charset=utf-8'),'/style.css':('style.css','text/css; charset=utf-8')}
        if path not in files: return self.send(404,encode({'error':'Nicht gefunden.'}))
        name,kind=files[path]; self.send(200,(ROOT/name).read_bytes(),kind)
    def do_POST(self):
        global DATA
        origin=self.headers.get('Origin')
        if not self.valid_host() or (origin and origin not in [f'http://127.0.0.1:{self.server.server_port}',f'http://localhost:{self.server.server_port}']):
            return self.send(403,encode({'error':'Fremder Zugriff blockiert.'}))
        if self.headers.get('X-FM26-Client')!='local':
            return self.send(403,encode({'error':'Client-Kennung fehlt.'}))
        try:
            length=int(self.headers.get('Content-Length','0'))
            if length<0 or length>MAX_SAVE: raise ValueError('Datei zu groß (maximal 2 GiB).')
            path=urlparse(self.path).path
            if path=='/api/import-save':
                with TemporaryDirectory(prefix='fm26-') as folder:
                    upload_path=Path(folder)/'upload.fm'
                    with upload_path.open('wb') as tmp:
                        left=length
                        while left:
                            chunk=self.rfile.read(min(left,1024*1024))
                            if not chunk: raise ValueError('Upload unvollständig.')
                            tmp.write(chunk); left-=len(chunk)
                    data=from_save(upload_path)
                with LOCK: DATA=data
                return self.send(200,encode(data))
            if length>100*1024**2: raise ValueError('JSON ist größer als 100 MiB.')
            payload=json.loads(self.rfile.read(length) or b'{}')
            if path=='/api/import-json':
                data=validate(payload)
                with LOCK: DATA=data
                return self.send(200,encode(data))
            if path=='/api/demo':
                data=demo()
                with LOCK: DATA=data
                return self.send(200,encode(data))
            if path=='/api/planning':
                with LOCK: data=DATA
                return self.send(200,encode(run_action(data,payload)))
            if path=='/api/optimize':
                with LOCK: data=DATA
                result=optimize(data,payload)
                return self.send(200,encode(result))
            self.send(404,encode({'error':'Nicht gefunden.'}))
        except (ValueError,TypeError,KeyError) as exc:
            self.send(400,encode({'error':str(exc)}))
        except Exception as exc:
            # Invalid or unsupported saves may raise parser-specific exceptions.
            self.send(422,encode({'error':f'Verarbeitung fehlgeschlagen ({type(exc).__name__}). Spielstand und Parser-Version prüfen.'}))

def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--port',type=int,default=8765)
    parser.add_argument('--no-browser',action='store_true'); args=parser.parse_args()
    server=ThreadingHTTPServer(('127.0.0.1',args.port),Handler)
    print(f'FM26 Best XI Builder: http://127.0.0.1:{server.server_port}')
    if not args.no_browser: webbrowser.open(f'http://127.0.0.1:{server.server_port}')
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()
if __name__=='__main__': main()
