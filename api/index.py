import os
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path

import requests
from flask import Flask, jsonify, request, send_from_directory
from openai import OpenAI
from dotenv import load_dotenv
import unicodedata

# Load environment variables from .env file if it exists
load_dotenv()

# Basic configuration via environment variables (reads from .env file)
BASE_URL = "https://api.webflow.com/v2"
WEBFLOW_API_TOKEN = os.getenv("WEBFLOW_API_TOKEN")
WEBFLOW_SITE_ID = os.getenv("WEBFLOW_SITE_ID")
WEBFLOW_COLLECTION_ID = os.getenv("WEBFLOW_COLLECTION_ID")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
UNSPLASH_ACCESS_KEY = os.getenv("UNSPLASH_ACCESS_KEY")

HEADERS = {
    "Authorization": f"Bearer {WEBFLOW_API_TOKEN}" if WEBFLOW_API_TOKEN else "",
    "Accept-Version": "2.0.0",
    "Content-Type": "application/json",
}


app = Flask(__name__)

# Determine the static directory (one level up from api/)
STATIC_DIR = Path(__file__).parent.parent / "static"


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", (text or "").lower())
    slug = slug.strip("-")
    return slug[:256]


def strip_html(html: str) -> str:
    return re.sub(r"<[^>]+>", " ", html or " ")


def estimate_reading_time_minutes(html: str) -> int:
    text = strip_html(html)
    words = re.findall(r"\w+", text)
    minutes = math.ceil(len(words) / 230) if words else 1
    return max(1, minutes)


def _upload_asset(binary: bytes, filename: str) -> tuple[str, str]:
    """Upload binary to Webflow Assets and return (fileId, hostedUrl)."""
    if not (WEBFLOW_SITE_ID and WEBFLOW_API_TOKEN):
        raise RuntimeError("Missing WEBFLOW_SITE_ID or WEBFLOW_API_TOKEN")

    # 1) Create asset record and get pre-signed S3 URL
    meta_endpoint = f"{BASE_URL}/sites/{WEBFLOW_SITE_ID}/assets"
    meta_resp = requests.post(
        meta_endpoint,
        headers=HEADERS,
        json={
            "fileName": filename,
            # fileHash is optional in v2; included for better caching when available
        },
        timeout=30,
    )
    if not meta_resp.ok:
        raise RuntimeError(f"Asset init failed: {meta_resp.status_code} {meta_resp.text}")

    meta = meta_resp.json()
    upload_url = meta["uploadUrl"]
    fields = {k: str(v) for k, v in meta.get("uploadDetails", {}).items()}

    files = {
        "file": (filename, binary, meta.get("contentType", "image/jpeg")),
    }

    # 2) Upload file to S3
    s3_resp = requests.post(upload_url, data=fields, files=files, timeout=60)
    if not (200 <= s3_resp.status_code < 300):
        raise RuntimeError(f"S3 upload failed: {s3_resp.status_code} {s3_resp.text}")

    return meta["id"], meta["hostedUrl"]


def _upload_image_from_url(image_url: str, fallback_name: str = "featured.jpg") -> dict:
    resp = requests.get(image_url, timeout=30)
    resp.raise_for_status()
    file_id, hosted_url = _upload_asset(resp.content, fallback_name)
    return {"url": hosted_url, "alt": os.path.basename(fallback_name) or "Featured image"}


def _unsplash_search_first(title_or_query: str) -> dict | None:
    if not UNSPLASH_ACCESS_KEY:
        return None
    url = (
        "https://api.unsplash.com/search/photos"
        f"?query={requests.utils.quote(title_or_query)}&per_page=5&page=1&order_by=relevant&orientation=landscape&content_filter=high&client_id={UNSPLASH_ACCESS_KEY}"
    )
    r = requests.get(url, timeout=15)
    if not r.ok:
        return None
    results = r.json().get("results", [])
    return results[0] if results else None


def _resolve_featured_image(title: str, featured_image_url: str | None) -> dict | None:
    if featured_image_url:
        try:
            return _upload_image_from_url(featured_image_url, "featured.jpg")
        except Exception:
            pass
    # Fallback to Unsplash
    img = _unsplash_search_first(title)
    if img and img.get("urls", {}).get("regular"):
        try:
            return _upload_image_from_url(img["urls"]["regular"], f"unsplash-{img.get('id','image')}.jpg")
        except Exception:
            return None
    return None


