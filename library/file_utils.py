from __future__ import annotations
import os
import sys
import pandas as pd

dir_path = os.path.dirname(os.path.realpath(__file__))
sys.path.append(dir_path)

import os
from pandas import DataFrame as DF

# Initiate logging
from log_config import get_logger

log = get_logger(__name__)


def results_to_csv(df: DF, csv_name: str, results_folder: str = "./results/") -> None:
    """Store the results to a csc in a defined folder."""
    make_dir_if_not_exists(results_folder)

    file = results_folder + csv_name
    df.to_csv(file, index=False)


def check_if_file_exists(directory, filename):
    """Check if path and file exist"""
    directory = ensure_file_slash(directory)

    if filename_is_blank(filename):
        return False

    file_path = directory + filename

    if os.path.exists(directory):
        if os.path.exists(file_path):
            return file_path
        else:
            log.warning(f"`\n{filename}` does not exist in {directory}.\n")
            return False
    else:
        log.warning(f"\n{directory} does not exist.\n")
        return False


def ensure_file_slash(directory: str):
    if directory != "" and directory[-1] != "/":
        directory = directory + "/"

    return directory


def filename_is_blank(filename: str):
    if filename == "":
        log.error("You entered a blank filename\n")
        return True
    else:
        return False


def make_dir_if_not_exists(folder: str) -> None:
    if not os.path.exists(folder):
        # If folder doesn't exist, create it.
        os.makedirs(folder)


# def csv_to_json(directory:str, csv_filename: str, create_file: bool = False, json_filename:str = None):
#     df =
