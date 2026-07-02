import os
from decimal import Decimal
from typing import Optional, Union

import pyodbc
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../dlr/mcp/.env"))


class SqlDBUtility:
    """
    Generic SQL Server utility to execute stored procedures and raw queries.
    Supports multiple named connection strings from .env.
    """

    def __init__(self, connection_key: str = "default"):
        self.connection_key = connection_key
        self._connection_string = self._build_connection_string(connection_key)

    def _build_connection_string(self, connection_key: str) -> str:
        key = (connection_key or "default").strip().upper()

        if key == "DEFAULT":
            conn_str = os.getenv("DB_CONNECTION_STRING")
            if conn_str:
                return conn_str

        named_conn_var = f"DB_CONNECTION_STRING_{key}"
        conn_str = os.getenv(named_conn_var)
        if conn_str:
            return conn_str

        server = os.getenv(f"DB_SERVER_{key}") or os.getenv("DB_SERVER")
        database = os.getenv(f"DB_DATABASE_{key}") or os.getenv("DB_DATABASE")
        username = os.getenv(f"DB_USERNAME_{key}") or os.getenv("DB_USERNAME")
        password = os.getenv(f"DB_PASSWORD_{key}") or os.getenv("DB_PASSWORD")
        driver = (
            os.getenv(f"DB_DRIVER_{key}")
            or os.getenv("DB_DRIVER", "ODBC Driver 17 for SQL Server")
        )

        if not all([server, database, username, password]):
            raise ValueError(
                f"Missing DB connection values for '{connection_key}'. "
                f"Provide DB_CONNECTION_STRING_{key} or DB_SERVER_{key}, "
                f"DB_DATABASE_{key}, DB_USERNAME_{key}, DB_PASSWORD_{key}."
            )

        return (
            f"Driver={{{driver}}};"
            f"Server={server};"
            f"Database={database};"
            f"UID={username};"
            f"PWD={password};"
            f"Encrypt=no;"
            f"TrustServerCertificate=yes;"
        )

    def _get_connection(self) -> pyodbc.Connection:
        return pyodbc.connect(self._connection_string)

    def execute_procedure(
        self,
        procedure_name: str,
        params: Optional[Union[list, tuple, dict]] = None,
        fetch_all: bool = True,
    ) -> list[dict]:
        params = self._sanitize_params(params)
        with self._get_connection() as conn:
            cursor = conn.cursor()

            if params is None:
                cursor.execute(f"{{CALL {procedure_name}}}")
            elif isinstance(params, dict):
                named = ", ".join(f"{k}=?" for k in params.keys())
                cursor.execute(f"EXEC {procedure_name} {named}", list(params.values()))
            else:
                placeholders = ", ".join("?" * len(params))
                cursor.execute(f"{{CALL {procedure_name} ({placeholders})}}", list(params))

            return self._fetch_results(cursor, fetch_all)

    def execute_query(
        self,
        query: str,
        params: Optional[Union[list, tuple]] = None,
        fetch_all: bool = True,
    ) -> list[dict]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if params:
                cursor.execute(query, list(params))
            else:
                cursor.execute(query)
            return self._fetch_results(cursor, fetch_all)

    def execute_non_query(
        self,
        procedure_name: str,
        params: Optional[Union[list, tuple, dict]] = None,
    ) -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()

            if params is None:
                cursor.execute(f"{{CALL {procedure_name}}}")
            elif isinstance(params, dict):
                named = ", ".join(f"{k}=?" for k in params.keys())
                cursor.execute(f"EXEC {procedure_name} {named}", list(params.values()))
            else:
                placeholders = ", ".join("?" * len(params))
                cursor.execute(f"{{CALL {procedure_name} ({placeholders})}}", list(params))

            conn.commit()
            return cursor.rowcount

    @staticmethod
    def _fetch_results(cursor: pyodbc.Cursor, fetch_all: bool) -> list[dict]:
        if cursor.description is None:
            return []

        columns = [col[0] for col in cursor.description]

        def convert_row(row):
            return {
                col: f"{float(val):.2f}" if isinstance(val, Decimal) else val
                for col, val in zip(columns, row)
            }

        if fetch_all:
            return [convert_row(row) for row in cursor.fetchall()]

        row = cursor.fetchone()
        return [convert_row(row)] if row else []

    def _sanitize_params(self, params):
        if isinstance(params, dict):
            return {
                k: int(v) if isinstance(v, str) and v.isdigit() else v
                for k, v in params.items()
            }
        elif isinstance(params, (list, tuple)):
            return [int(v) if isinstance(v, str) and v.isdigit() else v for v in params]
        return params
