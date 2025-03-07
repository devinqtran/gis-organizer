# backend/core/file_scanner.py

import os
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import fiona
import geopandas as gpd
from shapely.geometry import shape

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class GISFileMetadata:
    """Data class for storing GIS file metadata."""
    file_path: str
    file_name: str
    file_type: str
    file_size: int
    crs: Optional[str] = None
    layer_count: int = 1
    feature_count: Optional[int] = None
    attribute_schema: Optional[Dict[str, str]] = None
    bounds: Optional[Tuple[float, float, float, float]] = None
    geometry_types: Optional[List[str]] = None
    last_modified: Optional[str] = None

class FileScanner:
    """
    Scans and parses GIS files to extract metadata and structure information.
    Uses GDAL/OGR via Fiona for reading various GIS formats.
    """
    
    # Supported file extensions
    SUPPORTED_EXTENSIONS = {
        '.shp': 'Shapefile',
        '.geojson': 'GeoJSON',
        '.json': 'JSON',
        '.gdb': 'File Geodatabase',
        '.gpkg': 'GeoPackage',
        '.kml': 'KML',
        '.tif': 'GeoTIFF',
        '.tiff': 'GeoTIFF',
    }
    
    def __init__(self):
        # Register all drivers
        fiona.drivers()
        
    def is_supported_file(self, file_path: str) -> bool:
        """Check if the file format is supported."""
        _, ext = os.path.splitext(file_path.lower())
        return ext in self.SUPPORTED_EXTENSIONS or os.path.isdir(file_path) and ext == '.gdb'
    
    def scan_directory(self, directory_path: str) -> List[GISFileMetadata]:
        """
        Scan a directory recursively for supported GIS files.
        
        Args:
            directory_path: Path to the directory to scan
            
        Returns:
            List of GISFileMetadata objects for each supported file
        """
        if not os.path.exists(directory_path):
            raise FileNotFoundError(f"Directory not found: {directory_path}")
        
        logger.info(f"Scanning directory: {directory_path}")
        results = []
        
        for root, dirs, files in os.walk(directory_path):
            # Check for file geodatabases
            for dir_name in dirs:
                if dir_name.lower().endswith('.gdb'):
                    gdb_path = os.path.join(root, dir_name)
                    try:
                        metadata = self.extract_metadata(gdb_path)
                        if metadata:
                            results.append(metadata)
                    except Exception as e:
                        logger.error(f"Error processing geodatabase {gdb_path}: {str(e)}")
            
            # Process individual files
            for file in files:
                file_path = os.path.join(root, file)
                if self.is_supported_file(file_path):
                    try:
                        metadata = self.extract_metadata(file_path)
                        if metadata:
                            results.append(metadata)
                    except Exception as e:
                        logger.error(f"Error processing file {file_path}: {str(e)}")
        
        logger.info(f"Found {len(results)} GIS files")
        return results
    
    def extract_metadata(self, file_path: str) -> Optional[GISFileMetadata]:
        """
        Extract metadata from a GIS file.
        
        Args:
            file_path: Path to the GIS file
            
        Returns:
            GISFileMetadata object with extracted information or None if extraction failed
        """
        logger.info(f"Extracting metadata from: {file_path}")
        
        file_name = os.path.basename(file_path)
        file_size = os.path.getsize(file_path) if os.path.isfile(file_path) else 0
        _, ext = os.path.splitext(file_path.lower())
        file_type = self.SUPPORTED_EXTENSIONS.get(ext, "Unknown")
        last_modified = os.path.getmtime(file_path)
        
        # Initialize with basic file info
        metadata = GISFileMetadata(
            file_path=file_path,
            file_name=file_name,
            file_type=file_type,
            file_size=file_size,
            last_modified=str(last_modified)
        )
        
        try:
            # Handle different file types appropriately
            if ext == '.shp' or ext == '.geojson' or ext == '.json':
                return self._extract_vector_metadata(file_path, metadata)
            elif ext == '.gdb':
                return self._extract_geodatabase_metadata(file_path, metadata)
            elif ext in ['.tif', '.tiff']:
                return self._extract_raster_metadata(file_path, metadata)
            else:
                logger.warning(f"Detailed metadata extraction not implemented for {ext} files")
                return metadata
        except Exception as e:
            logger.error(f"Failed to extract metadata from {file_path}: {str(e)}")
            return metadata
    
    def _extract_vector_metadata(self, file_path: str, metadata: GISFileMetadata) -> GISFileMetadata:
        """Extract metadata from vector files (Shapefile, GeoJSON)."""
        try:
            # Use geopandas to read the file
            gdf = gpd.read_file(file_path)
            
            metadata.crs = str(gdf.crs)
            metadata.feature_count = len(gdf)
            metadata.bounds = tuple(gdf.total_bounds)
            
            # Get attribute schema
            metadata.attribute_schema = {column: str(dtype) for column, dtype in zip(gdf.columns, gdf.dtypes)}
            
            # Extract unique geometry types
            if 'geometry' in gdf:
                metadata.geometry_types = list(set(geom.geom_type for geom in gdf.geometry if geom))
            
            return metadata
            
        except Exception as e:
            logger.error(f"Error in vector metadata extraction: {str(e)}")
            raise
    
    def _extract_geodatabase_metadata(self, gdb_path: str, metadata: GISFileMetadata) -> GISFileMetadata:
        """Extract metadata from File Geodatabase."""
        try:
            # List layers in the geodatabase
            layers = fiona.listlayers(gdb_path)
            metadata.layer_count = len(layers)
            
            # For simplicity, we'll just get feature counts for each layer
            feature_counts = {}
            geometry_types = set()
            
            for layer in layers:
                with fiona.open(gdb_path, layer=layer) as src:
                    feature_counts[layer] = len(src)
                    # Sample some geometry types (first 100 features)
                    for i, feature in enumerate(src):
                        if i >= 100:  # Limit to avoid processing too many features
                            break
                        if feature.get('geometry'):
                            geometry_types.add(feature['geometry']['type'])
            
            metadata.feature_count = sum(feature_counts.values())
            metadata.geometry_types = list(geometry_types)
            
            # Additional metadata could be extracted here
            
            return metadata
            
        except Exception as e:
            logger.error(f"Error in geodatabase metadata extraction: {str(e)}")
            raise
    
    def _extract_raster_metadata(self, file_path: str, metadata: GISFileMetadata) -> GISFileMetadata:
        """Extract metadata from raster files (GeoTIFF)."""
        try:
            # This would require rasterio, but for simplicity we'll just return basic info
            # Future implementation would include bands, resolution, etc.
            metadata.file_type = "Raster"
            return metadata
            
        except Exception as e:
            logger.error(f"Error in raster metadata extraction: {str(e)}")
            raise

# Usage example
if __name__ == "__main__":
    scanner = FileScanner()
    results = scanner.scan_directory("./sample_data")
    for result in results:
        print(f"File: {result.file_name}")
        print(f"Type: {result.file_type}")
        print(f"Features: {result.feature_count}")
        print(f"CRS: {result.crs}")
        print("-" * 50)
