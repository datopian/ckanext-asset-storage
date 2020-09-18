import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit


class AssetStoragePlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IUploader, inherit=True)

    # IConfigurer

    def update_config(self, config):
        toolkit.add_template_directory(config, 'templates')
        toolkit.add_public_directory(config, 'public')
        toolkit.add_resource('fanstatic', 'asset-storage')

    # IUploader

    def get_uploader(self, upload_to, old_filename):
        pass
