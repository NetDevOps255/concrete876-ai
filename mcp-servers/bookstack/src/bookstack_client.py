"""BookStack API client for making authenticated requests."""
import os
import httpx
from typing import Any, Dict, Optional, List, Union


class BookStackClient:
    """Client for interacting with the BookStack API."""
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        token_id: Optional[str] = None,
        token_secret: Optional[str] = None,
    ):
        """Initialize the BookStack API client.
        
        Args:
            base_url: BookStack API base URL (e.g., http://localhost:6875/api)
            token_id: API Token ID
            token_secret: API Token Secret
        """
        self.base_url = (base_url or os.getenv("BOOKSTACK_BASE_URL", "")).rstrip("/")
        self.token_id = token_id or os.getenv("BOOKSTACK_TOKEN_ID", "")
        self.token_secret = token_secret or os.getenv("BOOKSTACK_TOKEN_SECRET", "")
        
        if not all([self.base_url, self.token_id, self.token_secret]):
            # Allow initialization without creds for dry-run/test purposes if needed,
            # but warn or handle graceful failure in methods. 
            pass
        
        # Create authorization header
        self.headers = {
            "Authorization": f"Token {self.token_id}:{self.token_secret}",
            "Accept": "application/json",
        }
    
    async def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Union[Dict[str, Any], str]:
        """Make a GET request to the BookStack API."""
        url = f"{self.base_url}{endpoint}"
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, headers=self.headers, params=params, timeout=30.0)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                return f"API Error: {str(e)} - Response: {e.response.text if e.response else 'No response'}"
    
    async def post(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        files: Optional[Dict[str, Any]] = None,
    ) -> Union[Dict[str, Any], str]:
        """Make a POST request to the BookStack API."""
        url = f"{self.base_url}{endpoint}"
        headers = self.headers.copy()
        
        if json is not None:
            headers["Content-Type"] = "application/json"
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    url,
                    headers=headers,
                    data=data,
                    json=json,
                    files=files,
                    timeout=60.0,
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                return f"API Error: {str(e)} - Response: {e.response.text if e.response else 'No response'}"
    
    async def put(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
    ) -> Union[Dict[str, Any], str]:
        """Make a PUT request to the BookStack API."""
        url = f"{self.base_url}{endpoint}"
        headers = self.headers.copy()
        
        if json is not None:
            headers["Content-Type"] = "application/json"
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.put(
                    url,
                    headers=headers,
                    data=data,
                    json=json,
                    timeout=30.0,
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                return f"API Error: {str(e)} - Response: {e.response.text if e.response else 'No response'}"
    
    async def delete(self, endpoint: str) -> Union[Dict[str, Any], str]:
        """Make a DELETE request to the BookStack API."""
        url = f"{self.base_url}{endpoint}"
        async with httpx.AsyncClient() as client:
            try:
                response = await client.delete(url, headers=self.headers, timeout=30.0)
                response.raise_for_status()
                # DELETE requests may return empty response
                if response.content:
                    return response.json()
                return {"status": "success"}
            except httpx.HTTPError as e:
                 return f"API Error: {str(e)} - Response: {e.response.text if e.response else 'No response'}"
