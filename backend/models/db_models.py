from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Table
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import datetime

Base = declarative_base()

# Many-to-many relationship between GIS files and keywords
file_keyword = Table(
    'file_keyword', Base.metadata,
    Column('file_id', Integer, ForeignKey('gis_files.id')),
    Column('keyword_id', Integer, ForeignKey('keywords.id'))
)

class GISFile(Base):
    """Model for GIS files."""
    __tablename__ = 'gis_files'
    
    id = Column(Integer, primary_key=True)
    file_path = Column(String, unique=True, nullable=False)
    file_name = Column(String, nullable=False)
    file_type = Column(String, nullable=False)
    file_size = Column(Integer)  # Size in bytes
    
    # Metadata fields
    title = Column(String)
    abstract = Column(String)
    creation_date = Column(DateTime)
    modification_date = Column(DateTime)
    
    # Spatial fields
    coordinate_system = Column(String)
    bbox_west = Column(Float)
    bbox_east = Column(Float)
    bbox_north = Column(Float)
    bbox_south = Column(Float)
    
    # Classification and organization
    category = Column(String)
    subcategory = Column(String)
    
    # Relationships
    keywords = relationship("Keyword", secondary=file_keyword, back_populates="files")
    attributes = relationship("FileAttribute", back_populates="file")
    
    date_indexed = Column(DateTime, default=datetime.datetime.utcnow)
    
    def __repr__(self):
        return f"<GISFile(id={self.id}, file_name='{self.file_name}')>"

class Keyword(Base):
    """Model for keywords/tags."""
    __tablename__ = 'keywords'
    
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    
    # Relationships
    files = relationship("GISFile", secondary=file_keyword, back_populates="keywords")
    
    def __repr__(self):
        return f"<Keyword(id={self.id}, name='{self.name}')>"

class FileAttribute(Base):
    """Model for GIS file attributes."""
    __tablename__ = 'file_attributes'
    
    id = Column(Integer, primary_key=True)
    file_id = Column(Integer, ForeignKey('gis_files.id'))
    name = Column(String, nullable=False)
    data_type = Column(String)
    description = Column(String)
    
    # Relationships
    file = relationship("GISFile", back_populates="attributes")
    
    def __repr__(self):
        return f"<FileAttribute(id={self.id}, name='{self.name}')>"