import streamlit as st
import io
import os
import time
import uuid
import json
import requests
from datetime import datetime

try:
    import pandas as pd
    import altair as alt
    HAS_CHARTS = True
except ImportError:
    HAS_CHARTS = False

# Optional external imports with graceful fallback
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    HAS_POSTGRES = True
except ImportError:
    HAS_POSTGRES = False

try:
    from supabase import create_client, Client
    HAS_SUPABASE = True
except ImportError:
    HAS_SUPABASE = False

try:
    from google.oauth2 import service_account
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaIoBaseUpload
    HAS_GOOGLE = True
except ImportError:
    HAS_GOOGLE = False

try:
    from google_auth_oauthlib.flow import InstalledAppFlow
    HAS_OAUTH = True
except ImportError:
    HAS_OAUTH = False

# --- Page Configuration & Custom CSS ---
st.set_page_config(
    page_title="Auto Publish Content Pipeline",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 50%, #db2777 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
        font-size: 2.3rem;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        color: #6b7280;
        font-size: 1.05rem;
        margin-bottom: 1.5rem;
    }
    .badge-demo {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 9999px;
        font-size: 0.82rem;
        font-weight: 600;
        background-color: #fef3c7;
        color: #92400e;
        border: 1px solid #fde68a;
    }
    .badge-live {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 9999px;
        font-size: 0.82rem;
        font-weight: 600;
        background-color: #d1fae5;
        color: #065f46;
        border: 1px solid #a7f3d0;
    }
    .preview-card {
        background-color: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 1.2rem;
        margin-bottom: 1.2rem;
    }
    .platform-pill {
        display: inline-block;
        margin: 2px 4px 2px 0px;
        padding: 2px 10px;
        border-radius: 6px;
        font-size: 0.8rem;
        font-weight: 500;
        background: #374151;
        color: #f9fafb;
    }
