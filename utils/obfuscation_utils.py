import json
from multiprocessing.connection import Connection
from black import out
import pandas as pd
import os
import codecs
from dotenv import load_dotenv
from library.log_config import get_logger
from library.database_utils import columns_from_table
from datetime import datetime
import datetime as dt
import random
import math
import ast
import numpy as np

from pandas import DataFrame as DF

# Initiate logging
log = get_logger(__name__)

load_dotenv()
OBFUSCATION_PROFILE_FOLDER_NAME = os.environ.get("OBFUSCATION_PROFILE_FOLDER_NAME")
ROOT_DIR = os.path.dirname(os.path.abspath(OBFUSCATION_PROFILE_FOLDER_NAME))


def read_in_obfuscation_profile(schema: str, base_table_name: str) -> DF:
    """Reads in the obfuscation profile as a csv and returns a dataframe of the data"""
    path = ROOT_DIR + "/" + OBFUSCATION_PROFILE_FOLDER_NAME + "/"
    file = schema + "." + base_table_name + ".csv"

    df_obfuscation_profile = pd.read_csv(path + file)
    log.info(f"Reading in obfuscation profile from {file}; located: {path}")
    return df_obfuscation_profile


def find_fields_to_obfuscate(
    schema: str, base_table_name: str, table: str, conn: Connection
) -> DF:
    """Compares obfuscation profile with fields in table to ensure they line up and returns fields to obfuscate and data types"""
    df_obfuscation_profile = read_in_obfuscation_profile(schema, base_table_name)
    df_table_columns = columns_from_table(schema, table, conn)

    # Try/Except in order to catch if the user doesn't define fields to be unique
    try:
        # Pull out fields that make up a unique entry in order to enforce uniqueness
        unique_df = df_obfuscation_profile.dropna(subset=["enforce_uniqueness"])
        unique_list = list(unique_df["column_name"])
    except:
        unique_list = []

    # Compare inner and outer join to ensure columns match 1:1
    # Inner Join
    df_merged = df_table_columns.merge(
        df_obfuscation_profile, how="inner", on="column_name"
    ).set_index("column_name")
    # Outer Join
    df_merged_outer = df_table_columns.merge(
        df_obfuscation_profile, how="outer", on="column_name"
    ).set_index("column_name")

    # Compare indexes of inner and outer joins directly to determine if there's a mismatch
    idx1 = pd.Index(df_merged_outer.index)
    idx2 = pd.Index(df_merged.index)
    difference = idx1.difference(idx2)
    mismatched_columns = [i for i in difference]
    assert (
        len(mismatched_columns) == 0
    ), f"""The columns in the obfuscation profile do not match the columns in the table.\nMismatched column_name(s) = {mismatched_columns}"""

    # In the obfusction profile, you mush explicitly say "No" if you don't want a field obfuscated
    # Try/Except in order to catch if the user doesn't define fields to be unique
    try:
        df_obfuscate = (
            df_merged[df_merged["obfuscate"].str.lower() != "no"]
            .drop(["obfuscate", "enforce_uniqueness"], axis=1)
            .sort_index(ascending=True)
        )
    except:
        df_obfuscate = (
            df_merged[df_merged["obfuscate"].str.lower() != "no"]
            .drop("obfuscate", axis=1)
            .sort_index(ascending=True)
        )

    # Replace all integer data types (e.g. int8, int4) with just "int"
    df_obfuscate = df_obfuscate.replace(to_replace="^int.*", value="int", regex=True)

    log.info(f"Found the following columns to obfuscate: \n{df_obfuscate}")

    return df_obfuscate, unique_list


def obfuscate_varchar(
    input: str, random_int: int, random_days: int, field_name: str = None
) -> str:
    """
    Scrambles alphanumeric input string to make it unrecognizeable to the input.
    """
    if input is None:
        return None
    else:
        temp = str(input)
        changed_flag = False

        # Some strings are actually lists or dicts. But some strings throw an error.
        try:
            temp_literal = ast.literal_eval(temp)
            actual_type = type(temp_literal)

            if actual_type is list:
                output = obfuscate_list(temp_literal, random_int, random_days)
                changed_flag = True
            elif actual_type is dict:
                output = obfuscate_dict(temp_literal, random_int, random_days)
                changed_flag = True
        except:
            pass

        if not changed_flag:
            try:
                temp = codecs.encode(input, "rot13")
            except:
                # If there are no letters in input, encoder will fail.
                pass

            output = ""

            # For every digit in the string, add a random int and take the modulus to ensure it's single digit
            for c in temp:
                if c.isnumeric():
                    output += str((int(c) + random_int) % 10)
                else:
                    output += c

            # Special treatment for MBI and HICN fields as instructed by Cheryl
            # (https://github.cms.gov/CMS-MAX/synthetic-data/pull/5#discussion_r320900)
            if field_name is not None:
                if "hicn" in field_name:
                    output = output.replace(output[:3], "MAX")
                elif "mbi" in field_name:
                    output = output.replace(output[4:6], "TE")

        return output


def obfuscate_int(input: int, random_int: int, random_days: int) -> int:
    """
    Obfuscate an integer by adding a random integer to evey digit
    """
    if input is None:
        return None
    elif math.isnan(input):
        return input
    else:
        input_str = str(int(input))
        output = obfuscate_varchar(input_str, random_int, random_days)
        return output