def _publish_items_for_collection(collection_id: str, item_ids: list[str]):
    publish_endpoint = f"{BASE_URL}/collections/{collection_id}/items/publish"
    return requests.post(publish_endpoint, headers=HEADERS, json={"itemIds": item_ids}, timeout=30)

def _delete_item(collection_id: str, item_id: str) -> requests.Response:
    endpoint = f"{BASE_URL}/collections/{collection_id}/items/{item_id}"
    return requests.delete(endpoint, headers=HEADERS, timeout=30)


def create_blog_post_item(*, title: str, subtitle: str, body_html: str, author_id: str | None,
                          category_id: str | None, featured_image: dict | None,
                          publish: bool, publish_date_iso: str | None,
                          banner_title: str | None = None, banner_description: str | None = None,
                          banner_image: str | None = None, banner_link: str | None = None,
                          banner_category: str | None = None) -> dict:
    if not WEBFLOW_COLLECTION_ID:
        raise RuntimeError("Missing WEBFLOW_COLLECTION_ID")

    field_data: dict = {
        "name": title,
        "slug": slugify(title),
        "subtitle-small-description": subtitle,
        "body-copy": body_html,
        "publish-date": publish_date_iso
            or datetime.now(timezone.utc).strftime("%Y-%m-%dT00:00:00.000Z"),
        "reading-time-in-minutes": estimate_reading_time_minutes(body_html),
    }

    if featured_image:
        field_data["featured-image"] = featured_image
    if author_id:
        field_data["author"] = author_id
    if category_id:
        field_data["category"] = category_id
    
    # Add banner fields if provided
    if banner_title:
        field_data["banner-title"] = banner_title
    if banner_description:
        field_data["banner-description"] = banner_description
    if banner_link:
        field_data["banner-link"] = banner_link
    if banner_image:
        field_data["banner-image"] = {"url": banner_image} if isinstance(banner_image, str) else banner_image
    if banner_category:
        # Capitalize the category before sending to Webflow
        field_data["banner-category"] = banner_category.capitalize() if isinstance(banner_category, str) else banner_category

    payload = {
        "isDraft": not publish,
        "isArchived": False,
        "fieldData": field_data,
    }

    endpoint = f"{BASE_URL}/collections/{WEBFLOW_COLLECTION_ID}/items"
    resp = requests.post(endpoint, headers=HEADERS, json=payload, timeout=60)
    if not resp.ok:
        raise RuntimeError(f"Create item failed: {resp.status_code} {resp.text}")

    item = resp.json()
    # Optionally publish
    if publish and item.get("id"):
        pub = _publish_items_for_collection(WEBFLOW_COLLECTION_ID, [item["id"]])
        if pub.status_code not in (200, 202):
            # Non-fatal: return item anyway
            item["publishWarning"] = {
                "status": pub.status_code,
                "body": pub.text,
            }
    return item


