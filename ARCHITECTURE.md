# Architecture Overview

## System Flow

```
┌─────────────────┐
│   User Browser  │
│   localhost:5000│
└────────┬────────┘
         │
         │ HTTP Request
         ▼
┌─────────────────────────────────────────┐
│         Flask Web Server                │
│  ┌───────────────────────────────────┐  │
│  │  Static File Server (HTML/CSS/JS) │  │
│  └───────────────────────────────────┘  │
│  ┌───────────────────────────────────┐  │
│  │  API Endpoints                    │  │
│  │  - GET  /        (Web UI)         │  │
│  │  - GET  /health  (Health check)   │  │
│  │  - POST /generate (Create post)   │  │
│  └───────────────────────────────────┘  │
└─────────────────┬───────────────────────┘
                  │
                  ├─────────────┐
                  │             │
                  ▼             ▼
         ┌────────────┐  ┌─────────────┐
         │  OpenAI    │  │  Webflow    │
         │  GPT-4o    │  │  CMS API v2 │
         │            │  │             │
         │ - Generate │  │ - Upload    │
         │   title    │  │   images    │
         │ - Generate │  │ - Create    │
         │   subtitle │  │   items     │
         │ - Generate │  │ - Publish   │
         │   body     │  │   posts     │
         └────────────┘  └─────────────┘
                  ▲
                  │
                  │ (Optional)
         ┌────────────────┐
         │   Unsplash API │
         │  - Fetch images│
         └────────────────┘
```

## Technology Stack

### Frontend
- **HTML5** — Structure
- **CSS3** — Modern, responsive styling with CSS variables
- **Vanilla JavaScript** — Form handling and API calls
- **No frameworks** — Pure web technologies for simplicity

### Backend
- **Python 3.9+** — Runtime
- **Flask 3.0** — Web framework
- **OpenAI Python SDK** — AI content generation
- **Requests** — HTTP client for Webflow/Unsplash APIs

### Deployment
- **Vercel** — Serverless hosting
- **Vercel Functions** — Python serverless runtime

## File Structure

```
bwp_blog_automation/
├── api/
│   └── index.py              # Main Flask application
├── static/
│   ├── index.html            # Web UI
│   ├── style.css             # Styles
│   └── script.js             # Frontend logic
├── venv/                     # Virtual environment (auto-created)
├── .gitignore                # Git ignore rules
├── requirements.txt          # Python dependencies
├── vercel.json               # Vercel deployment config
├── setup.sh                  # Setup script
├── run.sh                    # Run script
├── README.md                 # Full documentation
├── QUICKSTART.md             # Quick start guide
└── ARCHITECTURE.md           # This file
```

## Data Flow

### 1. User Input
```
User fills form:
  - Blog topic/prompt
  - Author ID (optional)
  - Category ID (optional)
  - Featured image URL (optional)
  - Publish checkbox
  - Publish date (optional)
```

### 2. Content Generation
```
Flask receives POST /generate
  ↓
OpenAI generates:
  - Title (50-60 chars)
  - Subtitle (100-150 words)
  - Body (700-1000 words, HTML)
  ↓
Reading time calculated from body
```

### 3. Image Handling
```
If featured_image_url provided:
  ↓ Download image
  ↓ Upload to Webflow Assets
Else:
  ↓ Search Unsplash for title
  ↓ Download first result
  ↓ Upload to Webflow Assets
```

### 4. CMS Creation
```
Build field data object:
  - name: title
  - slug: auto-generated from title
  - subtitle-small-description: subtitle
  - body-copy: HTML body
  - publish-date: ISO 8601 date
  - reading-time-in-minutes: calculated
  - featured-image: {url, alt}
  - author: reference ID
  - category: reference ID
  ↓
POST to Webflow /collections/{id}/items
  ↓
If publish=true:
  POST to /collections/{id}/items/publish
```

### 5. Response
```
Return to user:
  - Success/error status
  - Created item details
  - Webflow item ID
  - Draft/published status
```

## API Endpoints

### `GET /`
- Serves the web UI (`static/index.html`)
- Entry point for browser users

### `GET /health`
- Returns: `{"ok": true, "time": "ISO timestamp"}`
- Used for health checks and monitoring

### `POST /generate`
**Request:**
```json
{
  "prompt": "string (required)",
  "author_id": "string | null",
  "category_id": "string | null",
  "featured_image_url": "string | null",
  "publish": "boolean",
  "publish_date": "ISO 8601 string | null"
}
```

**Response (success):**
```json
{
  "ok": true,
  "item": {
    "id": "string",
    "isDraft": "boolean",
    "fieldData": {
      "name": "string",
      "slug": "string",
      "subtitle-small-description": "string",
      "body-copy": "string (HTML)",
      "publish-date": "string (ISO 8601)",
      "reading-time-in-minutes": "number",
      "featured-image": {
        "url": "string",
        "alt": "string"
      },
      "author": "string | null",
      "category": "string | null"
    }
  }
}
```

**Response (error):**
```json
{
  "ok": false,
  "error": "string"
}
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | ✅ Yes | OpenAI API key for content generation |
| `WEBFLOW_API_TOKEN` | ⚠️ Default set | Webflow v2 API token |
| `WEBFLOW_SITE_ID` | ⚠️ Default set | Webflow site ID |
| `WEBFLOW_COLLECTION_ID` | ⚠️ Default set | Target blog collection ID |
| `UNSPLASH_ACCESS_KEY` | ❌ Optional | For automatic image fetching |

## Security Considerations

1. **API Keys**: Never commit `.env` files or hardcode keys in frontend
2. **Input Validation**: All user inputs are validated before processing
3. **Error Handling**: Errors don't expose sensitive information
4. **CORS**: Configured for same-origin only in production
5. **Rate Limiting**: Consider adding rate limits in production

## Performance

- **Content Generation**: 30-60 seconds (OpenAI API latency)
- **Image Upload**: 2-5 seconds (depends on image size)
- **CMS Creation**: 1-2 seconds (Webflow API)
- **Total**: ~35-70 seconds per post

## Scalability

### Current Setup
- Single-threaded Flask development server
- Suitable for: Personal use, demos, testing

### Production Recommendations
- Use Vercel serverless functions (auto-scaling)
- Add Redis for caching
- Implement job queue for long-running tasks
- Add rate limiting and authentication

## Future Enhancements

- [ ] User authentication
- [ ] Multiple content templates
- [ ] Scheduled publishing
- [ ] Email notifications
- [ ] Analytics dashboard
- [ ] Batch post generation
- [ ] SEO optimization tools
- [ ] Content preview before publishing
- [ ] Multi-language support
- [ ] WordPress/other CMS integrations


