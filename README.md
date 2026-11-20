# 🚀 Auto Publish Content Pipeline

This app lets you upload videos, preview metadata for YouTube, Facebook, and Instagram, upload videos directly to Google Drive, and sync record payloads to Supabase for automated n8n processing.

---

## ⚡ Quick Start (1-Click Run on Windows)

Simply double-click **`run.bat`**.
It will:

1. Automatically install any missing dependencies (`requirements.txt`).
2. Pop open your browser on the first run so you can sign in with your own Google Drive account.
3. Launch the web interface automatically.

---

## 🔑 First-Time Google Drive Login

When you run the app for the first time:

1. A Google sign-in page will open in your default browser.
2. Select your Google account.
3. If you see **"Google hasn’t verified this app"**:
   - Click **Advanced** (bottom left).
   - Click **Go to [App Name] (unsafe)**.
   - Click **Continue / Allow**.
4. A personal `token.json` file will be generated on your computer. Your account is now linked!

> **Note:** If you ever want to switch to a different Google account, simply click the **"🔄 Switch Drive Account"** button in the app's sidebar.

---

## 🛠️ Manual Launch (Alternative)

If you prefer to run it manually from the terminal:

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Authorize Google Drive (first time only)
python authenticate.py

# 3. Start the application
streamlit run app.py
```

---

## 📁 What is Inside this Folder?

- `app.py`: Main Streamlit web application.
- `authenticate.py`: Standalone Google Drive OAuth login helper.
- `requirements.txt`: Python package requirements (includes `psycopg2-binary`, `streamlit`, `pandas`, `altair`).
- `run.bat`: 1-click Windows launcher.
- `.env.example`: Template for environment variables (copy to `.env`).
- `client_secret.example.json`: Example template for Google Cloud OAuth Client ID.
- `final core , final enhancements (v2).json`: Main n8n workflow file.
- `instagram_subworkflow.json`: Modular Instagram Reel publisher subworkflow.

---

## 🔒 Security & Secrets Management (For Git & Team Sharing)

The repository is configured to **strictly prevent leaking sensitive credentials**:

1. **`.env` is Git-ignored:** Contains real database passwords and secret keys. Never commit it!
   - Teammates should copy `.env.example` to `.env` and fill in their credentials:
     ```bash
     copy .env.example .env
     ```
2. **`token.json` & `client_secret.json` are Git-ignored:** Keeps personal Google account authorizations private. Teammates download their own `client_secret.json` from Google Cloud Console.

---

## 🗄️ AWS PostgreSQL Database Setup

The app now directly communicates with your **AWS PostgreSQL** database (matching the `final core aws db.json` n8n workflow).

Configure your database connection in [`.env`](file:///c:/Users/user/Desktop/my-app/.env):

```env
# AWS PostgreSQL Configuration
PG_HOST=your-rds-endpoint.amazonaws.com
PG_PORT=5432
PG_DATABASE=postgres
PG_USER=postgres
PG_PASSWORD=your_password
# Or full connection URI:
# DATABASE_URL=postgresql://user:password@endpoint:5432/dbname
```

### Supported Tables:
- **`public.videos`**: Stores video submission records (`title`, `description`, `platform`, `video_id`, `status`, `youtube`, `facebook`, `instagram`, `needs_compression`).
- **`public.snapshot`**: Stores performance snapshots (`snapshot` JSON, `collected at`, `created_at`).
- **`public.instagram`**: Stores Instagram video IDs (`"instagram id"`, `"created at"`).
- **`public.facebook`**: Stores Facebook video IDs (`"facebook id"`, `"created at"`).
- **`public.youtube`**: Stores YouTube video IDs (`"youtube id"`, `"created at"`).

*(Note: If AWS PostgreSQL credentials are not provided, the app gracefully falls back to Supabase).*
