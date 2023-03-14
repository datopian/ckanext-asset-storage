# Makefile for ckanext-asset-storage

PACKAGE_DIR := ckanext/asset_storage
PACKAGE_NAME := ckanext.asset_storage

SHELL := bash
PYTHON := python
PIP := pip
PIP_COMPILE := pip-compile
PYTEST := pytest
DOCKER_COMPOSE := docker-compose
PSQL := psql
GIT := git

# Find GNU sed in path (on OS X gsed should be preferred)
SED := $(shell which gsed sed | head -n1)

# The `ckan` command line only exists in newer versions of CKAN
CKAN_CLI := $(shell which ckan | head -n1)

TEST_INI_PATH := ./test.ini
SENTINELS := .make-status

PACKAGE_TAG_PREFIX := "v"
PACKAGE_TAG_SUFFIX := ""

# CKAN environment variables
CKAN_PATH := ckan
CKAN_REPO_URL := https://github.com/ckan/ckan.git
CKAN_VERSION := ckan-2.9.8
CKAN_CONFIG_FILE := $(CKAN_PATH)/development.ini
CKAN_INI_TEMPLATE_FILE := $(CKAN_PATH)/ckan/config/deployment.ini_tmpl
CKAN_SITE_URL := http://localhost:5000
POSTGRES_USER := ckan
POSTGRES_PASSWORD := ckan
POSTGRES_DB := ckan
POSTGRES_HOST := 127.0.0.1
CKAN_SOLR_PASSWORD := ckan
DATASTORE_DB_NAME := datastore
DATASTORE_DB_RO_USER := datastore_ro
DATASTORE_DB_RO_PASSWORD := datastore_ro
CKAN_LOAD_PLUGINS := asset_storage stats text_view image_view recline_view datastore

CKAN_CONFIG_VALUES := \
		ckan.site_url=$(CKAN_SITE_URL) \
		sqlalchemy.url=postgresql://$(POSTGRES_USER):$(POSTGRES_PASSWORD)@localhost/$(POSTGRES_DB) \
		ckan.datastore.write_url=postgresql://$(POSTGRES_USER):$(POSTGRES_PASSWORD)@localhost/$(DATASTORE_DB_NAME) \
		ckan.datastore.read_url=postgresql://$(DATASTORE_DB_RO_USER):$(DATASTORE_DB_RO_PASSWORD)@localhost/$(DATASTORE_DB_NAME) \
		ckan.plugins='$(CKAN_LOAD_PLUGINS)' \
		ckan.storage_path='%(here)s/storage' \
		solr_url=http://127.0.0.1:8983/solr/ckan

CKAN_TEST_CONFIG_VALUES := \
		sqlalchemy.url=postgresql://$(POSTGRES_USER):$(POSTGRES_PASSWORD)@localhost/$(POSTGRES_DB)_test \
		ckan.datastore.write_url=postgresql://$(POSTGRES_USER):$(POSTGRES_PASSWORD)@localhost/$(DATASTORE_DB_NAME)_test \
		ckan.datastore.read_url=postgresql://$(DATASTORE_DB_RO_USER):$(DATASTORE_DB_RO_PASSWORD)@localhost/$(DATASTORE_DB_NAME)_test

ifdef WITH_COVERAGE
  COVERAGE_ARG := --cov=$(PACKAGE_NAME)
else
  COVERAGE_ARG :=
endif

## Install this extension to the current Python environment
install: $(SENTINELS)/install
.PHONY: install

## Set up the extension for development in the current Python environment
develop: $(SENTINELS)/develop
.PHONEY: develop

## Run all tests
test: $(SENTINELS)/tests-passed
.PHONY: test

## Install the right version of CKAN into the virtual environment
ckan-install: $(SENTINELS)/ckan-installed
	@echo "Current CKAN version: $(shell cat $(SENTINELS)/ckan-version)"
.PHONY: ckan-install

## Run CKAN in the local virtual environment
ckan-start: $(SENTINELS)/ckan-installed $(SENTINELS)/install-dev $(CKAN_CONFIG_FILE) | _check_virtualenv
	$(CKAN_CLI) -c $(CKAN_CONFIG_FILE) db init
	$(CKAN_CLI) -c $(CKAN_CONFIG_FILE) server -r

.PHONY: ckan-start

$(CKAN_PATH):
	$(GIT) clone $(CKAN_REPO_URL) $@

