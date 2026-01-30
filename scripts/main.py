#!/usr/bin/env python3
"""
Main orchestration script for automated rosdep.yaml updates.
"""

import os
import sys
import logging
from typing import Optional, List
from github_api import create_github_client, RateLimitError
from package_analyzer import PackageAnalyzer
from rosdep_updater import update_rosdep_with_packages

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('rosdep_automation.log', mode='a')
    ]
)

logger = logging.getLogger(__name__)


def main():
    """Main automation workflow."""
    logger.info("=" * 60)
    logger.info("STARTING ROSDEP.YAML AUTOMATION")
    logger.info("=" * 60)
    
    # Get environment variables
    github_token = os.getenv('GITHUB_TOKEN')
    repository_name = os.getenv('REPOSITORY_NAME')
    force_update = os.getenv('FORCE_UPDATE', 'false').lower() == 'true'
    
    if not github_token:
        logger.error("GITHUB_TOKEN environment variable not set")
        sys.exit(1)
    
    logger.info(f"Configuration:")
    logger.info(f"  - Specific repository: {repository_name or 'None (scan all)'}")
    logger.info(f"  - Force update: {force_update}")
    
    try:
        # Initialize GitHub client
        logger.info("Initializing GitHub API client...")
        github_client = create_github_client()
        if not github_client:
            logger.error("Failed to create GitHub client")
            sys.exit(1)
        
        # Initialize package analyzer
        logger.info("Initializing package analyzer...")
        analyzer = PackageAnalyzer(github_client)
        
        # Analyze repositories for ROS packages
        logger.info("Scanning repositories for ROS packages...")
        
        # Get existing packages from rosdep.yaml for filtering
        from rosdep_updater import ROSDepUpdater
        rosdep_updater = ROSDepUpdater('rosdep.yaml')
        existing_packages = rosdep_updater.get_existing_packages()
        logger.info(f"Found {len(existing_packages)} existing packages in rosdep.yaml")
        
        if repository_name:
            logger.info(f"Analyzing specific repository: {repository_name}")
            packages = analyzer.analyze_organization_repositories(specific_repo=repository_name, existing_packages=existing_packages)
        else:
            logger.info("Analyzing all haru-project repositories")
            packages = analyzer.analyze_organization_repositories(existing_packages=existing_packages)
        
        if not packages:
            logger.info("No ROS packages found")
            return
        
        # Remove duplicates
        unique_packages = analyzer.get_unique_packages(packages)
        if len(unique_packages) != len(packages):
            logger.info(f"Removed {len(packages) - len(unique_packages)} duplicate packages")
        
        logger.info(f"Found {len(unique_packages)} unique ROS packages:")
        for package in unique_packages:
            logger.info(f"  - {package.name} (from {package.repository})")
        
        # Update rosdep.yaml
        logger.info("Updating rosdep.yaml...")
        result = update_rosdep_with_packages(
            unique_packages,
            rosdep_file='rosdep.yaml',
            force_update=force_update
        )
        
        # Log results
        if result['success']:
            logger.info(f"Update completed successfully!")
            logger.info(f"  - Packages added: {result['packages_added']}")
            if result['changes']:
                changes = result['changes']
                logger.info(f"  - Total packages: {changes['total_packages_before']} → {changes['total_packages_after']}")
                if changes['added_packages']:
                    logger.info(f"  - New packages: {', '.join(changes['added_packages'])}")
        else:
            logger.error(f"Update failed: {result['message']}")
        
        # Exit with appropriate code
        if result['success']:
            logger.info("Automation completed successfully")
            sys.exit(0)
        else:
            logger.error("Automation completed with errors")
            sys.exit(1)
            
    except RateLimitError as e:
        if e.reset_epoch:
            from datetime import datetime, timezone
            reset_time = datetime.fromtimestamp(e.reset_epoch, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
            logger.error(f"GitHub API rate limit exceeded. Reset at {reset_time}.")
        logger.error(str(e))
        sys.exit(1)
    except Exception as e:
        error_msg = f"Automation failed with exception: {e}"
        logger.error(error_msg, exc_info=True)
        sys.exit(1)
    
    finally:
        logger.info("=" * 60)
        logger.info("AUTOMATION WORKFLOW COMPLETED")
        logger.info("=" * 60)


if __name__ == "__main__":
    main()
