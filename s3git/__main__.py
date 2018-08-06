from sys import argv
import argparse
import logging

from s3git.core import S3GitSync
from s3git.exceptions import BaseError

logging.basicConfig(
    level=logging.INFO, format='%(levelname)s: %(message)s')

logger = logging.getLogger(__name__)


def _parse_arguments(*args):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'branch', nargs='?', default=None,
        help='commit, head or branch to sync at')
    parser.add_argument(
        '-f', dest='force_reupload', default=False, action='store_true',
        help='forces a whole reupload')
    return parser.parse_args(args)


def main():
    parsed = vars(_parse_arguments(*argv[1:]))

    try:
        s3_sync = S3GitSync(**parsed)
        s3_sync.synchronize()
    except BaseError as exc:
        logger.error(exc.msg)
        exit(1)


if __name__ == '__main__':
    main()
