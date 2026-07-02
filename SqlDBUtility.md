# SqlDBUtility

`SqlDBUtility` is a small Python helper class for working with SQL Server through `pyodbc`. It can use **multiple connection strings** so different tools, modules, or environments can point to different databases without changing the class itself.

---

## Features

- Supports more than one named connection.
- Loads connection values from environment variables.
- Executes stored procedures that return rows.
- Executes raw `SELECT` queries.
- Executes non-query stored procedures for insert, update, and delete operations.
- Returns results as a list of dictionaries.

---

## Environment setup

The class reads configuration from a `.env` file. You can define one default connection string or multiple named connection strings.

### Option 1: Single default connection

```env
DB_CONNECTION_STRING=Driver={ODBC Driver 17 for SQL Server};Server=localhost;Database=MyDb;UID=myuser;PWD=mypassword;Encrypt=no;TrustServerCertificate=yes;
```

### Option 2: Multiple named connections

Use a separate variable for each tool or purpose:

```env
DB_CONNECTION_STRING_MAIN=Driver={ODBC Driver 17 for SQL Server};Server=localhost;Database=MainDb;UID=user1;PWD=pass1;Encrypt=no;TrustServerCertificate=yes;
DB_CONNECTION_STRING_REPORTING=Driver={ODBC Driver 17 for SQL Server};Server=localhost;Database=ReportsDb;UID=user2;PWD=pass2;Encrypt=no;TrustServerCertificate=yes;
DB_CONNECTION_STRING_AUDIT=Driver={ODBC Driver 17 for SQL Server};Server=localhost;Database=AuditDb;UID=user3;PWD=pass3;Encrypt=no;TrustServerCertificate=yes;
```

The class can select the correct connection string by name, such as `main`, `reporting`, or `audit`.

---

## Updated class

```python
import pyodbc
import os
from typing import Optional, Union
from dotenv import load_dotenv
from decimal import Decimal

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
        driver = os.getenv(f"DB_DRIVER_{key}") or os.getenv("DB_DRIVER", "ODBC Driver 17 for SQL Server")

        if not all([server, database, username, password]):
            raise ValueError(
                f"Missing DB connection values for '{connection_key}'. "
                f"Provide DB_CONNECTION_STRING_{key} or DB_SERVER_{key}, DB_DATABASE_{key}, DB_USERNAME_{key}, DB_PASSWORD_{key}."
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
```

---

## How multiple connections work

Pass a `connection_key` when creating the class instance.

### Example

```python
db_main = SqlDBUtility("main")
db_reporting = SqlDBUtility("reporting")
db_audit = SqlDBUtility("audit")
```

Each instance looks for its own connection string first:

- `DB_CONNECTION_STRING_MAIN`
- `DB_CONNECTION_STRING_REPORTING`
- `DB_CONNECTION_STRING_AUDIT`

If a named full connection string is not found, the class falls back to named values such as:

- `DB_SERVER_MAIN`
- `DB_DATABASE_MAIN`
- `DB_USERNAME_MAIN`
- `DB_PASSWORD_MAIN`

and similarly for other keys.

---

## Reading data

Use `execute_procedure()` for stored procedures and `execute_query()` for raw SQL queries.

### Stored procedure example

```python
rows = db_main.execute_procedure("dbo.GetMembers")
```

### Query example

```python
rows = db_reporting.execute_query(
    "SELECT * FROM Flats WHERE SocietyId = ?",
    params=[5]
)
```

Both methods return a list of dictionaries.

---

## Writing data

Use `execute_non_query()` for stored procedures that modify data.

```python
count = db_audit.execute_non_query(
    "dbo.LogActivity",
    params={"@UserId": 101, "@Action": "Login"}
)
```

The method returns the number of rows affected.

---

## Example usage

```python
from your_module import SqlDBUtility

main_db = SqlDBUtility("main")
reporting_db = SqlDBUtility("reporting")

members = main_db.execute_procedure("dbo.GetAllMembers")
summary = reporting_db.execute_query(
    "SELECT TOP 10 * FROM MemberSummary WHERE Status = ?",
    params=["Active"]
)
```

This pattern is useful when different tools or features in the same application need different databases.

---

## Notes

- Keep credentials in `.env` and out of source control.
- Avoid printing connection strings in production.
- Use clear names like `main`, `reporting`, `audit`, or `admin` for connection keys.
- Use parameterized SQL to avoid injection issues.

---

## Summary

`SqlDBUtility` now supports multiple connection strings, making it easier to use the same class across different tools or database contexts. Each instance can point to a different SQL Server connection without changing the calling code.
