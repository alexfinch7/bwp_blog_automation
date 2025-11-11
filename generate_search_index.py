#!/usr/bin/env python3
"""
Generate search index JSON from Webflow CMS collections.

This script fetches data from multiple Webflow collections (press, artists, shows, blog)
and creates a unified JSON file for search functionality.
"""

import os
import json
import requests
import xml.etree.ElementTree as ET
from dotenv import load_dotenv
from typing import List, Dict, Optional
from bs4 import BeautifulSoup

# Load environment variables
load_dotenv()

# Configuration
WEBFLOW_API_TOKEN = os.getenv("WEBFLOW_API_TOKEN")
BASE_URL = "https://api.webflow.com/v2"

HEADERS = {
    "Authorization": f"Bearer {WEBFLOW_API_TOKEN}",
    "Accept-Version": "2.0.0",
    "Content-Type": "application/json",
}

# Collection configurations
COLLECTIONS = {
    "press": {
        "collection_id": "66c6ebdfee466c476dfd533d",
        "url_prefix": "https://www.broadwayplus.com/press/",
        "extract_description": False
    },
    "artists": {
        "collection_id": "667d5b4fca6fdba79be7fe45",
        "url_prefix": "https://www.broadwayplus.com/artists/",
        "extract_description": True
    },
    "shows": {
        "collection_id": "667d5b7f0f8c2b2d62e3d676",
        "url_prefix": "https://www.broadwayplus.com/shows/",
        "extract_description": True
    },
    "blog": {
        "collection_id": "66ba3e1671702de92f5a9ee1",
        "url_prefix": "https://www.broadwayplus.com/blog/",
        "extract_description": True
    }
}

# Sitemap configuration
SITEMAP_URL = "https://www.broadwayplus.com/sitemap.xml"
EXCLUDED_URL_PATTERNS = [
    "/artist",
    "/account",
    "/admin",
    "/cart",
    "/users",
    "/artist-roster-old",
    "/warehouse",
    "/checkout",
    "/utility",
    "/lockdatadrafts",
    "/artists",
    "/shows"
]


def fetch_collection_items(collection_id: str, limit: int = 100) -> List[Dict]:
    """
    Fetch all items from a Webflow collection with pagination.
    
    Args:
        collection_id: The Webflow collection ID
        limit: Number of items per request (max 100)
    
    Returns:
        List of all items from the collection
    """
    all_items = []
    offset = 0
    
    while True:
        endpoint = f"{BASE_URL}/collections/{collection_id}/items"
        params = {
            "offset": offset,
            "limit": limit
        }
        
        print(f"📡 Fetching items from collection {collection_id} (offset: {offset})...")
        
        try:
            response = requests.get(endpoint, headers=HEADERS, params=params)
            response.raise_for_status()
            
            data = response.json()
            items = data.get("items", [])
            
            if not items:
                print(f"   ✅ No more items (fetched {len(all_items)} total)")
                break
            
            all_items.extend(items)
            print(f"   📦 Fetched {len(items)} items (total: {len(all_items)})")
            
            # Check if we've fetched all items
            pagination = data.get("pagination", {})
            total = pagination.get("total", 0)
            
            if len(all_items) >= total:
                print(f"   ✅ Fetched all {total} items")
                break
            
            offset += limit
            
        except requests.exceptions.RequestException as e:
            print(f"   ❌ Error fetching items: {e}")
            break
    
    return all_items


