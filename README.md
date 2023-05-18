# DBastard

### Description
A lightweight tool to read and manage a DB. Operates DDL queries in terminal. Outputs SELECT queries to XLS.  
Well-supports django-created or sqlalchemy databases.  

### Set up
Edit the config.py to set up details for the database to work with. Alternatively, use flags to run the app with specific arguments.  
Supports the following flags:
```
'-db', '--database' for database name'
'-p', '--password' for database password'
'-u', '--user' for 'database user'
```
The use of arguments overrides the settings from config.py for a single run.  

### Commands
List of supported commands:
```
 "show tables" - display available tables
 "create table" - create a new table
 "drop table" - remove an existing table
 "alter table" - change an existing table
 "execute script" - run SQL script from a file
 "show records" - display records from a specific table. Operates with a table name (to view all records) / SELECT queries for custom selections.
 "quit" - leave the program
```
### Use cases
One of the potential use cases, that proved helpful, is for a quick overview of a newly created or updated database.  

Being the simpliest possible console application, it allows to quickly check if the tables have been properly created, fk's have been correctly set, and all the columns are there as expected. 
If a new table is to be added (that is not to be included to the list of ORM models, for example, to stage some tests), the app is helpfull, since it allows to create a new table (or modify/delete an existing table) in a console dialogue.  

The app outputs the SQL queries to an XLS file (each query to a new tab), thus allowing to use the extracted data in other applications in the most convenient way. It can give away all records of a certain table (when the user enters the name of the table to the "show records" dialogue), or alternatively, it can form an XLS based on a specific SELECT query (basic SQL knowledge is required for this mode).  

The app can execute an SQL script from a file. This function serves well when you need to quickly check if the file execution results in the expected changes.  

Many of these functions are present in the standard psql console application, but DBastard's output seems to be more user-friendly, while its commands are easy to remember and type.
