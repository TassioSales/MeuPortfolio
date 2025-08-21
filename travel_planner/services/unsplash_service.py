"""
Unsplash Image Service

This module provides an interface to the Unsplash API for fetching high-quality,
royalty-free images for travel destinations, activities, and more.
"""
import os
import json
import random
from typing import Dict, List, Optional, Any, Union, Tuple
from datetime import datetime, timedelta
from urllib.parse import quote_plus

import httpx
from pydantic import BaseModel, Field, HttpUrl

from config.settings import settings
from config.log_config import get_logger
from utils.helpers import retry_with_backoff

# Configure logger
logger = get_logger(__name__)

# Unsplash API endpoints
UNSPLASH_BASE_URL = "https://api.unsplash.com"
SEARCH_PHOTOS_URL = f"{UNSPLASH_BASE_URL}/search/photos"
RANDOM_PHOTO_URL = f"{UNSPLASH_BASE_URL}/photos/random"
COLLECTIONS_URL = f"{UNSPLASH_BASE_URL}/collections"

# Default image dimensions
DEFAULT_WIDTH = 1200
DEFAULT_HEIGHT = 800
DEFAULT_QUALITY = 80
DEFAULT_ORIENTATION = "landscape"  # or "portrait", "squarish"

# Cache for storing search results (in-memory for now, can be replaced with Redis)
_image_cache = {}
_cache_expiry = {}

class UnsplashImage(BaseModel):
    """Model representing an Unsplash image."""
    id: str
    url: str
    width: int
    height: int
    color: Optional[str] = None
    description: Optional[str] = None
    alt_description: Optional[str] = None
    user_name: str
    user_url: str
    download_location: Optional[str] = None
    image_type: str = "photo"
    tags: List[Dict[str, Any]] = []
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    likes: int = 0
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }

class UnsplashAPIError(Exception):
    """Custom exception for Unsplash API errors."""
    def __init__(self, message: str, status_code: int = None, errors: List[Dict] = None):
        self.message = message
        self.status_code = status_code
        self.errors = errors or []
        super().__init__(self.message)

