"""Local-only EBM simulation launcher. No external dependencies."""
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import argparse
import webbrowser
import socket
import json
from http.cookies import SimpleCookie
from urllib.parse import urlsplit
import auth

ROOT = Path(__file__).resolve().parent

class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def end_headers(self):
        self.send_header('Cache-Control', 'no-cache')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('X-Frame-Options','DENY')
        super().end_headers()

    def do_GET(self):
        if self.path.startswith('/api/'):
            return self.api('GET')
        if urlsplit(self.path).path not in ('/','/index.html','/app.js','/assistant.js','/offline-pos.js','/sw.js'):
            return self.send_error(404)
        super().do_GET()

    def do_HEAD(self):
        if urlsplit(self.path).path not in ('/','/index.html','/app.js','/assistant.js','/offline-pos.js','/sw.js'):
            return self.send_error(404)
        super().do_HEAD()

    def do_POST(self):
        self.api('POST')

    def api(self,method):
        cookie=None
        try:
            if method=='POST':
                origin=self.headers.get('Origin')
                if origin and origin != 'http://'+self.headers.get('Host',''):
                    raise auth.APIError(403,'Permintaan lintas situs ditolak.')
                if not self.headers.get('Content-Type','').startswith('application/json'):
                    raise auth.APIError(415,'Gunakan application/json.')
            length=int(self.headers.get('Content-Length','0'))
            if not 0<=length<=20000:
                raise auth.APIError(413,'Permintaan terlalu besar.')
            data=json.loads(self.rfile.read(length) or b'{}') if method=='POST' else {}
            if not isinstance(data,dict):
                raise auth.APIError(400,'Format data tidak valid.')
            cookies=SimpleCookie(self.headers.get('Cookie',''))
            token=cookies['ebm_session'].value if 'ebm_session' in cookies else ''
            result,cookie=auth.handle(method,self.path,data,token,self.headers.get('X-CSRF-Token',''))
            status=200
        except auth.APIError as error:
            status=error.status;result=dict(error=error.message)
        except (ValueError,TypeError):
            status=400;result=dict(error='Format permintaan tidak valid.')
        except Exception:
            status=500;result=dict(error='Terjadi kesalahan pada server lokal.')
        body=json.dumps(result).encode()
        self.send_response(status)
        self.send_header('Content-Type','application/json; charset=utf-8')
        self.send_header('Content-Length',str(len(body)))
        if cookie is not None:
            self.send_header('Set-Cookie',f'ebm_session={cookie}; HttpOnly; SameSite=Strict; Path=/; Max-Age={43200 if cookie else 0}')
        self.end_headers();self.wfile.write(body)

class LocalServer(ThreadingHTTPServer):
    allow_reuse_address = False

    def server_bind(self):
        if hasattr(socket, 'SO_EXCLUSIVEADDRUSE'):
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--no-browser', action='store_true')
    parser.add_argument('--port',type=int,default=8080)
    args = parser.parse_args()
    auth.init()
    server = None
    for port in range(args.port, args.port+11):
        try:
            server = LocalServer(('127.0.0.1', port), Handler)
            break
        except OSError:
            continue
    if server is None:
        print('Tidak dapat membuka port lokal 8080-8090. Periksa izin firewall/aplikasi keamanan.')
        return 1
    url = f'http://127.0.0.1:{server.server_port}'
    print(f'Simulasi EBM: {url}', flush=True)
    print('Biarkan jendela ini terbuka. Tekan Ctrl+C untuk berhenti.')
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
