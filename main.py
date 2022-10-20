from __future__ import annotations
from library.database_utils import (
    connect_to_db_with_psycopg2,
    find_table_to_query,
    query_into_df,
)
from library.user_input_utils import (
    ensure_lastpass_entry_exists,
    yes_true_else_false,
    enter_for_default,
    ensure_positive_int,
)
from utils.obfuscation_utils import (
    find_fields_to_obfuscate,
    obfuscate_dataframe,
)
from library.file_utils import results_to_csv
from library.log_config import get_logger
from dotenv import load_dotenv
import os
import pandas as pd
import math

# Load environmental file
load_dotenv()
BEDAP_LASTPASS_ENTRY = os.environ.get("BEDAP_LASTPASS_ENTRY")
DEFAULT_CSV_LOCATION = os.environ.get("DEFAULT_CSV_LOCATION")
DEFAULT_SCHEMA = os.environ.get("DEFAULT_SCHEMA")
DEFAULT_TABLE = os.environ.get("DEFAULT_TABLE")


def define_where_clauses(num_clauses: int) -> list[dict]:
    """Function used to define where clauses for the queries. Returns a list of dictionaries."""
    if num_clauses == 0:
        # If there are no clauses, return a dictionary with no no clause and 100%
        return [{"clause": None, "percentage": 100}]

    # Initialize
    clauses = []
    percent_left = 100

    # Loop from 1 to num_clauses and ask for details.
    for i in range(1, num_clauses + 1):
        clause = input(f"\n   Define WHERE clause #{i}: ")
        # If they didn't include "WHERE" in the clause, add it
        # If they didn't write anything, don't add a WHERE clause
        if clause != "" and clause[:6].lower() != "where ":
            clause = "WHERE " + clause

        # If we're not on the last profile, ask for a percentage
        if i != num_clauses:
            while True:
                try:
                    percentage = ensure_positive_int(
                        "\tWhat percentege of your results would you like to fit this profile? (e.g. Enter 20 for 20%)",
                        # Suggest the percentage left over / number of clauses left
                        math.floor(percent_left / (num_clauses + 1 - i)),
                        0,
                    )
                    if percentage >= percent_left:
                        # If the user tries to allocated more than 100%, throw an error.
                        raise AssertionError

                    break
                except:
                    print(
                        f"\tThe value you entered ({percentage}) is greater than the percentage left {percent_left}"
                    )
            percent_left = percent_left - percentage
        else:
            # If we're on the last profile, allocate whatever percentage is left
            percentage = percent_left
            print(f"\t{percentage}% allocated to WHERE clause #{i}\n")

        clause_dict = {"clause": clause, "percentage": percentage}
        clauses.append(clause_dict)

    return clauses


def determine_query_limit(clause_list: list, limit: int):
    """Determine individual query limit from overall limit"""
    limit_left = limit
    for clause_dict in clause_list:
        percentage = float(clause_dict["percentage"]) * 0.01
        clause_limit = round(percentage * limit)
        if clause_limit >= limit_left:
            clause_dict["limit"] = limit_left
        else:
            clause_dict["limit"] = clause_limit
        limit_left = limit_left - clause_limit

    return clause_list


def determine_file_name(table: str, random: bool, number_of_clauses: int, limit: int):
    """Function to determine the default file name"""
    if random is True:
        csv_name = table + "_random_"
    else:
        csv_name = table + "_"

    if number_of_clauses == 1:
        csv_name = csv_name + str(number_of_clauses) + "clause_"
    elif number_of_clauses > 1:
        csv_name = csv_name + str(number_of_clauses) + "clauses_"

    if limit > 0:
        csv_name = csv_name + str(limit) + "limit_obfuscated.csv"
    else:
        csv_name = csv_name + "obfuscated.csv"

    file_name = enter_for_default(
        "What would you like the file to be called?", csv_name
    )

    # If the file name doesn't end in .csv, add it
    if file_name[-4:] != ".csv":
        file_name = file_name + ".csv"

    return file_name


