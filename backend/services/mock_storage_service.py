#!/usr/bin/env python3
"""
Mock Storage Service for DeliverMe
Used when Google Cloud Storage credentials are not available
"""

import os
import uuid
from datetime import datetime, timedelta
from typing import Tuple
import logging

logger = logging.getLogger(__name__)

class MockStorageService:
    """Mock service for handling storage operations when GCS is not available"""
    
    def __init__(self):
        """Initialize the mock storage service"""
        self.bucket_name = "mock-bucket"
        logger.warning("Using mock storage service - files will not be actually uploaded to GCS")
    
    def make_object_key(self, driver_id: int, doc_type: str, filename: str) -> str:
        """
        Generate a standardized object key for driver documents
        
        Args:
            driver_id: Driver's unique identifier
            doc_type: Type of document ('driver_license', 'id_card', or 'insurance')
            filename: Original filename
            
        Returns:
            str: Object key in format drivers/{driver_id}/{doc_type}/{filename}
        """
        # Validate document type
        valid_doc_types = ['driver_license', 'id_card', 'insurance']
        if doc_type not in valid_doc_types:
            raise ValueError(f"Invalid document type. Must be one of: {valid_doc_types}")
        
        # Extract file extension
        file_ext = os.path.splitext(filename)[1].lower()
        
        # Generate unique filename to avoid conflicts
        unique_id = str(uuid.uuid4())[:8]
        safe_filename = f"{doc_type}_{unique_id}{file_ext}"
        
        # Return standardized object key
        return f"drivers/{driver_id}/{doc_type}/{safe_filename}"
    
    def make_item_photo_object_key(self, delivery_id: int, filename: str) -> str:
        """
        Generate a standardized object key for delivery item photos
        
        Args:
            delivery_id: Delivery's unique identifier
            filename: Original filename
            
        Returns:
            str: Object key in format deliveries/{delivery_id}/item_photos/{filename}
        """
        # Extract file extension
        file_ext = os.path.splitext(filename)[1].lower()
        
        # Generate unique filename to avoid conflicts
        unique_id = str(uuid.uuid4())[:8]
        safe_filename = f"item_photo_{unique_id}{file_ext}"
        
        # Return standardized object key
        return f"deliveries/{delivery_id}/item_photos/{safe_filename}"
    
    def get_upload_url(self, driver_id: int, doc_type: str, filename: str, content_type: str) -> Tuple[str, str]:
        """
        Get a mock upload URL for uploading a driver document
        
        Args:
            driver_id: Driver's unique identifier
            doc_type: Type of document ('driver_license', 'id_card', or 'insurance')
            filename: Original filename
            content_type: MIME type of the file
            
        Returns:
            Tuple[str, str]: (mock_upload_url, object_key)
        """
        try:
            # Generate object key
            object_key = self.make_object_key(driver_id, doc_type, filename)
            
            # Create mock upload URL (this would be a real signed URL in production)
            mock_url = f"https://mock-storage.googleapis.com/{self.bucket_name}/{object_key}?mock=true"
            
            logger.warning(f"Generated MOCK upload URL for {object_key} - file will not be actually uploaded")
            return mock_url, object_key
            
        except Exception as e:
            logger.error(f"Failed to get mock upload URL for driver {driver_id}: {str(e)}")
            raise
    
    def get_item_photo_upload_url(self, delivery_id: int, filename: str, content_type: str) -> Tuple[str, str]:
        """
        Get a mock upload URL for uploading a delivery item photo
        
        Args:
            delivery_id: Delivery's unique identifier
            filename: Original filename
            content_type: MIME type of the file
            
        Returns:
            Tuple[str, str]: (mock_upload_url, object_key)
        """
        try:
            # Generate object key
            object_key = self.make_item_photo_object_key(delivery_id, filename)
            
            # Create mock upload URL (this would be a real signed URL in production)
            mock_url = f"https://mock-storage.googleapis.com/{self.bucket_name}/{object_key}?mock=true"
            
            logger.warning(f"Generated MOCK upload URL for item photo {object_key} - file will not be actually uploaded")
            return mock_url, object_key
            
        except Exception as e:
            logger.error(f"Failed to get mock upload URL for delivery {delivery_id}: {str(e)}")
            raise
    
    def get_download_url(self, object_key: str, expires_seconds: int = 300) -> str:
        """
        Get a mock download URL for downloading a driver document
        
        Args:
            object_key: Object key (path) in the bucket
            expires_seconds: URL expiration time in seconds (default: 5 minutes)
            
        Returns:
            str: Mock URL for downloading the document
        """
        try:
            # Create mock download URL
            mock_url = f"https://mock-storage.googleapis.com/{self.bucket_name}/{object_key}?mock=true&expires={expires_seconds}"
            
            logger.warning(f"Generated MOCK download URL for {object_key} - file does not exist")
            return mock_url
            
        except Exception as e:
            logger.error(f"Failed to get mock download URL for {object_key}: {str(e)}")
            raise
    
    def object_exists(self, bucket: str, key: str) -> bool:
        """
        Mock check if an object exists in storage
        
        Args:
            bucket: Bucket name
            key: Object key (path) in the bucket
            
        Returns:
            bool: Always returns True for mock service
        """
        logger.warning(f"MOCK: Assuming object {key} exists in bucket {bucket}")
        return True
    
    def cleanup_old_document(self, driver_id: int, doc_type: str, old_object_key: str) -> bool:
        """
        Mock cleanup of old document
        
        Args:
            driver_id: Driver's unique identifier
            doc_type: Type of document
            old_object_key: Object key of the old document to delete
            
        Returns:
            bool: Always returns True for mock service
        """
        if not old_object_key:
            return True
        
        logger.warning(f"MOCK: Would delete old document {old_object_key}")
        return True
    
    def cleanup_old_item_photo(self, delivery_id: int, old_object_key: str) -> bool:
        """
        Mock cleanup of old item photo
        
        Args:
            delivery_id: Delivery's unique identifier
            old_object_key: Object key of the old photo to delete
            
        Returns:
            bool: Always returns True for mock service
        """
        if not old_object_key:
            return True
        
        logger.warning(f"MOCK: Would delete old item photo {old_object_key}")
        return True

# Global instance
mock_storage_service = MockStorageService()