</style>
""", unsafe_allow_html=True)

# --- Configuration & Paths ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TOKEN_FILE = os.path.join(BASE_DIR, "token.json")
CLIENT_SECRET_FILE = os.getenv("CLIENT_SECRET_FILE", os.path.join(BASE_DIR, "client_secret.json"))
SERVICE_ACCOUNT_FILE = os.getenv("SERVICE_ACCOUNT_FILE", os.path.join(BASE_DIR, "service_account.json"))
ENV_FILE = os.path.join(BASE_DIR, ".env")
SUPABASE_JSON_FILE = os.path.join(BASE_DIR, "supabase.json")

SCOPES = ['https://www.googleapis.com/auth/drive']
DEFAULT_WATCHED_FOLDER_ID = "1gZdm7oBrwHgkBNWuKPsf2IzN8zRgqfaR"

# --- Load Environment / Supabase Credentials ---
def load_env_file(filepath):
    """Loads key-value pairs from .env into os.environ if present."""
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        k, v = line.split('=', 1)
                        os.environ[k.strip()] = v.strip().strip('"').strip("'")
        except Exception:
            pass

load_env_file(ENV_FILE)

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
SUPABASE_SECRET_KEY = os.getenv("SUPABASE_SECRET_KEY", SUPABASE_KEY)
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL", "http://localhost:5678/webhook-test/new-video-submission")

# AWS PostgreSQL Configuration
PG_HOST = os.getenv("PG_HOST", "")
PG_PORT = os.getenv("PG_PORT", "5432")
PG_DATABASE = os.getenv("PG_DATABASE", "postgres")
PG_USER = os.getenv("PG_USER", "")
PG_PASSWORD = os.getenv("PG_PASSWORD", "")
DATABASE_URL = os.getenv("DATABASE_URL", "")

# Also check for supabase.json
if not (SUPABASE_URL and SUPABASE_KEY) and os.path.exists(SUPABASE_JSON_FILE):
    try:
        with open(SUPABASE_JSON_FILE, 'r', encoding='utf-8') as f:
            sb_data = json.load(f)
            SUPABASE_URL = sb_data.get("SUPABASE_URL") or sb_data.get("url") or ""
            SUPABASE_KEY = sb_data.get("SUPABASE_KEY") or sb_data.get("key") or sb_data.get("anon_key") or sb_data.get("service_role_key") or ""
    except Exception:
        pass

# Check Streamlit secrets
try:
    if hasattr(st, "secrets"):
        if "SUPABASE_URL" in st.secrets:
            SUPABASE_URL = st.secrets["SUPABASE_URL"]
        if "SUPABASE_KEY" in st.secrets:
            SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
        if "WATCHED_FOLDER_ID" in st.secrets:
            DEFAULT_WATCHED_FOLDER_ID = st.secrets["WATCHED_FOLDER_ID"]
        if "ADMIN_USERNAME" in st.secrets:
            ADMIN_USERNAME = st.secrets["ADMIN_USERNAME"]
        if "ADMIN_PASSWORD" in st.secrets:
            ADMIN_PASSWORD = st.secrets["ADMIN_PASSWORD"]
        if "N8N_WEBHOOK_URL" in st.secrets:
            N8N_WEBHOOK_URL = st.secrets["N8N_WEBHOOK_URL"]
        if "PG_HOST" in st.secrets:
            PG_HOST = st.secrets["PG_HOST"]
        if "PG_PORT" in st.secrets:
            PG_PORT = st.secrets["PG_PORT"]
        if "PG_DATABASE" in st.secrets:
            PG_DATABASE = st.secrets["PG_DATABASE"]
        if "PG_USER" in st.secrets:
            PG_USER = st.secrets["PG_USER"]
        if "PG_PASSWORD" in st.secrets:
            PG_PASSWORD = st.secrets["PG_PASSWORD"]
        if "DATABASE_URL" in st.secrets:
            DATABASE_URL = st.secrets["DATABASE_URL"]
except Exception:
    pass

# --- AWS PostgreSQL Connection Logic ---
def get_postgres_connection():
    """Returns a new psycopg2 connection or None."""
    if not HAS_POSTGRES:
        return None
    db_url = (os.getenv("DATABASE_URL") or DATABASE_URL or "").strip()
    if db_url:
        try:
            conn = psycopg2.connect(db_url, connect_timeout=4)
            conn.autocommit = False
            return conn
        except Exception:
            pass

    host = (os.getenv("PG_HOST") or PG_HOST or "").strip()
    user = (os.getenv("PG_USER") or PG_USER or "").strip()
    pwd = (os.getenv("PG_PASSWORD") or PG_PASSWORD or "").strip()
    db = (os.getenv("PG_DATABASE") or PG_DATABASE or "postgres").strip()
    port = (os.getenv("PG_PORT") or PG_PORT or "5432").strip()

    if host and user:
        try:
            conn = psycopg2.connect(
                host=host,
                port=port,
                dbname=db,
                user=user,
                password=pwd,
                connect_timeout=4
            )
            conn.autocommit = False
            return conn
        except Exception:
            return None
    return None

def check_postgres_status():
    """Checks PostgreSQL connectivity and returns (bool, status_str)."""
    if not HAS_POSTGRES:
        return False, "psycopg2 library not available"
    conn = get_postgres_connection()
    if conn is not None:
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT 1;")
            conn.close()
            return True, "Connected"
        except Exception as e:
            try:
                conn.close()
            except Exception:
                pass
            return False, str(e)
    if os.getenv("PG_HOST") or os.getenv("DATABASE_URL") or PG_HOST or DATABASE_URL:
        return False, "Failed to connect to AWS RDS/PostgreSQL"
    return False, "Not configured"

has_postgres_creds, pg_status_msg = check_postgres_status()

# --- Google Drive Authentication Logic ---
@st.cache_resource
def get_drive_service_user(token_path):
    """Initializes Google Drive service using personal user OAuth2 credentials."""
    creds = None
    if os.path.exists(token_path):
        try:
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)
        except Exception:
            creds = None

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            with open(token_path, 'w') as f:
                f.write(creds.to_json())
        except Exception:
            creds = None

    if creds and creds.valid:
        return build('drive', 'v3', credentials=creds)
    return None

drive_service_instance = get_drive_service_user(TOKEN_FILE)
auth_type = "oauth_user" if drive_service_instance else None
has_drive_creds = drive_service_instance is not None

folder_name = "uploaded videos"
if has_drive_creds:
    try:
        f_info = drive_service_instance.files().get(
            fileId=DEFAULT_WATCHED_FOLDER_ID,
            fields='name',
            supportsAllDrives=True
        ).execute()
        folder_name = f_info.get('name', 'uploaded videos')
    except Exception:
        folder_name = "uploaded videos"

# --- Supabase Client Initialization ---
@st.cache_resource
def get_supabase_client(url, key):
    if not (HAS_SUPABASE and url and key):
        return None
    try:
        client = create_client(url, key)
        # Verify connection by querying the videos table
        client.table("videos").select("id").limit(1).execute()
        return client
    except Exception as e:
        st.session_state["supabase_error"] = str(e)
        return None

supabase_client_instance = get_supabase_client(SUPABASE_URL, SUPABASE_KEY)
supabase_admin_client = get_supabase_client(SUPABASE_URL, SUPABASE_SECRET_KEY) or supabase_client_instance
has_supabase_creds = supabase_client_instance is not None or supabase_admin_client is not None

# --- Session State ---
if "submissions" not in st.session_state:
    st.session_state["submissions"] = []
if "is_admin" not in st.session_state:
    st.session_state["is_admin"] = False

def send_n8n_webhook(webhook_url, payload, timeout=10):
    """
    Delivers the video submission metadata payload to an n8n webhook endpoint.
    Returns a dict with success boolean, status_code, and message.
    """
    if not webhook_url or not webhook_url.strip():
        return {"success": False, "status_code": None, "message": "No webhook URL provided"}
        
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Streamlit-VideoPipeline/1.0"
    }
    
    try:
        response = requests.post(
            webhook_url.strip(),
            json=payload,
            headers=headers,
            timeout=timeout
        )
        if 200 <= response.status_code < 300:
            return {
                "success": True,
                "status_code": response.status_code,
                "response": response.text[:500],
                "message": f"Delivered to n8n (HTTP {response.status_code})"
            }
        else:
            return {
                "success": False,
                "status_code": response.status_code,
                "response": response.text[:500],
                "message": f"n8n returned HTTP {response.status_code}: {response.text[:150]}"
            }
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "status_code": None,
            "message": f"Webhook connection error: {str(e)}"
        }

# --- Sidebar ---
with st.sidebar:
    st.markdown("### ⚙️ Pipeline Control")
    
    # Operational Mode Options
    mode_options = []
    if has_drive_creds:
        mode_options.append("🟢 Live Drive & Database")
    mode_options.append("🧪 Simulated Demo Mode")
    
    selected_mode = st.radio(
        "Execution Mode",
        options=mode_options,
        index=0,
        help="Choose live upload to Drive and Supabase, or test simulation."
    )
    is_live = "Live" in selected_mode

    st.markdown("---")
    st.markdown("### 🔌 Connection Status")
    
    if auth_type == "oauth_user":
        st.success(f"🟢 **Google Drive**: Connected\n- Folder: `{folder_name}`\n- Storage: Personal Quota")
        if st.button("🔄 Switch Drive Account", help="Sign in with a different Google account"):
            if os.path.exists(TOKEN_FILE):
                try:
                    os.remove(TOKEN_FILE)
                except Exception:
                    pass
            st.cache_resource.clear()
            st.rerun()
    else:
        st.warning("⚠️ **Google Drive**: Not Connected (Demo Mode)")
        if os.path.exists(CLIENT_SECRET_FILE) and HAS_OAUTH:
            if st.button("🔑 Connect Your Google Drive", use_container_width=True):
                with st.spinner("Opening browser to authorize Google Drive..."):
                    try:
                        flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
                        new_creds = flow.run_local_server(port=0, prompt='consent', access_type='offline')
                        with open(TOKEN_FILE, 'w', encoding='utf-8') as f:
                            f.write(new_creds.to_json())
                        st.success("Google Drive connected successfully!")
                        st.cache_resource.clear()
                        st.rerun()
                    except Exception as ex:
                        st.error(f"Login failed: {ex}")
        
    # Database Connection Indicators
    if has_postgres_creds:
        pg_display = PG_HOST if PG_HOST else "AWS RDS/PostgreSQL"
        st.success(f"🟢 **AWS PostgreSQL**: Connected (`{pg_display}`)")
    elif PG_HOST or DATABASE_URL:
        st.warning(f"⚠️ **AWS PostgreSQL**: Connection Failed ({pg_status_msg})")
    else:
        st.caption("ℹ️ **AWS PostgreSQL**: Not configured (set in `.env`)")

    if has_supabase_creds:
        st.info("🟢 **Supabase**: Connected (`videos` table)")
    elif SUPABASE_URL and SUPABASE_KEY:
        st.caption("ℹ️ **Supabase**: Configured (Fallback)")
    else:
        st.caption("🟡 **Supabase**: Offline")

    st.markdown("---")
    folder_id = st.text_input(
        "Google Drive Folder ID",
        value=DEFAULT_WATCHED_FOLDER_ID,
        help="Google Drive folder ID monitored by n8n."
    )

    st.markdown("---")
    st.markdown("### ⚡ n8n Webhook Integration")
    webhook_enabled = st.checkbox("Trigger n8n Webhook on submit", value=True, help="Sends metadata directly to n8n.")
    n8n_url = st.text_input(
        "n8n Webhook URL",
        value=N8N_WEBHOOK_URL,
        help="Paste your n8n Webhook node URL (Test URL or Production URL)."
    )
    if st.button("🧪 Send Test Ping to n8n", use_container_width=True):
        if n8n_url.strip():
            with st.spinner("Pinging n8n webhook..."):
                ping_res = send_n8n_webhook(n8n_url.strip(), {
                    "event": "test_ping",
                    "source": "Streamlit App",
                    "title": "Sample Ping",
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
                if ping_res["success"]:
                    st.success(f"✅ Webhook delivered! (HTTP {ping_res['status_code']})")
                else:
                    st.error(f"❌ Failed: {ping_res['message']}")
        else:
            st.warning("Please provide a webhook URL first.")

    if st.session_state["submissions"]:
        if st.button("🗑️ Clear Activity History"):
            st.session_state["submissions"] = []
            st.rerun()

    st.markdown("---")
    st.markdown("### 🔐 Admin Access")
    if st.session_state.get("is_admin", False):
        st.success(f"🔓 Logged in as **{ADMIN_USERNAME}**")
        st.caption("Database payloads and IDs are currently visible.")
        if st.button("🚪 Logout Admin", use_container_width=True):
            st.session_state["is_admin"] = False
            st.rerun()
    else:
        with st.expander("🔑 Admin Login", expanded=False):
            with st.form("admin_login_form"):
                admin_user_input = st.text_input("Username")
                admin_pass_input = st.text_input("Password", type="password")
                admin_submit = st.form_submit_button("Sign In", use_container_width=True)
                if admin_submit:
                    if admin_user_input.strip() == ADMIN_USERNAME and admin_pass_input == ADMIN_PASSWORD:
                        st.session_state["is_admin"] = True
                        st.success("Admin access granted!")
                        st.rerun()
                    else:
                        st.error("Invalid username or password.")

# --- Backend Helper Functions ---
def upload_to_drive(file_obj, filename, target_folder_id, drive_service=None, real_upload=False):
    """Uploads file to real Google Drive via in-memory stream without disk files."""
    if not real_upload or drive_service is None:
        time.sleep(1.0)
        return f"mock_drive_{uuid.uuid4().hex[:12]}"

    file_obj.seek(0)
    
    file_metadata = {
        'name': filename,
        'parents': [target_folder_id]
    }
    
    mimetype = getattr(file_obj, 'type', None) or 'video/mp4'
    media = MediaIoBaseUpload(
        file_obj,
        mimetype=mimetype,
        resumable=True,
        chunksize=1024 * 1024 * 5
    )

    drive_file = drive_service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id, name, webViewLink',
        supportsAllDrives=True
    ).execute()
    return drive_file.get('id')

def insert_video_record(db_client, title, description, hashtags, platforms, drive_file_id, file_size_mb=0):
    """
    Inserts a record into public.videos following the schema with YouTube, Facebook, and Instagram booleans.
    Prefers AWS PostgreSQL; falls back to Supabase if PostgreSQL is not configured.
    """
    full_desc = description.strip()
    if hashtags.strip():
        full_desc = f"{full_desc}\n\n{hashtags.strip()}".strip() if full_desc else hashtags.strip()
        
    # Check if video exceeds platform limits (Instagram Reels max ~100MB, Facebook ~1GB, general >300MB)
    needs_compression = (
        ("Instagram" in platforms and file_size_mb > 95) or
        ("Facebook" in platforms and file_size_mb > 1000) or
        (file_size_mb > 300)
    )
        
    post_data = {
        "title": title.strip(),
        "description": full_desc,
        "platform": ", ".join(platforms),
        "video_id": drive_file_id,
        "status": "pending",
        # Explicit boolean fields for target platforms
        "youtube": "YouTube" in platforms,
        "facebook": "Facebook" in platforms,
        "instagram": "Instagram" in platforms,
        "needs_compression": needs_compression
    }
    
    # 1. Try AWS PostgreSQL first
    pg_conn = get_postgres_connection()
    if pg_conn is not None:
        try:
            with pg_conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS public.videos (
                        id SERIAL PRIMARY KEY,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        title TEXT,
                        description TEXT,
                        platform TEXT,
                        video_id TEXT,
                        status TEXT DEFAULT 'pending',
                        youtube BOOLEAN DEFAULT false,
                        facebook BOOLEAN DEFAULT false,
                        instagram BOOLEAN DEFAULT false,
                        needs_compression BOOLEAN DEFAULT false
                    );
                """)
                cur.execute("""
                    INSERT INTO public.videos 
                    (title, description, platform, video_id, status, youtube, facebook, instagram, needs_compression)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id;
                """, (
                    post_data["title"],
                    post_data["description"],
                    post_data["platform"],
                    post_data["video_id"],
                    post_data["status"],
                    post_data["youtube"],
                    post_data["facebook"],
                    post_data["instagram"],
                    post_data["needs_compression"]
                ))
                inserted_row = cur.fetchone()
                inserted_id = inserted_row[0] if inserted_row else None
            pg_conn.commit()
            pg_conn.close()
            return {"id": inserted_id, "data": post_data, "status": "db_inserted", "engine": "AWS PostgreSQL"}
        except Exception as e:
            st.session_state["pg_insert_error"] = str(e)
            if pg_conn:
                try:
                    pg_conn.close()
                except Exception:
                    pass

    # 2. Fallback to Supabase
    if db_client is not None:
        try:
            res = db_client.table("videos").insert(post_data).execute()
            inserted_id = None
            if hasattr(res, "data") and res.data and len(res.data) > 0:
                inserted_id = res.data[0].get("id")
            return {"id": inserted_id, "data": post_data, "status": "db_inserted", "engine": "Supabase"}
        except Exception as e:
            st.session_state["supabase_insert_error"] = str(e)
        
    time.sleep(0.3)
    return {"id": "simulated", "data": post_data, "status": "session_saved", "engine": "Simulated"}