def explanation() -> None:
    print("\nTime to obfuscate your results...")
    print(
        """
===================================================================================================
▒█▀▀█ ▒█▀▀▀ ▒█▀▀▄ ░█▀▀█ ▒█▀▀█ 　 ▒█▀▀▀█ ▒█▀▀█ ▒█▀▀▀ ▒█░▒█ ▒█▀▀▀█ ▒█▀▀█ ░█▀▀█ ▀▀█▀▀ ▒█▀▀▀█ ▒█▀▀█
▒█▀▀▄ ▒█▀▀▀ ▒█░▒█ ▒█▄▄█ ▒█▄▄█ 　 ▒█░░▒█ ▒█▀▀▄ ▒█▀▀▀ ▒█░▒█ ░▀▀▀▄▄ ▒█░░░ ▒█▄▄█ ░▒█░░ ▒█░░▒█ ▒█▄▄▀
▒█▄▄█ ▒█▄▄▄ ▒█▄▄▀ ▒█░▒█ ▒█░░░ 　 ▒█▄▄▄█ ▒█▄▄█ ▒█░░░ ░▀▄▄▀ ▒█▄▄▄█ ▒█▄▄█ ▒█░▒█ ░▒█░░ ▒█▄▄▄█ ▒█░▒█
===================================================================================================

EXPLANATION:

DETERMINING A TABLE TO QUERY
-----------------------------
You are going to need to know the SCHEMA and TABLE you would like to query. If you would like the
most-recent table of a frequently updating series of tables, you only need  to enter the base name
for that table (e.g. beneficiaries' if you want 'beneficiaries_YYYYMMDD') If the table doesn't have
a date appended, or you'd like to query a specific date just enter the  full table name.

FILTERING PROFILES
-------------------
You can filter the table by profiles (i.e. a WHERE clause). You can filter by more than one profile,
and specify how you would like the profiles to be represented in the results (i.e. 20% to profile 1,
30% to profile 2, and 50% to profile 3)

If you would like to filter the results, you will enter the full WHERE clause, one profile at a time.
You will then be prompted to enter the percentage of the total results you would like to be allocated
to that WHERE clause.

LIMIT
-----
The limit you enter will be the total limit, and individual query limits will be determined from this.
So, if you selected 20% to profile 1, 30% to profile 2, and 50% to profile 3 and a limit of 1000,
profile 1 = 200 results, profile 2 = 300 results, and profile 3 = 500 results.

RANDOM
------
You will have the option to return random entries. If you don't randomize, the top results will be returned.
===================================================================================================
"""
    )


if __name__ == "__main__":
    # Initiate logging
    log = get_logger(__name__)

    explanation()
    schema = enter_for_default("What is the schema?", DEFAULT_SCHEMA)

    base_table_name = enter_for_default(
        "What is the table (or base table) name?", DEFAULT_TABLE
    )

    # Connect to Db
    lpass_manager = ensure_lastpass_entry_exists(BEDAP_LASTPASS_ENTRY)
    conn = connect_to_db_with_psycopg2(lpass_manager)

    # SELECT * FROM schema.table
    table = find_table_to_query(schema, base_table_name, conn)

    # WHERE
    number_of_clauses = ensure_positive_int(
        "\nHow many different profiles are you going to want to implement?", 0, 0
    )
    where_clause_list = define_where_clauses(number_of_clauses)

    # LIMIT
    total_limit = ensure_positive_int(
        "Enter the total number of results you'd like returned (0 = No limit;",
        10,
        False,
    )
    # Determine limit of each query individually
    where_clause_list = determine_query_limit(where_clause_list, total_limit)

    # Randomize results
    random = yes_true_else_false("Would you like the results randomized?")

    # Preview Obfuscation?
    show_obfuscation = yes_true_else_false(
        "Would you like a preview of the obfuscation?"
    )

    # Define where to save restults
    results_location = enter_for_default(
        "Where would you like the results saved?", DEFAULT_CSV_LOCATION
    )
    file_name = determine_file_name(table, random, number_of_clauses, total_limit)

    # Lookup obfuscation profile
    fields_to_obfuscate, unique_field_list = find_fields_to_obfuscate(
        schema, base_table_name, table, conn
    )

    # Loop through all the profiles and perform queries.
    for clause_dict in where_clause_list:
        clause = clause_dict["clause"]
        limit = clause_dict["limit"]
        query_results = query_into_df(
            schema, table, conn, clause, limit=limit, random=random
        )

        try:
            df_obfuscated = pd.concat(
                [
                    df_obfuscated,
                    obfuscate_dataframe(
                        query_results,
                        fields_to_obfuscate,
                        show_comparison=show_obfuscation,
                    ),
                ],
            )
        except:
            df_obfuscated = obfuscate_dataframe(
                query_results, fields_to_obfuscate, show_comparison=show_obfuscation
            )

    # Enforce uniqueness based on pre-defined unique columns
    if unique_field_list:
        df_obfuscated = df_obfuscated.drop_duplicates(subset=unique_field_list)

    # Save results to a CSV
    results_to_csv(df_obfuscated, file_name, results_folder=results_location)
    log.info(f"Results saved to `{results_location}{file_name}`")
