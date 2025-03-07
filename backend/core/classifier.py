# backend/core/classifier.py

import os
import re
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import json

from .file_scanner import GISFileMetadata

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class ClassificationRule:
    """Data class for classification rules."""
    name: str
    description: str
    category: str
    priority: int = 0
    # Rule conditions
    filename_pattern: Optional[str] = None
    attribute_contains: Optional[Dict[str, str]] = None
    geometry_types: Optional[List[str]] = None
    
    def matches(self, metadata: GISFileMetadata) -> bool:
        """Check if a file matches this classification rule."""
        # Check filename pattern
        if self.filename_pattern and not re.search(self.filename_pattern, metadata.file_name, re.IGNORECASE):
            return False
            
        # Check attribute schema
        if self.attribute_contains and metadata.attribute_schema:
            for attr_name, attr_value in self.attribute_contains.items():
                # Check if the attribute exists
                if attr_name not in metadata.attribute_schema:
                    return False
                # For more complex matching, we would need to access the actual data values
        
        # Check geometry types
        if self.geometry_types and metadata.geometry_types:
            if not any(geom_type in self.geometry_types for geom_type in metadata.geometry_types):
                return False
                
        # If we passed all checks, it's a match
        return True


@dataclass
class ClassificationResult:
    """Data class for classification results."""
    metadata: GISFileMetadata
    category: str
    confidence: float  # 0.0 to 1.0
    matching_rules: List[str]  # Names of matching rules
    suggested_path: Optional[str] = None
    suggested_name: Optional[str] = None


