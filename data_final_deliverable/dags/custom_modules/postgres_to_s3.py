import warnings
from typing import List, Optional, Union

from airflow.hooks.postgres_hook import PostgresHook
from airflow.exceptions import AirflowException
from airflow.models import BaseOperator
from airflow.providers.amazon.aws.hooks.s3 import S3Hook
from airflow.providers.amazon.aws.utils.redshift import build_credentials_block
from airflow.providers.postgres.hooks.postgres import PostgresHook

import pandas as pd

AVAILABLE_METHODS = ['APPEND', 'REPLACE', 'UPSERT']


class PostgresToS3Operator(BaseOperator):
    """
    Executes a COPY command to load a file from Postgres to S3

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
        s3_bucket: str,
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
        # get staging layer unique bucket name in XCom
        task_instance = context['task_instance']
        value = task_instance.xcom_pull(task_ids="get_s3_bucket_names")
        self.s3_bucket = value["staging"]
        self.log.info("bucket name: {0}".format(value))

        df = self.pg_to_pandas(context)
        self.df_object_to_s3(df)

    def pg_to_pandas(self, context):
        """
        Method to read a table from postgres to convert it into a pandas
         dataframe.

        Args:
            context
                Context of dags.custom_modules.s3_to_postgres.
                S3ToPostgresOperator.execute

        Returns:
            df: pandas dataframe
              Dataframe with user_reviews table from postgres.
        """
        self.log.info('Starting execution')
        self.pg_hook = PostgresHook(postgres_conn_id=self.postgres_conn_id)
        self.s3 = S3Hook(aws_conn_id=self.aws_conn_id, verify=self.verify)

        self.log.info("Downloading Postgres table: {0}".format(self.s3))
        self.current_table = self.schema + '.' + self.table
        request = "SELECT * FROM " + self.current_table
        connection = self.pg_hook.get_conn()
        cursor = connection.cursor()
        cursor.execute(request)
        source = cursor.fetchall()
        
        request_cols = "SELECT * FROM information_schema.columns " \
                       "WHERE table_schema = 'debootcamp' " \
                       "AND table_name = 'products';"
        cursor.execute(request_cols)
        cols = cursor.fetchall()
        cols = [k[3] for k in cols]
        self.log.info("columns: {0}".format(cols))

        df = pd.DataFrame(source, columns=cols)
        self.log.info("df: {0}".format(df))
        return df

    def df_object_to_s3(self, df):
        """
        Inserts dataframe to S3 as a csv file.

        Args:
            df: pandas dataframe
              Dataframe with user_reviews table from postgres.
        Returns:
            None
        """
        self.log.info("loading file... {0}".format(df))
        self.s3.load_string(string_data=df.to_csv(index=False),
                            key="user_purchase.csv",
                            bucket_name=self.s3_bucket,
                            replace=True)
