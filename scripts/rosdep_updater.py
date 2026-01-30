#!/usr/bin/env python3
"""
rosdep.yaml management with YAML validation and automated updates.
"""

import yaml
import logging
import os
import shutil
from typing import List, Dict, Set, Any
from package_analyzer import ROSPackage

logger = logging.getLogger(__name__)


class ROSDepUpdater:
    """Manages rosdep.yaml file updates with validation."""
    
    def __init__(self, rosdep_file: str = 'rosdep.yaml'):
        """
        Initialize rosdep updater.
        
        Args:
            rosdep_file: Path to rosdep.yaml file
        """
        self.rosdep_file = rosdep_file
        self.rosdep_data = {}
        self.load_rosdep_file()
        
    def load_rosdep_file(self):
        """Load existing rosdep.yaml file."""
        try:
            if os.path.exists(self.rosdep_file):
                with open(self.rosdep_file, 'r', encoding='utf-8') as f:
                    self.rosdep_data = yaml.safe_load(f) or {}
                logger.info(f"Loaded rosdep.yaml with {len(self.rosdep_data)} entries")
            else:
                logger.warning(f"rosdep.yaml file not found: {self.rosdep_file}")
                self.rosdep_data = {}
        except yaml.YAMLError as e:
            logger.error(f"Error parsing rosdep.yaml: {e}")
            self.rosdep_data = {}
        except Exception as e:
            logger.error(f"Error loading rosdep.yaml: {e}")
            self.rosdep_data = {}
    
    def get_existing_packages(self) -> Set[str]:
        """
        Get set of existing package names in rosdep.yaml.
        
        Returns:
            Set of package names already in rosdep.yaml
        """
        return set(self.rosdep_data.keys()) if self.rosdep_data else set()
    
    def validate_yaml_syntax(self, yaml_data: Dict) -> bool:
        """
        Validate YAML syntax and structure.
        
        Args:
            yaml_data: Data to validate
            
        Returns:
            True if valid YAML structure
        """
        try:
            # Test serialization and deserialization
            yaml_string = yaml.dump(yaml_data, default_flow_style=False)
            parsed_data = yaml.safe_load(yaml_string)
            
            # Basic structure validation
            if not isinstance(parsed_data, dict):
                logger.error("rosdep.yaml must be a dictionary")
                return False
                
            # Validate each entry structure
            for package_name, package_data in parsed_data.items():
                if not isinstance(package_data, dict):
                    logger.error(f"Package {package_name} must have dictionary value")
                    return False
                    
                if 'ubuntu' not in package_data:
                    logger.error(f"Package {package_name} missing 'ubuntu' key")
                    return False
                    
                ubuntu_data = package_data['ubuntu']
                if isinstance(ubuntu_data, list):
                    for pkg in ubuntu_data:
                        if not isinstance(pkg, str):
                            logger.error(f"Package {package_name} ubuntu list must contain strings")
                            return False
                elif isinstance(ubuntu_data, dict):
                    # Validate distribution entries
                    for distro, packages in ubuntu_data.items():
                        if not isinstance(packages, list):
                            logger.error(f"Package {package_name} distro {distro} must be list")
                            return False
                            
                        for pkg in packages:
                            if not isinstance(pkg, str):
                                logger.error(f"Package {package_name} distro {distro} must contain strings")
                                return False
                else:
                    logger.error(f"Package {package_name} ubuntu data must be dictionary or list")
                    return False
                            
            logger.debug("YAML validation passed")
            return True
            
        except yaml.YAMLError as e:
            logger.error(f"YAML syntax error: {e}")
            return False
        except Exception as e:
            logger.error(f"YAML validation error: {e}")
            return False
    
    def add_ros_package(self, ros_package: ROSPackage, force_update: bool = False) -> bool:
        """
        Add ROS package to rosdep data.
        
        Args:
            ros_package: ROS package to add
            force_update: Force update existing entries
            
        Returns:
            True if package was added or updated
        """
        package_name = ros_package.name
        
        # Check if package already exists
        if package_name in self.rosdep_data and not force_update:
            logger.info(f"Package {package_name} already exists, skipping (use force_update=True to override)")
            return False
            
        # Generate rosdep entries
        rosdep_entries = ros_package.get_rosdep_entries()
        
        # Create package entry
        package_entry = {
            'ubuntu': rosdep_entries
        }
        
        # Add to rosdep data
        self.rosdep_data[package_name] = package_entry
        
        action = "Updated" if package_name in self.rosdep_data else "Added"
        logger.info(f"{action} package {package_name} from repository {ros_package.repository}")
        
        return True
    
    def add_multiple_packages(self, packages: List[ROSPackage], force_update: bool = False) -> int:
        """
        Add multiple ROS packages to rosdep data.
        
        Args:
            packages: List of ROS packages to add
            force_update: Force update existing entries
            
        Returns:
            Number of packages added/updated
        """
        added_count = 0
        
        for package in packages:
            try:
                if self.add_ros_package(package, force_update):
                    added_count += 1
            except Exception as e:
                logger.error(f"Error adding package {package.name}: {e}")
                continue
                
        return added_count
    
    def save_rosdep_file(self, backup: bool = True) -> bool:
        """
        Save rosdep data to file with validation.
        
        Args:
            backup: Create backup of original file
            
        Returns:
            True if successfully saved
        """
        # Validate before saving
        if not self.validate_yaml_syntax(self.rosdep_data):
            logger.error("Cannot save rosdep.yaml: validation failed")
            return False
            
        try:
            # Create backup if requested
            if backup and os.path.exists(self.rosdep_file):
                backup_file = f"{self.rosdep_file}.backup"
                shutil.copy2(self.rosdep_file, backup_file)
                logger.info(f"Created backup: {backup_file}")
                
            # Sort packages alphabetically for consistent output
            sorted_data = dict(sorted(self.rosdep_data.items()))
            
            # Write to file with proper formatting
            with open(self.rosdep_file, 'w', encoding='utf-8') as f:
                yaml.dump(
                    sorted_data,
                    f,
                    default_flow_style=False,
                    sort_keys=False,  # We pre-sorted
                    indent=2,
                    width=120,
                    allow_unicode=True
                )
                
            logger.info(f"Successfully saved rosdep.yaml with {len(self.rosdep_data)} packages")
            return True
            
        except Exception as e:
            logger.error(f"Error saving rosdep.yaml: {e}")
            return False
    
    def get_changes_summary(self, original_packages: Set[str]) -> Dict[str, Any]:
        """
        Get summary of changes made to rosdep.yaml.
        
        Args:
            original_packages: Set of packages before update
            
        Returns:
            Dictionary with change summary
        """
        current_packages = self.get_existing_packages()
        
        added_packages = current_packages - original_packages
        removed_packages = original_packages - current_packages
        
        return {
            'total_packages_before': len(original_packages),
            'total_packages_after': len(current_packages),
            'added_packages': list(sorted(added_packages)),
            'removed_packages': list(sorted(removed_packages)),
            'added_count': len(added_packages),
            'removed_count': len(removed_packages),
            'net_change': len(added_packages) - len(removed_packages)
        }
    
    def filter_new_packages(self, packages: List[ROSPackage]) -> List[ROSPackage]:
        """
        Filter packages to only include those not already in rosdep.yaml.
        
        Args:
            packages: List of ROS packages
            
        Returns:
            List of packages not yet in rosdep.yaml
        """
        existing_packages = self.get_existing_packages()
        new_packages = []
        
        for package in packages:
            if package.name not in existing_packages:
                new_packages.append(package)
            else:
                logger.debug(f"Package {package.name} already exists in rosdep.yaml")
                
        logger.info(f"Filtered {len(packages)} packages down to {len(new_packages)} new packages")
        return new_packages
    
    def validate_existing_entries(self) -> List[str]:
        """
        Validate existing rosdep.yaml entries for common issues.
        
        Returns:
            List of validation warnings/errors
        """
        issues = []
        
        for package_name, package_data in self.rosdep_data.items():
            # Check for missing ubuntu key
            if 'ubuntu' not in package_data:
                issues.append(f"Package {package_name} missing 'ubuntu' key")
                continue
                
            ubuntu_data = package_data['ubuntu']
            if isinstance(ubuntu_data, list):
                if not ubuntu_data:
                    issues.append(f"Package {package_name} has empty ubuntu list")
                for pkg in ubuntu_data:
                    if not pkg.startswith('ros-'):
                        issues.append(f"Package {package_name} has non-ROS package: {pkg}")
            elif isinstance(ubuntu_data, dict):
                # Check for empty distributions
                for distro, packages in ubuntu_data.items():
                    if not packages:
                        issues.append(f"Package {package_name} has empty {distro} distribution")
                        
                    # Check for invalid package names
                    for pkg in packages:
                        if not pkg.startswith('ros-'):
                            issues.append(f"Package {package_name} has non-ROS package: {pkg}")
            else:
                issues.append(f"Package {package_name} ubuntu data must be dictionary or list")
                        
        return issues


