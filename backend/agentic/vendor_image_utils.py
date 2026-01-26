# agentic/vendor_image_utils.py
# ==============================================================================
# VENDOR PRODUCT IMAGE UTILITIES FOR AGENTIC WORKFLOWS
# ==============================================================================
#
# Internal utilities for fetching real product images from the web during
# vendor analysis in the product search workflow.
#
# ARCHITECTURE:
# 1. Fetch vendor-specific product images from Google Custom Search API
# 2. Search within manufacturer domains for authentic product images
# 3. Fallback to SerpAPI/Serper if Google CSE fails
# 4. Return image URLs for enriching vendor analysis results
#
# USAGE:
#   from agentic.vendor_image_utils import fetch_vendor_product_images
#   images = fetch_vendor_product_images("Emerson", "Flow Meter", "Pressure Transmitter")
#   # Returns: [{"url": "...", "source": "google_cse", ...}, ...]
#
# ==============================================================================

import logging
import os
from typing import Dict, Any, Optional, List
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import requests
import hashlib
from io import BytesIO
import mimetypes

# Try to import Azure Blob config
try:
    from azure_blob_config import Collections, azure_blob_manager
    AZURE_AVAILABLE = True
except ImportError:
    AZURE_AVAILABLE = False

logger = logging.getLogger(__name__)

# Get API keys from environment
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_CX = os.getenv("GOOGLE_CX")  # Custom Search Engine ID
SERPAPI_KEY = os.getenv("SERPAPI_API_KEY") or os.getenv("SERPAPI_KEY")
SERPER_KEY = os.getenv("SERPER_API_KEY") or os.getenv("SERPER_KEY")


def get_manufacturer_domains_from_llm(vendor_name: str) -> List[str]:
    """
    Get manufacturer domains for a vendor (static mapping with LLM fallback).

    Args:
        vendor_name: Name of the vendor/manufacturer

    Returns:
        List of domain names to search within
    """
    # Static mapping of common vendors to their domains
    VENDOR_DOMAINS = {
        'emerson': ['emerson.com', 'emersonprocess.com', 'emersonindustrial.com'],
        'honeywell': ['honeywell.com', 'honeywellprocess.com'],
        'siemens': ['siemens.com', 'siemens-industry.com'],
        'yokogawa': ['yokogawa.com', 'ydc.co.jp'],
        'wika': ['wika.com'],
        'abb': ['abb.com', 'abb-group.com'],
        'endress': ['endress.com', 'endress-hauser.com'],
        'rosemount': ['rosemount.com'],
        'danfoss': ['danfoss.com'],
        'bosch': ['bosch.com', 'boschsensortec.com'],
        'hydac': ['hydac.com'],
        'eaton': ['eaton.com'],
        'parker': ['parker.com'],
        'rexroth': ['bosch-rexroth.com'],
        'festo': ['festo.com'],
        'norgren': ['norgren.com'],
        'smc': ['smcworld.com', 'smcusa.com'],
        'aventics': ['aventics.com'],
    }

    vendor_lower = vendor_name.lower().replace(' ', '')

    # Try exact match first
    for key, domains in VENDOR_DOMAINS.items():
        if key in vendor_lower:
            logger.debug(f"[VENDOR_IMAGES] Domain mapping for '{vendor_name}': {domains}")
            return domains

    # Fallback: generate common domains from vendor name
    vendor_clean = vendor_name.lower().replace(' ', '').replace('&', '').replace('+', '')
    fallback_domains = [
        f"{vendor_clean}.com",
        f"{vendor_clean}.de",
        f"{vendor_clean}group.com"
    ]
    logger.debug(f"[VENDOR_IMAGES] Using fallback domains for '{vendor_name}': {fallback_domains}")
    return fallback_domains


def fetch_vendor_product_images_google_cse(
    vendor_name: str,
    product_name: Optional[str] = None,
    model_family: Optional[str] = None,
    product_type: Optional[str] = None,
    manufacturer_domains: Optional[List[str]] = None,
    timeout: int = 10
) -> List[Dict[str, Any]]:
    """
    Fetch vendor-specific product images using Google Custom Search API.

    Args:
        vendor_name: Name of the vendor/manufacturer
        product_name: Optional specific product name/model
        model_family: Optional model family/series
        product_type: Optional type of product
        manufacturer_domains: Optional list of manufacturer domains to search
        timeout: Request timeout in seconds

    Returns:
        List of image dictionaries with URL, source, thumbnail, domain
    """
    if not GOOGLE_API_KEY or not GOOGLE_CX:
        logger.warning("[VENDOR_IMAGES] Google CSE credentials not configured")
        return []

    try:
        from googleapiclient.discovery import build

        # Build search query
        query = vendor_name
        if model_family:
            query += f" {model_family}"
        if product_type:
            query += f" {product_type}"
        query += " product image"

        # Get manufacturer domains
        if manufacturer_domains is None:
            manufacturer_domains = get_manufacturer_domains_from_llm(vendor_name)

        domain_filter = " OR ".join([f"site:{domain}" for domain in manufacturer_domains])
        search_query = f"{query} ({domain_filter}) filetype:jpg OR filetype:png"

        logger.debug(f"[VENDOR_IMAGES] Google CSE search for '{vendor_name}': {search_query[:100]}...")

        # Execute search
        service = build("customsearch", "v1", developerKey=GOOGLE_API_KEY)
        result = service.cse().list(
            q=search_query,
            cx=GOOGLE_CX,
            searchType="image",
            num=5,  # Limit to 5 images to avoid quota exhaustion
            safe="medium",
            imgSize="MEDIUM"
        ).execute()

        images = []
        unsupported_schemes = ['x-raw-image://', 'data:', 'blob:', 'chrome://', 'about:']

        for item in result.get("items", []):
            url = item.get("link")

            # Validate URL
            if not url or any(url.startswith(scheme) for scheme in unsupported_schemes):
                continue
            if not url.startswith(('http://', 'https://')):
                continue

            images.append({
                "url": url,
                "title": item.get("title", ""),
                "source": "google_cse",
                "thumbnail": item.get("image", {}).get("thumbnailLink", ""),
                "domain": item.get("displayLink", "")
            })

        if images:
            logger.info(f"[VENDOR_IMAGES] Google CSE found {len(images)} images for {vendor_name}")
        return images

    except Exception as e:
        logger.warning(f"[VENDOR_IMAGES] Google CSE image search failed for {vendor_name}: {e}")
        return []


