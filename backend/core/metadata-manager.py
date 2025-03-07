import os
import logging
import json
import xml.etree.ElementTree as ET
import xml.dom.minidom as minidom
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import datetime
import pytz
import re

from .file_scanner import GISFileMetadata

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class EnhancedMetadata:
    """Data class for enhanced GIS metadata."""
    # Basic identification
    title: str
    abstract: Optional[str] = None
    purpose: Optional[str] = None
    
    # Dates
    creation_date: Optional[str] = None
    publication_date: Optional[str] = None
    revision_date: Optional[str] = None
    
    # Contacts
    contact_organization: Optional[str] = None
    contact_person: Optional[str] = None
    contact_email: Optional[str] = None
    
    # Spatial information
    coordinate_system: Optional[str] = None
    bbox_west: Optional[float] = None
    bbox_east: Optional[float] = None
    bbox_north: Optional[float] = None
    bbox_south: Optional[float] = None
    
    # Data quality
    lineage: Optional[str] = None
    positional_accuracy: Optional[str] = None
    attribute_accuracy: Optional[str] = None
    completeness: Optional[str] = None
    
    # Distribution
    distribution_format: Optional[str] = None
    online_resource: Optional[str] = None
    
    # Keywords
    keywords: Optional[List[str]] = None
    
    # Technical
    feature_count: Optional[int] = None
    attribute_list: Optional[List[str]] = None
    geometry_type: Optional[str] = None
    file_size: Optional[int] = None
    file_format: Optional[str] = None