def generate_content_with_openai(prompt: str) -> dict:
    if not OPENAI_API_KEY:
        raise RuntimeError("Missing OPENAI_API_KEY")

    client = OpenAI(api_key=OPENAI_API_KEY)
    
    # Step 1: Try direct format first (faster)
    content_prompt = (
        f"{prompt}\n\n"
        "Create a comprehensive, well-researched blog post. Use web search for current information.\n\n"
        "Return in this EXACT format:\n"
        "title: [50-60 character title]\n"
        "subtitle: [20-30 word engaging summary]\n"
        "body-html: [700-1000 word HTML content with <h5> headings, <p> paragraphs, <strong> emphasis, "
        "and inline <sup><a href='URL'>[n]</a></sup> citations]\n\n"
        "Be informative and neutral. Cite sources inline with clickable superscript numbers."
    )

    print("🔍 Calling GPT-5 with web search...")
    
    # Use Responses API with web search
    response = client.responses.create(
        model="gpt-5",
        tools=[{"type": "web_search"}],
        input=content_prompt,
        reasoning={"effort": "low"}
    )
    
    print("✅ GPT-5 response received!")
    
    # Extract the message content with annotations
    message_text = None
    annotations = []
    
    for item in response.output:
        if item.type == "message" and hasattr(item, 'content'):
            for content_item in item.content:
                if hasattr(content_item, 'text'):
                    message_text = content_item.text
                if hasattr(content_item, 'annotations') and content_item.annotations:
                    annotations = content_item.annotations
                    print(f"📚 Found {len(annotations)} inline citations")
    
    if not message_text:
        raise RuntimeError("No text content in GPT-5 response")
    
    # Step 2: Try to parse the simple format
    try:
        print("📝 Attempting to parse title:/subtitle:/body-html: format...")
        data = _parse_simple_format(message_text)
        print("✅ Successfully parsed simple format!")
        return data
    except Exception as e:
        print(f"⚠️  Simple format parsing failed: {e}")
        print("🔄 Falling back to JSON structured format...")
    
    # Fallback: Use structured JSON parsing
    # Clean up any markdown-style citations GPT-5 may have added
    import re as regex
    message_text = regex.sub(r'\(\[([^\]]+)\]\([^\)]+\)\)\[\d+\]', r'\1', message_text)
    message_text = regex.sub(r'\[\d+\](?=[\s\.,;]|$)', '', message_text)
    
    # Insert citation superscripts at annotation positions
    text_with_citations = message_text
    citation_map = {}
    for idx, annotation in enumerate(annotations, 1):
        if annotation.type == "url_citation":
            citation_map[idx] = {
                'url': annotation.url,
                'title': annotation.title,
                'start': annotation.start_index,
                'end': annotation.end_index
            }
    
    sorted_citations = sorted(citation_map.items(), key=lambda x: x[1]['start'], reverse=True)
    for cite_num, cite_data in sorted_citations:
        url = cite_data['url']
        title = cite_data['title']
        citation_html = f'<sup><a href="{url}" target="_blank" rel="noopener" title="{title}">[{cite_num}]</a></sup>'
        text_with_citations = text_with_citations[:cite_data['end']] + citation_html + text_with_citations[cite_data['end']:]
    
    # Use AI to structure into JSON
    structure_prompt = (
        f"Convert to JSON. PRESERVE all HTML tags:\n\n{text_with_citations}\n\n"
        '{"title": "...", "subtitle": "20-30 words max", "body": "HTML with citations"}\n'
        "Do NOT add Sources section."
    )
    
    structure_response = client.chat.completions.create(
        model="gpt-5-nano",
        messages=[
            {"role": "system", "content": "Format as JSON. Preserve HTML. Return ONLY JSON."},
            {"role": "user", "content": structure_prompt}
        ]
    )

    content = (structure_response.choices[0].message.content or "").strip()
    content = re.sub(r"^```json\s*|```$", "", content, flags=re.DOTALL)
    
    try:
        data = json.loads(content)
    except Exception as e:
        raise RuntimeError(f"OpenAI returned invalid JSON: {content}") from e

    for key in ("title", "subtitle", "body"):
        if key not in data:
            raise RuntimeError("OpenAI JSON missing required keys")
    
    print(f"✅ Content generation complete!\n")
    return data


def _parse_simple_format(text: str) -> dict:
    """Parse the simple title:/subtitle:/body-html: format"""
    lines = text.split('\n')
    title = None
    subtitle = None
    body_lines = []
    current_section = None
    
    for line in lines:
        if line.startswith('title:'):
            title = line[6:].strip()
            current_section = 'title'
        elif line.startswith('subtitle:'):
            subtitle = line[9:].strip()
            current_section = 'subtitle'
        elif line.startswith('body-html:'):
            current_section = 'body'
            body_part = line[10:].strip()
            if body_part:
                body_lines.append(body_part)
        elif current_section == 'body' and line.strip():
            body_lines.append(line)
    
    if not title or not subtitle or not body_lines:
        raise ValueError("Missing required fields in simple format")
    
    return {
        "title": title,
        "subtitle": subtitle,
        "body": '\n'.join(body_lines)
    }


@app.get("/")
def index():
    """Serve the main UI"""
    return send_from_directory(STATIC_DIR, "index.html")


@app.get("/<path:filename>")
def serve_static(filename):
    """Serve static files (CSS, JS, images)"""
    return send_from_directory(STATIC_DIR, filename)


@app.get("/health")
def health():
    return jsonify({"ok": True, "time": datetime.now(timezone.utc).isoformat()})