class DataClassifier:
    """
    Classifies GIS data based on rules and patterns.
    Supports both rule-based and optional ML-based classification.
    """
    
    DEFAULT_RULES = [
        ClassificationRule(
            name="Base Maps",
            description="Base map layers like administrative boundaries",
            category="basemaps",
            filename_pattern=r"(boundary|admin|border|limits)",
            geometry_types=["Polygon", "MultiPolygon"]
        ),
        ClassificationRule(
            name="Roads",
            description="Road network data",
            category="transportation",
            filename_pattern=r"(road|street|highway|transportation)",
            geometry_types=["LineString", "MultiLineString"]
        ),
        ClassificationRule(
            name="Points of Interest",
            description="POI data",
            category="points_of_interest",
            filename_pattern=r"(poi|point|location|facility)",
            geometry_types=["Point", "MultiPoint"]
        ),
        ClassificationRule(
            name="Hydrography",
            description="Water features",
            category="hydrography",
            filename_pattern=r"(water|river|stream|lake|hydro)",
            geometry_types=["Polygon", "MultiPolygon", "LineString"]
        ),
        ClassificationRule(
            name="Elevation",
            description="Elevation data",
            category="elevation",
            filename_pattern=r"(dem|elevation|contour|height|dtm)",
        ),
        ClassificationRule(
            name="Land Cover",
            description="Land cover or land use data",
            category="land_cover",
            filename_pattern=r"(land|cover|use|lulc|vegetation)",
            geometry_types=["Polygon", "MultiPolygon"]
        ),
    ]
    
    def __init__(self, custom_rules_path: Optional[str] = None):
        """
        Initialize the classifier with rules.
        
        Args:
            custom_rules_path: Optional path to a JSON file with custom classification rules
        """
        self.rules = self.DEFAULT_RULES.copy()
        
        # Load custom rules if provided
        if custom_rules_path and os.path.exists(custom_rules_path):
            self._load_custom_rules(custom_rules_path)
    
    def _load_custom_rules(self, rules_path: str):
        """Load custom classification rules from a JSON file."""
        try:
            with open(rules_path, 'r') as f:
                custom_rules = json.load(f)
                
            for rule_data in custom_rules:
                rule = ClassificationRule(
                    name=rule_data.get('name', 'Unknown'),
                    description=rule_data.get('description', ''),
                    category=rule_data.get('category', 'other'),
                    priority=rule_data.get('priority', 0),
                    filename_pattern=rule_data.get('filename_pattern'),
                    attribute_contains=rule_data.get('attribute_contains'),
                    geometry_types=rule_data.get('geometry_types')
                )
                self.rules.append(rule)
                
            logger.info(f"Loaded {len(custom_rules)} custom classification rules")
            
        except Exception as e:
            logger.error(f"Failed to load custom rules: {str(e)}")
    
    def classify_file(self, metadata: GISFileMetadata) -> ClassificationResult:
        """
        Classify a GIS file based on its metadata.
        
        Args:
            metadata: GISFileMetadata object with file information
            
        Returns:
            ClassificationResult with category and confidence
        """
        matching_rules = []
        
        # Find all matching rules
        for rule in self.rules:
            if rule.matches(metadata):
                matching_rules.append(rule)
        
        # Sort matching rules by priority
        matching_rules.sort(key=lambda r: r.priority, reverse=True)
        
        # If no rules match, use a default classification
        if not matching_rules:
            return ClassificationResult(
                metadata=metadata,
                category="unclassified",
                confidence=0.0,
                matching_rules=[],
                suggested_path=os.path.join("unclassified", metadata.file_name)
            )
        
        # Use the highest priority rule for classification
        top_rule = matching_rules[0]
        
        # Calculate confidence based on number of matching rules and their priorities
        # This is a simple approach and could be made more sophisticated
        confidence = min(1.0, (0.5 + 0.1 * len(matching_rules) + 0.1 * top_rule.priority))
        
        # Generate suggested file path based on classification
        suggested_path = os.path.join(top_rule.category, metadata.file_name)
        
        return ClassificationResult(
            metadata=metadata,
            category=top_rule.category,
            confidence=confidence,
            matching_rules=[rule.name for rule in matching_rules],
            suggested_path=suggested_path
        )
    
    def classify_batch(self, metadata_list: List[GISFileMetadata]) -> List[ClassificationResult]:
        """
        Classify a batch of GIS files.
        
        Args:
            metadata_list: List of GISFileMetadata objects
            
        Returns:
            List of ClassificationResult objects
        """
        results = []
        for metadata in metadata_list:
            results.append(self.classify_file(metadata))
        
        return results
        
    def add_rule(self, rule: ClassificationRule):
        """Add a new classification rule."""
        self.rules.append(rule)
        
    def save_rules(self, output_path: str):
        """Save current rules to a JSON file."""
        rule_dicts = []
        for rule in self.rules:
            rule_dict = {
                'name': rule.name,
                'description': rule.description,
                'category': rule.category,
                'priority': rule.priority
            }
            
            if rule.filename_pattern:
                rule_dict['filename_pattern'] = rule.filename_pattern
            if rule.attribute_contains:
                rule_dict['attribute_contains'] = rule.attribute_contains
            if rule.geometry_types:
                rule_dict['geometry_types'] = rule.geometry_types
                
            rule_dicts.append(rule_dict)
            
        try:
            with open(output_path, 'w') as f:
                json.dump(rule_dicts, f, indent=2)
            logger.info(f"Saved {len(rule_dicts)} rules to {output_path}")
        except Exception as e:
            logger.error(f"Failed to save rules: {str(e)}")

# Usage example
if __name__ == "__main__":
    from file_scanner import FileScanner
    
    scanner = FileScanner()
    classifier = DataClassifier()
    
    # Scan a directory
    metadata_list = scanner.scan_directory("./sample_data")
    
    # Classify files
    results = classifier.classify_batch(metadata_list)
    
    # Print results
    for result in results:
        print(f"File: {result.metadata.file_name}")
        print(f"Category: {result.category} (confidence: {result.confidence:.2f})")
        print(f"Matching rules: {', '.join(result.matching_rules)}")
        print(f"Suggested path: {result.suggested_path}")
        print("-" * 50)
