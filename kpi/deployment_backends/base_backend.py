#!/usr/bin/python
# -*- coding: utf-8 -*-


class BaseDeploymentBackend:
    def __init__(self, asset):
        self.asset = asset

    def store_data(self, vals=None):
        self.asset._deployment_data.update(vals)

    @property
    def backend(self):
        return self.asset._deployment_data.get('backend', None)

    @property
    def identifier(self):
        return self.asset._deployment_data.get('identifier', None)

    @property
    def active(self):
        return self.asset._deployment_data.get('active', False)

    @property
    def version(self):
        raise NotImplementedError('Use `asset.deployment.version_id`')

    @property
    def version_id(self):
        return self.asset._deployment_data.get('version', None)

    @property
    def submission_count(self):
        return self._submission_count()

    @property
    def mongo_userform_id(self):
        return None
