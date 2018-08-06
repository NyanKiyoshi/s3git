import configparser
import os
import posixpath
from os.path import isfile
from tempfile import SpooledTemporaryFile

import boto3
import botocore.exceptions
from magic import from_buffer

from s3git.exceptions import *
from s3git.utils import cached_property

S3CONFIG_PATH = '.git/s3config.cfg'
DEFAULT_SECTION = 'default'

S3_ENDPOINT_URL = os.getenv('S3_ENDPOINT_URL', None)


class ConfigParser(configparser.ConfigParser):
    def get_available_section(self, *sections: str):
        for section in sections:
            if self.has_section(section):
                return section
        return None


class S3Bucket:
    DELETE_MAX_COUNT_PER_REQUEST = 1000
    MIME_TYPE_READ_SIZE = 1024

    REQUIRED_KEYS = (
        'S3_ACCESS_KEY_ID',
        'S3_SECRET_ACCESS_KEY',
        'S3_BUCKET_NAME')

    OPTIONAL_KEYS = (
        'S3_UPLOAD_LOCATION',)

    __slots__ = REQUIRED_KEYS + OPTIONAL_KEYS

    # cached properties are stored here as data classes don't use `__dict__`
    CACHED_DATA = {}

    def __init__(self, **kwargs):
        for k in self.__slots__:
            setattr(self, k, kwargs.get(k, None))

    @cached_property
    def base_path(self):
        return self.S3_UPLOAD_LOCATION or ''

    @cached_property
    def bucket(self):
        s3 = boto3.resource(
            service_name='s3',
            aws_access_key_id=self.S3_ACCESS_KEY_ID,
            aws_secret_access_key=self.S3_SECRET_ACCESS_KEY,
            endpoint_url=S3_ENDPOINT_URL)

        bucket = s3.Bucket(self.S3_BUCKET_NAME)
        return bucket

    def _get_mime_type(self, fp):
        mime_type = from_buffer(fp.read(self.MIME_TYPE_READ_SIZE), mime=True)
        fp.seek(0)
        return mime_type

    def get_target_path(self, path):
        return posixpath.join(self.base_path, path)

    def upload(self, fp, path):
        path = self.get_target_path(path)
        mime_type = self._get_mime_type(fp)
        return self.bucket.upload_fileobj(
            Fileobj=fp, Key=path, ExtraArgs={'ContentType': mime_type})

    def get_file(self, path):
        path = self.get_target_path(path)
        fp = SpooledTemporaryFile(suffix='-s3git', mode='wb')
        try:
            self.bucket.download_fileobj(Key=path, Fileobj=fp)
        except botocore.exceptions.ClientError as exc:
            fp.close()

            # If a client error is thrown, then check that it was a 404 error.
            # If it was a 404 error, then the file does not exist.
            error_code = int(exc.response['Error']['Code'])
            if error_code == 404:
                fp = None
            else:
                raise exc
        except Exception as exc:
            fp.close()
            raise exc
        else:
            fp.seek(0)
        return fp

    def _delete_objects(self, object_list):
        payload = {
            'Objects': [
                {'Key': self.get_target_path(path)} for path in object_list
            ]
        }

        return self.bucket.delete_objects(Delete=payload)

    def delete_files(self, paths):
        start_pos = 0
        end_pos = self.DELETE_MAX_COUNT_PER_REQUEST

        while start_pos < len(paths):
            to_delete = paths[start_pos:end_pos]
            self._delete_objects(to_delete)

            start_pos = end_pos
            end_pos += self.DELETE_MAX_COUNT_PER_REQUEST

    @property
    def as_dict(self):
        return {k: getattr(self, k) for k in self.__slots__}

    def __repr__(self):
        return '<{self.__class__.__name__} @{id} {self.as_dict}>'.format(
            self=self, id=id(self))

    @classmethod
    def read_config(cls, section):
        options = {}
        config_path = S3CONFIG_PATH

        if not isfile(config_path):
            raise MissingConfigurationFile(S3CONFIG_PATH)

        cfg = ConfigParser()
        cfg.read(config_path)

        section = cfg.get_available_section(section, DEFAULT_SECTION)
        if not section:
            raise MissingSectionConfigurationFile(S3CONFIG_PATH)

        for required_key in cls.REQUIRED_KEYS:
            if not cfg.has_option(section, required_key):
                raise RequiredValueMissingInConfigurationFile(
                    (section, required_key))
            options[required_key] = cfg.get(section, required_key)

        for optional_key in cls.OPTIONAL_KEYS:
            if cfg.has_option(section, optional_key):
                options[optional_key] = cfg.get(section, optional_key)

        result_instance = cls(**options)
        return result_instance
