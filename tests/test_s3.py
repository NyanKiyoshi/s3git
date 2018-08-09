from io import BytesIO
from tempfile import SpooledTemporaryFile
from unittest import mock

import botocore.exceptions
import pytest

from s3git.exceptions import *
from s3git.s3 import S3CONFIG_PATH, S3Bucket


@mock.patch('boto3.resource')
def test_bucket_passes_correct_parameters(mocked_resource):
    s3_bucket = S3Bucket()
    s3_bucket.S3_ACCESS_KEY_ID = 'keyid'
    s3_bucket.S3_SECRET_ACCESS_KEY = 'secret'
    s3_bucket.S3_BUCKET_NAME = 'mybucket'

    bucket = mocked_resource.return_value

    assert s3_bucket.bucket == bucket.Bucket.return_value
    bucket.Bucket.assert_called_once_with('mybucket')

    mocked_resource.assert_called_once_with(
        service_name='s3',
        aws_access_key_id='keyid',
        aws_secret_access_key='secret',
        endpoint_url=None)


def test__repr__():
    repr(S3Bucket())


def test_as_dict():
    kwargs = {
        'S3_ACCESS_KEY_ID': 'keyid',
        'S3_SECRET_ACCESS_KEY': 'secret',
        'S3_BUCKET_NAME': 'mybucket',
        'S3_UPLOAD_LOCATION': None}
    s3_bucket = S3Bucket(**kwargs)
    assert s3_bucket.as_dict == kwargs


def test__get_mime_type(binary_image):
    s3_bucket = S3Bucket()
    fp = BytesIO(binary_image)
    assert s3_bucket._get_mime_type(fp) == 'image/gif'
    assert fp.tell() == 0


@pytest.mark.parametrize('base_path,expected_key', (
    (None, 'binary-image'),
    ('abc', 'abc/binary-image')))
def test_upload(binary_image, s3_bucket: S3Bucket, base_path, expected_key):
    s3_bucket.S3_UPLOAD_LOCATION = base_path
    mocked_upload_fileobj = s3_bucket.bucket.upload_fileobj = mock.Mock(
        wraps=s3_bucket.bucket.upload_fileobj)

    in_fp = BytesIO(binary_image)
    out_fp = BytesIO()

    s3_bucket.upload(in_fp, 'binary-image')
    mocked_upload_fileobj.assert_called_once_with(
        Fileobj=in_fp, Key=expected_key,
        ExtraArgs={'ContentType': 'image/gif'})

    s3_bucket.bucket.download_fileobj(Key=expected_key, Fileobj=out_fp)

    out_fp.seek(0)
    assert out_fp.read() == binary_image


@pytest.mark.parametrize('base_path,expected_key', (
    (None, 'binary-image'),
    ('abc', 'abc/binary-image')))
def test_get_file(binary_image, s3_bucket: S3Bucket, base_path, expected_key):
    s3_bucket.S3_UPLOAD_LOCATION = base_path
    in_fp = BytesIO(binary_image)

    s3_bucket.bucket.upload_fileobj(Key=expected_key, Fileobj=in_fp)
    out_fp = s3_bucket.get_file('binary-image')

    assert isinstance(out_fp, SpooledTemporaryFile)
    assert not out_fp.closed
    assert out_fp.tell() == 0
    assert out_fp.read() == binary_image


@mock.patch('s3git.s3.SpooledTemporaryFile')
def test_get_file_404_returns_none(
        mocked_spooled, s3_bucket: S3Bucket):

    assert s3_bucket.get_file('binary-image') is None
    mocked_spooled.return_value.close.assert_called_once_with()


@mock.patch('s3git.s3.SpooledTemporaryFile')
def test_get_file_non_404_client_error_raises_exception(
        mocked_spooled, s3_bucket: S3Bucket):
    s3_bucket.S3_BUCKET_NAME = 'inexistent'
    with pytest.raises(botocore.exceptions.ClientError):
        s3_bucket.get_file('binary-image')
    mocked_spooled.return_value.close.assert_called_once_with()


@mock.patch('s3git.s3.SpooledTemporaryFile')
@mock.patch.object(S3Bucket, 'bucket')
def test_get_file_unknown_exception_raises_exception(
        mocked_s3_bucket, mocked_spooled):
    def _raiser_wrapper(*args, **kwargs):
        raise SystemError()

    mocked_s3_bucket.download_fileobj.side_effect = _raiser_wrapper
    with pytest.raises(SystemError):
        S3Bucket().get_file('test')
    mocked_spooled.return_value.close.assert_called_once_with()


@pytest.mark.parametrize('basepath,files,expected_paths', (
        (None, ['dummy'], ['dummy']),
        (None, ['dummy', 'hello'], ['dummy', 'hello']),

        ('ab', ['dummy'], ['ab/dummy']),
        ('ab', ['dummy', 'hello'], ['ab/dummy', 'ab/hello'])))
