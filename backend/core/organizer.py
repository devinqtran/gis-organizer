# backend/core/organizer.py

import os
import shutil
import logging
import json
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import fiona
import geopandas as gpd
import datetime

from .file_scanner import GISFileMetadata
from .classifier import ClassificationResult

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class OrganizationTemplate:
    """Data class for organization templates."""
    name: str
    description: str
    folder_structure: Dict[str, Any]  # Nested dictionary of folder structure
    naming_convention: Optional[Dict[str, str]] = None  # Rules for renaming files
    metadata_requirements: Optional[List[str]] = None  # Required metadata fields

@dataclass
class OrganizationPlan:
    """Data class for organization plan."""
    source_files: List[ClassificationResult]
    template: OrganizationTemplate
    destination_root: str
    operations: List[Dict[str, Any]] = None  # List of operations to perform
    
    def __post_init__(self):
        if self.operations is None:
            self.operations = []

@dataclass
class OrganizationResult:
    """Data class for organization results."""
    plan: OrganizationPlan
    success: bool
    timestamp: str
    message: str
    successful_operations: int = 0
    failed_operations: int = 0
    execution_time: float = 0.0

class DataOrganizer:
    """
    Organizes GIS data based on classification results and templates.
    Handles file movement, renaming, and structure creation.
    """
    
    # Default organization templates
    DEFAULT_TEMPLATES = [
        OrganizationTemplate(
            name="Standard GIS Project",
            description="Standard GIS project organization with separate folders for vector, raster, and output data",
            folder_structure={
                "vector": {
                    "basemaps": {},
                    "transportation": {},
                    "points_of_interest": {},
                    "hydrography": {},
                    "boundaries": {},
                    "other": {}
                },
                "raster": {
                    "elevation": {},
                    "imagery": {},
                    "land_cover": {},
                    "other": {}
                },
                "output": {
                    "maps": {},
                    "analysis": {},
                    "exports": {}
                },
                "metadata": {},
                "documentation": {}
            }
        ),
        OrganizationTemplate(
            name="Simple Flat Structure",
            description="Simple flat organization with categories as folders",
            folder_structure={
                "basemaps": {},
                "transportation": {},
                "points_of_interest": {},
                "hydrography": {},
                "elevation": {},
                "land_cover": {},
                "imagery": {},
                "other": {}
            }
        )
    ]
    
    def __init__(self, custom_templates_path: Optional[str] = None):
        """
        Initialize the organizer with templates.
        
        Args:
            custom_templates_path: Optional path to a JSON file with custom organization templates
        """
        self.templates = self.DEFAULT_TEMPLATES.copy()
        
        # Load custom templates if provided
        if custom_templates_path and os.path.exists(custom_templates_path):
            self._load_custom_templates(custom_templates_path)
    
    def _load_custom_templates(self, templates_path: str):
        """Load custom organization templates from a JSON file."""
        try:
            with open(templates_path, 'r') as f:
                custom_templates = json.load(f)
                
            for template_data in custom_templates:
                template = OrganizationTemplate(
                    name=template_data.get('name', 'Custom Template'),
                    description=template_data.get('description', ''),
                    folder_structure=template_data.get('folder_structure', {}),
                    naming_convention=template_data.get('naming_convention'),
                    metadata_requirements=template_data.get('metadata_requirements')
                )
                self.templates.append(template)
                
            logger.info(f"Loaded {len(custom_templates)} custom organization templates")
            
        except Exception as e:
            logger.error(f"Failed to load custom templates: {str(e)}")
    
    def create_organization_plan(self, 
                               classified_files: List[ClassificationResult],
                               template_name: str,
                               destination_root: str) -> OrganizationPlan:
        """
        Create a plan for organizing files based on classification results and a template.
        
        Args:
            classified_files: List of ClassificationResult objects
            template_name: Name of the template to use
            destination_root: Root directory for the organized files
            
        Returns:
            OrganizationPlan object with operations to perform
        """
        # Find the template
        template = next((t for t in self.templates if t.name == template_name), None)
        if not template:
            raise ValueError(f"Template '{template_name}' not found")
        
        # Create the plan
        plan = OrganizationPlan(
            source_files=classified_files,
            template=template,
            destination_root=destination_root
        )
        
        # Process each classified file
        for result in classified_files:
            metadata = result.metadata
            category = result.category
            
            # Determine destination path based on template and classification
            if template_name == "Standard GIS Project":
                # For the standard template, we need to determine if it's vector or raster
                if metadata.file_type in ["Shapefile", "GeoJSON", "File Geodatabase"]:
                    base_folder = "vector"
                elif metadata.file_type in ["GeoTIFF"]:
                    base_folder = "raster"
                else:
                    base_folder = "vector"  # Default to vector for unknown types
                
                # Use the category, or 'other' if the category doesn't exist in the template
                if category in template.folder_structure[base_folder]:
                    sub_folder = category
                else:
                    sub_folder = "other"
                
                dest_folder = os.path.join(destination_root, base_folder, sub_folder)
                
            elif template_name == "Simple Flat Structure":
                # For flat structure, just use the category directly
                if category in template.folder_structure:
                    dest_folder = os.path.join(destination_root, category)
                else:
                    dest_folder = os.path.join(destination_root, "other")
            else:
                # Generic handling for custom templates
                dest_folder = os.path.join(destination_root, category)
            
            # Determine destination filename (apply naming convention if specified)
            dest_filename = metadata.file_name
            if template.naming_convention:
                # Apply naming convention rules (simplified implementation)
                if 'prefix' in template.naming_convention:
                    dest_filename = f"{template.naming_convention['prefix']}_{dest_filename}"
                if 'category_prefix' in template.naming_convention and template.naming_convention['category_prefix']:
                    dest_filename = f"{category}_{dest_filename}"
            
            # Create operation
            operation = {
                "type": "move",
                "source": metadata.file_path,
                "destination": os.path.join(dest_folder, dest_filename),
                "category": category,
                "metadata": metadata
            }
            
            plan.operations.append(operation)
        
        return plan
    
    def preview_organization(self, plan: OrganizationPlan) -> Dict[str, Any]:
        """
        Generate a preview of the organization plan.
        
        Args:
            plan: OrganizationPlan object
            
        Returns:
            Dictionary with preview information
        """
        preview = {
            "template": plan.template.name,
            "destination_root": plan.destination_root,
            "file_count": len(plan.operations),
            "folder_structure": {},
            "operations": []
        }
        
        # Build folder structure preview
        for op in plan.operations:
            dest_path = op["destination"]
            rel_path = os.path.relpath(dest_path, plan.destination_root)
            folder_path = os.path.dirname(rel_path)
            
            # Add to folder structure
            folders = folder_path.split(os.path.sep)
            current = preview["folder_structure"]
            for folder in folders:
                if folder not in current:
                    current[folder] = {}
                current = current[folder]
            
            # Add operation summary
            preview["operations"].append({
                "source": op["source"],
                "destination": rel_path,
                "category": op["category"]
            })
        
        return preview
    
    def execute_organization(self, plan: OrganizationPlan, dry_run: bool = False) -> OrganizationResult:
        """
        Execute the organization plan.
        
        Args:
            plan: OrganizationPlan object
            dry_run: If True, only simulate the operations without actually performing them
            
        Returns:
            OrganizationResult object with results
        """
        start_time = datetime.datetime.now()
        result = OrganizationResult(
            plan=plan,
            success=True,
            timestamp=start_time.isoformat(),
            message="Organization completed successfully"
        )
        
        try:
            # Create folder structure first
            self._create_folder_structure(plan.destination_root, plan.template.folder_structure, dry_run)
            
            # Execute operations
            for op in plan.operations:
                try:
                    if op["type"] == "move":
                        source = op["source"]
                        destination = op["destination"]
                        
                        # Create destination folder if it doesn't exist
                        dest_dir = os.path.dirname(destination)
                        if not os.path.exists(dest_dir) and not dry_run:
                            os.makedirs(dest_dir, exist_ok=True)
                        
                        # Move/copy file
                        if not dry_run:
                            # Check if source is a geodatabase (directory)
                            if os.path.isdir(source) and source.lower().endswith('.gdb'):
                                if os.path.exists(destination):
                                    # If destination exists, remove it first
                                    shutil.rmtree(destination)
                                # Copy the entire directory
                                shutil.copytree(source, destination)
                            else:
                                # Regular file copy
                                shutil.copy2(source, destination)
                        
                        logger.info(f"{'[DRY RUN] Would move' if dry_run else 'Moved'} {source} to {destination}")
                        result.successful_operations += 1
                    
                except Exception as e:
                    logger.error(f"Operation failed: {str(e)}")
                    result.failed_operations += 1
                    
            # Calculate execution time
            end_time = datetime.datetime.now()
            result.execution_time = (end_time - start_time).total_seconds()
            
            # Update result message
            if result.failed_operations > 0:
                result.success = False
                result.message = f"Organization completed with {result.failed_operations} errors"
                
            if dry_run:
                result.message = f"[DRY RUN] {result.message}"
                
        except Exception as e:
            result.success = False
            result.message = f"Organization failed: {str(e)}"
            
        return result
    
    def _create_folder_structure(self, root_path: str, structure: Dict[str, Any], dry_run: bool = False):
        """
        Recursively create folder structure.
        
        Args:
            root_path: Root directory path
            structure: Dictionary representing folder structure
            dry_run: If True, only simulate creating directories
        """
        if not dry_run and not os.path.exists(root_path):
            os.makedirs(root_path, exist_ok=True)
            
        for folder, sub_structure in structure.items():
            folder_path = os.path.join(root_path, folder)
            if not dry_run and not os.path.exists(folder_path):
                os.makedirs(folder_path, exist_ok=True)
                
            if sub_structure:  # If there are subfolders
                self._create_folder_structure(folder_path, sub_structure, dry_run)
    
    def save_template(self, template: OrganizationTemplate, output_path: str):
        """Save a template to a JSON file."""
        template_dict = {
            'name': template.name,
            'description': template.description,
            'folder_structure': template.folder_structure
        }
        
        if template.naming_convention:
            template_dict['naming_convention'] = template.naming_convention
        if template.metadata_requirements:
            template_dict['metadata_requirements'] = template.metadata_requirements
            
        try:
            # Check if file exists
            if os.path.exists(output_path):
                # Load existing templates
                with open(output_path, 'r') as f:
                    templates = json.load(f)
            else:
                templates = []
                
            # Check if template already exists
            for i, existing in enumerate(templates):
                if existing.get('name') == template.name:
                    # Update existing template
                    templates[i] = template_dict
                    break
            else:
                # Add new template
                templates.append(template_dict)
                
            # Save templates
            with open(output_path, 'w') as f:
                json.dump(templates, f, indent=2)
                
            logger.info(f"Saved template '{template.name}' to {output_path}")
            
        except Exception as e:
            logger.error(f"Failed to save template: {str(e)}")

# Usage example
if __name__ == "__main__":
    from file_scanner import FileScanner
    from classifier import DataClassifier
    
    scanner = FileScanner()
    classifier = DataClassifier()
    organizer = DataOrganizer()
    
    # Scan a directory
    metadata_list = scanner.scan_directory("./sample_data")
    
    # Classify files
    classification_results = classifier.classify_batch(metadata_list)
    
    # Create organization plan
    plan = organizer.create_organization_plan(
        classification_results,
        "Standard GIS Project",
        "./organized_data"
    )
    
    # Preview organization
    preview = organizer.preview_organization(plan)
    print(json.dumps(preview, indent=2))
    
    # Execute organization (dry run)
    result = organizer.execute_organization(plan, dry_run=True)
    print(f"Result: {result.message}")
    print(f"Successful operations: {result.successful_operations}")
    print(f"Failed operations: {result.failed_operations}")
    print(f"Execution time: {result.execution_time:.2f} seconds")