class UnsplashService:
    """Service for interacting with the Unsplash API."""
    
    def __init__(self, access_key: str = None, timeout: float = 10.0):
        """Initialize the Unsplash service.
        
        Args:
            access_key: Unsplash API access key (defaults to settings.UNSPLASH_ACCESS_KEY)
            timeout: Request timeout in seconds
        """
        self.access_key = access_key or settings.UNSPLASH_ACCESS_KEY
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=timeout)
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    async def close(self):
        """Close the HTTP client."""
        if self.client:
            await self.client.aclose()
    
    async def _make_request(self, method: str, url: str, **kwargs) -> Dict:
        """Make an authenticated request to the Unsplash API."""
        headers = kwargs.pop('headers', {})
        headers.update({
            "Authorization": f"Client-ID {self.access_key}",
            "Accept-Version": "v1"
        })
        
        # Add cache-busting parameter
        params = kwargs.get('params', {})
        params['t'] = str(int(datetime.utcnow().timestamp()))
        kwargs['params'] = params
        
        # Make the request with retry logic
        @retry_with_backoff(max_retries=3, backoff_in_seconds=1)
        async def _request():
            try:
                response = await self.client.request(
                    method, url, headers=headers, **kwargs
                )
                response.raise_for_status()
                
                # Check rate limits
                self._check_rate_limits(response)
                
                # Return JSON for successful responses
                if response.status_code == 200 and response.content:
                    return response.json()
                return {}
                
            except httpx.HTTPStatusError as e:
                self._handle_http_error(e)
            except Exception as e:
                logger.error(f"Request to {url} failed: {str(e)}")
                raise UnsplashAPIError(f"Request failed: {str(e)}")
        
        return await _request()
    
    def _check_rate_limits(self, response: httpx.Response) -> None:
        """Check API rate limits and log warnings if approaching limits."""
        remaining = int(response.headers.get('X-Ratelimit-Remaining', '0'))
        limit = int(response.headers.get('X-Ratelimit-Limit', '50'))
        
        if remaining < limit * 0.2:  # Less than 20% of limit remaining
            logger.warning(
                f"Approaching Unsplash API rate limit: {remaining}/{limit} requests remaining. "
                f"Resets at: {response.headers.get('X-Ratelimit-Reset', 'N/A')}"
            )
    
    def _handle_http_error(self, error: httpx.HTTPStatusError) -> None:
        """Handle HTTP errors from the Unsplash API."""
        status_code = error.response.status_code
        error_data = {}
        
        try:
            error_data = error.response.json()
        except:
            pass
        
        error_msg = error_data.get('errors', [str(error)])[0]
        
        if status_code == 401:
            raise UnsplashAPIError(
                "Unauthorized - Check your Unsplash API key",
                status_code=status_code,
                errors=[error_msg]
            )
        elif status_code == 403:
            raise UnsplashAPIError(
                "Forbidden - You don't have permission to access this resource",
                status_code=status_code,
                errors=[error_msg]
            )
        elif status_code == 404:
            raise UnsplashAPIError(
                "Resource not found",
                status_code=status_code,
                errors=[error_msg]
            )
        elif status_code == 429:
            reset_time = error.response.headers.get('X-Ratelimit-Reset')
            raise UnsplashAPIError(
                f"Rate limit exceeded. Try again after {reset_time}",
                status_code=status_code,
                errors=[error_msg]
            )
        else:
            raise UnsplashAPIError(
                f"Unsplash API error: {error_msg}",
                status_code=status_code,
                errors=[error_msg] if isinstance(error_msg, list) else [str(error_msg)]
            )
    
    async def search_photos(
        self,
        query: str,
        page: int = 1,
        per_page: int = 10,
        orientation: str = DEFAULT_ORIENTATION,
        color: str = None,
        order_by: str = "relevant"
    ) -> Dict[str, Any]:
        """Search for photos on Unsplash.
        
        Args:
            query: Search query (e.g., "paris", "beach vacation")
            page: Page number to retrieve (default: 1)
            per_page: Number of items per page (default: 10, max: 30)
            orientation: Filter by orientation (landscape, portrait, squarish)
            color: Filter by color (black_and_white, black, white, yellow, etc.)
            order_by: Sort order (relevant, latest)
            
        Returns:
            Dict containing search results and metadata
        """
        # Check cache first
        cache_key = f"search:{query.lower()}:{page}:{per_page}:{orientation}:{color or 'none'}:{order_by}"
        cached = self._get_from_cache(cache_key)
        if cached:
            logger.debug(f"Cache hit for search: {query}")
            return cached
        
        # Build query parameters
        params = {
            "query": query,
            "page": max(1, min(page, 30)),
            "per_page": max(1, min(per_page, 30)),
            "orientation": orientation,
            "order_by": order_by
        }
        
        if color:
            params["color"] = color
        
        try:
            # Make the API request
            data = await self._make_request("GET", SEARCH_PHOTOS_URL, params=params)
            
            # Parse the response
            results = {
                "total": data.get("total", 0),
                "total_pages": data.get("total_pages", 0),
                "results": [self._parse_photo(photo) for photo in data.get("results", [])]
            }
            
            # Cache the results
            self._add_to_cache(cache_key, results, expiry_minutes=60)
            
            return results
            
        except Exception as e:
            logger.error(f"Photo search failed: {str(e)}")
            return {
                "total": 0,
                "total_pages": 0,
                "results": []
            }
    
    async def get_random_photo(
        self,
        query: str = None,
        collections: List[str] = None,
        orientation: str = DEFAULT_ORIENTATION,
        width: int = None,
        height: int = None,
        featured: bool = False,
        username: str = None,
        count: int = 1
    ) -> Union[UnsplashImage, List[UnsplashImage]]:
        """Get a random photo from Unsplash.
        
        Args:
            query: Limit selection to photos matching this search term
            collections: Collection IDs to filter by
            orientation: Filter by orientation (landscape, portrait, squarish)
            width: Desired image width in pixels
            height: Desired image height in pixels
            featured: Limit to featured photos only
            username: Limit to photos by this username
            count: Number of random photos to return (1-30)
            
        Returns:
            A single UnsplashImage or a list of UnsplashImage objects
        """
        # Build cache key
        cache_key_parts = ["random"]
        if query:
            cache_key_parts.append(f"q:{query.lower()}")
        if collections:
            cache_key_parts.append(f"col:{':'.join(sorted(collections))}")
        if orientation:
            cache_key_parts.append(f"o:{orientation}")
        if width or height:
            cache_key_parts.append(f"size:{width or 'auto'}x{height or 'auto'}")
        if featured:
            cache_key_parts.append("featured")
        if username:
            cache_key_parts.append(f"user:{username}")
        if count > 1:
            cache_key_parts.append(f"count:{count}")
        
        cache_key = ":".join(cache_key_parts)
        
        # Check cache first
        cached = self._get_from_cache(cache_key)
        if cached:
            logger.debug(f"Cache hit for random photo: {cache_key}")
            return cached
        
        # Build query parameters
        params = {
            "orientation": orientation,
            "count": max(1, min(count, 30))
        }
        
        if query:
            params["query"] = query
        if collections:
            params["collections"] = ",".join(collections)
        if width:
            params["w"] = width
        if height:
            params["h"] = height
        if featured:
            params["featured"] = "true"
        if username:
            params["username"] = username
        
        try:
            # Make the API request
            data = await self._make_request("GET", RANDOM_PHOTO_URL, params=params)
            
            # Parse the response
            if isinstance(data, list):
                results = [self._parse_photo(photo) for photo in data]
            else:
                results = [self._parse_photo(data)]
            
            # Cache the results
            self._add_to_cache(cache_key, results[0] if count == 1 else results, expiry_minutes=30)
            
            return results[0] if count == 1 else results
            
        except Exception as e:
            logger.error(f"Failed to get random photo: {str(e)}")
            return [] if count > 1 else None
    
    async def get_photo_by_id(self, photo_id: str) -> Optional[UnsplashImage]:
        """Get a single photo by its ID.
        
        Args:
            photo_id: The ID of the photo to retrieve
            
        Returns:
            UnsplashImage object or None if not found
        """
        if not photo_id:
            return None
            
        # Check cache first
        cache_key = f"photo:{photo_id}"
        cached = self._get_from_cache(cache_key)
        if cached:
            logger.debug(f"Cache hit for photo ID: {photo_id}")
            return cached
        
        try:
            # Make the API request
            url = f"{UNSPLASH_BASE_URL}/photos/{photo_id}"
            data = await self._make_request("GET", url)
            
            # Parse the response
            photo = self._parse_photo(data)
            
            # Cache the result
            self._add_to_cache(cache_key, photo, expiry_minutes=1440)  # 24 hours
            
            return photo
            
        except Exception as e:
            logger.error(f"Failed to get photo {photo_id}: {str(e)}")
            return None
    
    async def get_photo_urls(
        self,
        query: str,
        width: int = DEFAULT_WIDTH,
        height: int = DEFAULT_HEIGHT,
        quality: int = DEFAULT_QUALITY,
        count: int = 10,
        **kwargs
    ) -> List[Dict[str, str]]:
        """Get direct image URLs for a search query.
        
        Args:
            query: Search query (e.g., "paris", "beach")
            width: Desired image width in pixels
            height: Desired image height in pixels
            quality: Image quality (0-100)
            count: Number of images to return
            **kwargs: Additional arguments to pass to search_photos
            
        Returns:
            List of dicts with image URLs and metadata
        """
        # Check cache first
        cache_key = f"urls:{query.lower()}:{width}x{height}:q{quality}:c{count}"
        cached = self._get_from_cache(cache_key)
        if cached:
            logger.debug(f"Cache hit for photo URLs: {query}")
            return cached
        
        try:
            # Search for photos
            results = await self.search_photos(
                query=query,
                per_page=min(count, 30),
                **kwargs
            )
            
            # Extract URLs with specified dimensions
            urls = []
            for photo in results.get("results", [])[:count]:
                url = self._get_image_url(photo, width, height, quality)
                if url:
                    urls.append({
                        "id": photo.id,
                        "url": url,
                        "width": width,
                        "height": height,
                        "description": photo.description or photo.alt_description or "",
                        "user": photo.user_name,
                        "user_url": photo.user_url,
                        "color": photo.color
                    })
            
            # Cache the results
            self._add_to_cache(cache_key, urls, expiry_minutes=120)
            
            return urls
            
        except Exception as e:
            logger.error(f"Failed to get photo URLs: {str(e)}")
            return []
    
    async def get_destination_cover(
        self,
        destination: str,
        width: int = DEFAULT_WIDTH,
        height: int = DEFAULT_HEIGHT,
        quality: int = DEFAULT_QUALITY,
        use_landmarks: bool = True
    ) -> Optional[Dict[str, str]]:
        """Get a cover image for a travel destination.
        
        Args:
            destination: Destination name (e.g., "Paris, France")
            width: Desired image width in pixels
            height: Desired image height in pixels
            quality: Image quality (0-100)
            use_landmarks: Whether to include landmark names in the search
            
        Returns:
            Dict with image URL and metadata, or None if not found
        """
        # Check cache first
        cache_key = f"cover:{destination.lower()}:{width}x{height}:q{quality}"
        cached = self._get_from_cache(cache_key)
        if cached:
            logger.debug(f"Cache hit for destination cover: {destination}")
            return cached
        
        try:
            # Try different search terms to find a good cover image
            search_terms = [destination]
            
            if use_landmarks:
                # Add common landmarks for better results
                if "paris" in destination.lower():
                    search_terms.extend(["eiffel tower paris", "louvre museum paris", "notre dame paris"])
                elif "new york" in destination.lower():
                    search_terms.extend(["statue of liberty new york", "central park new york", "times square new york"])
                elif "london" in destination.lower():
                    search_terms.extend(["big ben london", "london eye", "tower bridge london"])
                elif "tokyo" in destination.lower():
                    search_terms.extend(["tokyo tower", "shibuya crossing tokyo", "sensoji temple tokyo"])
                elif "rome" in destination.lower():
                    search_terms.extend(["colosseum rome", "trevi fountain rome", "vatican city rome"])
            
            # Try each search term until we find a good image
            for term in search_terms:
                results = await self.search_photos(
                    query=term,
                    per_page=5,
                    orientation="landscape"
                )
                
                if results.get("results"):
                    # Get the first result with a good aspect ratio
                    for photo in results["results"]:
                        if photo.width / photo.height >= 1.5:  # Prefer landscape images
                            image_url = self._get_image_url(photo, width, height, quality)
                            if image_url:
                                result = {
                                    "url": image_url,
                                    "width": width,
                                    "height": height,
                                    "description": photo.description or photo.alt_description or "",
                                    "search_term": term,
                                    "color": photo.color
                                }
                                
                                # Cache the result
                                self._add_to_cache(cache_key, result, expiry_minutes=1440)  # 24 hours
                                
                                return result
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get destination cover for {destination}: {str(e)}")
            return None
    
    def _parse_photo(self, data: Dict) -> UnsplashImage:
        """Parse a photo object from the API response."""
        if not data or not isinstance(data, dict):
            return None
            
        return UnsplashImage(
            id=data.get("id"),
            url=data.get("urls", {}).get("regular") or data.get("urls", {}).get("small") or data.get("urls", {}).get("thumb"),
            width=data.get("width"),
            height=data.get("height"),
            color=data.get("color"),
            description=data.get("description"),
            alt_description=data.get("alt_description"),
            user_name=data.get("user", {}).get("name", "Unknown"),
            user_url=data.get("user", {}).get("links", {}).get("html", ""),
            download_location=data.get("links", {}).get("download_location"),
            image_type=data.get("type", "photo"),
            tags=data.get("tags", []),
            created_at=datetime.strptime(data.get("created_at"), "%Y-%m-%dT%H:%M:%SZ") if data.get("created_at") else None,
            updated_at=datetime.strptime(data.get("updated_at"), "%Y-%m-%dT%H:%M:%SZ") if data.get("updated_at") else None,
            likes=data.get("likes", 0)
        )
    
    def _get_image_url(
        self,
        photo: UnsplashImage,
        width: int = None,
        height: int = None,
        quality: int = DEFAULT_QUALITY,
        fit: str = "crop"  # or "clamp", "clip", "facearea", "fill", "fillmax", "max", "scale", "min"
    ) -> Optional[str]:
        """Get a resized image URL with the specified dimensions."""
        if not photo or not photo.url:
            return None
        
        # Start with the original URL
        url = photo.url
        
        # Add query parameters for resizing if needed
        if width or height or quality < 100:
            # Check if URL already has query parameters
            base_url = url.split('?')[0]
            query_params = {}
            
            # Parse existing query parameters if any
            if '?' in url:
                from urllib.parse import parse_qs, urlparse
                parsed = urlparse(url)
                query_params = {k: v[0] for k, v in parse_qs(parsed.query).items()}
                base_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
            
            # Update with new parameters
            if width:
                query_params["w"] = str(width)
            if height:
                query_params["h"] = str(height)
            if quality < 100:
                query_params["q"] = str(quality)
            if fit and fit != "crop":
                query_params["fit"] = fit
            
            # Rebuild the URL with query parameters
            if query_params:
                from urllib.parse import urlencode
                url = f"{base_url}?{urlencode(query_params)}"
        
        return url
    
    def _get_from_cache(self, key: str) -> Any:
        """Get a value from the cache."""
        if not settings.ENABLE_CACHING:
            return None
            
        now = datetime.utcnow()
        if key in _image_cache and key in _cache_expiry and _cache_expiry[key] > now:
            return _image_cache[key]
        
        # Clean up expired cache entries
        self._clean_cache()
        return None
    
    def _add_to_cache(self, key: str, value: Any, expiry_minutes: int = 60) -> None:
        """Add a value to the cache."""
        if not settings.ENABLE_CACHING:
            return
            
        _image_cache[key] = value
        _cache_expiry[key] = datetime.utcnow() + timedelta(minutes=expiry_minutes)
    
    def _clean_cache(self) -> None:
        """Remove expired cache entries."""
        if not settings.ENABLE_CACHING:
            return
            
        now = datetime.utcnow()
        expired_keys = [k for k, v in _cache_expiry.items() if v <= now]
        
        for key in expired_keys:
            _image_cache.pop(key, None)
            _cache_expiry.pop(key, None)
        
        # Limit cache size
        max_size = getattr(settings, 'MAX_CACHE_SIZE', 1000)
        if len(_image_cache) > max_size:
            # Remove the oldest entries (approximate based on expiry time)
            sorted_keys = sorted(_cache_expiry.items(), key=lambda x: x[1])
            for key, _ in sorted_keys[:len(_image_cache) - max_size]:
                _image_cache.pop(key, None)
                _cache_expiry.pop(key, None)