def extract_item_data(item: Dict, category: str, config: Dict) -> Optional[Dict]:
    """
    Extract relevant data from a Webflow CMS item.
    
    Args:
        item: The raw Webflow item
        category: Category name (press, artists, shows, blog)
        config: Configuration for this collection
    
    Returns:
        Extracted data dictionary or None if item should be skipped
    """
    try:
        field_data = item.get("fieldData", {})
        
        # Extract common fields
        item_id = item.get("id")
        slug = field_data.get("slug")
        
        if not item_id or not slug:
            print(f"   ⚠️  Skipping item without id or slug")
            return None
        
        # Build URL
        url = config["url_prefix"] + slug
        
        # Extract title (different field names per collection)
        title = field_data.get("name") or field_data.get("title", "Untitled")
        
        # Extract image
        image_url = None
        for image_field in ["featured-image", "main-image", "headshot-image"]:
            image_data = field_data.get(image_field)
            if image_data and isinstance(image_data, dict):
                image_url = image_data.get("url")
                if image_url:
                    break
        
        # Build base result
        result = {
            "id": item_id,
            "title": title,
            "url": url,
            "image": image_url,
            "category": category
        }
        
        # Extract description if configured
        if config["extract_description"]:
            description = None
            
            # Try different description fields based on category
            if category == "artists":
                description = field_data.get("short-bio")
            elif category == "shows":
                # Get plain text summary and truncate to ~20 words
                plain_summary = field_data.get("plain-text-summary", "")
                if plain_summary:
                    words = plain_summary.split()[:20]
                    description = " ".join(words)
                    if len(field_data.get("plain-text-summary", "").split()) > 20:
                        description += "..."
            elif category == "blog":
                description = field_data.get("subtitle-small-description")
            
            result["description"] = description
        
        return result
        
    except Exception as e:
        print(f"   ⚠️  Error extracting data from item: {e}")
        return None


def should_exclude_url(url: str) -> bool:
    """Check if URL should be excluded based on patterns."""
    # Remove base domain
    path = url.replace("https://www.broadwayplus.com", "")
    
    # Home page is allowed
    if path == "" or path == "/":
        return False
    
    # Check each exclusion pattern
    for pattern in EXCLUDED_URL_PATTERNS:
        if path.startswith(pattern):
            return True
    
    return False


def fetch_sitemap_urls() -> List[str]:
    """Fetch and parse sitemap.xml to get all URLs."""
    try:
        print(f"\n{'='*60}")
        print(f"🗺️  Fetching sitemap from {SITEMAP_URL}")
        print(f"{'='*60}")
        
        response = requests.get(SITEMAP_URL, timeout=15)
        response.raise_for_status()
        
        # Parse XML
        root = ET.fromstring(response.content)
        
        # Extract all URLs (handle XML namespace)
        namespace = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
        urls = []
        
        for url_element in root.findall('ns:url', namespace):
            loc = url_element.find('ns:loc', namespace)
            if loc is not None and loc.text:
                urls.append(loc.text)
        
        print(f"📊 Found {len(urls)} total URLs in sitemap")
        
        # Filter out excluded URLs
        filtered_urls = [url for url in urls if not should_exclude_url(url)]
        
        print(f"✅ {len(filtered_urls)} URLs after filtering")
        print(f"❌ {len(urls) - len(filtered_urls)} URLs excluded")
        
        return filtered_urls
        
    except Exception as e:
        print(f"❌ Error fetching sitemap: {e}")
        return []


def extract_og_metadata(url: str) -> Optional[Dict]:
    """
    Fetch a URL and extract OpenGraph metadata.
    
    Args:
        url: The URL to fetch
    
    Returns:
        Dictionary with extracted metadata or None if failed
    """
    try:
        print(f"   📄 Fetching {url}")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (compatible; BroadwayPlusBot/1.0)'
        }
        
        response = requests.get(url, timeout=10, headers=headers, allow_redirects=True)
        
        # Skip if not successful
        if response.status_code != 200:
            print(f"      ⚠️  Status {response.status_code}, skipping")
            return None
        
        # Parse HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract OpenGraph tags
        og_title = None
        og_description = None
        og_image = None
        
        # Get og:title
        title_tag = soup.find('meta', property='og:title')
        if title_tag:
            og_title = title_tag.get('content')
        
        # Fallback to regular title
        if not og_title:
            title_tag = soup.find('title')
            if title_tag:
                og_title = title_tag.get_text()
        
        # Get og:description
        desc_tag = soup.find('meta', property='og:description')
        if desc_tag:
            og_description = desc_tag.get('content')
        
        # Fallback to meta description
        if not og_description:
            desc_tag = soup.find('meta', attrs={'name': 'description'})
            if desc_tag:
                og_description = desc_tag.get('content')
        
        # Truncate description to 20 words
        if og_description:
            words = og_description.split()[:20]
            og_description = " ".join(words)
            if len(og_description.split()) == 20:
                og_description += "..."
        
        # Get og:image
        image_tag = soup.find('meta', property='og:image')
        if image_tag:
            og_image = image_tag.get('content')
        
        # Build result
        result = {
            "id": "-1",
            "title": og_title or "Untitled",
            "description": og_description,
            "url": url,
            "image": og_image,
            "category": "home"
        }
        
        print(f"      ✅ '{og_title[:50] if og_title else 'Untitled'}'")
        
        return result
        
    except requests.exceptions.Timeout:
        print(f"      ⏱️  Timeout, skipping")
        return None
    except requests.exceptions.RequestException as e:
        print(f"      ❌ Request error: {e}")
        return None
    except Exception as e:
        print(f"      ❌ Parse error: {e}")
        return None