def fetch_vendor_product_images_serpapi(
    vendor_name: str,
    product_name: Optional[str] = None,
    model_family: Optional[str] = None,
    product_type: Optional[str] = None,
    timeout: int = 10
) -> List[Dict[str, Any]]:
    """
    Fetch vendor-specific product images using SerpAPI (fallback).

    Args:
        vendor_name: Name of the vendor/manufacturer
        product_name: Optional specific product name
        model_family: Optional model family
        product_type: Optional product type
        timeout: Request timeout in seconds

    Returns:
        List of image dictionaries
    """
    if not SERPAPI_KEY:
        logger.warning("[VENDOR_IMAGES] SerpAPI key not configured")
        return []

    try:
        import requests

        # Build query
        query = vendor_name
        if model_family:
            query += f" {model_family}"
        if product_type:
            query += f" {product_type}"
        query += " product"

        logger.debug(f"[VENDOR_IMAGES] SerpAPI search for '{vendor_name}': {query}")

        # Execute search
        params = {
            "q": query,
            "tbm": "isch",  # Image search
            "api_key": SERPAPI_KEY,
            "num": 5
        }

        response = requests.get(
            "https://serpapi.com/search",
            params=params,
            timeout=timeout
        )

        if response.status_code != 200:
            logger.warning(f"[VENDOR_IMAGES] SerpAPI returned {response.status_code}")
            return []

        data = response.json()
        images = []

        for item in data.get("images_results", []):
            images.append({
                "url": item.get("original"),
                "title": item.get("title", ""),
                "source": "serpapi",
                "thumbnail": item.get("thumbnail", ""),
                "domain": item.get("source", "")
            })

        if images:
            logger.info(f"[VENDOR_IMAGES] SerpAPI found {len(images)} images for {vendor_name}")
        return images

    except Exception as e:
        logger.warning(f"[VENDOR_IMAGES] SerpAPI search failed for {vendor_name}: {e}")
        return []


def fetch_vendor_product_images(
    vendor_name: str,
    product_name: Optional[str] = None,
    model_family: Optional[str] = None,
    product_type: Optional[str] = None,
    max_retries: int = 1
) -> List[Dict[str, Any]]:
    """
    Fetch vendor-specific product images with automatic fallback.

    Tries Google Custom Search API first, falls back to SerpAPI if needed.

    Args:
        vendor_name: Name of the vendor/manufacturer
        product_name: Optional product name
        model_family: Optional model family
        product_type: Optional product type
        max_retries: Number of retry attempts on failure

    Returns:
        List of image dictionaries with URL, source, etc.
    """
    logger.info(f"[VENDOR_IMAGES] Fetching images for vendor: {vendor_name}")

    # Try Google CSE first
    images = fetch_vendor_product_images_google_cse(
        vendor_name=vendor_name,
        product_name=product_name,
        model_family=model_family,
        product_type=product_type
    )

    # If no results, try SerpAPI
    if not images:
        logger.info(f"[VENDOR_IMAGES] No Google CSE results, trying SerpAPI...")
        images = fetch_vendor_product_images_serpapi(
            vendor_name=vendor_name,
            product_name=product_name,
            model_family=model_family,
            product_type=product_type
        )

    logger.info(f"[VENDOR_IMAGES] Retrieved {len(images)} images for {vendor_name}")
    
    # NEW: Cache images and return local/API URLs
    cached_images = []
    
    # Use ThreadPoolExecutor to cache images in parallel
    with ThreadPoolExecutor(max_workers=5) as executor:
        # Create future for each image caching task
        future_to_img = {
            executor.submit(
                cache_vendor_image, 
                img["url"], 
                vendor_name
            ): img for img in images
        }
        
        for future in as_completed(future_to_img):
            original_img = future_to_img[future]
            try:
                cached_result = future.result()
                if cached_result:
                    # Update image object with local URL
                    original_img["url"] = cached_result["url"]
                    original_img["cached"] = True
                    original_img["local_path"] = cached_result.get("local_path")
                    cached_images.append(original_img)
                else:
                    # Keep original if caching failed, but it might fail on frontend if CORS/hotlink blocked
                    cached_images.append(original_img)
            except Exception as e:
                logger.warning(f"[VENDOR_IMAGES] Failed to cache image {original_img.get('url')}: {e}")
                cached_images.append(original_img)
                
    return cached_images


