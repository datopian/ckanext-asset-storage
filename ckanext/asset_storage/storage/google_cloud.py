from datetime import timedelta
from typing import Optional

from google.cloud import storage
from google.oauth2 import service_account

from ckanext.asset_storage.storage import DownloadTarget, StorageBackend, exc


class GoogleCloudStorage(StorageBackend):
    """A storage backend for storing assets in Google Cloud Storage

    See https://cloud.google.com/storage
    """
    def __init__(self, project_name, bucket_name, account_key_file, public_read=True, path_prefix=None,
                 signed_url_lifetime=3600):
        # type: (str, str, str, bool, Optional[str], Optional[int]) -> GoogleCloudStorage
        """Constructor for Google Cloud Storage backend

        Args:
            project_name: Google Cloud project name
            bucket_name: Google Cloud Storage bucket name
            account_key_file: Path to the Google Cloud credentials JSON file
            public_read: Whether to allow public read access to uploaded assets. Setting to False means the asset can
                only be accessed after a request to this code to generate a signed URL. This will have some performance
                impact.
            path_prefix: A prefix to prepend to all stored assets in the bucket
            signed_url_lifetime: When public access is not allowed, this sets the max lifetime of signed URLs.
        """
        self._bucket_name = bucket_name
        self._path_prefix = path_prefix
        self._public_read = public_read
        self._signed_url_lifetime = signed_url_lifetime
        self._credentials = self._load_credentials(account_key_file)
        self._client = storage.Client(project=project_name, credentials=self._credentials)

    def get_storage_uri(self, name, prefix=None):
        """Get the URL of the file in storage
        """
        if self._public_read:
            bucket = self._client.bucket(self._bucket_name)
            blob = bucket.blob(self._get_blob_path(name, prefix))
            return blob.public_url
        elif prefix:
            return '{}/{}'.format(prefix, name)
        else:
            return name

    def upload(self, stream, name, prefix=None, mimetype=None):
        """Save the file in local storage
        """
        bucket = self._client.bucket(self._bucket_name)
        blob = bucket.blob(self._get_blob_path(name, prefix))
        if self._public_read:
            blob.acl.all().grant_read()
        else:
            blob.acl.all().revoke_read()

        blob.upload_from_file(stream, content_type=mimetype)
        return stream.tell()

    def download(self, uri):
        """Provide the direct URL to download the file from storage
        """
        bucket = self._client.bucket(self._bucket_name)
        blob = bucket.get_blob(self._get_blob_path(uri))
        if blob is None:
            raise exc.ObjectNotFound('The requested file was not found')

        # If we got here, we assume blob is private and return a signed URL
        signed_url = blob.generate_signed_url(expiration=timedelta(seconds=self._signed_url_lifetime),
                                              method='GET',
                                              version='v4',
                                              credentials=self._credentials)
        return DownloadTarget.redirect(signed_url)

    def delete(self, uri):
        bucket = self._client.bucket(self._bucket_name)
        blob = bucket.get_blob(self._get_blob_path(uri))
        if blob is None:
            return False
        blob.delete()
        return True

    def _get_blob_path(self, name, prefix=None):
        # type: (str, Optional[str]) -> str
        path = [seg for seg in (self._path_prefix, prefix, name) if seg]
        return '/'.join(path)

    @staticmethod
    def _load_credentials(account_key_file):
        # type: (str) -> service_account.Credentials
        """Load Google Cloud credentials from JSON file
        """
        return service_account.Credentials.from_service_account_file(account_key_file)
