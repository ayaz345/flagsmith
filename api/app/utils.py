import pathlib

import shortuuid


def create_hash():
    """Helper function to create a short hash"""
    return shortuuid.uuid()


def get_version_info():
    """Reads the version info baked into src folder of the docker container"""
    return {
        "ci_commit_sha": get_file("./CI_COMMIT_SHA"),
        "image_tag": get_file("./IMAGE_TAG"),
    }


def get_file(file_path):
    """Attempts to read a file from the filesystem and return the contents"""
    if pathlib.Path(file_path).is_file():
        return open(file_path).read().replace("\n", "")

    return "unknown"
