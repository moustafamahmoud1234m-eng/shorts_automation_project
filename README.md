# Multi-Platform Shorts Automation & AI Insights Engine

An n8n pipeline that publishes a single short-form video to **YouTube Shorts, Instagram Reels, Facebook ** from one Google Drive upload, then (Phase 2) pulls performance analytics and uses an AI model to generate optimization recommendations.

> Graduation project, Digital Egypt Pioneers Initiative (DEPI).
---

## Problem

1. **Manual publishing burnout:** the same video gets re-uploaded by hand to every platform.
2. **Data blindness:** creators rarely analyze cross-platform metrics, so weak hooks, captions and posting times go unnoticed.

## Solution

A closed-loop workflow in two phases:

| Phase | What it does |
| :--- | :--- |
| **1. Autonomous Publishing** | Drop an `.mp4` in Google Drive. n8n looks up its title/caption/hashtags in Google Sheets and publishes to every platform, logs the result and archives the file. |
| **2. AI Insights (feedback loop)** | 24-72 hours after publishing, pull views, likes, shares, comments and retention, send them to an AI model, and deliver a report with concrete recommendations. |

Cuts cross-posting effort to a few seconds per video and runs on free-tier APIs.

---

## Architecture

```
PHASE 1: PUBLISHING

Google Drive (Pending_Shorts)
        |
        v
  Drive Trigger (n8n)
        |
        v
  Get row(s) in Google Sheets   <-- title, caption, hashtags, status
        |
        v
  Download file (binary)
        |
  +-----+----------------+----------------+------------
  |                      |                |            
  v                      v                v            
YouTube node        Facebook Page     Instagram Reels  
(upload video)      (Graph API,       (Graph API,        
                    HTTP Request)     container flow)
  |                      |                |            
  +----------+-----------+----------------+------------
             |
             v
  Update Google Sheet (status, platform IDs, published_at)
             |
             v
  Move file -> Published_Shorts


PHASE 2: AI INSIGHTS

Schedule Trigger (24h / 72h)
        |
        v
Fetch analytics (YouTube Analytics, IG Insights, FB Insights, TikTok)
        |
        v
AI analysis (OpenRouter free models / Gemini)
        |
        v
Report -> Telegram / Email, and saved to Google Sheets
```

---

## Status

| Component | Status |
| :--- | :--- |
| Google Drive trigger, Sheets lookup, download | Done |
| YouTube upload | Done |
| Facebook Page publishing | Done |
| Instagram Reels publishing | In progress |
| Sheet logging and file archiving | Done |
| Phase 2: analytics + AI report | Planned |

---

## Tech Stack

- **n8n** (self-hosted with Docker, exposed through an ngrok static domain for OAuth callbacks)
- **Google Drive & Sheets APIs** (storage and metadata database)
- **YouTube Data API v3** and **YouTube Analytics API**
- **Meta Graph API** (Facebook Page videos, Instagram content publishing, Insights)
- **OpenRouter** (`:free` models) / Gemini for analysis
- **Telegram Bot** for report delivery

---

## Google Sheet Schema

Sheet name: `Shorts_Metadata`

| Column | Description |
| :--- | :--- |
| `file_name` | Must match the video's file name in Drive **exactly** |
| `title` | Video title |
| `caption` | Description / caption text |
| `hashtags` | e.g. `#shorts #tech` |
| `status` | `pending` -> `published` |
| `yt_id`, `ig_id`, `fb_id`| Platform post IDs, filled after publishing |
| `published_at` | Publish timestamp |

The workflow finds the metadata row by matching the uploaded file's name against `file_name`.

---

## Setup

### 1. Run n8n
Self-host n8n (Docker) and expose it on a public HTTPS URL (for example an ngrok static domain). Set `WEBHOOK_URL` to that URL so OAuth redirects work.

### 2. Google Cloud
1. Create a project and enable: Drive API, Sheets API, YouTube Data API v3, YouTube Analytics API.
2. Create an **OAuth client** (Web application) with redirect URI:
   `https://<your-domain>/rest/oauth2-credential/callback`
3. Add scopes: `drive`, `spreadsheets`, `youtube.upload`, `youtube.readonly`, `yt-analytics.readonly`.
4. Add yourself as a test user (or publish the app to avoid 7-day refresh token expiry).
5. In n8n, create **Google Drive OAuth2**, **Google Sheets OAuth2** and **YouTube OAuth2** credentials.

### 3. Google Drive & Sheet
Create two folders, `Pending_Shorts` and `Published_Shorts`, and the `Shorts_Metadata` sheet described above.

### 4. Meta (Facebook & Instagram)
1. Create a Meta app and add the **Manage everything on your Page** and **Instagram** use cases.
2. Requested permissions: `pages_show_list`, `pages_read_engagement`, `pages_manage_posts`, `read_insights`, `instagram_basic`, `instagram_content_publish`, `instagram_manage_insights`.
3. Exchange the short-lived user token for a long-lived one, then read `me/accounts` to get a **Page Access Token** that does not expire.
4. Instagram must be a **Professional** account linked to the Facebook Page. Get its ID with `GET /{page-id}?fields=instagram_business_account`.
5. Store the Page token in an n8n **Header Auth** credential (`Authorization: Bearer <token>`).

### 5. Import the workflow
Import `workflows/shorts_publisher.json` into n8n, reconnect your own credentials on each node, and activate the workflow.

---

## Usage

1. Add a row to `Shorts_Metadata` with the video's exact `file_name`, `title`, `caption`, `hashtags` and `status = pending`.
2. Upload the `.mp4` (vertical 9:16, under 60 seconds) to `Pending_Shorts`.
3. The workflow publishes to every platform, updates the sheet and moves the file to `Published_Shorts`.

---

## Known Limitations

- **YouTube:** uploads from an unverified API project may be locked to private until the project passes YouTube's API compliance audit. Channels also have a daily upload cap, and the API quota allows roughly 6 uploads per day (1,600 units per upload out of 10,000).
- **Content ID:** third-party music or footage can trigger automatic claims or regional blocks. Use your own or royalty-free media.
- **Instagram Reels:** publishing requires a **publicly accessible video URL**; the flow is create container -> poll status -> publish.
- **Meta apps** in Development mode only publish for users with a role on the app.
- **Name matching:** a one-character mismatch between the Drive file name and `file_name` stops the run.

---

## Security

- Never commit tokens, app secrets or client secrets.
- n8n credentials are not included in exported workflow JSON. Double-check your export before pushing.
- Rotate any token that was ever pasted into a chat, screenshot or log.

---

## Repository Structure

```
.
├── README.md
├── workflows/
│   └── shorts_publisher.json
├── docs/
│   ├── architecture.png
│   └── screenshots/
└── sheet_template.csv
```

---

## Roadmap

- [ ] Phase 1: Drive -> Sheets -> YouTube + Facebook
- [ ] Instagram Reels
- [ ] Phase 2: scheduled analytics fetch
- [ ] AI report (hook/retention, virality ratios, hashtag and timing advice)
- [ ] Telegram/email delivery and insights log in Sheets