def fetch_sitemap_pages() -> List[Dict]:
    """Fetch and extract metadata from sitemap pages."""
    urls = fetch_sitemap_urls()
    
    if not urls:
        print("⚠️  No URLs to process from sitemap")
        return []
    
    print(f"\n📝 Extracting metadata from {len(urls)} pages...")
    print("(This may take a few minutes)")
    
    results = []
    success_count = 0
    
    for idx, url in enumerate(urls, 1):
        print(f"\n[{idx}/{len(urls)}]", end=" ")
        
        metadata = extract_og_metadata(url)
        if metadata:
            results.append(metadata)
            success_count += 1
    
    print(f"\n\n✅ Successfully extracted {success_count}/{len(urls)} pages")
    
    return results


def generate_search_index() -> List[Dict]:
    """
    Generate complete search index from all collections and sitemap pages.
    
    Returns:
        List of all indexed items
    """
    all_results = []
    
    # Fetch CMS collections
    for category, config in COLLECTIONS.items():
        print(f"\n{'='*60}")
        print(f"🔍 Processing {category.upper()} collection...")
        print(f"{'='*60}")
        
        items = fetch_collection_items(config["collection_id"])
        
        print(f"\n📝 Extracting data from {len(items)} items...")
        
        for item in items:
            extracted = extract_item_data(item, category, config)
            if extracted:
                all_results.append(extracted)
        
        print(f"✅ Added {len([r for r in all_results if r['category'] == category])} items from {category}")
    
    # Fetch sitemap pages
    sitemap_pages = fetch_sitemap_pages()
    all_results.extend(sitemap_pages)
    print(f"✅ Added {len(sitemap_pages)} pages from sitemap")
    
    return all_results


def save_search_index(data: List[Dict], filename: str = "search_index.json"):
    """
    Save search index to JSON file.
    
    Args:
        data: List of indexed items
        filename: Output filename
    """
    output_path = os.path.join(os.path.dirname(__file__), filename)
    
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"\n{'='*60}")
        print(f"✅ Search index saved to: {output_path}")
        print(f"📊 Total items: {len(data)}")
        print(f"{'='*60}")
        
        # Print summary by category
        print("\n📋 Summary by category:")
        for category in COLLECTIONS.keys():
            count = len([item for item in data if item["category"] == category])
            print(f"   • {category.capitalize()}: {count} items")
        
        # Add home/sitemap pages
        home_count = len([item for item in data if item["category"] == "home"])
        if home_count > 0:
            print(f"   • Home (sitemap pages): {home_count} items")
        
    except Exception as e:
        print(f"❌ Error saving search index: {e}")


def main():
    """Main execution function."""
    print("🚀 Starting search index generation...")
    print(f"🔑 Using API token: {WEBFLOW_API_TOKEN[:20]}..." if WEBFLOW_API_TOKEN else "❌ No API token found!")
    
    if not WEBFLOW_API_TOKEN:
        print("\n❌ ERROR: WEBFLOW_API_TOKEN not found in environment variables")
        print("Please set WEBFLOW_API_TOKEN in your .env file")
        return
    
    # Generate index
    search_index = generate_search_index()
    
    # Save to file
    save_search_index(search_index)
    
    print("\n✨ Done!")


if __name__ == "__main__":
    main()

