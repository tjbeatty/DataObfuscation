import os
import sys

dir_path = os.path.dirname(os.path.realpath(__file__))
sys.path.append(dir_path)

"""Utilities for common database access tasks.
"""
import subprocess
import psycopg2
import sqlalchemy
import os
import boto3
from dotenv import load_dotenv
from dataclasses import dataclass
from sqlalchemy.engine import Connection
from command_line_utils import bash_cmd

# Initiate logging
from log_config import get_logger

log = get_logger(__name__)

# Load environmental file
load_dotenv()
LASTPASS_USERNAME = os.environ.get("LASTPASS_USERNAME")


@dataclass
class LastpassManager:
    """Class for creating a database engine with Lastpass."""

    lpass_entry: str
    driver: str = "psycopg2"
    dialect: str = "postgresql"

    def __post_init__(self) -> None:
        self._authenticate()

        try:
            self.db_type = self._lpass_cred("--field Type")
            self.database = self._lpass_cred("--field Database")
            self.user = self._lpass_cred("--username")
            self.password = self._lpass_cred("--password")
            self.host = self._lpass_cred("--field Hostname")
            self.port = self._lpass_cred("--field Port")

            if self.driver is not None:
                self.engine_str = f"{self.dialect}+{self.driver}://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"
            else:
                self.engine_str = f"{self.dialect}://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"
        except:
            log.warning(f"'{self.lpass_entry}' Last Pass entry does not exist.")
            raise AssertionError

    def _authenticate(self):
        try:
            bash_cmd("lpass status")
        except subprocess.CalledProcessError:
            lpass_login = LASTPASS_USERNAME
            bash_cmd(f"lpass login {lpass_login}")

    def _lpass_cred(self, args: str) -> str:
        """Fetch a single credential from the lastpass CLI.

        Args:
            entry (str): Lastpass entry to request.
            args (str): Flags to pass to the CLI.

        Returns:
            str: Requested Lastpass credential.
        """
        result = bash_cmd(f"lpass show '{self.lpass_entry}' {args}")
        return result

    def create_psycopg2_connection(
        self,
    ) -> Connection:
        """Build a database connection with credentials from Lastpass.

        Args:
            cred_key (str): Lastpass entry to request.
            dbname (str): name of the database connection to use.

        Returns:
            Database connection.

        """

        return psycopg2.connect(
            host=self.host,
            database=self.database,
            port=int(self.port),
            user=self.user.lower(),
            password=self.password,
        )

    def create_sqlalchemy_connection(
        self,
    ) -> Connection:
        """Build a database connection with credentials from Lastpass.

        Args:
            cred_key (str): Lastpass entry to request.
            dbname (str): name of the database connection to use.

        Returns:
            Database connection.

        """

        return sqlalchemy.create_engine(self.engine_str).connect()


def connect_to_aws_service(aws_account_id: str, aws_role_name: str, service="s3"):
    log.info(f"Fetching boto3 client...")

    role = f"arn:aws:iam::{aws_account_id}:role/{aws_role_name}"

    sts = boto3.client(service_name="sts")

    log.info(f"Assuming AWS Role: {role}")
    assumed_role = sts.assume_role(RoleArn=role, RoleSessionName="AssumeRoleSession1")
    log.info(f"Role assumption complete...")

    credentials = assumed_role["Credentials"]

    # Use the temporary credentials that AssumeRole returns to make a connection to Amazon S3
    s3_resource = boto3.resource(
        service,
        aws_access_key_id=credentials["AccessKeyId"],
        aws_secret_access_key=credentials["SecretAccessKey"],
        aws_session_token=credentials["SessionToken"],
    )
    log.info("Connected to s3...")
    return s3_resource
