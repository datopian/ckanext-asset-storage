from datetime import datetime, timedelta
from typing import Optional

from azure.core.exceptions import ResourceNotFoundError
from azure.storage.blob import ContentSettings  # type: ignore
from azure.storage.blob import BlobClient, BlobSasPermissions, BlobServiceClient, generate_blob_sas
from memoized_property import memoized_property

from ckanext.asset_storage.storage import DownloadTarget, StorageBackend, exc

try:
    from dateutil.tz import UTC
except ImportError:
    from pytz import UTC


class AzureBlobStorage(StorageBackend):
    """A storage backend for storing assets in Azure Blob Storage

    See https://azure.microsoft.com/en-us/services/storage/blobs/
    """
    def __init__(self, container_name, connection_string, path_prefix=None, signed_url_lifetime=3600):
        # type: (str, str, Optional[str], Optional[int]) -> AzureBlobStorage
        """Constructor for Azure Blob Storage storage backend

        The Azure Blob Storage storage backend's behaviour regarding public URLs depend
        on the container settings. If the container in use is configured to allow public
        blob access (see
        https://docs.microsoft.com/en-us/azure/storage/blobs/anonymous-read-access-configure?tabs=portal),
        this adapter will provide public URLs for blobs, which can be read directly by
        clients. If however public access is not enabled on the container, the URL for
        stored assets will be an internal URL, and a limited-time SAS URL will be provided
        to clients after hitting this code on read.

        Args:
            container_name: Azure Blob Storage container name
            connection_string: The Azure Blob Storage connection string to use
            path_prefix: A prefix to prepend to all stored assets in the container
            signed_url_lifetime: When public access is disabled, this sets the max lifetime in seconds of signed URLs
        """
        # self._container_name = container_name
        self._path_prefix = path_prefix
        self._signed_url_lifetime = signed_url_lifetime

        self._svc_client = BlobServiceClient.from_connection_string(connection_string)
        self._container_client = self._svc_client.get_container_client(container_name)

    def get_storage_uri(self, name, prefix=None):
        """Get the URL of the file in storage
        """
        if self._is_public_read:
            blob = self._blob_client(name, prefix)
            return blob.url
        elif prefix:
            return '{}/{}'.format(prefix, name)
        else:
            return name

    def upload(self, stream, name, prefix=None, mimetype=None):
        """Save the file in storage
        """
        blob = self._blob_client(name, prefix)
        blob.upload_blob(stream)
        if mimetype:
            blob.set_http_headers(ContentSettings(content_type=mimetype))
        return stream.tell()

    def download(self, uri):
        """Provide the direct URL to download the file from storage
        """
        blob = self._blob_client(uri)
        if not self._blob_exists(blob):
            raise exc.ObjectNotFound('The requested file was not found')

        # If we got here, we assume blob is private and return a signed URL
        signed_url = self._get_signed_url(blob, self._signed_url_lifetime)
        return DownloadTarget.redirect(signed_url)

    def delete(self, uri):
        blob = self._blob_client(uri)
        try:
            blob.delete_blob()
        except ResourceNotFoundError:
            return False
        return True

    def _get_blob_path(self, name, prefix=None):
        # type: (str, Optional[str]) -> str
        path = [seg for seg in (self._path_prefix, prefix, name) if seg]
        return '/'.join(path)

    def _blob_client(self, name, prefix=None):
        # type: (str, Optional[str]) -> BlobClient
        return self._container_client.get_blob_client(self._get_blob_path(name, prefix))

    def _get_signed_url(self, blob, expires_in):
        # type: (BlobClient, int) -> str
        permissions = BlobSasPermissions(read=True)
        token_expires = (datetime.now(tz=UTC) + timedelta(seconds=expires_in))

        sas_token = generate_blob_sas(account_name=blob.account_name,
                                      account_key=blob.credential.account_key,
                                      container_name=blob.container_name,
                                      blob_name=blob.blob_name,
                                      permission=permissions,
                                      expiry=token_expires)

        blob_client = BlobClient(self._svc_client.url,
                                 container_name=blob.container_name,
                                 blob_name=blob.blob_name,
                                 credential=sas_token)

        return blob_client.url  # type: ignore

    @memoized_property
    def _is_public_read(self):
        return self._container_client.get_container_access_policy().get('public_access') in {'container', 'blob'}

    @staticmethod
    def _blob_exists(blob):
        # type: (BlobClient) -> bool
        """Tell me if a blob really exists in storage
        """
        try:
            blob.get_blob_properties()
        except ResourceNotFoundError:
            return False
        return True