def update_rosdep_with_packages(packages: List[ROSPackage], rosdep_file: str = 'rosdep.yaml', force_update: bool = False) -> Dict[str, Any]:
    """
    High-level function to update rosdep.yaml with new packages.
    
    Args:
        packages: List of ROS packages to add
        rosdep_file: Path to rosdep.yaml file
        force_update: Force update existing entries
        
    Returns:
        Dictionary with update results
    """
    updater = ROSDepUpdater(rosdep_file)
    
    # Get baseline
    original_packages = updater.get_existing_packages()
    
    # Filter to only new packages unless force update
    if not force_update:
        packages_to_add = updater.filter_new_packages(packages)
    else:
        packages_to_add = packages
        
    if not packages_to_add:
        logger.info("No new packages to add")
        return {
            'success': True,
            'packages_added': 0,
            'changes': updater.get_changes_summary(original_packages),
            'message': 'No new packages found'
        }
    
    # Add packages
    added_count = updater.add_multiple_packages(packages_to_add, force_update)
    
    if added_count == 0:
        logger.info("No packages were added")
        return {
            'success': True,
            'packages_added': 0,
            'changes': updater.get_changes_summary(original_packages),
            'message': 'No packages were added'
        }
    
    # Save file
    if updater.save_rosdep_file():
        changes = updater.get_changes_summary(original_packages)
        logger.info(f"Successfully updated rosdep.yaml: {changes['added_count']} packages added")
        
        return {
            'success': True,
            'packages_added': added_count,
            'changes': changes,
            'message': f"Added {added_count} new packages to rosdep.yaml"
        }
    else:
        logger.error("Failed to save rosdep.yaml")
        return {
            'success': False,
            'packages_added': 0,
            'changes': {},
            'message': 'Failed to save rosdep.yaml'
        }


if __name__ == "__main__":
    # Test the rosdep updater
    logging.basicConfig(level=logging.INFO)
    
    from github_api import create_github_client
    from package_analyzer import PackageAnalyzer
    
    client = create_github_client()
    if client:
        analyzer = PackageAnalyzer(client)
        packages = analyzer.analyze_organization_repositories()
        
        if packages:
            result = update_rosdep_with_packages(packages, 'test_rosdep.yaml')
            print(f"\nUpdate result: {result}")
        else:
            print("No packages found to process")
