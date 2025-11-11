## Blog Automation - Webflow CMS

A full-stack web application that generates blog posts using AI and publishes them to Webflow CMS.

### Features

- 🤖 **AI-Powered Content Generation** — Uses OpenAI GPT-5 with Responses API
- 🔍 **Real-Time Web Search** — Searches the web for current, accurate information
- 📚 **Automatic Source Citations** — All sources are listed with clickable links
- 🎨 **Modern Web UI** — Beautiful, responsive interface for easy content creation
- ✏️ **Rich Text Editor** — Visual WYSIWYG editor with live HTML sync
- 🤖 **AI-Assisted Editing** — Make targeted changes with natural language prompts
- 🖼️ **Smart Image Search** — AI-powered Unsplash image search and selection
- 📊 **Reading Time Estimation** — Automatically calculates reading time
- 🚀 **One-Click Publishing** — Publish directly to Webflow or save as draft
- 🔍 **Search Index Generator** — Create searchable JSON index from all CMS collections
- ☁️ **Vercel-Ready** — Deploy to production with one command

### Quick Start (Local Development)

**Step 1: Run setup**
```bash
chmod +x setup.sh run.sh
./setup.sh
```

**Step 2: Configure your API keys**

A `.env` file has been created with your Webflow credentials already filled in. Your OpenAI key is also set. Just verify it looks correct:

```bash
cat .env
```

If you need to change anything, edit the `.env` file:
```bash
nano .env  # or use your preferred editor
```

**Step 3: Start the server**
```bash
./run.sh
```

**Step 4: Open your browser**
```
http://localhost:5000
```

You'll see a beautiful web interface where you can:
- Enter a blog topic/prompt
- Configure author and category
- Choose to publish or save as draft
- Generate and publish with one click!

### Manual Setup (if setup.sh doesn't work)

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set environment variable
export OPENAI_API_KEY='your-key'

# Run server
python api/index.py
```

### API Endpoints

The app also exposes REST API endpoints:

**`GET /health`** — Health check
```bash
curl http://localhost:5000/health
```

**`POST /generate`** — Generate blog post
```bash
curl -X POST http://localhost:5000/generate \
  -H 'Content-Type: application/json' \
  -d '{
    "prompt": "Write about Houston theaters",
    "publish": false,
    "author_id": "671fcf925e3bc8b2761baaa2",
    "category_id": "66ba3e3134ef3aa9b21a2fa1",
    "featured_image_url": "https://example.com/image.jpg",
    "publish_date": "2025-10-14T00:00:00.000Z"
  }'
```

### Deploy to Vercel

**Step 1: Install Vercel CLI**
```bash
npm install -g vercel
```

**Step 2: Login to Vercel**
```bash
vercel login
```

**Step 3: Deploy**
```bash
vercel --prod
```

**Step 4: Set Environment Variables in Vercel Dashboard**
- `OPENAI_API_KEY` — Your OpenAI API key
- `WEBFLOW_API_TOKEN` — Already in code: `6becb991e6ec8f7d49688237e13c3e38dc8ddf818ea08ea54e6db1f751687215`
- `WEBFLOW_SITE_ID` — Already in code: `666990319136648fdc377552`
- `WEBFLOW_COLLECTION_ID` — Already in code: `66ba3e1671702de92f5a9ee1`
- `UNSPLASH_ACCESS_KEY` — (Optional) For automatic image fetching

### Technical Details

**Webflow Collection Field Mapping:**
- `name` — Blog post title
- `slug` — Auto-generated from title
- `subtitle-small-description` — Post subtitle
- `body-copy` — HTML content
- `publish-date` — Publication date (ISO 8601)
- `reading-time-in-minutes` — Auto-calculated
- `featured-image` — Image object with URL and alt text
- `author` — Reference to author collection
- `category` — Reference to category collection

**Technology Stack:**
- Backend: Flask (Python)
- Frontend: Vanilla HTML/CSS/JS with Quill.js WYSIWYG editor
- AI: OpenAI GPT-5 (with GPT-4o-mini for supporting tasks)
- CMS: Webflow API v2
- Images: Unsplash API
- Deployment: Vercel Serverless Functions

### Search Index Generation

Generate a searchable JSON index from all Webflow CMS collections (press, artists, shows, blog):

```bash
./generate_index.sh
```

Or run directly:
```bash
source venv/bin/activate
python3 generate_search_index.py
```

This will create `search_index.json` with the following structure:

```json
[
  {
    "id": "item_id",
    "title": "Item Title",
    "description": "Short description (for artists, shows, blog)",
    "url": "https://www.broadwayplus.com/category/slug",
    "image": "https://cdn.prod.website-files.com/.../image.jpg",
    "category": "press|artists|shows|blog"
  }
]
```

**Features:**
- ✅ Automatic pagination (handles 100+ items per collection)
- ✅ Smart description extraction (max 20 words for shows)
- ✅ Category-specific URL building
- ✅ Image fallback handling
- ✅ Progress logging

**Collections:**
- Press (66c6ebdfee466c476dfd533d) - 44 items
- Artists (667d5b4fca6fdba79be7fe45) - 944 items
- Shows (667d5b7f0f8c2b2d62e3d676) - 155 items
- Blog (66ba3e1671702de92f5a9ee1) - 3+ items
- Home (sitemap pages) - 24 items

**Sitemap Pages:**
The script also fetches additional pages from `sitemap.xml` including:
- Home page, VIP Concierge, Virtual 1-1, Education, Corporate
- Group Tickets, FAQ, Team, Press, Partners, Brand Assets
- Contact Us, Work With Us, Privacy Policy, Terms of Service
- And other public-facing pages

All pages are crawled for OpenGraph metadata (title, description, image) and included in the search index with category `"home"`.

**Excluded from Sitemap:**
- `/artist/*`, `/artists/*` (already in CMS)
- `/shows/*` (already in CMS)
- `/account/*`, `/admin/*`, `/users/*` (auth pages)
- `/cart/*`, `/checkout/*` (e-commerce)
- `/warehouse/*`, `/utility/*`, `/lockdatadrafts/*` (internal)