$(CKAN_CONFIG_FILE): $(SENTINELS)/ckan-installed $(SENTINELS)/develop | _check_virtualenv
    cp $(CKAN_INI_TEMPLATE_FILE) $(CKAN_CONFIG_FILE)
	$(CKAN_CLI) config-tool $(CKAN_CONFIG_FILE) -s DEFAULT debug=true
	$(CKAN_CLI) config-tool $(CKAN_CONFIG_FILE) $(CKAN_CONFIG_VALUES)

.env:
	@___POSTGRES_USER=$(POSTGRES_USER) \
	___POSTGRES_PASSWORD=$(POSTGRES_PASSWORD) \
	___POSTGRES_DB=$(POSTGRES_DB) \
	___CKAN_SOLR_PASSWORD=$(CKAN_SOLR_PASSWORD) \
	___DATASTORE_DB_NAME=$(DATASTORE_DB_NAME) \
	___DATASTORE_DB_USER=$(POSTGRES_USER) \
	___DATASTORE_DB_RO_USER=$(DATASTORE_DB_RO_USER) \
	___DATASTORE_DB_RO_PASSWORD=$(DATASTORE_DB_RO_PASSWORD) \
	env | grep ^___ | $(SED) 's/^___//' > .env
	@cat .env

## Start all Docker services
docker-up: .env
	$(DOCKER_COMPOSE) up -d
	@until $(DOCKER_COMPOSE) exec db pg_isready -U $(POSTGRES_USER); do sleep 1; done
	@sleep 2
	@echo " \
    	CREATE ROLE $(DATASTORE_DB_RO_USER) NOSUPERUSER NOCREATEDB NOCREATEROLE LOGIN PASSWORD '$(DATASTORE_DB_RO_PASSWORD)'; \
    	CREATE DATABASE $(DATASTORE_DB_NAME) OWNER $(POSTGRES_USER) ENCODING 'utf-8'; \
    	CREATE DATABASE $(DATASTORE_DB_NAME)_test OWNER $(POSTGRES_USER) ENCODING 'utf-8'; \
    	CREATE DATABASE $(POSTGRES_DB)_test OWNER $(POSTGRES_USER) ENCODING 'utf-8'; \
    	GRANT ALL PRIVILEGES ON DATABASE $(DATASTORE_DB_NAME) TO $(POSTGRES_USER);  \
    	GRANT ALL PRIVILEGES ON DATABASE $(DATASTORE_DB_NAME)_test TO $(POSTGRES_USER);  \
    	GRANT ALL PRIVILEGES ON DATABASE $(POSTGRES_DB)_test TO $(POSTGRES_USER);  \
    " | $(DOCKER_COMPOSE) exec -T db psql --username "$(POSTGRES_USER)"
.PHONY: docker-up

## Stop all Docker services
docker-down: .env
	$(DOCKER_COMPOSE) down
.PHONY: docker-down

## Initialize the development environment
dev-setup: _check_virtualenv $(SENTINELS)/ckan-installed $(CKAN_PATH)/who.ini $(CKAN_CONFIG_FILE) $(SENTINELS)/develop
.PHONY: setup

## Start a full development environment
dev-start: dev-setup docker-up ckan-start
.PHONY: start-dev

## Create the database for test running
create-test-db:
	@echo " \
    	CREATE ROLE $(DATASTORE_DB_RO_USER) NOSUPERUSER NOCREATEDB NOCREATEROLE LOGIN PASSWORD '$(DATASTORE_DB_RO_PASSWORD)'; \
    	CREATE DATABASE $(DATASTORE_DB_NAME)_test OWNER $(POSTGRES_USER) ENCODING 'utf-8'; \
    	CREATE DATABASE $(POSTGRES_DB)_test OWNER $(POSTGRES_USER) ENCODING 'utf-8'; \
    	GRANT ALL PRIVILEGES ON DATABASE $(DATASTORE_DB_NAME)_test TO $(POSTGRES_USER);  \
    	GRANT ALL PRIVILEGES ON DATABASE $(POSTGRES_DB)_test TO $(POSTGRES_USER);  \
    " | PGPASSWORD=$(POSTGRES_PASSWORD) $(PSQL) -h $(POSTGRES_HOST) --username "$(POSTGRES_USER)"
.PHONY: create-test-db

# Private targets

