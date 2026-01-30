#!/usr/bin/env python3
"""
GitHub API interactions for haru-project organization repository scanning.
"""

import os
import requests
import logging
from typing import List, Dict, Optional, Set

logger = logging.getLogger(__name__)


class RateLimitError(RuntimeError):
    """Raised when GitHub API rate limit is exceeded."""

    def __init__(self, message: str, reset_epoch: Optional[int] = None):
        super().__init__(message)
        self.reset_epoch = reset_epoch


class GitHubAPI:
    """GitHub API client for organization repository management."""
    
    def __init__(self, token: Optional[str]):
        """Initialize with GitHub token."""
        self.token = token
        self.public_headers = {
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'haru-project-rosdep-automation'
        }
        self.headers = dict(self.public_headers)
        if token:
            self.headers['Authorization'] = f'token {token}'
        self.base_url = 'https://api.github.com'

    def _is_rate_limited(self, response: requests.Response) -> bool:
        if response.status_code not in (403, 429):
            return False
        remaining = response.headers.get('X-RateLimit-Remaining')
        if remaining == '0':
            return True
        try:
            message = response.json().get('message', '').lower()
        except Exception:
            message = response.text.lower()
        return 'rate limit exceeded' in message or 'too many requests' in message

    def _raise_rate_limit(self, response: requests.Response, context: str) -> None:
        reset = response.headers.get('X-RateLimit-Reset')
        reset_epoch = int(reset) if reset and reset.isdigit() else None
        message = None
        try:
            message = response.json().get('message')
        except Exception:
            message = response.text.strip() or None
        detail = message or 'API rate limit exceeded'
        raise RateLimitError(f"{context}: {detail}", reset_epoch=reset_epoch)

    def _request(self, url: str, params: Optional[Dict] = None, use_auth: bool = True) -> requests.Response:
        headers = self.headers if (use_auth and self.token) else self.public_headers
        response = requests.get(url, headers=headers, params=params, timeout=30)
        if self._is_rate_limited(response):
            self._raise_rate_limit(response, f"Rate limit hit for {url}")
        return response

    def _log_forbidden(self, response: requests.Response, context: str) -> None:
        message = None
        try:
            message = response.json().get('message')
        except Exception:
            message = response.text.strip() or None
        remaining = response.headers.get('X-RateLimit-Remaining')
        reset = response.headers.get('X-RateLimit-Reset')
        suffix = f" (rate limit remaining={remaining}, reset={reset})" if remaining is not None else ""
        if message:
            logger.error(f"{context}: {response.status_code} {message}{suffix}")
        else:
            logger.error(f"{context}: {response.status_code} Forbidden{suffix}")
        
    def get_organization_repositories(self, org: str = 'haru-project') -> List[Dict]:
        """
        Get all repositories from the organization.
        
        Args:
            org: Organization name
            
        Returns:
            List of repository dictionaries
        """
        repositories = []
        page = 1
        per_page = 100
        
        while True:
            url = f"{self.base_url}/orgs/{org}/repos"
            params = {
                'page': page,
                'per_page': per_page,
                'type': 'all',
                'sort': 'updated'
            }
            
            try:
                response = self._request(url, params=params, use_auth=True)
                if response.status_code in (401, 403):
                    self._log_forbidden(response, f"Error fetching repositories from {org}")
                    if self.token:
                        logger.warning("Falling back to public repositories only (unauthenticated request).")
                        params_public = dict(params)
                        params_public['type'] = 'public'
                        response = self._request(url, params=params_public, use_auth=False)
                    if response.status_code in (401, 403):
                        response.raise_for_status()
                else:
                    response.raise_for_status()
                
                repos = response.json()
                if not repos:
                    break
                    
                repositories.extend(repos)
                
                # Check if there are more pages
                if len(repos) < per_page:
                    break
                    
                page += 1
                
            except requests.RequestException as e:
                logger.error(f"Error fetching repositories from {org}: {e}")
                break
                
        logger.info(f"Found {len(repositories)} repositories in {org} organization")
        return repositories
    
    def get_repository_contents(self, owner: str, repo: str, path: str = '', ref: str = None) -> Optional[List[Dict]]:
        """
        Get repository contents at specified path.
        
        Args:
            owner: Repository owner
            repo: Repository name  
            path: Path within repository
            ref: Git reference (defaults to default branch for efficiency)
            
        Returns:
            List of content items or None if error
        """
        url = f"{self.base_url}/repos/{owner}/{repo}/contents/{path}"
        params = {}
        if ref:
            params['ref'] = ref
        
        try:
            response = self._request(url, params=params, use_auth=True)
            if response.status_code in (401, 403) and self.token:
                self._log_forbidden(response, f"Error fetching contents from {owner}/{repo} at {path}")
                response = self._request(url, params=params, use_auth=False)
            response.raise_for_status()
            return response.json()
            
        except requests.RequestException as e:
            logger.warning(f"Error fetching contents from {owner}/{repo} at {path}: {e}")
            return None
    
    def get_file_content(self, owner: str, repo: str, path: str, ref: str = None) -> Optional[str]:
        """
        Get file content from repository.
        
        Args:
            owner: Repository owner
            repo: Repository name
            path: File path
            ref: Git reference (defaults to default branch for efficiency)
            
        Returns:
            File content as string or None if error
        """
        url = f"{self.base_url}/repos/{owner}/{repo}/contents/{path}"
        params = {}
        if ref:
            params['ref'] = ref
        
        try:
            response = self._request(url, params=params, use_auth=True)
            if response.status_code in (401, 403) and self.token:
                self._log_forbidden(response, f"Error fetching file {owner}/{repo}/{path}")
                response = self._request(url, params=params, use_auth=False)
            response.raise_for_status()
            
            content_data = response.json()
            if content_data.get('type') == 'file':
                import base64
                content = base64.b64decode(content_data['content']).decode('utf-8')
                return content
                
        except requests.RequestException as e:
            logger.warning(f"Error fetching file {owner}/{repo}/{path}: {e}")
            
        return None
    
    def find_package_xml_files(self, owner: str, repo: str, path: str = '', ref: str = None) -> List[str]:
        """
        Recursively find all package.xml files in repository.
        
        Args:
            owner: Repository owner
            repo: Repository name
            path: Starting path for search
            ref: Git reference (defaults to default branch)
            
        Returns:
            List of package.xml file paths
        """
        package_files = []
        
        contents = self.get_repository_contents(owner, repo, path, ref)
        if not contents:
            return package_files
            
        for item in contents:
            if item['type'] == 'file' and item['name'] == 'package.xml':
                package_files.append(item['path'])
                logger.debug(f"Found package.xml at {owner}/{repo}/{item['path']}")
                
            elif item['type'] == 'dir':
                # Recursively search directories
                subdir_files = self.find_package_xml_files(owner, repo, item['path'], ref)
                package_files.extend(subdir_files)
                
        return package_files
    
    def repository_exists(self, owner: str, repo: str) -> bool:
        """
        Check if repository exists and is accessible.
        
        Args:
            owner: Repository owner
            repo: Repository name
            
        Returns:
            True if repository exists and accessible
        """
        url = f"{self.base_url}/repos/{owner}/{repo}"
        
        try:
            response = self._request(url, use_auth=True)
            if response.status_code in (401, 403) and self.token:
                self._log_forbidden(response, f"Error checking repository {owner}/{repo}")
                response = self._request(url, use_auth=False)
            return response.status_code == 200
            
        except requests.RequestException:
            return False
    
    def get_specific_repository(self, owner: str, repo: str) -> Optional[Dict]:
        """
        Get specific repository information.
        
        Args:
            owner: Repository owner
            repo: Repository name
            
        Returns:
            Repository dictionary or None if not found
        """
        url = f"{self.base_url}/repos/{owner}/{repo}"
        
        try:
            response = self._request(url, use_auth=True)
            if response.status_code in (401, 403) and self.token:
                self._log_forbidden(response, f"Error fetching repository {owner}/{repo}")
                response = self._request(url, use_auth=False)
            response.raise_for_status()
            return response.json()
            
        except requests.RequestException as e:
            logger.warning(f"Error fetching repository {owner}/{repo}: {e}")
            return None

    def get_repository_tree_paths(self, owner: str, repo: str, ref: str) -> Optional[Set[str]]:
        """
        Get all file paths in a repository via git tree API.

        Args:
            owner: Repository owner
            repo: Repository name
            ref: Git reference (branch name or SHA)

        Returns:
            Set of file paths or None if error
        """
        url = f"{self.base_url}/repos/{owner}/{repo}/git/trees/{ref}"
        params = {'recursive': '1'}
        try:
            response = self._request(url, params=params, use_auth=True)
            if response.status_code in (401, 403) and self.token:
                self._log_forbidden(response, f"Error fetching tree for {owner}/{repo}")
                response = self._request(url, params=params, use_auth=False)
            response.raise_for_status()
            data = response.json()
            if data.get('truncated'):
                logger.warning(f"Tree listing truncated for {owner}/{repo} at {ref}")
            tree = data.get('tree', [])
            return {item['path'] for item in tree if item.get('type') == 'blob' and 'path' in item}
        except requests.RequestException as e:
            logger.warning(f"Error fetching tree for {owner}/{repo} at {ref}: {e}")
            return None


def create_github_client() -> Optional[GitHubAPI]:
    """Create GitHub API client from environment."""
    token = (
        os.getenv('ROSDEP_GITHUB_TOKEN')
        or os.getenv('GITHUB_ORG_TOKEN')
        or os.getenv('GH_TOKEN')
        or os.getenv('GITHUB_TOKEN')
    )
    if not token:
        logger.error("GITHUB_TOKEN environment variable not set")
        return None
        
    return GitHubAPI(token)


if __name__ == "__main__":
    # Test the GitHub API client
    logging.basicConfig(level=logging.INFO)
    
    client = create_github_client()
    if client:
        repos = client.get_organization_repositories()
        print(f"Found {len(repos)} repositories")
        
        # Test package.xml discovery on first few repos
        for repo in repos[:3]:
            package_files = client.find_package_xml_files('haru-project', repo['name'])
            print(f"{repo['name']}: {len(package_files)} package.xml files")
