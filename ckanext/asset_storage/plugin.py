from ast import literal_eval

import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
import six

from ckanext.asset_storage import uploader
from ckanext.asset_storage.blueprints import blueprint


class AssetStoragePlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IUploader)
    plugins.implements(plugins.IBlueprint)

    # IConfigurer

    def update_config(self, config):
        toolkit.add_template_directory(config, 'templates')
        toolkit.add_public_directory(config, 'public')
        toolkit.add_resource('fanstatic', 'asset-storage')

        backend_config = config.get(uploader.CONF_BACKEND_CONFIG)
        if not backend_config:
            backend_config = {}
        elif isinstance(backend_config, six.string_types):
            backend_config = literal_eval(backend_config)

        config[uploader.CONF_BACKEND_CONFIG] = backend_config

    # IBlueprint

    def get_blueprint(self):
        return blueprint

    # IUploader

    def get_uploader(self, upload_to, old_filename):
        return uploader.AssetUploader(object_type=upload_to,
                                      old_filename=old_filename,
                                      storage=uploader.get_configured_storage())

    def get_resource_uploader(self, data_dict):
        """We do not handle resource uploading in this extension
        """
        return None