@app.get("/api/authors")
def get_authors():
    """Fetch all authors from Webflow CMS"""
    # Authors collection ID - correct one from your API example
    authors_collection_id = "66ba3e4dfc6866b033934371"
    
    try:
        endpoint = f"{BASE_URL}/collections/{authors_collection_id}/items"
        resp = requests.get(endpoint, headers=HEADERS, timeout=30)
        
        if not resp.ok:
            return jsonify({"ok": False, "error": f"Failed to fetch authors: {resp.status_code} - {resp.text}"}), 500
        
        data = resp.json()
        authors = []
        for item in data.get("items", []):
            field_data = item.get("fieldData", {})
            authors.append({
                "id": item.get("id"),
                "name": field_data.get("name", "Unknown Author")
            })
        
        return jsonify({"ok": True, "authors": authors})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.get("/api/categories")
def get_categories():
    """Fetch all categories from Webflow CMS"""
    # Categories collection ID - correct one from your API example
    categories_collection_id = "66ba3e234a55e39f3f62ee0f"
    
    try:
        endpoint = f"{BASE_URL}/collections/{categories_collection_id}/items"
        resp = requests.get(endpoint, headers=HEADERS, timeout=30)
        
        if not resp.ok:
            return jsonify({"ok": False, "error": f"Failed to fetch categories: {resp.status_code} - {resp.text}"}), 500
        
        data = resp.json()
        categories = []
        for item in data.get("items", []):
            field_data = item.get("fieldData", {})
            categories.append({
                "id": item.get("id"),
                "name": field_data.get("name", "Unknown Category")
            })
        
        return jsonify({"ok": True, "categories": categories})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500




