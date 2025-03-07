from flask import Flask, request, jsonify, Blueprint
from ..core.file_scanner import GISFileScanner
from ..core.metadata_manager import MetadataManager
from ..core.organizer import GISOrganizer
from ..core.classifier import GISClassifier
import os
import json

# Create blueprint for API routes
api_bp = Blueprint('api', __name__)

# Initialize core components
file_scanner = GISFileScanner()
metadata_manager = MetadataManager()
classifier = GISClassifier()
organizer = GISOrganizer()

@api_bp.route('/scan', methods=['POST'])
def scan_directory():
    """
    Scan a directory for GIS files and return metadata.
    
    Expects JSON: {"directory": "/path/to/scan"}
    """
    data = request.json
    directory = data.get('directory')
    
    if not directory or not os.path.exists(directory):
        return jsonify({"error": "Invalid directory path"}), 400
    
    try:
        files = file_scanner.scan_directory(directory)
        return jsonify({
            "count": len(files),
            "files": [file.to_dict() for file in files]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp.route('/metadata/extract', methods=['POST'])
def extract_metadata():
    """
    Extract metadata from a GIS file.
    
    Expects JSON: {"file_path": "/path/to/file.shp"}
    """
    data = request.json
    file_path = data.get('file_path')
    
    if not file_path or not os.path.exists(file_path):
        return jsonify({"error": "Invalid file path"}), 400
    
    try:
        # Get basic metadata from file scanner
        file_metadata = file_scanner.scan_file(file_path)
        
        # Extract existing metadata
        existing_metadata = metadata_manager.extract_existing_metadata(file_path)
        
        # Create enhanced metadata
        enhanced_metadata = metadata_manager.create_enhanced_metadata(file_metadata, existing_metadata)
        
        return jsonify({"metadata": asdict(enhanced_metadata)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp.route('/metadata/save', methods=['POST'])
def save_metadata():
    """
    Save metadata to file.
    
    Expects JSON: {
        "file_path": "/path/to/file.shp",
        "metadata": {...},
        "format": "fgdc" or "iso"
    }
    """
    data = request.json
    file_path = data.get('file_path')
    metadata_dict = data.get('metadata')
    format_type = data.get('format', 'fgdc')
    
    if not all([file_path, metadata_dict]) or not os.path.exists(file_path):
        return jsonify({"error": "Invalid request parameters"}), 400
    
    try:
        # Convert dict to EnhancedMetadata object
        from dataclasses import asdict
        from ..core.metadata_manager import EnhancedMetadata
        
        metadata = EnhancedMetadata(**metadata_dict)
        
        # Generate output path
        base_path = os.path.splitext(file_path)[0]
        output_path = f"{base_path}_{format_type}.xml"
        
        # Save metadata
        if format_type.lower() == 'iso':
            success = metadata_manager.export_to_iso(metadata, output_path)
        else:
            success = metadata_manager.export_to_fgdc(metadata, output_path)
        
        if success:
            return jsonify({"success": True, "output_path": output_path})
        else:
            return jsonify({"error": "Failed to save metadata"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp.route('/organize', methods=['POST'])
def organize_files():
    """
    Organize GIS files.
    
    Expects JSON: {
        "source_directory": "/path/to/source",
        "target_directory": "/path/to/target",
        "organization_method": "spatial" or "attribute" or "type"
    }
    """
    data = request.json
    source_dir = data.get('source_directory')
    target_dir = data.get('target_directory')
    method = data.get('organization_method', 'type')
    
    if not all([source_dir, target_dir]) or not os.path.exists(source_dir):
        return jsonify({"error": "Invalid directory paths"}), 400
    
    try:
        # Scan files
        files = file_scanner.scan_directory(source_dir)
        
        # Organize files
        results = organizer.organize_files(files, target_dir, method)
        
        return jsonify({
            "success": True,
            "organized_files": len(results),
            "results": results
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp.route('/classify', methods=['POST'])
def classify_files():
    """
    Classify GIS files by content.
    
    Expects JSON: {"file_paths": ["/path/to/file1.shp", "/path/to/file2.geojson"]}
    """
    data = request.json
    file_paths = data.get('file_paths', [])
    
    if not file_paths:
        return jsonify({"error": "No files provided"}), 400
    
    try:
        results = {}
        for path in file_paths:
            if os.path.exists(path):
                # Get file metadata
                metadata = file_scanner.scan_file(path)
                
                # Classify file
                classification = classifier.classify_file(metadata)
                results[path] = classification
        
        return jsonify({
            "classifications": results
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500