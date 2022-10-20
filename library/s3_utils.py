import os
import sys

dir_path = os.path.dirname(os.path.realpath(__file__))
sys.path.append(dir_path)

from botocore.exceptions import ClientError
from boto3.resources.factory import ServiceResource
from file_utils import (
    ensure_file_slash,
    filename_is_blank,
    check_if_file_exists,
    make_dir_if_not_exists,
)

# Initiate logging
from log_config import get_logger

log = get_logger(__name__)


def check_if_folder_exists_in_s3_bucket(
    s3_resource: ServiceResource, bucket_name: str, directory: str
) -> bool:
    "Checks S3 bucket to determine if a folder exists"

    directory = ensure_file_slash(directory)

    try:
        s3_resource.meta.client.head_bucket(Bucket=bucket_name)
        try:
            s3_resource.Object(bucket_name=bucket_name, key=directory).load()
            log.info(f"'{directory}' exists in S3 Bucket '{bucket_name}'")
            return True
        except ClientError as e:
            log.error(f"Error = {e}")
            log.info(f"'{directory}' does not exist in S3 Bucket '{bucket_name}'")
            return False
    except ClientError:
        log.info(f"S3 Bucket '{bucket_name}' does not exist")
        return False


def check_if_file_exists_in_s3(
    s3_resource: ServiceResource, bucket_name: str, filename: str, path: str = None
) -> bool:

    if filename_is_blank(filename):
        return False

    if path is None:
        try:
            s3_resource.meta.client.head_bucket(Bucket=bucket_name)
            try:
                s3_resource.Object(bucket_name=bucket_name, key=filename).load()
                log.info(f"'{filename}' exists in S3 Bucket '{bucket_name}'")
                return True
            except ClientError:
                log.info(f"'{filename}' does not exist in S3 Bucket '{bucket_name}'")
                return False
        except ClientError:
            log.info(f"S3 Bucket '{bucket_name}' does not exist")
            return False

    else:
        try:
            check_if_folder_exists_in_s3_bucket(s3_resource, bucket_name, path)
            path = ensure_file_slash(path)
            file_path = path + filename
            s3_resource.Object(bucket_name=bucket_name, key=file_path).load()
            log.info(f"'{filename}' exists in directory '{path}'")
            return True
        except ClientError:
            log.info(f"'{filename}' does not exist in directory '{path}'")
            return False


def move_local_file_to_s3(
    s3_resource: ServiceResource,
    local_filename: str,
    local_path: str,
    bucket: str,
    s3_filename: str = None,
    s3_path: str = None,
):
    if not s3_filename:
        s3_filename = local_filename
    try:
        local_filepath = check_if_file_exists(local_path, local_filename)

        if s3_path:
            s3_path = ensure_file_slash(s3_path)
            s3_filepath = s3_path + s3_filename
        else:
            s3_filepath = s3_filename

        s3_resource.Bucket(bucket).upload_file(local_filepath, s3_filepath)
        log.info(f"'{local_filename}' moved to '{s3_filepath}' in '{bucket}'")
    except Exception as e:
        print(f"{type(e)}: {e}")


def create_directory_in_s3(
    s3_resource: ServiceResource, bucket: str, folder_name: str
) -> None:
    """Creates a directory in S3.
    Due to the flat file structure of S3, this needs to be done separately from loading a file.
    """
    directory = ensure_file_slash(folder_name)
    s3_resource.Bucket(bucket).put_object(Key=directory)


def pull_file_from_s3(
    s3_resource: ServiceResource,
    bucket: str,
    s3_filename: str,
    s3_path: str = None,
    local_path: str = None,
    local_filename: str = None,
) -> bool:
    try:
        if s3_path:
            s3_path = ensure_file_slash(s3_path)
            s3_filepath = s3_path + s3_filename
        else:
            s3_filepath = s3_filename

        if check_if_file_exists_in_s3(s3_resource, bucket, s3_filename, s3_path):
            if not local_filename:
                local_filename = s3_filename

            if not local_path:
                local_path = os.path.dirname(os.path.realpath(__file__))
        else:
            return False

        local_path = ensure_file_slash(local_path)
        local_filepath = local_path + local_filename
        make_dir_if_not_exists(local_path)
        s3_resource.Bucket(bucket).download_file(s3_filepath, local_filepath)
        log.info(f"'{local_filename}' moved to '{local_path}'")
        return True
    except Exception as e:
        print(f"{type(e)}: {e}")
        return False