class MetadataManager:
    """
    Manages GIS metadata operations including extraction, enhancement, 
    validation and export to standards like FGDC or ISO 19115.
    """
    
    def __init__(self):
        """Initialize the metadata manager."""
        pass
    
    def extract_existing_metadata(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Extract existing metadata from a GIS file.
        
        Args:
            file_path: Path to the GIS file
            
        Returns:
            Dictionary with extracted metadata or None if not found
        """
        # Check for common metadata file extensions
        metadata_extensions = ['.xml', '.meta', '.metadata']
        
        # Remove file extension and try common metadata file patterns
        base_path = os.path.splitext(file_path)[0]
        
        for ext in metadata_extensions:
            metadata_path = base_path + ext
            if os.path.exists(metadata_path):
                return self._parse_metadata_file(metadata_path)
        
        # Look for metadata in parent directory
        file_name = os.path.basename(file_path)
        parent_dir = os.path.dirname(file_path)
        
        for metadata_file in os.listdir(parent_dir):
            if metadata_file.endswith('.xml') or metadata_file.endswith('.meta'):
                metadata_path = os.path.join(parent_dir, metadata_file)
                # Try to parse and check if it references our file
                metadata = self._parse_metadata_file(metadata_path)
                if metadata and 'filename' in metadata and metadata['filename'] == file_name:
                    return metadata
        
        return None
    
    def _parse_metadata_file(self, metadata_path: str) -> Optional[Dict[str, Any]]:
        """
        Parse a metadata file based on its format.
        
        Args:
            metadata_path: Path to the metadata file
            
        Returns:
            Dictionary of parsed metadata or None if parsing failed
        """
        try:
            # Check file extension to determine format
            _, ext = os.path.splitext(metadata_path.lower())
            
            if ext == '.xml':
                return self._parse_xml_metadata(metadata_path)
            elif ext == '.json':
                return self._parse_json_metadata(metadata_path)
            else:
                # Try to parse as plain text
                return self._parse_text_metadata(metadata_path)
                
        except Exception as e:
            logger.error(f"Failed to parse metadata file {metadata_path}: {str(e)}")
            return None
    
    def _parse_xml_metadata(self, xml_path: str) -> Optional[Dict[str, Any]]:
        """Parse XML metadata file (FGDC or ISO format)."""
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
            
            # Check if it's FGDC format
            if 'fgdc' in root.tag.lower() or 'metadata' == root.tag.lower():
                return self._parse_fgdc_metadata(root)
            
            # Check if it's ISO format
            if 'iso' in root.tag.lower() or 'MD_Metadata' in root.tag:
                return self._parse_iso_metadata(root)
            
            # Generic XML parsing as fallback
            result = {}
            for child in root:
                if child.text and child.text.strip():
                    result[child.tag] = child.text.strip()
            
            return result
            
        except Exception as e:
            logger.error(f"XML parsing error: {str(e)}")
            return None
    
    def _parse_fgdc_metadata(self, root: ET.Element) -> Dict[str, Any]:
        """Parse FGDC-format XML metadata."""
        result = {}
        
        # Extract basic identification
        idinfo = root.find('.//idinfo')
        if idinfo is not None:
            citation = idinfo.find('./citation/citeinfo')
            if citation is not None:
                title = citation.find('./title')
                if title is not None and title.text:
                    result['title'] = title.text.strip()
                
                pubdate = citation.find('./pubdate')
                if pubdate is not None and pubdate.text:
                    result['publication_date'] = pubdate.text.strip()
            
            abstract = idinfo.find('./descript/abstract')
            if abstract is not None and abstract.text:
                result['abstract'] = abstract.text.strip()
            
            purpose = idinfo.find('./descript/purpose')
            if purpose is not None and purpose.text:
                result['purpose'] = purpose.text.strip()
            
            # Extract keywords
            keywords = []
            for keyword_node in idinfo.findall('.//keywords/theme/themekey'):
                if keyword_node.text:
                    keywords.append(keyword_node.text.strip())
            if keywords:
                result['keywords'] = keywords
        
        # Extract spatial information
        spdom = root.find('.//spdom/bounding')
        if spdom is not None:
            for direction in ['westbc', 'eastbc', 'northbc', 'southbc']:
                node = spdom.find(f'./{direction}')
                if node is not None and node.text:
                    result[f'bbox_{direction[:-2]}'] = float(node.text.strip())
        
        # Extract contact information
        contact = root.find('.//idinfo/ptcontac/cntinfo')
        if contact is not None:
            cntorg = contact.find('./cntorg')
            if cntorg is not None and cntorg.text:
                result['contact_organization'] = cntorg.text.strip()
            
            cntperson = contact.find('./cntperp/cntper')
            if cntperson is not None and cntperson.text:
                result['contact_person'] = cntperson.text.strip()
            
            cntemail = contact.find('./cntemail')
            if cntemail is not None and cntemail.text:
                result['contact_email'] = cntemail.text.strip()
        
        return result
    
    def _parse_iso_metadata(self, root: ET.Element) -> Dict[str, Any]:
        """Parse ISO 19115 format metadata."""
        # Simplified implementation - would need more comprehensive parsing for full ISO standard
        result = {}
        
        # Extract basic identification
        ident = root.find('.//identificationInfo') or root.find('.//{*}identificationInfo')
        if ident is not None:
            # Title
            title_elem = ident.find('.//{*}title') or ident.find('.//{*}title//{*}CharacterString')
            if title_elem is not None and title_elem.text:
                result['title'] = title_elem.text.strip()
            
            # Abstract
            abstract_elem = ident.find('.//{*}abstract') or ident.find('.//{*}abstract//{*}CharacterString')
            if abstract_elem is not None and abstract_elem.text:
                result['abstract'] = abstract_elem.text.strip()
        
        # Extract dates
        date_elems = root.findall('.//{*}date//{*}DateTime') or root.findall('.//{*}dateStamp//{*}DateTime')
        if date_elems:
            for date_elem in date_elems:
                if date_elem.text:
                    result['creation_date'] = date_elem.text.strip()
                    break
        
        # Extract bbox
        bbox_elem = root.find('.//{*}EX_GeographicBoundingBox')
        if bbox_elem is not None:
            for direction in ['westBoundLongitude', 'eastBoundLongitude', 'southBoundLatitude', 'northBoundLatitude']:
                dir_elem = bbox_elem.find(f'.//{{*}}{direction}//{{*}}Decimal')
                if dir_elem is not None and dir_elem.text:
                    result[f'bbox_{direction[:5].lower()}'] = float(dir_elem.text.strip())
        
        return result
    
    def _parse_json_metadata(self, json_path: str) -> Optional[Dict[str, Any]]:
        """Parse JSON format metadata."""
        try:
            with open(json_path, 'r') as f:
                return json.load(f)
                
        except Exception as e:
            logger.error(f"JSON parsing error: {str(e)}")
            return None
    
    def _parse_text_metadata(self, text_path: str) -> Optional[Dict[str, Any]]:
        """Parse plain text metadata (basic key-value format)."""
        try:
            result = {}
            with open(text_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if ':' in line:
                        key, value = line.split(':', 1)
                        result[key.strip().lower()] = value.strip()
            return result
                
        except Exception as e:
            logger.error(f"Text parsing error: {str(e)}")
            return None
    
    def create_enhanced_metadata(self, basic_metadata: GISFileMetadata, 
                               existing_metadata: Optional[Dict[str, Any]] = None) -> EnhancedMetadata:
        """
        Create enhanced metadata by combining basic file info with existing metadata.
        
        Args:
            basic_metadata: GISFileMetadata object from file scanner
            existing_metadata: Optional dictionary of existing metadata
            
        Returns:
            EnhancedMetadata object with combined information
        """
        # Start with default values
        title = os.path.basename(basic_metadata.file_path)
        
        # Current date for creation if not available
        now = datetime.datetime.now(pytz.UTC).isoformat()
        
        enhanced = EnhancedMetadata(
            title=title,
            creation_date=now,
            file_format=basic_metadata.file_type,
            file_size=basic_metadata.file_size,
            feature_count=basic_metadata.feature_count,
            coordinate_system=basic_metadata.crs,
            geometry_type=basic_metadata.geometry_types[0] if basic_metadata.geometry_types else None
        )
        
        # Set bbox if available
        if basic_metadata.bounds:
            west, south, east, north = basic_metadata.bounds
            enhanced.bbox_west = west
            enhanced.bbox_east = east
            enhanced.bbox_north = north
            enhanced.bbox_south = south
        
        # Add attribute information
        if basic_metadata.attribute_schema:
            enhanced.attribute_list = list(basic_metadata.attribute_schema.keys())
        
        # Merge with existing metadata if available
        if existing_metadata:
            # Map existing metadata fields to enhanced metadata
            for field in [
                'title', 'abstract', 'purpose', 'creation_date', 'publication_date', 
                'revision_date', 'contact_organization', 'contact_person', 'contact_email', 
                'lineage', 'positional_accuracy', 'attribute_accuracy', 'completeness', 
                'distribution_format', 'online_resource', 'keywords'
            ]:
                if field in existing_metadata and existing_metadata[field]:
                    setattr(enhanced, field, existing_metadata[field])
            
            # Handle bounding box fields
            for direction in ['west', 'east', 'north', 'south']:
                bbox_key = f'bbox_{direction}'
                if bbox_key in existing_metadata and existing_metadata[bbox_key]:
                    setattr(enhanced, bbox_key, existing_metadata[bbox_key])
        
        return enhanced
    
    def export_to_fgdc(self, metadata: EnhancedMetadata, output_path: str) -> bool:
        """
        Export enhanced metadata to FGDC standard XML.
        
        Args:
            metadata: EnhancedMetadata object
            output_path: Path to save the XML file
            
        Returns:
            True if export successful, False otherwise
        """
        try:
            # Create root element
            root = ET.Element("metadata")
            
            # Identification information
            idinfo = ET.SubElement(root, "idinfo")
            
            # Citation
            citation = ET.SubElement(idinfo, "citation")
            citeinfo = ET.SubElement(citation, "citeinfo")
            
            ET.SubElement(citeinfo, "title").text = metadata.title
            
            if metadata.publication_date:
                ET.SubElement(citeinfo, "pubdate").text = metadata.publication_date
            
            # Description
            descript = ET.SubElement(idinfo, "descript")
            if metadata.abstract:
                ET.SubElement(descript, "abstract").text = metadata.abstract
            if metadata.purpose:
                ET.SubElement(descript, "purpose").text = metadata.purpose
            
            # Time period
            timeinfo = ET.SubElement(idinfo, "timeinfo")
            sngdate = ET.SubElement(timeinfo, "sngdate")
            if metadata.creation_date:
                ET.SubElement(sngdate, "caldate").text = metadata.creation_date.split('T')[0] if 'T' in metadata.creation_date else metadata.creation_date
            
            # Keywords
            if metadata.keywords:
                keywords = ET.SubElement(idinfo, "keywords")
                theme = ET.SubElement(keywords, "theme")
                for keyword in metadata.keywords:
                    ET.SubElement(theme, "themekey").text = keyword
            
            # Bounding coordinates
            if all(getattr(metadata, f'bbox_{direction}') is not None for direction in ['west', 'east', 'north', 'south']):
                spdom = ET.SubElement(idinfo, "spdom")
                bounding = ET.SubElement(spdom, "bounding")
                ET.SubElement(bounding, "westbc").text = str(metadata.bbox_west)
                ET.SubElement(bounding, "eastbc").text = str(metadata.bbox_east)
                ET.SubElement(bounding, "northbc").text = str(metadata.bbox_north)
                ET.SubElement(bounding, "southbc").text = str(metadata.bbox_south)
            
            # Contact information
            if metadata.contact_organization or metadata.contact_person:
                contact = ET.SubElement(idinfo, "ptcontac")
                cntinfo = ET.SubElement(contact, "cntinfo")
                
                if metadata.contact_organization:
                    ET.SubElement(cntinfo, "cntorg").text = metadata.contact_organization
                
                if metadata.contact_person:
                    cntperp = ET.SubElement(cntinfo, "cntperp")
                    ET.SubElement(cntperp, "cntper").text = metadata.contact_person
                
                if metadata.contact_email:
                    ET.SubElement(cntinfo, "cntemail").text = metadata.contact_email
            
            # Data quality
            dataqual = ET.SubElement(root, "dataqual")
            
            if metadata.lineage:
                lineage = ET.SubElement(dataqual, "lineage")
                ET.SubElement(lineage, "procstep").text = metadata.lineage
            
            if metadata.positional_accuracy:
                posaccr = ET.SubElement(dataqual, "posaccr")
                ET.SubElement(posaccr, "horizpa").text = metadata.positional_accuracy
            
            if metadata.attribute_accuracy:
                attraccr = ET.SubElement(dataqual, "attraccr")
                ET.SubElement(attraccr, "attracc").text = metadata.attribute_accuracy
            
            if metadata.completeness:
                complete = ET.SubElement(dataqual, "complete")
                ET.SubElement(complete, "completeinfo").text = metadata.completeness
            
            # Format XML for pretty printing
            xml_string = ET.tostring(root, encoding='utf-8')
            dom = minidom.parseString(xml_string)
            pretty_xml = dom.toprettyxml(indent="  ")
            
            # Write to file
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(pretty_xml)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to export FGDC metadata: {str(e)}")
            return False
    
    def export_to_iso(self, metadata: EnhancedMetadata, output_path: str) -> bool:
        """
        Export enhanced metadata to ISO 19115 standard XML.
        
        Args:
            metadata: EnhancedMetadata object
            output_path: Path to save the XML file
            
        Returns:
            True if export successful, False otherwise
        """
        try:
            # Create root element with namespaces
            root = ET.Element("MD_Metadata", {
                "xmlns": "http://www.isotc211.org/2005/gmd",
                "xmlns:gco": "http://www.isotc211.org/2005/gco",
                "xmlns:gts": "http://www.isotc211.org/2005/gts",
                "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance"
            })
            
            # File identifier
            fileId = ET.SubElement(root, "fileIdentifier")
            ET.SubElement(fileId, "{http://www.isotc211.org/2005/gco}CharacterString").text = os.path.basename(output_path)
            
            # Language
            language = ET.SubElement(root, "language")
            ET.SubElement(language, "{http://www.isotc211.org/2005/gco}CharacterString").text = "eng"
            
            # Hierarchy level (dataset)
            hierarchyLevel = ET.SubElement(root, "hierarchyLevel")
            ET.SubElement(hierarchyLevel, "{http://www.isotc211.org/2005/gco}CharacterString").text = "dataset"
            
            # Contact information
            if metadata.contact_organization or metadata.contact_person:
                contact = ET.SubElement(root, "contact")
                respParty = ET.SubElement(contact, "CI_ResponsibleParty")
                
                if metadata.contact_person:
                    indName = ET.SubElement(respParty, "individualName")
                    ET.SubElement(indName, "{http://www.isotc211.org/2005/gco}CharacterString").text = metadata.contact_person
                
                if metadata.contact_organization:
                    orgName = ET.SubElement(respParty, "organisationName")
                    ET.SubElement(orgName, "{http://www.isotc211.org/2005/gco}CharacterString").text = metadata.contact_organization
                
                if metadata.contact_email:
                    contactInfo = ET.SubElement(respParty, "contactInfo")
                    address = ET.SubElement(contactInfo, "CI_Contact")
                    addressEl = ET.SubElement(address, "address")
                    addressDetails = ET.SubElement(addressEl, "CI_Address")
                    email = ET.SubElement(addressDetails, "electronicMailAddress")
                    ET.SubElement(email, "{http://www.isotc211.org/2005/gco}CharacterString").text = metadata.contact_email
                
                # Set role (originator)
                role = ET.SubElement(respParty, "role")
                roleCode = ET.SubElement(role, "CI_RoleCode", {"codeList": "http://www.isotc211.org/2005/resources/Codelist/gmxCodelists.xml#CI_RoleCode", "codeListValue": "originator"})
                roleCode.text = "originator"
            
            # Date stamp
            dateStamp = ET.SubElement(root, "dateStamp")
            if metadata.creation_date:
                dateTime = ET.SubElement(dateStamp, "{http://www.isotc211.org/2005/gco}DateTime")
                dateTime.text = metadata.creation_date
            else:
                # Current date
                now = datetime.datetime.now(pytz.UTC).isoformat()
                dateTime = ET.SubElement(dateStamp, "{http://www.isotc211.org/2005/gco}DateTime")
                dateTime.text = now
            
            # Standard name
            metadataStandardName = ET.SubElement(root, "metadataStandardName")
            ET.SubElement(metadataStandardName, "{http://www.isotc211.org/2005/gco}CharacterString").text = "ISO 19115:2003/19139"
            
            # Standard version
            metadataStandardVersion = ET.SubElement(root, "metadataStandardVersion")
            ET.SubElement(metadataStandardVersion, "{http://www.isotc211.org/2005/gco}CharacterString").text = "1.0"
            
            # Identification info
            identInfo = ET.SubElement(root, "identificationInfo")
            dataIdent = ET.SubElement(identInfo, "MD_DataIdentification")
            
            # Citation
            citation = ET.SubElement(dataIdent, "citation")
            ciCitation = ET.SubElement(citation, "CI_Citation")
            
            # Title
            title = ET.SubElement(ciCitation, "title")
            ET.SubElement(title, "{http://www.isotc211.org/2005/gco}CharacterString").text = metadata.title
            
            # Date
            if metadata.publication_date or metadata.creation_date:
                date = ET.SubElement(ciCitation, "date")
                ciDate = ET.SubElement(date, "CI_Date")
                dateEl = ET.SubElement(ciDate, "date")
                use_date = metadata.publication_date or metadata.creation_date
                ET.SubElement(dateEl, "{http://www.isotc211.org/2005/gco}DateTime").text = use_date
                
                dateType = ET.SubElement(ciDate, "dateType")
                dateTypeCode = ET.SubElement(dateType, "CI_DateTypeCode", {"codeList": "http://www.isotc211.org/2005/resources/Codelist/gmxCodelists.xml#CI_DateTypeCode", "codeListValue": "publication"})
                dateTypeCode.text = "publication"
            
            # Abstract
            if metadata.abstract:
                abstract = ET.SubElement(dataIdent, "abstract")
                ET.SubElement(abstract, "{http://www.isotc211.org/2005/gco}CharacterString").text = metadata.abstract
            
            # Purpose
            if metadata.purpose:
                purpose = ET.SubElement(dataIdent, "purpose")
                ET.SubElement(purpose, "{http://www.isotc211.org/2005/gco}CharacterString").text = metadata.purpose
            
            # Keywords
            if metadata.keywords:
                descriptiveKeywords = ET.SubElement(dataIdent, "descriptiveKeywords")
                mdKeywords = ET.SubElement(descriptiveKeywords, "MD_Keywords")
                
                for keyword in metadata.keywords:
                    keywordEl = ET.SubElement(mdKeywords, "keyword")
                    ET.SubElement(keywordEl, "{http://www.isotc211.org/2005/gco}CharacterString").text = keyword
            
            # Extent information (bounding box)
            if all(getattr(metadata, f'bbox_{direction}') is not None for direction in ['west', 'east', 'north', 'south']):
                extent = ET.SubElement(dataIdent, "extent")
                exExtent = ET.SubElement(extent, "EX_Extent")
                geographicElement = ET.SubElement(exExtent, "geographicElement")
                geoBbox = ET.SubElement(geographicElement, "EX_GeographicBoundingBox")
                
                # West bound
                westLong = ET.SubElement(geoBbox, "westBoundLongitude")
                ET.SubElement(westLong, "{http://www.isotc211.org/2005/gco}Decimal").text = str(metadata.bbox_west)
                
                # East bound
                eastLong = ET.SubElement(geoBbox, "eastBoundLongitude")
                ET.SubElement(eastLong, "{http://www.isotc211.org/2005/gco}Decimal").text = str(metadata.bbox_east)
                
                # South bound
                southLat = ET.SubElement(geoBbox, "southBoundLatitude")
                ET.SubElement(southLat, "{http://www.isotc211.org/2005/gco}Decimal").text = str(metadata.bbox_south)
                
                # North bound
                northLat = ET.SubElement(geoBbox, "northBoundLatitude")
                ET.SubElement(northLat, "{http://www.isotc211.org/2005/gco}Decimal").text = str(metadata.bbox_north)
            
            # Data quality information
            if any(getattr(metadata, field) for field in ['lineage', 'positional_accuracy', 'attribute_accuracy', 'completeness']):
                dataQualInfo = ET.SubElement(root, "dataQualityInfo")
                dataQual = ET.SubElement(dataQualInfo, "DQ_DataQuality")
                
                # Scope
                scope = ET.SubElement(dataQual, "scope")
                dqScope = ET.SubElement(scope, "DQ_Scope")
                level = ET.SubElement(dqScope, "level")
                scopeCode = ET.SubElement(level, "MD_ScopeCode", {"codeList": "http://www.isotc211.org/2005/resources/Codelist/gmxCodelists.xml#MD_ScopeCode", "codeListValue": "dataset"})
                scopeCode.text = "dataset"
                
                # Lineage
                if metadata.lineage:
                    lineage = ET.SubElement(dataQual, "lineage")
                    liStatement = ET.SubElement(lineage, "LI_Lineage")
                    statement = ET.SubElement(liStatement, "statement")
                    ET.SubElement(statement, "{http://www.isotc211.org/2005/gco}CharacterString").text = metadata.lineage
            
            # Distribution information
            if metadata.distribution_format or metadata.online_resource:
                distInfo = ET.SubElement(root, "distributionInfo")
                mdDist = ET.SubElement(distInfo, "MD_Distribution")
                
                # Format
                if metadata.distribution_format:
                    distFormat = ET.SubElement(mdDist, "distributionFormat")
                    mdFormat = ET.SubElement(distFormat, "MD_Format")
                    name = ET.SubElement(mdFormat, "name")
                    ET.SubElement(name, "{http://www.isotc211.org/2005/gco}CharacterString").text = metadata.distribution_format
                
                # Online resource
                if metadata.online_resource:
                    transferOptions = ET.SubElement(mdDist, "transferOptions")
                    mdDigTrans = ET.SubElement(transferOptions, "MD_DigitalTransferOptions")
                    onLine = ET.SubElement(mdDigTrans, "onLine")
                    ciOnlineRes = ET.SubElement(onLine, "CI_OnlineResource")
                    linkage = ET.SubElement(ciOnlineRes, "linkage")
                    url = ET.SubElement(linkage, "{http://www.isotc211.org/2005/gco}CharacterString")
                    url.text = metadata.online_resource
            
            # Format XML for pretty printing
            xml_string = ET.tostring(root, encoding='utf-8')
            dom = minidom.parseString(xml_string)
            pretty_xml = dom.toprettyxml(indent="  ")
            
            # Write to file
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(pretty_xml)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to export ISO metadata: {str(e)}")
            return False
        
    def _is_valid_date(self, date_string: str) -> bool:
            """
            Validate if a string is in a valid date format.
            Accepts ISO format (YYYY-MM-DD) or (YYYY-MM-DDThh:mm:ss) formats.
            
            Args:
                date_string: Date string to validate
                
            Returns:
                True if valid, False otherwise
            """
            # Check for ISO format YYYY-MM-DD or YYYY-MM-DDThh:mm:ss
            iso_pattern = r'^\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}:\d{2}(.\d+)?(Z|[+-]\d{2}:\d{2})?)?$'
            if re.match(iso_pattern, date_string):
                return True
            
            # Check for YYYYMMDD format
            basic_pattern = r'^\d{8}$'
            if re.match(basic_pattern, date_string):
                return True
            
            return False
    
    def validate_metadata(self, metadata: EnhancedMetadata) -> Tuple[bool, List[str]]:
        """
        Validate metadata for completeness and correctness.
        
        Args:
            metadata: EnhancedMetadata object to validate
            
        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []
        
        # Check required fields
        if not metadata.title or metadata.title.strip() == "":
            issues.append("Title is required")
        
        # Check dates format
        for date_field in ['creation_date', 'publication_date', 'revision_date']:
            date_value = getattr(metadata, date_field)
            if date_value and not self._is_valid_date(date_value):
                issues.append(f"{date_field.replace('_', ' ').title()} has invalid format")
        
        # Check bbox values
        if any(getattr(metadata, f"bbox_{d}") is not None for d in ['west', 'east', 'north', 'south']):
            # If any bbox value is present, all should be present
            if not all(getattr(metadata, f"bbox_{d}") is not None for d in ['west', 'east', 'north', 'south']):
                issues.append("Incomplete bounding box coordinates")
            else:
                # Check that west < east and south < north
                if metadata.bbox_west > metadata.bbox_east:
                    issues.append("West longitude must be less than East longitude")
                    
                if metadata.bbox_south > metadata.bbox_north:
                    issues.append("South latitude must be less than North latitude")
                
                # Check coordinate ranges
                if not (-180 <= metadata.bbox_west <= 180):
                    issues.append("West longitude must be between -180 and 180")
                if not (-180 <= metadata.bbox_east <= 180):
                    issues.append("East longitude must be between -180 and 180")
                if not (-90 <= metadata.bbox_south <= 90):
                    issues.append("South latitude must be between -90 and 90")
                if not (-90 <= metadata.bbox_north <= 90):
                    issues.append("North latitude must be between -90 and 90")
        
        # Check contact information
        if metadata.contact_email and not self._is_valid_email(metadata.contact_email):
            issues.append("Invalid contact email format")
        
        # Check for critical missing information
        if not metadata.abstract:
            issues.append("Abstract is recommended but missing")
        
        if not metadata.keywords or len(metadata.keywords) == 0:
            issues.append("Keywords are recommended but missing")
    
        # Return validation result
        return len(issues) == 0, issues

    def _is_valid_email(self, email: str) -> bool:
        """
        Validate email format.
        
        Args:
            email: Email string to validate
            
        Returns:
            True if valid, False otherwise
        """
        email_pattern = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
        return re.match(email_pattern, email) is not None
    
    def auto_complete_metadata(self, metadata: EnhancedMetadata) -> EnhancedMetadata:
        """
        Attempt to automatically complete missing metadata fields.
        
        Args:
            metadata: EnhancedMetadata object with some missing fields
            
        Returns:
            EnhancedMetadata object with more complete information
        """
        # Create a copy to avoid modifying the original
        enhanced = EnhancedMetadata(**asdict(metadata))
        
        # Set creation date if missing
        if not enhanced.creation_date:
            enhanced.creation_date = datetime.datetime.now(pytz.UTC).isoformat()
        
        # Generate abstract if missing
        if not enhanced.abstract:
            abstract_parts = []
            if enhanced.title:
                abstract_parts.append(f"This dataset contains {enhanced.title}.")
            
            if enhanced.geometry_type:
                abstract_parts.append(f"It consists of {enhanced.geometry_type} features.")
            
            if enhanced.feature_count:
                abstract_parts.append(f"The dataset contains {enhanced.feature_count} features.")
            
            if enhanced.attribute_list:
                abstract_parts.append(f"Attributes include: {', '.join(enhanced.attribute_list[:5])}" + 
                                (f" and {len(enhanced.attribute_list) - 5} more." if len(enhanced.attribute_list) > 5 else "."))
            
            if all(getattr(enhanced, f'bbox_{d}') is not None for d in ['west', 'east', 'north', 'south']):
                abstract_parts.append(f"Geographic extent: {enhanced.bbox_west:.2f}W to {enhanced.bbox_east:.2f}E, " +
                                f"{enhanced.bbox_south:.2f}S to {enhanced.bbox_north:.2f}N.")
            
            enhanced.abstract = " ".join(abstract_parts) if abstract_parts else None
        
        # Generate keywords if missing
        if not enhanced.keywords or len(enhanced.keywords) == 0:
            keywords = set()
            
            # Add geometry type
            if enhanced.geometry_type:
                keywords.add(enhanced.geometry_type.lower())
            
            # Add terms from title
            if enhanced.title:
                # Split by non-alphanumeric characters and filter out short words
                title_words = [word.lower() for word in re.split(r'[^a-zA-Z0-9]', enhanced.title) if len(word) > 3]
                keywords.update(title_words)
            
            # Add coordinate system info
            if enhanced.coordinate_system:
                # Extract potential EPSG code or other identifier
                if "EPSG" in enhanced.coordinate_system:
                    keywords.add("EPSG")
                    epsg_match = re.search(r'EPSG:(\d+)', enhanced.coordinate_system)
                    if epsg_match:
                        keywords.add(f"EPSG:{epsg_match.group(1)}")
            
            enhanced.keywords = list(keywords) if keywords else None
        
        return enhanced

    def standardize_crs(self, crs_string: str) -> str:
        """
        Attempt to standardize coordinate reference system representation.
        
        Args:
            crs_string: String representation of coordinate system
            
        Returns:
            Standardized CRS string (preferably as EPSG code if recognized)
        """
        # Check for EPSG code in various formats
        epsg_patterns = [
            r'EPSG:(\d+)',          # EPSG:4326
            r'EPSG[\s_-](\d+)',     # EPSG 4326, EPSG_4326
            r'epsg:(\d+)',          # epsg:4326
            r'SRID=(\d+)',          # SRID=4326
            r'AUTHORITY\["EPSG","(\d+)"\]'  # AUTHORITY["EPSG","4326"]
        ]
        
        for pattern in epsg_patterns:
            match = re.search(pattern, crs_string)
            if match:
                return f"EPSG:{match.group(1)}"
        
        # Some common WKT CRS to EPSG mappings
        wkt_to_epsg = {
            'GEOGCS["WGS 84"': "EPSG:4326",
            'PROJCS["WGS 84 / UTM zone': None,  # Needs more parsing for zone
            'PROJCS["NAD83': None  # Would need more specifics
        }
        
        for wkt_start, epsg in wkt_to_epsg.items():
            if crs_string.startswith(wkt_start):
                if epsg:
                    return epsg
                # For UTM zones, try to extract the zone number
                if "UTM zone" in crs_string:
                    utm_match = re.search(r'UTM zone (\d+)', crs_string)
                    if utm_match:
                        zone = int(utm_match.group(1))
                        # Northern hemisphere (default in many systems)
                        if "Southern Hemisphere" in crs_string or ", south" in crs_string.lower():
                            return f"EPSG:{32700 + zone}"  # Southern hemisphere UTM zones
                        else:
                            return f"EPSG:{32600 + zone}"  # Northern hemisphere UTM zones
        
        # If we can't standardize, return the original
        return crs_string