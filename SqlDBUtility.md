# SqlDBUtility

`SqlDBUtility` is a small Python helper class for working with SQL Server through `pyodbc`. It supports three common database operations:

- Executing stored procedures that return rows.
- Executing raw `SELECT` queries.
- Executing stored procedures that modify data and do not return rows.

The class reads database settings from environment variables loaded through a `.env` file, which keeps credentials out of source code. [web:1][page:1]

---

## Features

- Connects to SQL Server using `pyodbc`.
- Supports both **stored procedures** and **raw SQL queries**.
- Accepts parameters as lists, tuples, or dictionaries.
- Returns query results as a list of dictionaries.
- Converts `Decimal` values to formatted strings with 2 decimal places before returning data. [page:1][web:2]

---

## Requirements

Install the required Python packages:

```bash
pip install pyodbc python-dotenv
```

You also need:

- A reachable SQL Server instance.
- A valid ODBC driver installed on the machine.
- A `.env` file containing connection details. [web:1]

---

## Environment setup

The class loads environment variables from:

```python
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../dlr/mcp/.env"))
```

This means the `.env` file should exist at the path relative to the Python file where this class is stored.

### Option 1: Use a full connection string

If `DB_CONNECTION_STRING` is present, the class uses it directly:

```env
DB_CONNECTION_STRING=Driver={ODBC Driver 17 for SQL Server};Server=localhost;Database=MyDb;UID=myuser;PWD=mypassword;Encrypt=no;TrustServerCertificate=yes;
```

### Option 2: Use separate values

If `DB_CONNECTION_STRING` is not provided, the class builds the connection string from these variables:

```env
DB_SERVER=localhost
DB_DATABASE=MyDb
DB_USERNAME=myuser
DB_PASSWORD=mypassword
DB_DRIVER=ODBC Driver 17 for SQL Server
```

If `DB_DRIVER` is not set, the default driver is `ODBC Driver 17 for SQL Server`. [web:1][page:1]

---

## Class overview

```python
class SqlDBUtility:
    """
    Generic SQL Server utility to execute stored procedures and raw queries.
    Reads connection details from .env file.
    """
```

The class is designed to be simple to use in application services, repositories, background jobs, or scripts that need SQL Server access.

---

## Creating an instance

```python
db = SqlDBUtility()
```

When the object is created:

1. It loads the connection string from environment variables.
2. It prepares the internal SQL Server connection string.
3. It prints the connection string in the current implementation.

> Note: Printing the connection string may expose sensitive data in logs. In production, it is better to remove this `print()` statement.

---

## Reading data with stored procedures

Use `execute_procedure()` when you want to call a SQL Server stored procedure and read the results.

### Syntax

```python
results = db.execute_procedure(
    procedure_name="dbo.GetMembers",
    params=None,
    fetch_all=True
)
```

### Parameters

- `procedure_name`: Stored procedure name, such as `dbo.GetMembers`.
- `params`: Optional parameters as:
  - a list or tuple for positional parameters,
  - a dictionary for named parameters,
  - or `None` if the procedure has no parameters.
- `fetch_all`:
  - `True` returns all rows.
  - `False` returns only the first row. [page:1]

### Example: no parameters

```python
members = db.execute_procedure("dbo.GetAllMembers")
```

### Example: positional parameters

```python
member = db.execute_procedure("dbo.GetMemberById", params=, fetch_all=False)
```

### Example: named parameters

```python
active_members = db.execute_procedure(
    "dbo.GetMemberByStatus",
    params={"@Status": "Active", "@SocietyId": 5}
)
```

### Returned format

The result is always a list of dictionaries:

```python
[
    {"MemberId": 101, "Name": "Amit", "Status": "Active"},
    {"MemberId": 102, "Name": "Ravi", "Status": "Active"}
]
```

If `fetch_all=False`, the return value is still a list, but it contains at most one dictionary.

---

## Reading data with raw queries

Use `execute_query()` for plain `SELECT` statements.

### Syntax

```python
rows = db.execute_query(
    query="SELECT * FROM Flats WHERE SocietyId = ?",
    params=[2]
)
```

### Example: one parameter

```python
flats = db.execute_query(
    "SELECT FlatId, FlatNo, OwnerName FROM Flats WHERE SocietyId = ?",
    params=[2]
)
```

### Example: multiple parameters