# --- Main App Header ---
col_head1, col_head2 = st.columns([4, 1])
with col_head1:
    st.markdown('<div class="main-header">🚀 Auto Publish Content Pipeline</div>', unsafe_allow_html=True)
    status_sub = f"Linked to Google Drive folder: <b>{folder_name}</b>"
    if has_postgres_creds:
        status_sub += " | Database: <b>AWS PostgreSQL (public.videos)</b>"
    elif has_supabase_creds:
        status_sub += " | Database: <b>Supabase (public.videos)</b>"
    st.markdown(f'<div class="sub-header">{status_sub}</div>', unsafe_allow_html=True)
with col_head2:
    if is_live:
        st.markdown('<br><span class="badge-live">🟢 Live Pipeline Active</span>', unsafe_allow_html=True)
    else:
        st.markdown('<br><span class="badge-demo">🧪 Test Simulation Mode</span>', unsafe_allow_html=True)

# Status notification banner
if is_live and has_postgres_creds:
    st.success(f"🚀 Ready to publish! Videos upload to Google Drive folder **{folder_name}** and metadata is stored in AWS PostgreSQL **`public.videos`** for n8n.")
elif is_live and has_supabase_creds:
    st.success(f"🚀 Ready to publish! Videos upload to Google Drive folder **{folder_name}** and metadata is stored in Supabase **`videos`** table for n8n.")
