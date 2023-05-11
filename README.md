# DBastard
A lightweight tool to read and mange a DB. Operates DDL queries in terminal. Outputs SELECT queries to XLS.  
Well-supports django-created or sqlalchemy databases.  

Edit the config.py to set up details for the database to work with. Alternatively, use flags to run the app with specific arguments.  
Supports the following flags:
```
'-db', '--database' for database name'
'-p', '--password' for database password'
'-u', '--user' for 'database user'
```
The use of arguments overrides the settings from config.py for a single run.  

List of supported commands:
```
 "show tables" - display the available tables
 "create table" - create a new table
 "drop table" - remove an existing table
 "alter table" - change an existing table
 "execute script" - run SQL script from a file
 "show records" - display records from a specific table. Operates with a table name (to view all records) / SELECT queries for custom selections.
 "quit" - leave the program
```

Known issues:  
 - May misbehave with user-created tables named 'user' in sqlalchemy databases.  