@app.post("/edit")
def edit_content():
    """Simplified AI-assisted content editor using JSON diff format"""
    if request.is_json:
        payload = request.get_json() or {}
    else:
        payload = request.form.to_dict() if request.form else {}

    title = payload.get("title", "")
    subtitle = payload.get("subtitle", "")
    body = payload.get("body", "")
    edit_prompt = payload.get("edit_prompt", "").strip()

    if not edit_prompt:
        return jsonify({"ok": False, "error": "Missing 'edit_prompt'"}), 400

    try:
        print(f"✏️  AI Edit requested: {edit_prompt}")
        
        client = OpenAI(api_key=OPENAI_API_KEY)

        # Ask the model for a simple structured diff
        prompt = f"""You are an expert blog editor. Apply the following edit to the HTML blog content.

Edit request:
{edit_prompt}

Current content:
title: {title}
subtitle: {subtitle}
body-html:
{body}

Return ONLY valid JSON in this exact format (no markdown code blocks, no extra text):
{{
  "title": "New title or 'NO CHANGE'",
  "subtitle": "New subtitle or 'NO CHANGE'",
  "body_changes": [
    {{
      "find": "Exact snippet of HTML or text to replace",
      "replace": "New text or HTML to insert instead"
    }}
  ]
}}

CRITICAL RULES:
- Keep <sup><a href='...'>[n]</a></sup> citations intact unless explicitly told to change them
- Output ONLY the JSON object, nothing else
- Make "find" snippets as precise as possible to avoid duplicate matches
- If only changing title/subtitle, make body_changes an empty array []
- Use 'NO CHANGE' (exact string) if not modifying title or subtitle
- When only adding content, find a few words where the change should be made and append those words in addition to the new content.
EX: Text: 'Have a good day' find: 'a good' replace: 'a good, spectacular, marvelous'
Final Result: 'Have a good, spectacular, marvelous day'
"""

        response = client.chat.completions.create(
            model="gpt-5-mini",
            messages=[
                {"role": "system", "content": "You edit HTML precisely and output strict JSON. No prose, no markdown blocks."},
                {"role": "user", "content": prompt}
            ],
            reasoning_effort="low"
        )

        content = response.choices[0].message.content.strip()
        print(f"📝 Raw AI response:\n{content[:300]}...")
        
        # Strip markdown code blocks if present
        content = re.sub(r"^```json\s*|```$", "", content, flags=re.DOTALL | re.MULTILINE)
        content = content.strip()

        # Parse JSON
        data = json.loads(content)

        new_title = data.get("title", "NO CHANGE")
        new_subtitle = data.get("subtitle", "NO CHANGE")
        diffs = data.get("body_changes", [])

        # Apply changes to body
        new_body = body
        changes_applied = 0
        for idx, change in enumerate(diffs, 1):
            find = change.get("find", "").strip()
            replace = change.get("replace", "").strip()
            
            if find and find in new_body:
                new_body = new_body.replace(find, replace, 1)
                print(f"  ✅ Change #{idx}: Replaced '{find[:60]}...'")
                changes_applied += 1
            elif find:
                print(f"  ⚠️  Change #{idx}: Could not find snippet: '{find[:60]}...'")

        # Apply title/subtitle if changed
        if new_title == "NO CHANGE":
            new_title = title
        else:
            print(f"  ✅ Title updated")
            
        if new_subtitle == "NO CHANGE":
            new_subtitle = subtitle
        else:
            print(f"  ✅ Subtitle updated")

        print(f"✅ Edit complete: {changes_applied} body changes applied")

        return jsonify({
            "ok": True,
            "title": new_title,
            "subtitle": new_subtitle,
            "body": new_body,
            "changes": f"{changes_applied} changes applied"
        })

    except json.JSONDecodeError as je:
        print(f"❌ JSON parse failed: {je}")
        print(f"   Content was: {content[:200]}...")
        return jsonify({"ok": False, "error": f"Invalid JSON from AI: {str(je)}"}), 500
    except Exception as e:
        print(f"❌ Edit failed: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"ok": False, "error": str(e)}), 500


@app.post("/generate-banner")
def generate_banner():
    """Use AI to recommend related content from search index"""
    if request.is_json:
        payload = request.get_json() or {}
    else:
        payload = request.form.to_dict() if request.form else {}
    
    title = payload.get("title", "").strip()
    body = payload.get("body", "").strip()
    
    if not title or not body:
        return jsonify({"ok": False, "error": "Missing 'title' or 'body'"}), 400
    
    try:
        print(f"🎯 Generating banner recommendation for: {title[:50]}...")
        
        # Load search index
        search_index_path = Path(__file__).parent.parent / "search_index.json"
        
        if not search_index_path.exists():
            return jsonify({"ok": False, "error": "Search index not found. Run generate_search_index.py first."}), 500
        
        with open(search_index_path, 'r', encoding='utf-8') as f:
            search_index = json.load(f)
        
        print(f"📚 Loaded {len(search_index)} items from search index")
        
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        # Use GPT-5 Responses API to find the most relevant content
        prompt = f"""You are a content recommendation system. Given a blog post, find the SINGLE most relevant related content item from the search index.

Blog Post Title: {title}

Blog Post Content (first 1000 chars):
{body[:1000]}

Search Index (all available content):
{json.dumps(search_index)}

Return ONLY a valid JSON object with this EXACT structure:
{{
  "url": "the exact URL from the search index item you recommend"
}}

Choose the ONE item that is most thematically related and would be most interesting to readers of this blog post. Return ONLY the JSON, no other text."""

        response = client.responses.create(
            model="gpt-5",
            input=prompt,
            reasoning={"effort": "medium"}
        )
        
        # Extract response from Responses API format
        response_text = ""
        for item in response.output:
            if hasattr(item, "type") and item.type == "message":
                if hasattr(item, "content") and item.content:
                    for content_item in item.content:
                        if hasattr(content_item, "type") and content_item.type == "output_text":
                            if hasattr(content_item, "text") and content_item.text:
                                response_text += content_item.text
        
        response_text = response_text.strip()
        print(f"📝 AI response: {response_text[:200]}...")
        
        # Parse JSON response
        response_text = re.sub(r"^```json\s*|```$", "", response_text, flags=re.DOTALL | re.MULTILINE)
        data = json.loads(response_text)
        
        recommended_url = data.get("url", "").strip()
        
        if not recommended_url:
            return jsonify({"ok": False, "error": "AI did not return a valid URL"}), 500
        
        print(f"🔗 Recommended URL: {recommended_url}")
        
        # Find the item in search index
        recommended_item = None
        for item in search_index:
            if item.get("url") == recommended_url:
                recommended_item = item
                break
        
        if not recommended_item:
            return jsonify({"ok": False, "error": "Recommended URL not found in search index"}), 500
        
        # Build banner data
        banner = {
            "title": recommended_item.get("title", ""),
            "description": recommended_item.get("description", ""),
            "link": recommended_item.get("url", ""),
            "image": recommended_item.get("image"),
            "category": recommended_item.get("category", "")
        }
        
        print(f"✅ Banner generated: {banner['title'][:50]} (category: {banner['category']})")
        
        return jsonify({
            "ok": True,
            "banner": banner
        })
        
    except json.JSONDecodeError as je:
        print(f"❌ JSON parse failed: {je}")
        return jsonify({"ok": False, "error": f"Invalid JSON from AI: {str(je)}"}), 500
    except Exception as e:
        print(f"❌ Banner generation failed: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"ok": False, "error": str(e)}), 500


def _normalize_for_match(text: str) -> str:
    """
    Normalize text for robust matching:
    - lowercased
    - strip diacritics
    - collapse non-alphanumeric to single spaces
    - trim extra spaces
    """
    if not text:
        return ""
    # Strip diacritics
    nfkd = unicodedata.normalize("NFKD", text)
    ascii_text = "".join(ch for ch in nfkd if not unicodedata.combining(ch))
    # Lowercase and keep alnum/space
    lowered = ascii_text.lower()
    cleaned = re.sub(r"[^a-z0-9]+", " ", lowered)
    return cleaned.strip()


def _any_keyword_in(text: str, keywords: list[str]) -> bool:
    base = _normalize_for_match(text)
    for kw in keywords:
        if not kw:
            continue
        if _normalize_for_match(kw) in base:
            return True
    return False


@app.post("/auto-link")
def auto_link():
    """
    Analyze provided text for:
    - Artist names (matches to /artists/*)
    - Show names (matches to /shows/*)
    - Event-related services (VIP, corporate, educational, holiday, group)
    
    Returns links to relevant pages from search_index.json.
    """
    if request.is_json:
        payload = request.get_json() or {}
    else:
        payload = request.form.to_dict() if request.form else {}
    
    title = (payload.get("title") or "").strip()
    body = (payload.get("body") or "").strip()
    text = f"{title}\n{body}"
    if not text.strip():
        return jsonify({"ok": False, "error": "Missing 'title' or 'body'"}), 400
    
    try:
        # Load search index
        search_index_path = Path(__file__).parent.parent / "search_index.json"
        if not search_index_path.exists():
            return jsonify({"ok": False, "error": "Search index not found. Run generate_search_index.py first."}), 500
        with open(search_index_path, "r", encoding="utf-8") as f:
            search_index = json.load(f)
        
        # Prepare lookup maps
        norm_to_items_artists: dict[str, list[dict]] = {}
        norm_to_items_shows: dict[str, list[dict]] = {}
        service_candidates: list[dict] = []
        
        for item in search_index:
            cat = (item.get("category") or "").lower()
            title_i = item.get("title") or ""
            desc_i = item.get("description") or ""
            url_i = item.get("url") or ""
            norm_title = _normalize_for_match(title_i)
            
            if cat == "artists":
                norm_to_items_artists.setdefault(norm_title, []).append(item)
            elif cat == "shows":
                norm_to_items_shows.setdefault(norm_title, []).append(item)
            else:
                # Pages (mostly 'home' via sitemap) are candidates for services
                if cat in ("home", "blog"):
                    service_candidates.append(item)
        
        # Detect artists and shows by normalized title inclusion with word boundaries
        norm_text = f" {_normalize_for_match(text)} "
        
        def detect_matches(norm_map: dict[str, list[dict]]) -> list[dict]:
            seen_urls = set()
            results = []
            for norm_name, items in norm_map.items():
                if not norm_name:
                    continue
                # Simple word-boundary containment: surround with spaces
                probe = f" {norm_name} "
                if probe in norm_text:
                    for it in items:
                        u = it.get("url")
                        if u and u not in seen_urls:
                            seen_urls.add(u)
                            results.append({
                                "title": it.get("title"),
                                "url": u,
                                "image": it.get("image")
                            })
            return results
        
        detected_artists = detect_matches(norm_to_items_artists)
        detected_shows = detect_matches(norm_to_items_shows)
        
        # Event-related keyword groups
        keyword_groups: dict[str, list[str]] = {
            "vip": [
                "vip", "backstage", "meet and greet", "meet & greet",
                "premium", "concierge", "exclusive", "red carpet"
            ],
            "corporate": [
                "corporate", "team building", "offsite", "retreat",
                "client event", "employee event", "company outing",
                "incentive", "sponsorship", "brand activation"
            ],
            "educational": [
                "education", "educational", "student", "school",
                "workshop", "master class", "masterclass",
                "matinee", "field trip", "curriculum"
            ],
            "holiday": [
                "holiday", "christmas", "hanukkah", "new year",
                "valentine", "mother s day", "fathers day", "gift", "seasonal",
                "halloween", "black friday", "cyber monday"
            ],
            "group": [
                "group tickets", "group sales", "group rate", "groups",
                "bulk tickets", "group reservations"
            ],
        }
        
        matched_categories = []
        for cat_name, kws in keyword_groups.items():
            if _any_keyword_in(text, kws):
                matched_categories.append(cat_name)
        
        # Rank service candidates by keyword hits in title/desc/url
        services: list[dict] = []
        if matched_categories:
            # Flatten keywords we care about from matched categories
            active_keywords = [kw for cat_name in matched_categories for kw in keyword_groups[cat_name]]
            
            scored = []
            for it in service_candidates:
                score = 0
                t = it.get("title") or ""
                d = it.get("description") or ""
                u = it.get("url") or ""
                for kw in active_keywords:
                    if _any_keyword_in(t, [kw]):
                        score += 3
                    if _any_keyword_in(d, [kw]):
                        score += 2
                    if _any_keyword_in(u, [kw]):
                        score += 1
                if score > 0:
                    scored.append((score, it))
            # Sort by score desc, then keep top 8
            scored.sort(key=lambda x: x[0], reverse=True)
            top = [it for score, it in scored[:8]]
            for it in top:
                services.append({
                    "title": it.get("title"),
                    "url": it.get("url"),
                    "image": it.get("image"),
                    "category": "service"
                })
        
        return jsonify({
            "ok": True,
            "matches": {
                "artists": detected_artists,
                "shows": detected_shows,
                "services": services,
                "matched_categories": matched_categories
            }
        })
    
    except Exception as e:
        print(f"❌ Auto-link failed: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"ok": False, "error": str(e)}), 500


@app.post("/search-images")
def search_images():
    """Search Unsplash for images based on article content"""
    if request.is_json:
        payload = request.get_json() or {}
    else:
        payload = request.form.to_dict() if request.form else {}
    
    title = payload.get("title", "").strip()
    body = payload.get("body", "").strip()
    
    if not title:
        return jsonify({"ok": False, "error": "Missing 'title'"}), 400
    
    try:
        print(f"🔍 Generating Unsplash search query for: {title[:50]}...")
        
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        # Generate search query using AI
        system_prompt = (
            "In 5 words or less, generate a stock image search query for an article. "
            "Return ONLY strict JSON: {\"q\": string}. Do not wrap in markdown. "
            "Focus on visual concepts that would make good photos."
        )
        
        user_prompt = f"TITLE: {title}\n\nBODY PREVIEW: {body[:500]}"
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7
        )
        
        content = response.choices[0].message.content.strip()
        content = re.sub(r"^```json\s*|```$", "", content, flags=re.DOTALL | re.MULTILINE)
        
        try:
            data = json.loads(content)
            query = data.get("q", title)[:100]
        except:
            query = title[:100]
        
        print(f"📝 Unsplash search query: {query}")
        
        # Search Unsplash
        unsplash_url = (
            f"https://api.unsplash.com/search/photos"
            f"?query={requests.utils.quote(query)}"
            f"&per_page=6"
            f"&page=1"
            f"&order_by=relevant"
            f"&orientation=landscape"
            f"&content_filter=high"
            f"&client_id={UNSPLASH_ACCESS_KEY}"
        )
        
        unsplash_resp = requests.get(unsplash_url, timeout=15)
        unsplash_resp.raise_for_status()
        
        results = unsplash_resp.json().get("results", [])
        
        # Filter out images with text/signs/typography
        disallowed_keywords = ["sign", "signage", "text", "letter", "word", "typography", "quote", "poster"]
        
        filtered_results = []
        for item in results:
            desc = (item.get("description") or "") + " " + (item.get("alt_description") or "")
            if not any(bad in desc.lower() for bad in disallowed_keywords):
                filtered_results.append({
                    "id": item["id"],
                    "url": item["urls"]["regular"],
                    "thumb": item["urls"]["thumb"],
                    "alt": item.get("alt_description") or title,
                    "photographer": item["user"]["name"],
                    "photographer_url": item["user"]["links"]["html"]
                })
        
        # If we filtered everything out, just use the first few results
        if not filtered_results and results:
            for item in results[:6]:
                filtered_results.append({
                    "id": item["id"],
                    "url": item["urls"]["regular"],
                    "thumb": item["urls"]["thumb"],
                    "alt": item.get("alt_description") or title,
                    "photographer": item["user"]["name"],
                    "photographer_url": item["user"]["links"]["html"]
                })
        
        print(f"✅ Found {len(filtered_results)} images")
        
        return jsonify({
            "ok": True,
            "query": query,
            "images": filtered_results
        })
        
    except Exception as e:
        print(f"❌ Image search failed: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"ok": False, "error": str(e)}), 500


@app.post("/generate")
def generate():
    """Generate content but DON'T save to Webflow yet"""
    if request.is_json:
        payload = request.get_json() or {}
    else:
        payload = request.form.to_dict() if request.form else {}

    prompt = payload.get("prompt", "").strip()
    if not prompt:
        return jsonify({"error": "Missing 'prompt'"}), 400

    featured_image_url = payload.get("featured_image_url")

    try:
        content = generate_content_with_openai(prompt)
        featured_image = _resolve_featured_image(content.get("title", ""), featured_image_url)
        
        # Return content for editing, DON'T create item yet
        return jsonify({
            "ok": True,
            "content": {
                "title": content["title"].strip(),
                "subtitle": content["subtitle"].strip(),
                "body": content["body"].strip(),
                "featured_image": featured_image
            }
        })
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.post("/create-draft")
def create_draft():
    """Create the draft in Webflow after user edits"""
    if request.is_json:
        payload = request.get_json() or {}
    else:
        payload = request.form.to_dict() if request.form else {}

    title = payload.get("title", "").strip()
    subtitle = payload.get("subtitle", "").strip()
    body_html = payload.get("body", "").strip()
    author_id = payload.get("author_id")
    category_id = payload.get("category_id")
    featured_image = payload.get("featured_image")
    publish = bool(payload.get("publish", False))
    publish_date_iso = payload.get("publish_date")
    
    # Banner fields (optional)
    banner_title = payload.get("banner_title")
    banner_description = payload.get("banner_description")
    banner_image = payload.get("banner_image")
    banner_link = payload.get("banner_link")
    banner_category = payload.get("banner_category")

    previous_item_id = payload.get("previous_item_id")

    if not title or not body_html:
        return jsonify({"error": "Missing title or body"}), 400

    try:
        # If provided, delete previous draft first (best-effort)
        if previous_item_id and WEBFLOW_COLLECTION_ID:
            try:
                del_resp = _delete_item(WEBFLOW_COLLECTION_ID, previous_item_id)
                if del_resp.status_code not in (200, 204):
                    # Not fatal; continue to create a new one
                    print(f"⚠️  Delete previous draft failed: {del_resp.status_code} {del_resp.text}")
            except Exception as de:
                print(f"⚠️  Exception deleting previous draft {previous_item_id}: {de}")

        item = create_blog_post_item(
            title=title,
            subtitle=subtitle,
            body_html=body_html,
            author_id=author_id,
            category_id=category_id,
            featured_image=featured_image,
            publish=publish,
            publish_date_iso=publish_date_iso,
            banner_title=banner_title,
            banner_description=banner_description,
            banner_image=banner_image,
            banner_link=banner_link,
            banner_category=banner_category,
        )
        
        # Add preview link to the response
        item_id = item.get("id")
        preview_link = (
            f"https://preview.webflow.com/preview/fs-broadway-plus"
            f"?utm_medium=preview_link&utm_source=designer&utm_content=fs-broadway-plus"
            f"&preview=28f75bac6c1adbbd39096b4a19f8d0df"
            f"&pageId=66ba3e1671702de92f5a9eeb"
            f"&itemId={item_id}"
            f"&locale=en&workflow=preview"
        )
        
        return jsonify({"ok": True, "item": item, "previewLink": preview_link})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.post("/publish-draft")
def publish_draft():
    """Publish an existing draft item on Webflow"""
    if request.is_json:
        payload = request.get_json() or {}
    else:
        payload = request.form.to_dict() if request.form else {}

    item_id = (payload.get("item_id") or "").strip()
    if not item_id:
        return jsonify({"ok": False, "error": "Missing 'item_id'"}), 400
    if not WEBFLOW_COLLECTION_ID:
        return jsonify({"ok": False, "error": "Missing WEBFLOW_COLLECTION_ID"}), 500

    try:
        resp = _publish_items_for_collection(WEBFLOW_COLLECTION_ID, [item_id])
        if resp.status_code not in (200, 202):
            return jsonify({"ok": False, "error": f"Publish failed: {resp.status_code} {resp.text}"}), 500
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

# Exported app for Vercel
if __name__ == "__main__":
    # Local dev server
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")))