elif is_live and not (has_postgres_creds or has_supabase_creds):
    st.info("ℹ️ Google Drive is live. Metadata will be saved to local session queue.")
else:
    st.info("ℹ️ Running in **Simulated Mode**: Fast testing without consuming storage or database records.")

# --- Compression Modal Dialog ---
if hasattr(st, "dialog"):
    @st.dialog("🎬 Smart Video Optimization")
    def show_compression_modal(v_size_mb):
        st.markdown(f"""
        ### Video detected: **{v_size_mb} MB**
        
        To ensure smooth, high-speed publishing across social platforms (like **Instagram Reels** and **Facebook**), our pipeline will automatically optimize this video for mobile feeds.
        
        ✨ **What to expect:**
        - **High Quality:** Retains crisp 1080p resolution and clear audio.
        - **Zero Effort:** No manual resizing or re-encoding needed on your end.
        - **Guaranteed Delivery:** Prevents platform upload drops or size rejections.
        """)
        if st.button("Continue to Publish 🚀", type="primary", use_container_width=True):
            st.session_state["seen_dialog_sig"] = st.session_state.get("current_file_sig")
            st.rerun()

# --- Top-Level Tabs: Upload Pipeline & Video Snapshot Analytics ---
tab_upload, tab_analytics = st.tabs([
    "📤 1. Upload & Publish Pipeline",
    "📊 2. Video Snapshot Analytics Dashboard"
])

# --- Unified Layout: Upload & Native Reel Publishing ---
col_form, col_preview = tab_upload.columns([3, 2], gap="large")