# Singleton instance
unsplash_service = UnsplashService()

# Example usage
if __name__ == "__main__":
    import asyncio
    import os
    from dotenv import load_dotenv
    
    # Load environment variables
    load_dotenv()
    
    async def test_search_photos():
        """Test searching for photos."""
        async with UnsplashService() as service:
            print("Searching for 'beach' photos...")
            results = await service.search_photos("beach", per_page=3)
            print(f"Found {results['total']} results")
            for i, photo in enumerate(results['results'], 1):
                print(f"{i}. {photo.description or 'No description'}")
                print(f"   URL: {photo.url}")
    
    async def test_random_photo():
        """Test getting a random photo."""
        async with UnsplashService() as service:
            print("Getting a random travel photo...")
            photo = await service.get_random_photo(query="travel", orientation="landscape")
            if photo:
                print(f"Random photo: {photo.description or 'No description'}")
                print(f"URL: {photo.url}")
    
    async def test_destination_cover():
        """Test getting a destination cover image."""
        async with UnsplashService() as service:
            destinations = ["Paris, France", "Tokyo, Japan", "New York, USA"]
            for dest in destinations:
                print(f"\nGetting cover for {dest}...")
                cover = await service.get_destination_cover(dest)
                if cover:
                    print(f"Cover URL: {cover['url']}")
                    print(f"Description: {cover['description']}")
    
    # Run the tests
    # asyncio.run(test_search_photos())
    # asyncio.run(test_random_photo())
    # asyncio.run(test_destination_cover())