```python
members = db.execute_query(
    "SELECT MemberId, Name FROM Members WHERE Status = ? AND Wing = ?",
    params=["Active", "A"]
)
```

### Important note

- Use `?` placeholders for query parameters.
- Pass parameter values as a list or tuple.
- This is safer than concatenating SQL strings manually.

---

## Writing data with non-query procedures

Use `execute_non_query()` when the stored procedure inserts, updates, or deletes data and does not need to return rows.

### Syntax

```python
count = db.execute_non_query(
    procedure_name="dbo.UpdateMemberStatus",
    params={"@MemberId": 101, "@Status": "Inactive"}
)
```

### Example

```python
affected_rows = db.execute_non_query(
    "dbo.DeleteMember",
    params=
)
```

### Return value

The method returns `cursor.rowcount`, which represents the number of rows affected.

### Transaction behavior

The method calls `conn.commit()` after execution, so changes are saved automatically.

---

## How parameter handling works

The class accepts parameters in a flexible way:

### Dictionary parameters

Used for named SQL parameters:

```python
{"@Status": "Active", "@SocietyId": 5}
```

This becomes:

```sql
EXEC dbo.GetMemberByStatus @Status=?, @SocietyId=?
```

### List or tuple parameters

Used for positional parameters:

```python
[101, "Active"]
```

This becomes:

```sql
{CALL dbo.SomeProcedure (?, ?)}
```

### No parameters

If no parameters are supplied, the procedure is called directly.

---

## Parameter sanitization

Before execution, the class runs `_sanitize_params()`.

This method converts numeric strings into integers:

```python
"101" -> 101
```

This happens for both:

- dictionaries, and
- lists or tuples.

This is useful when values arrive from form inputs, JSON payloads, or URL query strings as text.

---

## Result conversion

The `_fetch_results()` method converts query results into a Python-friendly format.

### Behavior

- If a column value is a `Decimal`, it is converted to a string with 2 decimal places.
- All other values are returned as-is.
- If the query returns no columns, an empty list is returned.

### Example

A SQL value like:

```python
Decimal("1234.5")
```

may be returned as:

```python
"1234.50"
```

This helps when sending data to JSON APIs or UI layers that expect consistent string formatting for currency or numeric display. [web:2][page:1]

---

## Example usage in an application

```python
from your_module import SqlDBUtility

db = SqlDBUtility()

# Get one record
member = db.execute_procedure(
    "dbo.GetMemberById",
    params=,
    fetch_all=False
)

# Get many records
flats = db.execute_query(
    "SELECT FlatId, FlatNo FROM Flats WHERE SocietyId = ?",
    params=[2]
)

# Update data
updated = db.execute_non_query(
    "dbo.UpdateMemberStatus",
    params={"@MemberId": 101, "@Status": "Inactive"}
)

print(member)
print(flats)
print(updated)
```

---

## Typical workflow

1. Create and configure your `.env` file.
2. Import `SqlDBUtility`.
3. Instantiate the class.
4. Call `execute_procedure()` for stored procedures that return rows.
5. Call `execute_query()` for raw `SELECT` queries.
6. Call `execute_non_query()` for insert/update/delete procedures.

---

## Error considerations

The current class does not include custom error handling. In real applications, you may want to add:

- try/except blocks,
- logging,
- connection retry logic,
- validation for procedure names and SQL queries.

You should also avoid printing the full connection string, because it may contain credentials.

---

## Best practices

- Keep database credentials in `.env`, not in code.
- Use parameterized queries instead of string concatenation.
- Use stored procedures for reusable database logic.
- Remove or replace `print(self._connection_string)` in production.
- Return `Decimal` values in a format that matches your API or UI needs. [web:1][web:2]

---

## Quick examples

### Read a single record

```python
row = db.execute_procedure("dbo.GetMemberById", params=, fetch_all=False)
```

### Read multiple records

```python
rows = db.execute_query("SELECT * FROM Members WHERE Status = ?", params=["Active"])
```

### Update data

```python
count = db.execute_non_query("dbo.UpdateMemberStatus", params={"@MemberId": 101, "@Status": "Inactive"})
```

---

## Summary

`SqlDBUtility` provides a small and practical wrapper around `pyodbc` for SQL Server access. It simplifies reading configuration from `.env`, executing stored procedures and raw queries, and returning results in a dictionary-based structure that is easy to use in application code. [page:1][web:1]