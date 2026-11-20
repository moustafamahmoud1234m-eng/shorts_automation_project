import os
import sys
import wsgiref.simple_server
from google_auth_oauthlib.flow import InstalledAppFlow, _RedirectWSGIApp, _ExclusiveWSGIServer, _WSGIRequestHandler

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CLIENT_SECRET_FILE = os.path.join(BASE_DIR, "client_secret.json")
TOKEN_FILE = os.path.join(BASE_DIR, "token.json")
LINK_FILE = os.path.join(BASE_DIR, "auth_link.txt")
SCOPES = ['https://www.googleapis.com/auth/drive']

def main():
    flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
    
    host = "localhost"
    wsgi_app = _RedirectWSGIApp("Google Drive Authorized! You can now close this tab and return to Helium.")
    
    # port=0 lets the OS pick an available open port
    local_server = wsgiref.simple_server.make_server(
        host,
        0,
        wsgi_app,
        server_class=_ExclusiveWSGIServer,
        handler_class=_WSGIRequestHandler,
    )
    
    actual_port = local_server.server_port
    
    try:
        flow.redirect_uri = f"http://{host}:{actual_port}/"
        auth_url, _ = flow.authorization_url(prompt='consent', access_type='offline')
        
        with open(LINK_FILE, 'w', encoding='utf-8') as f:
            f.write(auth_url)
            
        print("AUTH_URL_READY", flush=True)
        print("AUTH_URL: " + auth_url, flush=True)
        
        # Wait for the browser redirect callback
        local_server.handle_request()
        
        authorization_response = wsgi_app.last_request_uri.replace("http", "https")
        flow.fetch_token(authorization_response=authorization_response)
        
        with open(TOKEN_FILE, 'w', encoding='utf-8') as f:
            f.write(flow.credentials.to_json())
            
        print("AUTH_SUCCESS", flush=True)
        print("Token saved to: " + TOKEN_FILE, flush=True)
    finally:
        local_server.server_close()
        if os.path.exists(LINK_FILE):
            try:
                os.remove(LINK_FILE)
            except Exception:
                pass

if __name__ == '__main__':
    main()
