#!/usr/bin/env python3
"""
Firebase Storage Service for DeliverMe
Handles document uploads using Firebase Storage
"""

import os
import uuid
from datetime import timedelta
from typing import Optional, Tuple
import firebase_admin
from firebase_admin import storage as firebase_storage
import logging

logger = logging.getLogger(__name__)

class StorageService:
    """Service for handling Firebase Storage operations"""
    
    def __init__(self):
        """Initialize the storage service with Firebase Storage"""
        try:
            # Ensure Firebase Admin SDK is initialized
            from services.firestore_client import _init_firebase_app
            _init_firebase_app()
            
            # Use bucket name from environment variable (must match Firebase Console)
            # Firebase projects created after ~2024 use firebasestorage.app domain
            self.bucket_name = (
                os.getenv("FIREBASE_STORAGE_BUCKET")
                or "delivermee-12c26.firebasestorage.app"
            )
            
            # Get Firebase Storage bucket
            try:
                self.bucket = firebase_storage.bucket(self.bucket_name)
                logger.info(f"Firebase Storage service initialized with bucket: {self.bucket_name}")
            except Exception as e:
                logger.error(f"Failed to get Firebase Storage bucket: {e}")
                raise
            
        except Exception as e:
            logger.error(f"Failed to initialize Firebase Storage service: {str(e)}")
            raise
    
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
    
    def create_signed_put(self, bucket: str, key: str, content_type: str, expires_seconds: int = 600) -> str:
        """
        Create a signed URL for uploading a file to Firebase Storage
        
        Args:
            bucket: Firebase Storage bucket name
            key: Object key (path) in the bucket
            content_type: MIME type of the file
            expires_seconds: URL expiration time in seconds (default: 10 minutes)
            
        Returns:
            str: Signed URL for PUT operation
        """
        try:
            # Get blob reference
            blob = self.bucket.blob(key)
            
            # Get credentials from Firebase Admin SDK and refresh them
            import firebase_admin
            import google.auth.transport.requests
            
            app = firebase_admin.get_app()
            cred = app.credential.get_credential()
            
            # Refresh credentials to ensure they are valid for signing
            auth_request = google.auth.transport.requests.Request()
            cred.refresh(auth_request)
            
            # Generate signed URL for PUT operation
            url = blob.generate_signed_url(
                version="v4",
                expiration=timedelta(seconds=expires_seconds),
                method="PUT",
                content_type=content_type,
                credentials=cred
            )
            
            logger.info(f"Generated signed PUT URL for {key} (expires in {expires_seconds}s)")
            return url
            
        except Exception as e:
            logger.error(f"Failed to create signed PUT URL for {key}: {str(e)}")
            raise

    
    def create_signed_get(self, bucket: str, key: str, expires_seconds: int = 300) -> str:
        """
        Create a signed URL for downloading a file from Firebase Storage
        
        Args:
            bucket: Firebase Storage bucket name
            key: Object key (path) in the bucket
            expires_seconds: URL expiration time in seconds (default: 5 minutes)
            
        Returns:
            str: Signed URL for GET operation
        """
        try:
            # Get blob reference
            blob = self.bucket.blob(key)
            
            # Check if blob exists
            if not blob.exists():
                raise FileNotFoundError(f"Object {key} not found in bucket {bucket}")
            
            # Generate signed URL for GET operation
            url = blob.generate_signed_url(
                version="v4",
                expiration=timedelta(seconds=expires_seconds),
                method="GET"
            )
            
            logger.info(f"Generated signed GET URL for {key} (expires in {expires_seconds}s)")
            return url
            
        except FileNotFoundError as e:
            logger.warning(f"Object not found: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Failed to create signed GET URL for {key}: {str(e)}")
            raise
    
    def delete_object(self, bucket: str, key: str) -> bool:
        """
        Delete an object from Firebase Storage
        
        Args:
            bucket: Firebase Storage bucket name
            key: Object key (path) in the bucket
            
        Returns:
            bool: True if deleted successfully, False otherwise
        """
        try:
            blob = self.bucket.blob(key)
            
            if blob.exists():
                blob.delete()
                logger.info(f"Deleted object {key} from bucket {bucket}")
                return True
            else:
                logger.warning(f"Object {key} not found in bucket {bucket}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to delete object {key}: {str(e)}")
            return False
    
    def object_exists(self, bucket: str, key: str) -> bool:
        """
        Check if an object exists in Firebase Storage
        
        Args:
            bucket: Firebase Storage bucket name
            key: Object key (path) in the bucket
            
        Returns:
            bool: True if object exists, False otherwise
        """
        try:
            blob = self.bucket.blob(key)
            return blob.exists()
        except Exception as e:
            logger.error(f"Error checking if object exists: {str(e)}")
            return False
    
    def get_upload_url(self, driver_id: int, doc_type: str, filename: str, content_type: str) -> Tuple[str, str]:
        """
        Get a signed URL for uploading a driver document to Firebase Storage
        
        Args:
            driver_id: Driver's unique identifier
            doc_type: Type of document ('driver_license', 'id_card', or 'insurance')
            filename: Original filename
            content_type: MIME type of the file
            
        Returns:
            Tuple[str, str]: (signed_url, object_key)
        """
        try:
            # Generate object key
            object_key = self.make_object_key(driver_id, doc_type, filename)
            
            # Create signed PUT URL
            signed_url = self.create_signed_put(
                bucket=self.bucket_name,
                key=object_key,
                content_type=content_type,
                expires_seconds=600  # 10 minutes
            )
            
            return signed_url, object_key
            
        except Exception as e:
            logger.error(f"Failed to get upload URL for driver {driver_id}: {str(e)}")
            raise
    
    def get_item_photo_upload_url(self, delivery_id: int, filename: str, content_type: str) -> Tuple[str, str]:
        """
        Get a signed URL for uploading a delivery item photo to Firebase Storage
        
        Args:
            delivery_id: Delivery's unique identifier
            filename: Original filename
            content_type: MIME type of the file
            
        Returns:
            Tuple[str, str]: (signed_url, object_key)
        """
        try:
            # Generate object key
            object_key = self.make_item_photo_object_key(delivery_id, filename)
            
            # Create signed PUT URL
            signed_url = self.create_signed_put(
                bucket=self.bucket_name,
                key=object_key,
                content_type=content_type,
                expires_seconds=600  # 10 minutes
            )
            
            return signed_url, object_key
            
        except Exception as e:
            logger.error(f"Failed to get upload URL for delivery {delivery_id}: {str(e)}")
            raise
    
    def get_download_url(self, object_key: str, expires_seconds: int = 300) -> str:
        """
        Get a signed URL for downloading a driver document from Firebase Storage
        
        Args:
            object_key: Object key (path) in the bucket
            expires_seconds: URL expiration time in seconds (default: 5 minutes)
            
        Returns:
            str: Signed URL for downloading the document
        """
        try:
            return self.create_signed_get(
                bucket=self.bucket_name,
                key=object_key,
                expires_seconds=expires_seconds
            )
        except Exception as e:
            logger.error(f"Failed to get download URL for {object_key}: {str(e)}")
            raise
    
    def get_public_url(self, object_key: str) -> str:
        """
        Get a Firebase Storage download URL for an object.
        
        Uses the Firebase Storage REST URL format which respects Storage Rules,
        allowing public read access when rules permit.
        
        Args:
            object_key: Object key (path) in the bucket
            
        Returns:
            str: Firebase Storage download URL
        """
        # URL-encode the object key (replace / with %2F for Firebase URL format)
        import urllib.parse
        encoded_key = urllib.parse.quote(object_key, safe='')
        return f"https://firebasestorage.googleapis.com/v0/b/{self.bucket_name}/o/{encoded_key}?alt=media"
    
    def make_blob_public(self, object_key: str) -> bool:
        """
        Firebase Storage with Uniform Bucket-Level Access (default for Firebase projects)
        does not support per-object ACLs. Instead, access is controlled by Storage Rules.
        The rules are already configured to allow read for authenticated users.
        For unauthenticated (public) read, update storage.rules accordingly.
        
        This method is a no-op — it logs a notice and returns True.
        The item_photo_url returned uses a Firebase download URL (?alt=media)
        which is served through Firebase Storage Rules, not GCS ACLs.
        
        Args:
            object_key: Object key (path) in the bucket
            
        Returns:
            bool: Always True (access controlled via Storage Rules, not ACLs)
        """
        logger.info(
            f"[make_blob_public] Access for '{object_key}' is governed by Firebase Storage Rules "
            f"(Uniform Bucket-Level Access is enabled — per-object ACLs are not supported). "
            f"No action needed — Storage Rules already allow read access."
        )
        return True
    
    def generate_signed_upload_url(self, object_key: str, content_type: str, expiration: int = 900) -> str:
        """Generate signed URL for uploading"""
        try:
            blob = self.bucket.blob(object_key)
            url = blob.generate_signed_url(
                version="v4",
                expiration=timedelta(seconds=expiration),
                method="PUT",
                content_type=content_type
            )
            return url
        except Exception as e:
            logger.error(f"Failed to generate signed upload URL: {e}")
            return None
    
    def cleanup_old_document(self, driver_id: int, doc_type: str, old_object_key: str) -> bool:
        """
        Clean up old document when uploading a new one
        
        Args:
            driver_id: Driver's unique identifier
            doc_type: Type of document ('driver_license', 'id_card', or 'insurance')
            old_object_key: Object key of the old document to delete
            
        Returns:
            bool: True if cleanup successful, False otherwise
        """
        if not old_object_key:
            return True
        
        try:
            # Only delete if it's in the same driver's folder
            if f"drivers/{driver_id}/{doc_type}/" in old_object_key:
                return self.delete_object(self.bucket_name, old_object_key)
            else:
                logger.warning(f"Refusing to delete object outside driver folder: {old_object_key}")
                return False
        except Exception as e:
            logger.error(f"Failed to cleanup old document: {str(e)}")
            return False
    
    def cleanup_old_item_photo(self, delivery_id: int, old_object_key: str) -> bool:
        """
        Clean up old item photo when uploading a new one
        
        Args:
            delivery_id: Delivery's unique identifier
            old_object_key: Object key of the old photo to delete
            
        Returns:
            bool: True if cleanup successful, False otherwise
        """
        if not old_object_key:
            return True
        
        try:
            # Only delete if it's in the same delivery's folder
            if f"deliveries/{delivery_id}/item_photos/" in old_object_key:
                return self.delete_object(self.bucket_name, old_object_key)
            else:
                logger.warning(f"Refusing to delete object outside delivery folder: {old_object_key}")
                return False
        except Exception as e:
            logger.error(f"Failed to cleanup old item photo: {str(e)}")
            return False

# Global instance - will be initialized lazily
storage_service = None

def get_storage_service():
    """Get the storage service instance, initializing it if necessary"""
    global storage_service
    if storage_service is None:
        try:
            logger.info("Initializing storage service...")
            storage_service = StorageService()
            logger.info(f"Storage service initialized successfully with bucket: {storage_service.bucket_name}")
        except Exception as e:
            logger.error(f"Failed to initialize storage service: {str(e)}")
            import traceback
            traceback.print_exc()
            # Don't fall back to mock - raise the error so we know what's wrong
            raise
    return storage_service

# Initialize on import
try:
    logger.info("Attempting to initialize storage service on module import...")
    storage_service = StorageService()
    logger.info(f"Storage service initialized on import with bucket: {storage_service.bucket_name}")
except Exception as e:
    logger.error(f"Failed to initialize storage service on import: {e}")
    logger.error("Storage service will be initialized on first use")
    import traceback
    traceback.print_exc()
    storage_service = None

