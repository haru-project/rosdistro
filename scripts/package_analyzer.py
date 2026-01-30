#!/usr/bin/env python3
"""
Package.xml analysis for extracting ROS package information.
"""

import xml.etree.ElementTree as ET
import logging
import os
from typing import List, Dict, Optional, Set
from github_api import GitHubAPI

logger = logging.getLogger(__name__)


class ROSPackage:
    """Represents a ROS package with its metadata."""
    
    def __init__(self, name: str, repository: str, file_path: str):
        """
        Initialize ROS package.
        
        Args:
            name: Package name from package.xml
            repository: Repository name containing the package
            file_path: Path to package.xml file
        """
        self.name = name
        self.repository = repository
        self.file_path = file_path
        self.debian_name = self._convert_to_debian_name(name)
        
    def _convert_to_debian_name(self, package_name: str) -> str:
        """
        Convert package name to debian package name format.
        Convert underscores to hyphens for debian compatibility.
        
        Args:
            package_name: Original package name
            
        Returns:
            Debian-compatible package name
        """
        return package_name.replace('_', '-')
    
    def get_rosdep_entries(self) -> Dict[str, List[str]]:
        """
        Generate rosdep.yaml entries for all ROS2 distributions.
        
        Returns:
            Dictionary with Ubuntu codenames and corresponding debian packages
        """
        return {
            'jammy': [f'ros-humble-{self.debian_name}'],  # Ubuntu 22.04 - ROS2 Humble
            'noble': [f'ros-jazzy-{self.debian_name}',    # Ubuntu 24.04 - ROS2 Jazzy
                     f'ros-kilted-{self.debian_name}']    # Ubuntu 24.04 - ROS2 Kilted
        }
    
    def __str__(self):
        return f"ROSPackage(name='{self.name}', repo='{self.repository}', debian='{self.debian_name}')"
    
    def __repr__(self):
        return self.__str__()


class PackageAnalyzer:
    """Analyzes repositories for ROS packages."""
    
    def __init__(self, github_client: GitHubAPI):
        """
        Initialize package analyzer.
        
        Args:
            github_client: GitHub API client
        """
        self.github_client = github_client
        
    def extract_package_name_from_xml(self, xml_content: str) -> Optional[str]:
        """
        Extract package name from package.xml content.
        
        Args:
            xml_content: Raw XML content
            
        Returns:
            Package name or None if parsing fails
        """
        try:
            root = ET.fromstring(xml_content)
            name_element = root.find('name')
            
            if name_element is not None and name_element.text:
                package_name = name_element.text.strip()
                logger.debug(f"Extracted package name: {package_name}")
                return package_name
                
        except ET.ParseError as e:
            logger.warning(f"Failed to parse package.xml: {e}")
            
        return None
    
    def validate_ros_package_structure(self, owner: str, repo: str, package_xml_path: str) -> bool:
        """
        Validate that the directory contains required ROS package files.
        
        Args:
            owner: Repository owner
            repo: Repository name
            package_xml_path: Path to package.xml
            
        Returns:
            True if valid ROS package structure
        """
        # Get directory of package.xml
        package_dir = os.path.dirname(package_xml_path) if package_xml_path else ''
        
        # Check for CMakeLists.txt in the same directory
        cmake_path = os.path.join(package_dir, 'CMakeLists.txt') if package_dir else 'CMakeLists.txt'
        
        # Get directory contents
        contents = self.github_client.get_repository_contents(owner, repo, package_dir)
        if not contents:
            return False
            
        # Look for required files
        has_cmake = any(item['name'] == 'CMakeLists.txt' for item in contents if item['type'] == 'file')
        
        if not has_cmake:
            logger.debug(f"No CMakeLists.txt found in {owner}/{repo}/{package_dir}")
            return False
            
        return True
    
    def analyze_repository(self, repository: Dict) -> List[ROSPackage]:
        """
        Analyze a single repository for ROS packages.
        
        Args:
            repository: Repository dictionary from GitHub API
            
        Returns:
            List of discovered ROS packages
        """
        packages = []
        owner = repository['owner']['login']
        repo_name = repository['name']
        
        logger.info(f"Analyzing repository: {owner}/{repo_name}")
        
        # Find all package.xml files recursively
        package_xml_files = self.github_client.find_package_xml_files(owner, repo_name)
        
        if not package_xml_files:
            logger.debug(f"No package.xml files found in {owner}/{repo_name}")
            return packages
            
        logger.info(f"Found {len(package_xml_files)} package.xml files in {repo_name}")
        
        for package_xml_path in package_xml_files:
            # Validate ROS package structure
            if not self.validate_ros_package_structure(owner, repo_name, package_xml_path):
                logger.warning(f"Invalid ROS package structure at {repo_name}/{package_xml_path}")
                continue
                
            # Get package.xml content
            xml_content = self.github_client.get_file_content(owner, repo_name, package_xml_path)
            if not xml_content:
                logger.warning(f"Could not read {repo_name}/{package_xml_path}")
                continue
                
            # Extract package name
            package_name = self.extract_package_name_from_xml(xml_content)
            if not package_name:
                logger.warning(f"Could not extract package name from {repo_name}/{package_xml_path}")
                continue
                
            # Create ROS package object
            ros_package = ROSPackage(package_name, repo_name, package_xml_path)
            packages.append(ros_package)
            
            logger.info(f"Found ROS package: {ros_package}")
            
        return packages
    
    def analyze_organization_repositories(self, org: str = 'haru-project', specific_repo: Optional[str] = None) -> List[ROSPackage]:
        """
        Analyze all repositories in organization for ROS packages.
        
        Args:
            org: Organization name
            specific_repo: Optional specific repository to analyze
            
        Returns:
            List of all discovered ROS packages
        """
        all_packages = []
        
        if specific_repo:
            # Analyze specific repository
            repo_data = self.github_client.get_specific_repository(org, specific_repo)
            if repo_data:
                packages = self.analyze_repository(repo_data)
                all_packages.extend(packages)
            else:
                logger.error(f"Repository {org}/{specific_repo} not found or not accessible")
        else:
            # Analyze all organization repositories
            repositories = self.github_client.get_organization_repositories(org)
            
            for repository in repositories:
                try:
                    packages = self.analyze_repository(repository)
                    all_packages.extend(packages)
                except Exception as e:
                    logger.error(f"Error analyzing repository {repository['name']}: {e}")
                    continue
                    
        logger.info(f"Analysis complete. Found {len(all_packages)} ROS packages total")
        return all_packages
    
    def get_unique_packages(self, packages: List[ROSPackage]) -> List[ROSPackage]:
        """
        Remove duplicate packages based on package name.
        
        Args:
            packages: List of ROS packages
            
        Returns:
            List of unique packages (latest by repository name)
        """
        unique_packages = {}
        
        for package in packages:
            key = package.name
            if key not in unique_packages:
                unique_packages[key] = package
            else:
                # Keep package from newer repository (by name)
                if package.repository > unique_packages[key].repository:
                    unique_packages[key] = package
                    logger.info(f"Replaced duplicate package {package.name}: {unique_packages[key].repository} -> {package.repository}")
                    
        return list(unique_packages.values())


if __name__ == "__main__":
    # Test the package analyzer
    logging.basicConfig(level=logging.INFO)
    
    from github_api import create_github_client
    
    client = create_github_client()
    if client:
        analyzer = PackageAnalyzer(client)
        packages = analyzer.analyze_organization_repositories()
        
        print(f"\nFound {len(packages)} ROS packages:")
        for package in packages:
            print(f"  {package}")
            print(f"    Rosdep entries: {package.get_rosdep_entries()}")