def obfuscate_date(input, rand_days: int) -> str:
    """
    Obfuscate a date by adding or subracting a random number of days from it.
    """

    format = "%Y-%m-%d"  # Format = YYYY-MM-DD
    today = datetime.now()

    # We are expecting the type to by pd.datetime. But, if it's in a dictionary, it will be a datetime.date
    # Datetimes and dates can't be compared (no idea why, it seems obvious that they should, but that's the world we live in)
    if type(input) is dt.date:
        today = today.date()
    if input is not None:
        try:
            # Keep dates in the past in the past, and dates in the future in the future.
            if input < today:
                date_out = input - dt.timedelta(days=rand_days)
            else:
                date_out = input + dt.timedelta(days=rand_days)
            date_out = date_out.strftime(format)
            return date_out
        except Exception as e:
            # If the field is NaT, the comparison above will fail.
            pass
    else:
        return input


def obfuscate_super(input: str, random_int: int, random_days: int):
    """Obfuscates a "super" data type from Postgres"""
    try:
        output = find_actual_type_and_obfuscate(input, random_int, random_days)
    except:
        output = input
    return output


def find_actual_datatype(value: str) -> tuple:
    """Determines the underlying datatype (dict, date, etc.) given a string"""
    value_type = type(value)
    if value_type is str:
        try:
            # If it is in a dictionary with a null value, ast.literal_eval will throw an error
            value = ast.literal_eval(value)
            value_type = type(value)
        except:
            try:
                # Try to identify dictionary using json.loads (which handles null values)
                value = json.loads(value)
                value_type = type(value)
            except:
                pass
        # Since datetime isn't a native type, it will still result in a string from literal_eval. So, testing if it can be a datetime too.
        try:
            format = "%Y-%m-%d"
            value = datetime.strptime(value, format).date()
            value_type = type(value)
        except:
            pass

    return value, value_type


def find_actual_type_and_obfuscate(value, random_int, random_days, field_name=None):
    """Determines the actual underlying datatype and obfuscates"""
    value, value_type = find_actual_datatype(value)

    if value_type is int:
        output_value = obfuscate_int(value, random_int, random_days)
    elif value_type is dt.date:
        output_value = obfuscate_date(value, random_days)
    elif value_type is list:
        output_value = obfuscate_list(value, random_int)
    elif value_type is dict:
        output_value = obfuscate_dict(value, random_int, random_days)
    else:
        output_value = obfuscate_varchar(value, random_int, random_days, field_name)

    return output_value


def obfuscate_list(input: list, random_int: int, random_days: int) -> list:
    """Loop through a list and obfuscate every item individually"""
    output = input
    for item, value in enumerate(input):
        output_value = find_actual_type_and_obfuscate(value, random_int, random_days)
        output[item] = output_value

    return output


def obfuscate_dict(input: dict, random_int: int, random_days: int) -> dict:
    """Obfuscate the values in a dictionary without editing the keys"""
    output = input
    for key in output:
        value = output[key]
        output_value = find_actual_type_and_obfuscate(
            value, random_int, random_days, key
        )
        output[key] = output_value

    return output


def compare_before_and_after(
    before_df: DF, after_df: DF, col, num_rows: int = 10
) -> None:
    """Function to show the before and after obfuscation"""
    merged = pd.merge(
        how="left",
        left=before_df[col].head(num_rows),
        right=after_df[col].head(num_rows),
        left_index=True,
        right_index=True,
        suffixes=("_ORIG", "_OBFUSCATED"),
    )
    print("\n", merged, "\n")


def obfuscate_column(df: DF, column: str, dtype: type):
    """Obfuscate a single column of a dataframe"""
    # log.info(f"Obfuscating `{column}`")
    if dtype == "int":
        df[column] = df.apply(
            lambda x: obfuscate_int(x[column], x["rand_int"], x["rand_days"]),
            axis=1,
        )

    elif dtype in ("date", "timestamp"):
        # Convert the column to datetime to make our lives easier during obfuscation
        df[column] = pd.to_datetime(df[column])
        df[column] = df.apply(
            lambda x: obfuscate_date(x[column], x["rand_days"]), axis=1
        )
    elif dtype == "varchar":
        df[column] = df.apply(
            lambda x: obfuscate_varchar(
                x[column], x["rand_int"], x["rand_days"], column
            ),
            axis=1,
        )
    elif dtype == "super":
        df[column] = df.apply(
            lambda x: obfuscate_super(x[column], x["rand_int"], x["rand_days"]),
            axis=1,
        )
        df[column] = df.apply(lambda x: json.dumps(x[column]), axis=1)
    else:
        raise AssertionError(f"Unexpected data type in fields to obfuscate: {dtype}")

    return df[column]


def obfuscate_dataframe(
    query_results: DF, fields_to_obfuscate: DF, show_comparison: bool = True
) -> DF:
    """Takes in a dataframe, compares columns to the obfuscation profile, and obfuscates them if they match"""
    query_cols = query_results.columns
    df_cleaned = query_results.copy()

    # Pass in random values to each row so each row has it's own randomness that is consistent across the row
    df_cleaned["rand_int"] = [random.randint(1, 9) for k in df_cleaned.index]
    df_cleaned["rand_days"] = [random.randint(1, 1000) for k in df_cleaned.index]

    # Loop through every column, and if the column matches the obfuscation profile, scramble the letters/digits
    for col in query_cols:
        if col in fields_to_obfuscate.index:
            dtype = fields_to_obfuscate.loc[col]["dtype"]
            # special_treatment = fields_to_obfuscate.loc[col]["special_treatment"]
            df_cleaned[col] = obfuscate_column(df_cleaned, col, dtype)

            # Show the before and after, if requested
            if show_comparison:
                compare_before_and_after(query_results, df_cleaned, col)

    log.info("Obfuscation Complete!")
    df_cleaned = df_cleaned.drop(["rand_int", "rand_days"], axis=1)

    return df_cleaned
