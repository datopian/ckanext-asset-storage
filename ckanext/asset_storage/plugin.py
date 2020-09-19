from ast import literal_eval

import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit

from ckanext.asset_storage import uploader
from ckanext.asset_storage.blueprints import blueprint


class AssetStoragePlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IUploader, inherit=True)
    plugins.implements(plugins.IBlueprint)

    # IConfigurer

    def update_config(self, config):
        toolkit.add_template_directory(config, 'templates')
        toolkit.add_public_directory(config, 'public')
        toolkit.add_resource('fanstatic', 'asset-storage')

        backend_config = config.get(uploader.CONF_BACKEND_CONFIG)
        if not backend_config:
            backend_config = {}
        else:
            backend_config = literal_eval(backend_config)
        config[uploader.CONF_BACKEND_CONFIG] = backend_config

    # IBlueprint

    def get_blueprint(self):
        return blueprint

    # IUploader

    def get_uploader(self, upload_to, old_filename):
        return uploader.AssetUploader(upload_to=upload_to,
                                      old_filename=old_filename,
                                      storage=uploader.get_configured_storage())
