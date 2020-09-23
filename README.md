ckanext-asset-storage
========================
[![Build Status](https://travis-ci.org/datopian/ckanext-asset-storage.svg?branch=master)](https://travis-ci.org/datopian/ckanext-asset-storage)
[![Coverage Status](https://coveralls.io/repos/github/datopian/ckanext-asset-storage/badge.svg?branch=master)](https://coveralls.io/github/datopian/ckanext-asset-storage?branch=master)

**Store CKAN assets (org / group images) to cloud storage**

This CKAN extension moves storage of uploaded asset files - specifically, organization
and group logos and the site logo, to a cloud storage backend. It is designed to be 
flexible as it allows for different storage backends, and may support additional storage
backends in the future. 

**NOTE** This does not handle resource storage at all. For offloading resource storage,
we recommend using [ckanext-blob-storage](https://github.com/datopian/ckanext-blob-storage). 

Requirements
------------
* This extension works with CKAN 2.8.x and CKAN 2.9.x. It may work, but has not been tested, with other CKAN versions.
* You need to have access to a supported Cloud Storage account to store assets in 

Supported Storage Backends include:
* Google Cloud Storage
* Azure Blob Storage
* AWS S3 (NOT YET)
* Local Storage (mainly for testing and fallback purposes)

Installation
------------

To install ckanext-asset-storage:

1. Activate your CKAN virtual environment, for example:
```
. /usr/lib/ckan/default/bin/activate
```

2. Install the ckanext-asset-storage Python package into your virtual environment:
```
pip install ckanext-asset-storage
```

3. Add `asset_storage` to the `ckan.plugins` setting in your CKAN
   config file (by default the config file is located at
   `/etc/ckan/default/production.ini`).

4. Restart CKAN. For example if you've deployed CKAN with Apache on Ubuntu:
```
sudo service apache2 reload
```

Configuring This Extension
--------------------------

### CKAN INI Options
The following CKAN configuration options should be set:

#### `ckanext.asset_storage.backend_type = 'backend_type'`

The storage backend type. The following types are supported out of the box:

* `local` - Local filesystem storage
* `google_cloud` - Google Cloud Storage
* `azure_blobs` - Azure Blob Storage
* `s3` - AWS S3 storage

You can also write *custom* storage backends, and specify the fully
qualified `package.module:Class` name of your storage class here. For 
example, specifying `ckanext.my_storage.storage:MyStorageClass` will
try to use `MyStorageClass` in the `ckanext.my_storage.storage` module
as a storage backend. 

#### `ckanext.asset_storage.backend_options = {"some_opt":"value"}`

Options to pass to the storage backend. This should be a Python dict 
with key-value pairs. 

The specific option keys depend on the storage `backend_type` in and 
are detailed below.

Available Storage Backends Overview and Settings
------------------------------------------------
### `local`
Stores asset in the local file system. This is not much different from CKAN's 
built-in behavior, and thus is mostly useful for testing purposes. 

The following configuration options are available:

* `storage_path` - (required, string) the local directory to store files in

### `google_cloud`
To use Google Cloud Storage, you must have an existing Google Cloud project and bucket. You need to obtain a 
Google Account Key file (a JSON file downloadable from the Google Console) for a user or a service account that
has "Object Admin" role on the bucket (at the very least they should be able to read, write and delete objcets).   

The following configuration options are available:

* `project_name` - (required, string) Google Cloud project name
* `bucket_name` - (required, string) Google Cloud Storage bucket name
* `account_key_file` - (required, string) Path to the Google Cloud credentials JSON file
* `path_prefix` - (optional, string) A prefix to prepend to all stored assets in the bucket
* `public_read` - (boolean, default `True`) Whether to allow public read access to uploaded assets. Setting to `False` 
  means the asset can only be accessed after a request to this code to generate a signed URL. This will have some 
  performance impact. You should keep this at the default unless you consider group / organization images sensitive / 
  private information. 
* `signed_url_lifetime` - (int, default `3600`) When public access is not allowed, this sets the max lifetime in seconds
  of signed URLs. Typically you should not change this. 

### `azure_blobs`
To use Azure Blob Storage, you must have an existing Azure account and Blob Storage container.  
By default, Azure Blob Storage containers are set to disallow public access to blobs, and this is 
not configurable at the blob level - only on the container level. For this reason, this storage
backend provides public URLs if and only if the container is configured to [allow public access 
to blobs](https://docs.microsoft.com/en-us/azure/storage/blobs/anonymous-read-access-configure?tabs=portal). 
If public access is enabled, asset URLs will be direct-to-cloud public URLs. Otherwise, asset 
URLs will point to CKAN, which will generate a time-limited SAS signed URL, and redirect the 
client to that URL.

The following configuration options are available:

* `container_name` - Azure Blob Storage container name
* `connection_string` - The Azure Blob Storage connection string to use
* `path_prefix`  - A prefix to prepend to all stored assets in the container
* `signed_url_lifetime` - When public access is not allowed, this sets the max lifetime of signed URLs.

### `s3`
TBD

Frequently Asked Questions
--------------------------
#### Q: Can I use the same Cloud container / bucket for assets and resources?
A: If you use a CKAN extension that stores resources in cloud storage (such
as [`ckanext-blob-storage`](https://github.com/datopian/ckanext-blob-storage)), 
and you already have a cloud container configured for storing assets, it should 
be very easy to reuse the same container to store assets if that is desired. 

Simply configure your storage backend to store assets under a path prefix (e.g. 
see the `path_prefix` config option for most cloud backends), and use a prefix
that will never be used by your resource storage extension to store resources.

For example, setting `path_prefix` to `_assets` will do the trick in most cases.  

Developer installation
----------------------

To install `ckanext-asset-storage` for development, do the following:

1. Pull the project code from Github
```
git clone https://github.com/datopian/ckanext-asset-storage.git
cd ckanext-asset-storage
```
2. Create a Python 2.7 virtual environment
```
virtualenv .venv27
source .venv27/bin/activate
```

Or a Python 3.x virtual environment:
```
python3 -m venv .venv3
source .venv3/bin/activate
```

(You can use `pyenv` to manage multiple versions of Python on your system)

3. Run the following command to bootstrap the entire environment
```
make dev-start
```

This will pull and install CKAN and all it's dependencies into your virtual
environment, create all necessary configuration files, launch external services
using Docker Compose and start the CKAN development server.

You can repeat the last command at any time to start developing again.

Type `make help` to get a like of user commands useful to managing the local
environment.

### Working with `requirements.txt` files

#### tl;dr

* You *do not* touch `*requirements.*.txt` files directly. We use
[`pip-tools`][1] and custom `make` targets to manage these files.
* Use `make develop` to install the right development time requirements into your
current virtual environment
* Use `make install` to install the right runtime requirements into your current
virtual environment
* To add requirements, edit `requirements.in` or `dev-requirements.in` and run
`make requirements`. This will recompile the requirements file(s) **for your
current Python version**. You may need to do this for the other Python version
by switching to a different Python virtual environment before committing your
changes.

#### More background
This project manages requirements in a relatively complex way, in order to
seamlessly support Python 2.7 and 3.x.

For this reason, you will see 4 requirements files in the project root:

* `requirements.py2.txt` - Python 2 runtime requirements
* `requirements.py3.txt` - Python 3 runtime requirements
* `dev-requirements.py2.txt` - Python 2 development requirements
* `dev-requirements.py3.txt` - Python 3 development requirements

These are generated using the `pip-compile` command (a part of `pip-tools`)
from the corresponding `requirements.in` and `dev-requirements.in` files.

To understand why `pip-compile` is used, read the `pip-tools` manual. In
short, this allows us to pin dependencies of dependencies, thus resolving
potential deployment conflicts, without the headache of managing the specific
version of each Nth-level dependency.

In order to support both Python 2.7 and 3.x, which tend to require slightly
different dependencies, we use `requirements.in` files to generate
major-version specific requirements files. These, in turn, should be used
when installing the package.

In order to simplify things, the `make` targets specified above will automate
the process *for the current Python version*.

#### Adding Requirements

Requirements are managed in `.in` files - these are the only files that
should be edited directly.

Take care to specify a version for each requirement, to the level required
to maintain future compatibility, but not to specify an *exact* version
unless necessary.

For example, the following are good `requirements.in` lines:

    pyjwt[crypto]==1.7.*
    pyyaml==5.*

This allows these packages to be upgraded to a minor version, without the risk
of breaking compatibility.

Developers wanting to add new requirements (runtime or development time),
should take special care to update the `requirements.txt` files for all
supported Python versions by running `make requirements` on different
virtual environment, after updating the relevant `.in` file.

#### Applying Patch-level upgrades to requirements

You can delete `*requirements.*.txt` and run `make requirements`.

TODO: we can probably do this in a better way - create a `make` target
for this.  

Tests
-----

To run the tests, do:

    make test

To run the tests and produce a coverage report, first make sure you have
coverage installed in your virtualenv (``pip install coverage``) then run:

    make coverage

Releasing a new version of ckanext-asset-storage
------------------------------------------------

ckanext-asset-storage should be available on PyPI as https://pypi.org/project/ckanext-asset-storage.
To publish a new version to PyPI follow these steps:

1. Update the version number in `ckanext/asset_storage/__init__.py` file.
   See [PEP 440](http://legacy.python.org/dev/peps/pep-0440/#public-version-identifiers)
   for how to choose version numbers.

2. Make sure you have the latest version of necessary packages:
```
    pip install --upgrade setuptools wheel twine
```

3. Create a source and binary distributions of the new version:
```
    python setup.py sdist bdist_wheel && twine check dist/*
```

   Fix any errors you get.

4. Upload the source distribution to PyPI:
```
    twine upload dist/*
```

5. Commit any outstanding changes:
```
    git commit -a
```

6. Tag the new release of the project on GitHub with the version number from
   the ``setup.py`` file. For example if the version number in ``setup.py`` is
   0.0.1 then do:
```
    git tag 0.0.1
    git push --tags
```


[1]: https://pypi.org/project/pip-tools/
