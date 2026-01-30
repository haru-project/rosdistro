#!/usr/bin/env python3
"""
GitHub API interactions for haru-project organization repository scanning.
"""

import os
import requests
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class GitHubAPI:
    """GitHub API client for organization repository management."""
    
    def __init__(self, token: str):
        """Initialize with GitHub token."""
        self.token = token
        self.headers = {
            'Authorization': f'token {token}',
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'haru-project-rosdep-automation'
        }
        self.base_url = 'https://api.github.com'
        
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
                response = requests.get(url, headers=self.headers, params=params)
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
    
    def get_repository_contents(self, owner: str, repo: str, path: str = '') -> Optional[List[Dict]]:
        """
        Get repository contents at specified path.
        
        Args:
            owner: Repository owner
            repo: Repository name  
            path: Path within repository
            
        Returns:
            List of content items or None if error
        """
        url = f"{self.base_url}/repos/{owner}/{repo}/contents/{path}"
        
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
            
        except requests.RequestException as e:
            logger.warning(f"Error fetching contents from {owner}/{repo} at {path}: {e}")
            return None
    
    def get_file_content(self, owner: str, repo: str, path: str) -> Optional[str]:
        """
        Get file content from repository.
        
        Args:
            owner: Repository owner
            repo: Repository name
            path: File path
            
        Returns:
            File content as string or None if error
        """
        url = f"{self.base_url}/repos/{owner}/{repo}/contents/{path}"
        
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            
            content_data = response.json()
            if content_data.get('type') == 'file':
                import base64
                content = base64.b64decode(content_data['content']).decode('utf-8')
                return content
                
        except requests.RequestException as e:
            logger.warning(f"Error fetching file {owner}/{repo}/{path}: {e}")
            
        return None
    
    def find_package_xml_files(self, owner: str, repo: str, path: str = '') -> List[str]:
        """
        Recursively find all package.xml files in repository.
        
        Args:
            owner: Repository owner
            repo: Repository name
            path: Starting path for search
            
        Returns:
            List of package.xml file paths
        """
        package_files = []
        
        contents = self.get_repository_contents(owner, repo, path)
        if not contents:
            return package_files
            
        for item in contents:
            if item['type'] == 'file' and item['name'] == 'package.xml':
                package_files.append(item['path'])
                logger.debug(f"Found package.xml at {owner}/{repo}/{item['path']}")
                
            elif item['type'] == 'dir':
                # Recursively search directories
                subdir_files = self.find_package_xml_files(owner, repo, item['path'])
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
            response = requests.get(url, headers=self.headers)
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
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
            
        except requests.RequestException as e:
            logger.warning(f"Error fetching repository {owner}/{repo}: {e}")
            return None


def create_github_client() -> Optional[GitHubAPI]:
    """Create GitHub API client from environment."""
    token = os.getenv('GITHUB_TOKEN')
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