with col_form:
    st.subheader("📤 Post & Reel Creator")
    
    uploaded_video = st.file_uploader(
        "Upload Video File *",
        type=["mp4", "mov", "mkv", "webm"],
        help="Select the video file you want to publish."
    )
    
    if uploaded_video is not None:
        v_size_bytes = len(uploaded_video.getbuffer())
        v_size_mb = round(v_size_bytes / (1024 * 1024), 2)
        current_sig = f"{uploaded_video.name}_{v_size_bytes}"
        st.session_state["current_file_sig"] = current_sig
        
        if v_size_mb > 100:
            if st.session_state.get("seen_dialog_sig") != current_sig:
                if hasattr(st, "dialog"):
                    show_compression_modal(v_size_mb)

    with st.form("publish_form", clear_on_submit=False):
        # 1. Headline & Caption (matches Screenshot 1 & Facebook)
        title = st.text_input(
            "Video Title *",
            placeholder="e.g. 5 AI Tools That Feel Illegal to Know",
            help="Main headline for your post."
        )
        
        caption = st.text_area(
            "Describe your reel / Caption (Instagram & Facebook)",
            placeholder="Write your reel caption, details, and description...",
            max_chars=2200,
            height=110
        )
        
        hashtags = st.text_input(
            "Hashtags",
            placeholder="e.g. #reels #tech #ai #viral",
            help="Space or comma separated hashtags."
        )

        platforms = st.multiselect(
            "Target Platforms",
            options=["Instagram", "Facebook", "YouTube"],
            default=["Instagram", "Facebook"]
        )

        # 2. Tagging & Compliance (matches Screenshots 1 & Facebook)
        st.markdown("---")
        st.markdown("##### 👥 Tags & Metadata")
        col_loc, col_collab = st.columns(2)
        with col_loc:
            location = st.text_input("📍 Add Location / Place", placeholder="e.g. New York, NY or Place ID")
        with col_collab:
            collaborators = st.text_input("👥 Collaborators / Tag People", placeholder="e.g. @creator1, @creator2")

        cc_file = st.file_uploader("💬 Closed Captions (.srt)", type=["srt"], help="Subtitle file upload for Facebook & Instagram")

        ai_label = st.checkbox(
            "Add AI label (Required by Meta for AI-generated or realistic synthetic media)",
            value=False
        )
        st.caption("ℹ️ *This label is required for realistic photos and videos made with AI. People will see it on your content.*")

        # 3. Video Editing: Crop & Trim (matches Screenshots 3 & 4)
        st.markdown("---")
        st.markdown("##### 📐 Crop, Trim & Audio")
        
        crop_ratio = st.radio(
            "Aspect Ratio (Crop)",
            options=["Original", "1:1", "9:16", "16:9"],
            index=2, # Default to 9:16 for Reels
            horizontal=True,
            help="Original keeps aspect ratio. 9:16, 1:1, or 16:9 informs n8n to crop/scale via FFmpeg."
        )

        sound_on = st.checkbox("Sound on 🔊", value=True)

        col_t1, col_t2 = st.columns(2)
        with col_t1:
            trim_start = col_t1.number_input("Trim Start (seconds)", min_value=0.0, value=0.0, step=0.5)
        with col_t2:
            trim_end = col_t2.number_input("Trim End (seconds, 0 = Full video)", min_value=0.0, value=0.0, step=0.5)

        # 4. Cover Photo (matches Screenshot 3)
        st.markdown("---")
        st.markdown("##### 🖼️ Cover Photo")
        cover_source = st.radio(
            "Cover Source",
            ["Select frame from video (thumb_offset)", "Upload custom cover image"],
            horizontal=True
        )
        cover_offset_sec = 1.5
        custom_cover_file = None
        if "frame from video" in cover_source:
            cover_offset_sec = st.slider("Cover Frame Position (seconds)", 0.0, 120.0, 1.5, step=0.5)
            st.caption(f"⚡ Native API `thumb_offset`: `{int(cover_offset_sec * 1000)} ms`")
        else:
            custom_cover_file = st.file_uploader("Select Cover from Computer", type=["jpg", "jpeg", "png"])

        # 5. Scheduling & Advanced Settings
        st.markdown("---")
        is_scheduled = st.checkbox("Schedule content for later", value=False)
        scheduled_iso = None
        scheduled_unix = None
        if is_scheduled:
            col_d, col_t = st.columns(2)
            s_date = col_d.date_input("Publish Date")
            s_time = col_t.time_input("Publish Time")
            try:
                dt_obj = datetime.combine(s_date, s_time)
                scheduled_iso = dt_obj.isoformat()
                scheduled_unix = int(dt_obj.timestamp())
            except Exception:
                scheduled_iso = f"{s_date}T{s_time}"
                scheduled_unix = None

        share_to_feed = st.checkbox("Share Reel to Main Feed & Profile Grid", value=True, help="Supported natively by Meta API: When enabled, your reel also appears on your main profile feed.")

        submitted = st.form_submit_button("🚀 Upload & Publish Reel to Pipeline", type="primary", use_container_width=True)

    if submitted:
        if not uploaded_video or not title:
            st.error("⚠️ Please provide both a video file and a title.")
        elif not platforms:
            st.warning("⚠️ Please select at least one target platform.")
        else:
            drive_svc = drive_service_instance if is_live else None
            supa_cli = supabase_client_instance if is_live else None

            spinner_msg = f"⏳ Step 1/3: Uploading '{uploaded_video.name}' ({round(uploaded_video.size / (1024*1024), 1)} MB) to Google Drive..." if is_live else "⏳ Simulating Drive upload..."
            drive_file_id = None
            
            with st.spinner(spinner_msg):
                try:
                    drive_file_id = upload_to_drive(
                        uploaded_video,
                        uploaded_video.name,
                        folder_id,
                        drive_service=drive_svc,
                        real_upload=is_live
                    )
                except Exception as e:
                    st.error(f"❌ Google Drive upload error: {e}")

            if drive_file_id:
                with st.spinner("⏳ Step 2/3: Storing metadata in database (public.videos)..."):
                    try:
                        file_bytes = uploaded_video.getbuffer()
                        file_size_mb = round(len(file_bytes) / (1024 * 1024), 2)
                        
                        full_description = caption.strip()
                        if hashtags.strip():
                            full_description = f"{full_description}\n\n{hashtags.strip()}".strip() if full_description else hashtags.strip()
                            
                        record_result = insert_video_record(
                            supa_cli,
                            title=title,
                            description=full_description,
                            hashtags=hashtags,
                            platforms=platforms,
                            drive_file_id=drive_file_id,
                            file_size_mb=file_size_mb
                        )
                        db_record_id = record_result.get("id")
                        db_engine = record_result.get("engine", "Database")
                        
                        # Prepare full rich payload for n8n webhook with all reel properties
                        webhook_payload = {
                            "event": "video_submission",
                            "db_id": db_record_id,
                            "drive_file_id": drive_file_id,
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "title": title.strip(),
                            "description": full_description,
                            "hashtags": hashtags.strip(),
                            "platforms": platforms,
                            "youtube": "YouTube" in platforms,
                            "facebook": "Facebook" in platforms,
                            "instagram": "Instagram" in platforms,
                            "needs_compression": record_result["data"].get("needs_compression", False),
                            "status": "pending",
                            "crop": crop_ratio,
                            "file": {
                                "name": uploaded_video.name,
                                "size_mb": file_size_mb,
                                "mimetype": getattr(uploaded_video, "type", "video/mp4")
                            },
                            "reel_properties": {
                                "crop": {
                                    "ratio": crop_ratio,
                                    "strategy": "crop_to_fill",
                                    "needs_ffmpeg": (crop_ratio != "Original")
                                },
                                "edit": {
                                    "crop": {
                                        "ratio": crop_ratio,
                                        "strategy": "crop_to_fill",
                                        "needs_ffmpeg": (crop_ratio != "Original")
                                    },
                                    "sound_on": sound_on,
                                    "strip_audio": not sound_on,
                                    "trim": {
                                        "start_seconds": trim_start if trim_start > 0 else None,
                                        "end_seconds": trim_end if trim_end > 0 else None,
                                        "needs_trim": (trim_start > 0 or trim_end > 0)
                                    },
                                    "trim_start_seconds": trim_start if trim_start > 0 else None,
                                    "trim_end_seconds": trim_end if trim_end > 0 else None,
                                    "needs_trim": (trim_start > 0 or trim_end > 0),
                                    "cover": {
                                        "source": "frame_offset" if "frame from video" in cover_source else "custom_upload",
                                        "thumb_offset_ms": int(cover_offset_sec * 1000) if "frame from video" in cover_source else None,
                                        "custom_image_name": custom_cover_file.name if custom_cover_file else None
                                    }
                                },
                                "metadata": {
                                    "caption": caption.strip(),
                                    "location": location.strip() if location else None,
                                    "collaborators": [c.strip() for c in collaborators.split(",") if c.strip()],
                                    "is_ai_generated": ai_label,
                                    "has_closed_captions": cc_file is not None,
                                    "closed_captions_filename": cc_file.name if cc_file else None
                                },
                                "scheduling": {
                                    "is_scheduled": is_scheduled,
                                    "publish_time_iso": scheduled_iso,
                                    "publish_time_unix": scheduled_unix
                                },
                                "advanced": {
                                    "share_to_feed": share_to_feed
                                }
                            },
                            "record": record_result["data"]
                        }
                        
                        # Dispatch to n8n webhook if enabled
                        webhook_res = None
                        if webhook_enabled and n8n_url and n8n_url.strip():
                            with st.spinner("⏳ Step 3/3: Triggering n8n publish webhook..."):
                                webhook_res = send_n8n_webhook(n8n_url.strip(), webhook_payload)
                                if webhook_res["success"]:
                                    st.success(f"⚡ **n8n Workflow Dispatched**: {webhook_res['message']}")
                                else:
                                    st.warning(f"⚠️ **n8n Notice**: {webhook_res['message']}")
                        
                        is_inserted_live = is_live and record_result.get("status") == "db_inserted"
                        sub_mode_label = f"Live (Drive & {db_engine})" if is_inserted_live else ("Live Drive" if is_live else "Simulated")
                        
                        st.session_state["submissions"].insert(0, {
                            "db_id": db_record_id,
                            "drive_file_id": drive_file_id,
                            "timestamp": datetime.now().strftime("%H:%M:%S"),
                            "title": title.strip(),
                            "description": full_description,
                            "platforms": platforms,
                            "filename": uploaded_video.name,
                            "filesize_mb": file_size_mb,
                            "mode": sub_mode_label,
                            "status": "pending",
                            "crop": crop_ratio,
                            "ai_label": ai_label,
                            "payload": webhook_payload,
                            "webhook_result": webhook_res
                        })
                        
                        if st.session_state.get("is_admin", False):
                            db_status_text = f"Inserted into {db_engine} `public.videos` table (ID: `{db_record_id}`)" if is_inserted_live else "Stored in session activity"
                            st.success(f"🎉 **Video Successfully Submitted to Pipeline!**")
                            st.markdown(f"""
                            - **Google Drive File ID**: `{drive_file_id}`
                            - **Database Record**: {db_status_text}
                            - **Platforms**: {', '.join(platforms)}
                            - **Aspect Ratio**: `{crop_ratio}` | **AI Label**: `{ai_label}`
                            - **Pipeline Status**: `pending` → Ready for n8n processing!
                            """)
                        else:
                            st.success(f"🎉 **Video Successfully Submitted!**")
                            st.markdown(f"""
                            - **Title**: {title.strip()}
                            - **Target Platforms**: {', '.join(platforms)}
                            - **Aspect Ratio**: `{crop_ratio}`
                            - **Pipeline Status**: `pending` (Queued for processing)
                            """)
                    except Exception as e:
                        st.error(f"❌ Error saving to database: {e}")