def test__delete_objects(s3_bucket: S3Bucket, basepath, files, expected_paths):
    s3_bucket.S3_UPLOAD_LOCATION = basepath

    for path in expected_paths:
        s3_bucket.bucket.upload_fileobj(Fileobj=BytesIO(), Key=path)

    response = s3_bucket._delete_objects(files)
    assert 'Deleted' in response

    deleted_keys = list(map(lambda o: o['Key'], response['Deleted']))
    assert deleted_keys == expected_paths


def test__delete_objects_inexistent(s3_bucket: S3Bucket):
    existing_file = 'hello'
    inexistent_file = 'world'

    s3_bucket.bucket.upload_fileobj(Fileobj=BytesIO(), Key=existing_file)

    response = s3_bucket._delete_objects([existing_file, inexistent_file])
    errors = response.get('Errors')
    deleted = response.get('Deleted')

    assert errors
    assert deleted

    assert len(errors) == 1
    assert len(deleted) == 1

    assert errors[0]['Key'] == inexistent_file
    assert deleted[0]['Key'] == existing_file


@mock.patch.object(S3Bucket, '_delete_objects')
@mock.patch.object(S3Bucket, 'DELETE_MAX_COUNT_PER_REQUEST', new=2)
@pytest.mark.parametrize('files,expected_calls', (
    ([],
     []),

    (['hello', 'world'],
     [mock.call(['hello', 'world'])]),

    (['hello', 'world', '!'],
     [mock.call(['hello', 'world']), mock.call(['!'])]),

    (['hello', 'world', '!', '123'],
     [mock.call(['hello', 'world']), mock.call(['!', '123'])]),
))
def test_delete_files_slices_huge_amount(
        mocked__delete_objects, files, expected_calls):
    s3_bucket = S3Bucket()
    s3_bucket.delete_files(files)
    mocked__delete_objects.assert_has_calls(expected_calls)


@pytest.mark.parametrize('config_content,branch_name,expected_result', (
    ('[default]\n'
     'S3_ACCESS_KEY_ID = id\n'
     'S3_SECRET_ACCESS_KEY = secret\n'
     'S3_BUCKET_NAME = bucket\n'
     '[hello]\n'
     'S3_ACCESS_KEY_ID = hi_id\n'
     'S3_SECRET_ACCESS_KEY = hi_secret\n'
     'S3_BUCKET_NAME = hi_bucket\n',

     'none',
     {
         'S3_ACCESS_KEY_ID': 'id',
         'S3_SECRET_ACCESS_KEY': 'secret',
         'S3_BUCKET_NAME': 'bucket',
         'S3_UPLOAD_LOCATION': None}),

    ('[default]\n'
     'S3_ACCESS_KEY_ID = id\n'
     'S3_SECRET_ACCESS_KEY = secret\n'
     'S3_BUCKET_NAME = bucket\n'
     '[hello]\n'
     'S3_ACCESS_KEY_ID = hi_id\n'
     'S3_SECRET_ACCESS_KEY = hi_secret\n'
     'S3_BUCKET_NAME = hi_bucket\n'
     'S3_UPLOAD_LOCATION = bello',

     'hello',
     {
         'S3_ACCESS_KEY_ID': 'hi_id',
         'S3_SECRET_ACCESS_KEY': 'hi_secret',
         'S3_BUCKET_NAME': 'hi_bucket',
         'S3_UPLOAD_LOCATION': 'bello'}),

))
def test_read_config(s3git, config_content, branch_name, expected_result):
    with open(S3CONFIG_PATH, 'w') as w:
        w.write(config_content)

    s3_bucket = S3Bucket.read_config(branch_name)

    assert s3_bucket.as_dict == expected_result


def test_read_config_missing_required_key_raises_error(s3git):
    with open(S3CONFIG_PATH, 'w') as w:
        w.write('[default]\n' 
                'S3_ACCESS_KEY_ID = id\n'
                'S3_SECRET_ACCESS_KEY = secret\n')

    expected_error_cls = RequiredValueMissingInConfigurationFile
    expected_error_msg = expected_error_cls.MSG % ('default', 'S3_BUCKET_NAME')

    with pytest.raises(expected_error_cls, message=expected_error_msg):
        S3Bucket.read_config('none')


def test_read_config_missing_no_fit_section_found(s3git):
    """
    Happens when there is no default section
    or no section with the name of the current branch.
    """
    with open(S3CONFIG_PATH, 'w') as w:
        w.write('[branch]\n' 
                'S3_ACCESS_KEY_ID = id\n'
                'S3_SECRET_ACCESS_KEY = secret\n'
                'S3_BUCKET_NAME = hi_bucket')

    expected_error_cls = MissingSectionConfigurationFile
    expected_error_msg = expected_error_cls.MSG % S3CONFIG_PATH

    with pytest.raises(expected_error_cls, message=expected_error_msg):
        S3Bucket.read_config('none')
