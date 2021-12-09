import warnings
from typing import List, Optional, Union

from airflow.hooks.postgres_hook import PostgresHook
from airflow.exceptions import AirflowException
from airflow.models import BaseOperator
from airflow.providers.amazon.aws.hooks.s3 import S3Hook
from airflow.providers.postgres.hooks.postgres import PostgresHook

import pandas as pd
import io
import os.path
import numpy as np

AVAILABLE_METHODS = ['APPEND', 'REPLACE', 'UPSERT']


class S3ToPostgresOperator(BaseOperator):
    """
    Executes a COPY command to load files from s3 to Postgres

    Args:
        schema: str
            reference to a specific schema in redshift database.
        table: str
            reference to a specific table in redshift database.
        s3_bucket: str
            reference to a specific S3 bucket.
        s3_key: str
            reference to a specific S3 key
        postgres_conn_id: str
            reference to a specific redshift database
        aws_conn_id: str
            reference to a specific S3 connection
            If the AWS connection contains 'aws_iam_role' in ``extras``
            the operator will use AWS STS credentials with a token
            https://docs.aws.amazon.com/redshift/latest/dg/
            copy-parameters-authorization.html#copy-credentials
        verify: bool or str
            Whether or not to verify SSL certificates for S3 connection.
            By default SSL certificates are verified.
            You can provide the following values:

            - ``False``: do not validate SSL certificates. SSL will still be
                         used (unless use_ssl is False), but SSL certificates
                         will not be verified.
            - ``path/to/cert/bundle.pem``: A filename of the CA cert bundle to
                    uses. You can specify this argument if you want to use a
                    different CA cert bundle than the one used by botocore.
    column_list: list of str
        list of column names to load
    copy_options: list
        reference to a list of COPY options
    method: str
        Action to be performed on execution.
        Available ``APPEND``, ``UPSERT`` and ``REPLACE``.
    upsert_keys: list of str
        List of fields to use as key on upsert action
    """
    template_fields = ('s3_bucket', 's3_key', 'schema', 'table', 'column_list',
                       'copy_options')
    template_ext = ()
    ui_color = '#99e699'

    def __init__(
        self,
        *,
        schema: str,
        table: str,
        s3_bucket=None,
        s3_key: str,
        postgres_conn_id: str = 'postgres_default',
        aws_conn_id: str = 'aws_default',
        verify=None,
        wildcard_match=False,
        column_list: Optional[List[str]] = None,
        copy_options: Optional[List] = None,
        autocommit: bool = False,
        method: str = 'APPEND',
        upsert_keys: Optional[List[str]] = None,
        **kwargs,
    ) -> None:

        if 'truncate_table' in kwargs:
            warnings.warn(
                """`truncate_table` is deprecated. 
                Please use `REPLACE` method.""",
                DeprecationWarning,
                stacklevel=2,
            )
            if kwargs['truncate_table']:
                method = 'REPLACE'
            kwargs.pop('truncate_table', None)

        super().__init__(**kwargs)
        self.schema = schema
        self.table = table
        self.s3_bucket = s3_bucket
        self.s3_key = s3_key
        self.postgres_conn_id = postgres_conn_id
        self.aws_conn_id = aws_conn_id
        self.verify = verify
        self.wildcard_match = wildcard_match
        self.column_list = column_list
        self.copy_options = copy_options or []
        self.autocommit = autocommit
        self.method = method
        self.upsert_keys = upsert_keys

        # attributes that get their values during execution
        self.pg_hook = None
        self.s3 = None
        self.current_table = None

        if self.method not in AVAILABLE_METHODS:
            raise AirflowException(f'Method not found! Available methods: '
                                   f'{AVAILABLE_METHODS}')

    def execute(self, context) -> None:
        """
        The code to execute when the runner calls the operator.

        Contains the methods to read a file from an S3 bucket into a Postgres
         table.

        Args:
            context
                Context of dags.custom_modules.s3_to_postgres.
                S3ToPostgresOperator.execute
        Returns:
            None
        """
        # get raw layer unique bucket name in XCom
        task_instance = context['task_instance']
        value = task_instance.xcom_pull(task_ids="get_s3_bucket_names")
        self.s3_bucket = value["raw"]
        
        s3_key_bucket = self.pg_s3_input(context)
        df_products, list_content = self.s3_object_to_df(s3_key_bucket)
        self.create_db_table(df_products)
        self.print_table()

    def pg_s3_input(self, context):
        """
        Method to read in both the Postgres and S3 hook objects.

        Checks wildcard key and raises exception if there are no matches or it
         does not exist.

        Returns:
            s3_key_bucket: boto3.s3.Object
                Object matching the wildcard expression

        Typical usage example:

        self.pg_s3_input()
        """
        self.log.info('Starting execution')
        self.pg_hook = PostgresHook(postgres_conn_id=self.postgres_conn_id)
        self.s3 = S3Hook(aws_conn_id=self.aws_conn_id, verify=self.verify)

        self.log.info("Downloading S3 file: {0}".format(self.s3))

        s3_key_bucket = None
        if self.wildcard_match:
            if self.s3.check_for_wildcard_key(self.s3_key, self.s3_bucket):
                raise AirflowException('No key matches', self.s3_key)
            s3_key_bucket = self.s3.get_wildcard_key(self.s3_key,
                                                     self.s3_bucket)
        else:
            if not self.s3.check_for_key(self.s3_key, self.s3_bucket):
                raise AirflowException("The key {0} does not exist".
                                       format(self.s3_key))
            s3_key_bucket = self.s3.get_key(self.s3_key,
                                            self.s3_bucket)

        return s3_key_bucket

    def s3_object_to_df(self, s3_key_bucket):
        """
        Converts s3 file into a string and dataframe.

        Prints the dataframe as a log in airflow.

        Args:
            s3_key_bucket
                Context of dags.custom_modules.s3_to_postgres.
                S3ToPostgresOperator.execute
        Returns:
            df_products: df
                S3 bucket file as a pandas dataframe.
            list_content: str
                S3 file as a single string.
        """
        self.log.info("s3_key_bucket: {0}".format(s3_key_bucket))

        list_content = s3_key_bucket.get()['Body'].read() \
            .decode(encoding='utf-8', errors='ignore')

        schema = {
            'InvoiceNo': str,
            'StockCode': str,
            'Description': str,
            'Quantity': int,
            'InvoiceDate': str,
            'UnitPrice': 'float64',
            'CustomerID': 'float64',
            'Country': str
        }

        df_products = pd.read_csv(io.StringIO(list_content),
                                  header=0,
                                  delimiter=',',
                                  low_memory=False,
                                  dtype=schema)

        self.log.info("df: {0}".format(df_products))
        df_products.replace(np.nan, None, inplace=True)
        return df_products, list_content

    def create_db_table(self, df_products):
        """
        Based on a .sql file it creates the table in the given database.

        Args:
            df_products: str
                S3 file as a single string.
        Returns:
            None
        """
        file_path = 'dags/repo/debootcamp.products.sql'

        self.log.info("all content: {0}".format(os.listdir()))

        with open(file_path, "r", encoding="UTF-8") as sql_file:
            sql_create_table_cmd = sql_file.read()
            sql_file.close()

            self.log.info("{0}".format(sql_create_table_cmd))

        self.pg_hook.run(sql_create_table_cmd)

        target_fields = ['InvoiceNo', 'StockCode', 'Description', 'Quantity',
                         'InvoiceDate', 'UnitPrice', 'CustomerID', 'Country']

        self.current_table = self.schema + '.' + self.table
        df_row_list = [tuple(x) for x in df_products.to_numpy()]

        # check table exist
        try:
            self.pg_hook.insert_rows(self.current_table, df_row_list,
                                     target_fields=target_fields,
                                     commit_every=1000,
                                     replace=True)
        except:
            self.pg_hook.insert_rows(self.current_table, df_row_list,
                                     target_fields=target_fields,
                                     commit_every=1000,
                                     replace=False)

    def print_table(self):
        """
        Sends table row values to airflow logs.

        Creates connection to db and executes query to get the complete table
         created in past methods.

        Returns:
            None
        """
        request = "SELECT * FROM " + "debootcamp.products" + \
                  " WHERE InvoiceNo = '536367' LIMIT 3"
        connection = self.pg_hook.get_conn()
        cursor = connection.cursor()
        cursor.execute(request)
        source = cursor.fetchall()

        self.log.info("{0}".format(source[0]))
        for row in source:
            self.log.info("InvoiceNo: {0} - \
                          StockCode: {1} - \
                          Description: {2} - \
                          Quantity: {3} - \
                          InvoiceDate: {4} - \
                          UnitPrice: {5} - \
                          CustomerID: {6} - \
                          Country: {7} ".
                          format(row[0], row[1], row[2], row[3],
                                 row[4], row[5], row[6], row[7]))