with col_preview:
    st.subheader("👁️ Live Preview & Queue")
    
    # Live Video Preview if uploaded
    if uploaded_video is not None:
        st.markdown("**🎬 Video Preview:**")
        st.video(uploaded_video)
        file_size_mb = round(len(uploaded_video.getbuffer()) / (1024 * 1024), 2)
        st.caption(f"📁 **File:** `{uploaded_video.name}` ({file_size_mb} MB) | **Format:** {uploaded_video.type}")
    else:
        st.info("Upload a video on the left to preview it here.")

    # Live Post Preview Card
    st.markdown("**📱 Social Card Preview:**")
    display_title = title.strip() if ('title' in locals() and title) else "Your Title Will Appear Here"
    display_desc = caption.strip() if ('caption' in locals() and caption) else "Your post description will appear here..."
    display_tags = hashtags.strip() if ('hashtags' in locals() and hashtags) else "#hashtags"
    selected_plat = platforms if ('platforms' in locals() and platforms) else ["No platform selected"]
    
    with st.container():
        st.markdown(f"""
        <div class="preview-card">
            <h4 style="margin:0 0 6px 0; color:#3b82f6;">{display_title}</h4>
            <p style="margin:0 0 8px 0; font-size:0.9rem; color:#9ca3af;">{display_desc}</p>
            <p style="margin:0 0 10px 0; font-size:0.85rem; color:#60a5fa; font-weight:500;">{display_tags}</p>
            <div>
                {' '.join([f'<span class="platform-pill">{p}</span>' for p in selected_plat])}
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Submission History / Queue
    if st.session_state.get("is_admin", False):
        st.markdown("### 📋 Automation Queue (`public.videos`) — *Admin View*")
    else:
        st.markdown("### 📋 Recent Submissions")
    if not st.session_state["submissions"]:
        st.caption("No submissions in this session yet. Submit a video above to see it appear here.")
    else:
        for idx, sub in enumerate(st.session_state["submissions"]):
            sub_title = sub.get("title", "Untitled")
            sub_time = sub.get("timestamp", "")
            sub_status = sub.get("status", "pending")
            sub_db_id = sub.get("db_id")
            sub_drive_id = sub.get("drive_file_id") or sub.get("id") or "N/A"
            sub_file = sub.get("filename", "video")
            sub_size = sub.get("filesize_mb", 0)
            sub_platforms = sub.get("platforms", [])
            sub_mode = sub.get("mode", "")
            sub_payload = sub.get("payload", {})

            with st.expander(f"#{idx+1} {sub_title} ({sub_time}) - {sub_status.upper()}", expanded=(idx == 0)):
                st.write(f"**File:** `{sub_file}` ({sub_size} MB)")
                st.write(f"**Platforms:** {', '.join(sub_platforms)}")
                st.write(f"**Status:** `{sub_status.upper()}`")
                
                if st.session_state.get("is_admin", False):
                    st.markdown("---")
                    st.markdown("**🛡️ Admin Technical Details & Payload:**")
                    if sub_db_id:
                        st.write(f"**Database Row ID:** `{sub_db_id}`")
                    st.write(f"**Drive File ID:** `{sub_drive_id}`")
                    wh_res = sub.get("webhook_result")
                    if wh_res:
                        wh_icon = "🟢" if wh_res.get("success") else "⚠️"
                        st.write(f"**n8n Webhook Status:** {wh_icon} `{wh_res.get('message', '')}`")
                    st.write(f"**Pipeline Mode:** `{sub_mode}`")
                    st.markdown("**Dispatched Payload to n8n:**")
                    st.json(sub_payload)
                else:
                    st.caption("🔒 *Database payload and backend records are restricted to admin access.*")


# =====================================================================
# --- TAB 2: VIDEO SNAPSHOT ANALYTICS DASHBOARD (Older vs. Newer) ---
# =====================================================================
def parse_raw_snapshot_items(raw_snap):
    """Unwraps Supabase snapshot JSON payload into a flat list of per-video metric dictionaries."""
    if not raw_snap:
        return []
    data = raw_snap
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except Exception:
            return []
    if isinstance(data, dict):
        if "data" in data and isinstance(data["data"], list):
            return [x for x in data["data"] if isinstance(x, dict)]
        # Support structured platform keys
        flat_dict = []
        for p in ["instagram", "facebook", "youtube", "platforms"]:
            if p in data and isinstance(data[p], list):
                flat_dict.extend([x for x in data[p] if isinstance(x, dict)])
        if flat_dict:
            return flat_dict
        return [data]
    if isinstance(data, list):
        flat = []
        for elem in data:
            if isinstance(elem, dict):
                if "data" in elem and isinstance(elem["data"], list):
                    flat.extend([x for x in elem["data"] if isinstance(x, dict)])
                elif "platform" in elem or "video_id" in elem:
                    flat.append(elem)
        return flat
    return []


def format_snap_timestamp(ts_str):
    """Formats ISO timestamp into a clean human-readable label."""
    if not ts_str:
        return "Unknown Timestamp"
    try:
        clean_ts = str(ts_str).replace("Z", "+00:00")
        dt = datetime.fromisoformat(clean_ts)
        return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
    except Exception:
        return str(ts_str)


def fetch_all_snapshots_from_db(db_client=None):
    """Fetches snapshot history and platform ID tables from AWS PostgreSQL (preferred) or Supabase."""
    snapshot_rows = []
    known_ids = {"instagram": [], "facebook": [], "youtube": []}

    # 1. Try AWS PostgreSQL first
    pg_conn = get_postgres_connection()
    if pg_conn is not None:
        try:
            with pg_conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Query snapshots
                cur.execute("SELECT * FROM public.snapshot ORDER BY created_at ASC;")
                raw_snaps = cur.fetchall()
                snapshot_rows = [dict(r) for r in raw_snaps]

                # Query platform ID tables
                for plat, col_name in [("instagram", "instagram id"), ("facebook", "facebook id"), ("youtube", "youtube id")]:
                    try:
                        cur.execute(f'SELECT * FROM public."{plat}";')
                        rows = cur.fetchall()
                        for row in rows:
                            r_dict = dict(row)
                            vid = str(r_dict.get(col_name) or r_dict.get(col_name.replace(" ", "_")) or r_dict.get("id") or "").strip()
                            if vid:
                                known_ids[plat].append({
                                    "video_id": vid,
                                    "created_at": r_dict.get("created at") or r_dict.get("created_at")
                                })
                    except Exception:
                        pg_conn.rollback()
            pg_conn.close()
            return snapshot_rows, known_ids, "AWS PostgreSQL"
        except Exception as e:
            st.session_state["pg_fetch_error"] = str(e)
            if pg_conn:
                try:
                    pg_conn.close()
                except Exception:
                    pass

    # 2. Fallback to Supabase
    if db_client is not None:
        try:
            res = db_client.table("snapshot").select("*").order("created_at", desc=False).execute()
            if hasattr(res, "data") and res.data:
                snapshot_rows = res.data
        except Exception as e:
            st.session_state["snapshot_fetch_error"] = str(e)

        for plat, col_name in [("instagram", "instagram id"), ("facebook", "facebook id"), ("youtube", "youtube id")]:
            try:
                p_res = db_client.table(plat).select("*").execute()
                if hasattr(p_res, "data") and p_res.data:
                    for row in p_res.data:
                        vid = str(row.get(col_name) or row.get(col_name.replace(" ", "_")) or row.get("id") or "").strip()
                        if vid:
                            known_ids[plat].append({
                                "video_id": vid,
                                "created_at": row.get("created at") or row.get("created_at")
                            })
            except Exception:
                pass
        return snapshot_rows, known_ids, "Supabase"

    return snapshot_rows, known_ids, "None (Offline)"


def build_video_Analytics_index(snapshot_rows, known_ids):
    """Groups all historical snapshots by video_id."""
    video_index = {}

    for idx, row in enumerate(snapshot_rows):
        ts = row.get("created_at") or row.get("collected at") or row.get("collected_at") or f"Snapshot #{idx+1}"
        raw_payload = row.get("snapshot") or row.get("snapshot_data")
        items = parse_raw_snapshot_items(raw_payload)

        for item in items:
            vid = str(item.get("video_id") or "").strip()
            if not vid or vid.lower() == "none":
                continue
            platform = str(item.get("platform") or "unknown").lower()
            title = str(item.get("title") or "").strip()

            if vid not in video_index:
                video_index[vid] = {
                    "video_id": vid,
                    "platform": platform,
                    "title": title,
                    "snapshots": []
                }
            if title and not video_index[vid]["title"]:
                video_index[vid]["title"] = title

            video_index[vid]["snapshots"].append({
                "snap_index": len(video_index[vid]["snapshots"]) + 1,
                "raw_timestamp": ts,
                "formatted_time": format_snap_timestamp(ts),
                "metrics": item
            })

    # Also register any platform video IDs that don't have a snapshot yet
    for plat, rows in known_ids.items():
        for r in rows:
            vid = r["video_id"]
            if vid not in video_index:
                video_index[vid] = {
                    "video_id": vid,
                    "platform": plat,
                    "title": "",
                    "snapshots": []
                }

    return video_index


def get_platform_metric_keys(platform):
    """Returns ordered list of (metric_key, display_label) for a platform."""
    plat = platform.lower()
    if plat == "instagram":
        return [
            ("views", "Views"),
            ("reach", "Reach"),
            ("total_interactions", "Total Interactions"),
            ("likes", "Likes"),
            ("comments", "Comments"),
            ("shares", "Shares"),
            ("saved", "Saved")
        ]
    elif plat == "facebook":
        return [
            ("plays", "Plays"),
            ("avg_watch_time_seconds", "Avg Watch Time (s)"),
            ("reactions", "Reactions"),
            ("comments", "Comments"),
            ("shares", "Shares")
        ]
    elif plat == "youtube":
        return [
            ("views", "Views"),
            ("likes", "Likes"),
            ("comments", "Comments"),
            ("duration_seconds", "Duration (s)")
        ]
    else:
        return [
            ("views", "Views"),
            ("likes", "Likes"),
            ("comments", "Comments"),
            ("shares", "Shares")
        ]


with tab_analytics:
    st.subheader("📊 Video Performance & Snapshot Comparison Dashboard")
    st.caption("Search any Video ID from your external AWS PostgreSQL / Supabase database (`public.snapshot`) to compare older vs. newer performance snapshots with visual charts.")

    active_db = supabase_admin_client or supabase_client_instance
    has_any_db = has_postgres_creds or (active_db is not None)

    if not has_any_db and not (PG_HOST or DATABASE_URL or SUPABASE_URL):
        st.warning("⚠️ No database connected. Please configure AWS PostgreSQL credentials (`PG_HOST`, `PG_USER`, etc.) or Supabase in `.env`.")
    else:
        # Top Action & Search Row
        ctrl_col1, ctrl_col2, ctrl_col3 = st.columns([3, 2, 1])

        with ctrl_col3:
            st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
            if st.button("🔄 Refresh DB", use_container_width=True, help="Reload latest snapshots from database"):
                st.rerun()

        snapshot_rows, known_ids, db_source = fetch_all_snapshots_from_db(active_db)
        video_index = build_video_Analytics_index(snapshot_rows, known_ids)

        if db_source == "AWS PostgreSQL":
            st.caption(f"🟢 Connected to **AWS PostgreSQL** (`public.snapshot`) — Retrieved {len(snapshot_rows)} snapshots across {len(video_index)} videos.")
        elif db_source == "Supabase":
            st.caption(f"🟢 Connected to **Supabase** (`public.snapshot`) — Retrieved {len(snapshot_rows)} snapshots across {len(video_index)} videos.")
        else:
            st.caption("⚠️ Database offline or unreachable. Check credentials in `.env` and click Refresh DB.")

        with ctrl_col1:
            search_query = st.text_input(
                "🔍 Search by Video ID, Title, or Platform",
                placeholder="Type a video ID (e.g. 17876179380597021, XtFeuFZRP2k) or title...",
                help="Filter videos dynamically or paste a specific Video ID."
            ).strip()

        with ctrl_col2:
            platform_filter = st.selectbox(
                "Filter by Platform",
                options=["All Platforms", "Instagram", "Facebook", "YouTube"],
                index=0
            )

        # Filter matching videos
        filtered_vids = []
        for vid, info in video_index.items():
            plat_match = (platform_filter == "All Platforms") or (info["platform"].lower() == platform_filter.lower())
            query_match = (
                not search_query
                or search_query.lower() in vid.lower()
                or search_query.lower() in info.get("title", "").lower()
                or search_query.lower() in info.get("platform", "").lower()
            )
            if plat_match and query_match:
                filtered_vids.append(vid)

        if not filtered_vids:
            st.info("No matching Video IDs found in `public.snapshot` for your current search filter.")
        else:
            # Build human-friendly labels for dropdown
            plat_icons = {"instagram": "📸 INSTAGRAM", "facebook": "📘 FACEBOOK", "youtube": "▶️ YOUTUBE"}
            vid_labels = {}
            for vid in filtered_vids:
                info = video_index[vid]
                p_badge = plat_icons.get(info["platform"].lower(), info["platform"].upper())
                t_str = f" — \"{info['title']}\"" if info.get("title") else ""
                s_cnt = len(info["snapshots"])
                vid_labels[vid] = f"{p_badge} | ID: {vid}{t_str} ({s_cnt} snapshot{'s' if s_cnt != 1 else ''})"

            selected_vid = st.selectbox(
                "🎯 Select Video ID to Inspect",
                options=filtered_vids,
                format_func=lambda x: vid_labels.get(x, x)
            )

            v_info = video_index[selected_vid]
            snaps = v_info["snapshots"]
            metric_defs = get_platform_metric_keys(v_info["platform"])

            st.markdown("---")

            if len(snaps) == 0:
                st.warning(
                    f"Video ID `{selected_vid}` is registered in the **`{v_info['platform']}`** table, "
                    "but no analytics snapshot has been recorded for it in `public.snapshot` yet. "
                    "Once your n8n Schedule Trigger runs, its snapshots will appear here automatically."
                )
            else:
                # --- Snapshot Comparison Pickers (Older vs Newer) ---
                snap_options = list(range(len(snaps)))
                default_old_idx = max(0, len(snaps) - 2)
                default_new_idx = len(snaps) - 1

                p_col1, p_col2 = st.columns(2)
                with p_col1:
                    old_idx = st.selectbox(
                        "🕒 Older Snapshot (Baseline)",
                        options=snap_options,
                        index=default_old_idx,
                        format_func=lambda i: f"Snapshot #{snaps[i]['snap_index']} — {snaps[i]['formatted_time']}"
                    )
                with p_col2:
                    new_idx = st.selectbox(
                        "🚀 Newer Snapshot (Comparison Target)",
                        options=snap_options,
                        index=default_new_idx,
                        format_func=lambda i: f"Snapshot #{snaps[i]['snap_index']} — {snaps[i]['formatted_time']}"
                    )

                older_snap = snaps[old_idx]
                newer_snap = snaps[new_idx]

                # --- 1. KPI Delta Cards ---
                st.markdown("#### 📈 Key Metric Deltas (Newer vs. Older Snapshot)")
                kpi_cols = st.columns(min(len(metric_defs), 7))
                for idx, (m_key, m_label) in enumerate(metric_defs):
                    col_k = kpi_cols[idx % len(kpi_cols)]
                    old_val = float(older_snap["metrics"].get(m_key) or 0)
                    new_val = float(newer_snap["metrics"].get(m_key) or 0)
                    delta_val = new_val - old_val

                    disp_new = int(new_val) if new_val.is_integer() else round(new_val, 2)
                    disp_delta = int(delta_val) if delta_val.is_integer() else round(delta_val, 2)

                    col_k.metric(
                        label=m_label,
                        value=disp_new,
                        delta=f"{disp_delta:+}" if delta_val != 0 else "0 (No change)"
                    )

                st.markdown("---")

                # --- 3. Visualized Charts ---
                st.markdown("#### 📊 Visualized Snapshot Charts")
                if HAS_CHARTS:
                    chart_tab1, chart_tab2, chart_tab3 = st.tabs([
                        "📊 Side-by-Side Comparison (Older vs. Newer)",
                        "📉 Historical Trend Across All Snapshots",
                        "📋 Detailed Comparison Table"
                    ])

                    with chart_tab1:
                        comp_rows = []
                        old_label = f"Older ({older_snap['formatted_time'][:16]})"
                        new_label = f"Newer ({newer_snap['formatted_time'][:16]})"
                        if old_label == new_label:
                            old_label = f"Older (#{older_snap['snap_index']})"
                            new_label = f"Newer (#{newer_snap['snap_index']})"

                        for m_key, m_label in metric_defs:
                            if m_key == "duration_seconds":
                                continue
                            v_old = float(older_snap["metrics"].get(m_key) or 0)
                            v_new = float(newer_snap["metrics"].get(m_key) or 0)
                            comp_rows.append({"Metric": m_label, "Snapshot": old_label, "Value": v_old, "Order": 1})
                            comp_rows.append({"Metric": m_label, "Snapshot": new_label, "Value": v_new, "Order": 2})

                        df_comp = pd.DataFrame(comp_rows)

                        bar_chart = (
                            alt.Chart(df_comp)
                            .mark_bar(cornerRadiusTopLeft=5, cornerRadiusTopRight=5)
                            .encode(
                                x=alt.X("Metric:N", title="Performance Metric", sort=None, axis=alt.Axis(labelAngle=0)),
                                xOffset=alt.XOffset("Snapshot:N", sort=[old_label, new_label]),
                                y=alt.Y("Value:Q", title="Count / Value"),
                                color=alt.Color(
                                    "Snapshot:N",
                                    scale=alt.Scale(domain=[old_label, new_label], range=["#64748b", "#6366f1"]),
                                    legend=alt.Legend(title="Snapshot Version", orient="top")
                                ),
                                tooltip=["Metric:N", "Snapshot:N", "Value:Q"]
                            )
                            .properties(height=360)
                        )
                        st.altair_chart(bar_chart, use_container_width=True)

                    with chart_tab2:
                        hist_rows = []
                        for s in snaps:
                            s_label = f"#{s['snap_index']} ({s['formatted_time'][:16]})"
                            for m_key, m_label in metric_defs:
                                if m_key == "duration_seconds":
                                    continue
                                val = float(s["metrics"].get(m_key) or 0)
                                hist_rows.append({
                                    "Snapshot": s_label,
                                    "Order": s["snap_index"],
                                    "Timestamp": s["formatted_time"],
                                    "Metric": m_label,
                                    "Value": val
                                })

                        df_hist = pd.DataFrame(hist_rows)
                        line_chart = (
                            alt.Chart(df_hist)
                            .mark_line(point=alt.OverlayMarkDef(size=80, filled=True), strokeWidth=3)
                            .encode(
                                x=alt.X("Snapshot:N", sort=alt.EncodingSortField(field="Order", order="ascending"), title="Snapshot Timeline", axis=alt.Axis(labelAngle=0)),
                                y=alt.Y("Value:Q", title="Metric Value"),
                                color=alt.Color("Metric:N", legend=alt.Legend(title="Metric", orient="top")),
                                tooltip=["Timestamp:N", "Metric:N", "Value:Q"]
                            )
                            .properties(height=360)
                        )
                        st.altair_chart(line_chart, use_container_width=True)

                    with chart_tab3:
                        table_rows = []
                        for m_key, m_label in metric_defs:
                            v_old = float(older_snap["metrics"].get(m_key) or 0)
                            v_new = float(newer_snap["metrics"].get(m_key) or 0)
                            diff = v_new - v_old
                            pct = ((diff / v_old) * 100.0) if v_old > 0 else (100.0 if v_new > 0 else 0.0)
                            trend_badge = "🟢 Growth" if diff > 0 else ("🔴 Decline" if diff < 0 else "⚪ Steady")
                            table_rows.append({
                                "Metric": m_label,
                                f"Older (#{older_snap['snap_index']})": v_old,
                                f"Newer (#{newer_snap['snap_index']})": v_new,
                                "Net Change": f"{diff:+g}",
                                "% Change": f"{pct:+.1f}%",
                                "Status": trend_badge
                            })
                        st.dataframe(pd.DataFrame(table_rows), use_container_width=True, hide_index=True)
                else:
                    st.info("Install `pandas` and `altair` to view interactive charts.")