_check_virtualenv:
	@if [ -z "$(VIRTUAL_ENV)" ] && [ -z "$(USE_GLOBAL_PYTHON_ENV)"]; then \
	  echo "You are not in a virtual environment - activate your virtual environment first"; \
	  exit 1; \
	fi
.PHONY: _check_virtualenv

$(SENTINELS):
	mkdir -p $@

$(SENTINELS)/ckan-version: $(CKAN_PATH) | _check_virtualenv $(SENTINELS)
	$(GIT) -C $(CKAN_PATH) remote update
	$(GIT) -C $(CKAN_PATH) checkout $(CKAN_VERSION)
	if [ -e $(CKAN_PATH)/requirement-setuptools.txt ]; then $(PIP) install -r $(CKAN_PATH)/requirement-setuptools.txt; fi
    $(PIP) install -r $(CKAN_PATH)/requirements.txt
	$(PIP) install -r $(CKAN_PATH)/dev-requirements.txt
	$(PIP) install -e $(CKAN_PATH)
	echo "$(CKAN_VERSION)" > $@

$(SENTINELS)/ckan-installed: $(SENTINELS)/ckan-version | $(SENTINELS)
	@if [ "$(shell cat $(SENTINELS)/ckan-version)" != "$(CKAN_VERSION)" ]; then \
	  echo "Switching to CKAN $(CKAN_VERSION)"; \
	  rm $(SENTINELS)/ckan-version; \
	  $(MAKE) $(SENTINELS)/ckan-version; \
	fi
	@touch $@

$(SENTINELS)/test.ini: $(TEST_INI_PATH) $(CKAN_PATH) $(CKAN_PATH)/test-core.ini | $(SENTINELS)
	$(SED) "s@use = config:.*@use = config:$(CKAN_PATH)/test-core.ini@" -i $(TEST_INI_PATH)
	$(CKAN_CLI) config-tool $(CKAN_PATH)/test-core.ini $(CKAN_CONFIG_VALUES) $(CKAN_TEST_CONFIG_VALUES)
	@touch $@

$(SENTINELS)/requirements: requirements.txt dev-requirements.txt | $(SENTINELS)
	@touch $@

$(SENTINELS)/install: requirements.txt | $(SENTINELS)
	$(PIP) install -r requirements.txt
	@touch $@

$(SENTINELS)/install-dev: requirements.txt | $(SENTINELS)
	$(PIP) install -r dev-requirements.txt
	$(PIP) install -e .
	@touch $@

$(SENTINELS)/develop: $(SENTINELS)/requirements $(SENTINELS)/install $(SENTINELS)/install-dev setup.py | $(SENTINELS)
	@touch $@

$(SENTINELS)/test-setup: $(SENTINELS)/develop $(SENTINELS)/test.ini
	$(CKAN_CLI) -c $(TEST_INI_PATH) db init
	@touch $@

$(SENTINELS)/tests-passed: $(SENTINELS)/test-setup $(shell find $(PACKAGE_DIR) -type f) .flake8 .isort.cfg | $(SENTINELS)
	$(PYTEST) $(COVERAGE_ARG) \
		--flake8 \
		--isort \
		--ckan-ini=$(TEST_INI_PATH) \
		--doctest-modules \
		$(PACKAGE_DIR)
	@touch $@

# Help related variables and targets

GREEN  := $(shell tput -Txterm setaf 2)
YELLOW := $(shell tput -Txterm setaf 3)
WHITE  := $(shell tput -Txterm setaf 7)
RESET  := $(shell tput -Txterm sgr0)
TARGET_MAX_CHAR_NUM := 15

## Show help
help:
	@echo ''
	@echo 'Usage:'
	@echo '  ${YELLOW}make${RESET} ${GREEN}<target>${RESET}'
	@echo ''
	@echo 'Targets:'
	@awk '/^[a-zA-Z\-\_0-9]+:/ { \
	  helpMessage = match(lastLine, /^## (.*)/); \
	  if (helpMessage) { \
	    helpCommand = substr($$1, 0, index($$1, ":")-1); \
	    helpMessage = substr(lastLine, RSTART + 3, RLENGTH); \
	    printf "  ${YELLOW}%-$(TARGET_MAX_CHAR_NUM)s${RESET} ${GREEN}%s${RESET}\n", helpCommand, helpMessage; \
	  } \
	} \
	{ lastLine = $$0 }' $(MAKEFILE_LIST)
