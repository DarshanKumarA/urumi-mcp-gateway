"""Loopback-only production-asset visual fixture; NEVER production or real credentials.
Run after npm run build. This simulated API is only for reviewing UI states.
"""
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
import json

ROOT=Path(__file__).resolve().parents[1]/"dist"
USER={"id":"fixture-admin","username":"demo_operator","role":"admin","enabled":True}
STAMP="2026-10-25T12:15:00Z"
TOOLS={"woocommerce":["list_products","get_order","list_orders","create_product","update_order_status"],"arithmetic":["sum_amounts"],"store_policy":["get_policy"]}
SERVERS=[dict(id=slug,slug=slug,display_name=name,url=f"http://urumi-{slug.replace('_','-')}.urumi.svc.cluster.local:8000/mcp",enabled=enabled,observed_status=status,has_credential=slug=="woocommerce",last_checked=STAMP,tools=[{"name":slug+"__"+tool} for tool in TOOLS[slug]],tools_stale=not enabled) for slug,name,enabled,status in [("woocommerce","WooCommerce",True,"connected"),("arithmetic","Arithmetic",True,"unreachable"),("store_policy","Store Policy",False,"connected")]]
KEYS=[dict(id="fixture-key",label="External MCP client",prefix="fixture-prefix",created_at=STAMP,last_used_at=STAMP,revoked_at=None)]
class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*args,**kwargs): super().__init__(*args,directory=str(ROOT),**kwargs)
    def log_message(self,*args): pass
    def output(self,data,status=200):
        body=json.dumps(data).encode();self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
    def do_GET(self):
        if self.path.startswith('/api/'):
            if self.path=='/api/me': return self.output(USER if 'fixture_session' in self.headers.get('Cookie','') else {},200 if 'fixture_session' in self.headers.get('Cookie','') else 401)
            if self.path=='/api/servers': return self.output(SERVERS)
            if self.path=='/api/users': return self.output([USER,dict(USER,id='fixture-member',username='team_member',role='member')])
            if self.path.endswith('/keys'): return self.output(KEYS)
            if self.path.startswith('/api/audits'): return self.output(dict(items=[dict(id=str(i),username='demo_operator' if i%2==0 else 'team_member',server_slug=s,gateway_tool=s+'__'+t,started_at=STAMP,duration_ms=ms,outcome=o,error_code='UPSTREAM_TIMEOUT' if o=='failed' else None) for i,(s,t,ms,o) in enumerate([('woocommerce','list_orders',84,'succeeded'),('arithmetic','sum_amounts',4,'succeeded'),('store_policy','get_policy',8,'succeeded'),('arithmetic','sum_amounts',None,'started'),('woocommerce','get_order',15000,'failed')])],total=5,has_more=False))
            return self.output({})
        if not (ROOT/self.path.lstrip('/')).is_file(): self.path='/index.html'
        super().do_GET()
    def do_POST(self):
        size=int(self.headers.get('Content-Length',0));data=json.loads(self.rfile.read(size) or b'{}')
        if self.path=='/api/auth/login':
            self.send_response(200);self.send_header('Set-Cookie','fixture_session=visual-only; HttpOnly; Path=/; SameSite=Lax');self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(json.dumps(USER).encode());return
        if self.path=='/api/auth/logout':
            self.send_response(204);self.send_header('Set-Cookie','fixture_session=; Max-Age=0; Path=/');self.end_headers();return
        if self.path=='/api/chat': return self.output(dict(answer='There is 1 order in the selected store-day window. Total order value is INR 499 and average order value is INR 499. This is order value, not cash collected; the order uses Cash on Delivery.',error=None,trace=[dict(tool='woocommerce__list_orders',server='woocommerce',outcome='succeeded',duration_ms=84,summary='Tool completed.'),dict(tool='arithmetic__sum_amounts',server='arithmetic',outcome='succeeded',duration_ms=4,summary='Tool completed.')]))
        if self.path=='/api/keys': return self.output(dict(raw_key='synthetic-key-visual-fixture-only'))
        if self.path=='/api/invitations': return self.output(dict(token='synthetic-invitation-visual-fixture-only'))
        if self.path.endswith('/disable') or self.path.endswith('/enable'):
            for s in SERVERS:
                if s['id']==self.path.split('/')[-2]: s['enabled']=self.path.endswith('/enable')
        return self.output({})
    do_PATCH=do_POST
    def do_DELETE(self): return self.output({})
if __name__=='__main__':
    print('Visual fixture on http://127.0.0.1:8765; synthetic data only',flush=True)
    ThreadingHTTPServer(('127.0.0.1',8765),Handler).serve_forever()
