from __future__ import annotations
import os
from multiprocessing.connection import Connection
from pyclbr import Function
from pandas import DataFrame as DF
from .connection_utils import LastpassManager
from .database_utils import check_if_schema_exists
from .file_utils import check_if_file_exists


# Initiate logging
from .log_config import get_logger

log = get_logger(__name__)


def yes_true_else_false(message: str) -> bool:
    """Function to be used in main for default behavior of user input (Y(es) = True, else False)"""
    user_input = input(f"{message} (Y or Yes for 'Yes'): ")

    if user_input.lower() in ("y", "yes", True, "true"):
        user_input = True
    else:
        user_input = False

    return user_input


def enter_for_default(message: str, default: str) -> str:
    """Function to be used in main for default behavior of user input (Enter = default value)"""
    user_input = input(f"{message} (Enter for `{default}`): ")

    if user_input == "":
        user_input = default

    return user_input


def ensure_positive_int(message: str, default: int, zero_behavior) -> int:
    """Function used to ensure user enters a positive integer."""
    while True:
        try:
            input = enter_for_default(message, default)

            input = int(input)
            if input < 0:
                raise AssertionError
            elif input == 0:
                input = zero_behavior
            break
        except KeyboardInterrupt:
            break
        except:
            print("That's not a positive integer. Please try again.")

    return input


def ensure_lastpass_entry_exists(default_entry: str) -> LastpassManager:
    while True:
        try:
            database = enter_for_default(
                "What is the name of the LastPass entry which contains the database credentials?",
                default_entry,
            )
            lpass = LastpassManager(database)

            return lpass
        except KeyboardInterrupt:
            break
        except:
            pass


def ensure_schema_exists(default_schema: str, conn: Connection):
    while True:
        schema = enter_for_default("What is the schema?", default_schema)

        df_tables_in_schema = check_if_schema_exists(schema, conn)
        try:
            if not df_tables_in_schema.empty:
                return schema, df_tables_in_schema
        except:
            pass


def ensure_not_blank(function: Function):
    while True:
        response = function
        if response != "":
            return response


def ensure_file_exists(file_text: str, directory_text: str, default_directory: str):
    while True:
        directory = enter_for_default(directory_text, default_directory)

        # Print all files in directory
        dir_list = os.listdir(directory)
        if len(dir_list) != 0:
            print(f"Here are the files in {directory}:\n")
            for file in sorted(dir_list):
                if file[0] != ".":
                    print(file)
            print("\n")

        filename = input(f"{file_text}: ")
        filepath = check_if_file_exists(directory, filename)

        if filepath:
            return filename, directory, filepath