def cache_vendor_image(image_url: str, vendor_name: str) -> Optional[Dict[str, Any]]:
    """
    Download and cache a vendor image to Azure Blob (or local).
    
    Args:
        image_url: Original URL of the image
        vendor_name: Name of the vendor (for organization)
        
    Returns:
        Dict with 'url' (API URL) and 'local_path' or None if failed
    """
    try:
        # Generate unique filename hash
        img_hash = hashlib.md5(image_url.encode()).hexdigest()
        
        # Download image
        try:
            response = requests.get(image_url, timeout=10, stream=True)
            if response.status_code != 200:
                logger.warning(f"[CACHE_IMG] Failed to download {image_url}: {response.status_code}")
                return None
                
            content_type = response.headers.get('content-type', '')
            if 'image' not in content_type:
                logger.warning(f"[CACHE_IMG] URL is not an image: {content_type}")
                return None
                
            image_data = response.content
            
            # Determine extension
            ext = mimetypes.guess_extension(content_type) or '.png'
            if ext == '.jpe': ext = '.jpg'
            
            filename = f"{vendor_name.lower().replace(' ', '_')}_{img_hash}{ext}"
            
        except Exception as e:
            logger.warning(f"[CACHE_IMG] Download error: {e}")
            return None

        # 1. Try Azure Blob Storage
        if AZURE_AVAILABLE and azure_blob_manager:
            try:
                from azure.storage.blob import ContentSettings
                
                blob_path = f"vendor_images/{filename}"
                blob_client = azure_blob_manager.get_blob_client(blob_path)
                
                # Check if exists
                if not blob_client.exists():
                    blob_client.upload_blob(
                        image_data,
                        overwrite=True,
                        content_settings=ContentSettings(content_type=content_type)
                    )
                    logger.info(f"[CACHE_IMG] Uploaded to Azure: {blob_path}")
                
                # Return API path - NO leading /api prefix (frontend handles it)
                return {
                    "url": f"images/{blob_path}", 
                    "local_path": blob_path,
                    "storage": "azure"
                }
            except Exception as azure_err:
                logger.warning(f"[CACHE_IMG] Azure upload failed: {azure_err}")
                # Fallthrough to local
        
        # 2. Fallback to Local Storage
        try:
            local_dir = os.path.join(os.getcwd(), 'static', 'images', 'vendor_images')
            os.makedirs(local_dir, exist_ok=True)
            
            local_path = os.path.join(local_dir, filename)
            
            if not os.path.exists(local_path):
                with open(local_path, 'wb') as f:
                    f.write(image_data)
                logger.info(f"[CACHE_IMG] Saved locally: {local_path}")
                
            # Return API path
            return {
                "url": f"images/vendor_images/{filename}",
                "local_path": filename,
                "storage": "local"
            }
        except Exception as local_err:
            logger.error(f"[CACHE_IMG] Local save failed: {local_err}")
            return None
            
    except Exception as e:
        logger.error(f"[CACHE_IMG] Critical cache error: {e}")
        return None


def fetch_images_for_vendor_matches(
    vendor_name: str,
    matches: List[Dict[str, Any]],
    max_workers: int = 3
) -> List[Dict[str, Any]]:
    """
    Enrich vendor matches with product images.

    Fetches images for vendor and optionally for specific product models.

    Args:
        vendor_name: Vendor to fetch images for
        matches: List of matched products
        max_workers: Max parallel workers for image fetching

    Returns:
        Enriched matches with image URLs
    """
    try:
        # Fetch vendor-level images
        vendor_images = fetch_vendor_product_images(vendor_name)

        # Add images to matches
        for match in matches:
            # If we have product-specific images, use those
            if vendor_images:
                # For now, attach vendor-level images to each match
                # In future, could do product-specific image search
                match['product_images'] = vendor_images[:2]  # Top 2 images
                match['image_source'] = vendor_images[0].get('source', 'unknown') if vendor_images else None
            else:
                match['product_images'] = []
                match['image_source'] = None

        logger.info(f"[VENDOR_IMAGES] Enriched {len(matches)} matches with images")
        return matches

    except Exception as e:
        logger.warning(f"[VENDOR_IMAGES] Failed to enrich matches with images: {e}")
        # Return matches without images on error
        for match in matches:
            match['product_images'] = []
            match['image_source'] = None
        return matches


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    'fetch_vendor_product_images',
    'fetch_vendor_product_images_google_cse',
    'fetch_vendor_product_images_serpapi',
    'fetch_images_for_vendor_matches',
    'get_manufacturer_domains_from_llm'
]
