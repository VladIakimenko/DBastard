import atexit
import os
from datetime import datetime
import subprocess

import xlwt
import psycopg2

from config import TABLE_WIDTH

TEMP_XLS_NAME = 'records.xls'
STD_ERROR_LOG = 'std_errors.txt'


class Postgres:
    def __init__(self, database, username, password):
        self.connection = psycopg2.connect(database=database,
                                           user=username,
                                           password=password)
        self.cursor = self.connection.cursor()
        atexit.register(self.terminate)
        self.workbook = xlwt.Workbook()

        print(f'<SYSTEM> Postgres: Connected to DB "{database}" as "{username}".')

    def terminate(self):
        """
        The method is called upon exit as per atexit.register
        """
        self.cursor.close()
        self.connection.close()
        if os.path.exists(TEMP_XLS_NAME):
            os.remove(TEMP_XLS_NAME)
        print('<SYSTEM> Postgres: Connection to DB terminated. Cursor closed.\nTemporary files removed.')

    def execute_script(self, script_path):
        """
        The method to execute a script from file
        returns: True if no exception raised, False otherwise
        """
        if not os.path.exists(script_path):
            print(f'<ERROR> File {script_path} not found!')
        else:
            with open(script_path, 'rt', encoding='UTF-8') as filehandle:
                query = filehandle.read()
        success = self.__try_commit(query, '<ERROR> Postgres: Could not execute SQL script!')
        return success

    def __get_tables(self):
        """
        A service method used by the .show_tables method
        returns: {table name: {col. number: column name,
        col. number: column name ... }, ...},
            IMPORTANT: col. number in this dictionary is
            the one that PostgreSQL references to when it
            assigns PK and FK and other constraints.
            If a column is dropped, it retains the number
            but changes the name to '...pg.dropped...'
        """
        query = """\
        SELECT table_name
          FROM information_schema.tables
         WHERE table_schema = 'public' AND table_type = 'BASE TABLE'"""

        self.cursor.execute(query)
        tables = self.cursor.fetchall()

        tables_with_columns = {}
        for table in tables:
            query = f"""\
            SELECT attnum, attname
              FROM pg_attribute
             WHERE attrelid = '{table[0]}'::regclass"""
            self.cursor.execute(query)
            row_numbers = self.cursor.fetchall()
            row_numbers = list(filter(lambda x: x[0] > 0 and 'pg.dropped' not in x[1], row_numbers))
            tables_with_columns[table[0]] = dict(row_numbers)
        return tables_with_columns

    def __get_constraints(self, tables):
        """
        A service method used by the .show_tables method
        tables - a dict received from .__get_tables() method
        returns: a dict where:
            keys are tables names
            values are lists of tuples with all constraints for this table.
                tuple[0] - constraint name
                tuple[1:] - *various constraint data
        """
        constraints = {}
        for table in tables:
            query = f"""\
            SELECT conname, conrelid::regclass, confrelid::regclass, conkey, confkey
              FROM pg_constraint
             WHERE confrelid = '{table}'::regclass OR conrelid = '{table}'::regclass;"""
            self.cursor.execute(query)
            constraints[table] = self.cursor.fetchall()
        return constraints

    def __get_data_type(self, table_name, column_name):
        """
        A service method to receive a single column data type
        """
        query = f"SELECT data_type FROM information_schema.columns " \
                f"WHERE table_name='{table_name}' AND column_name='{column_name}';"
        self.cursor.execute(query)
        return self.cursor.fetchone()[0]

    def show_tables(self, custom_width=None):
        """
        The method prints out the current DB layout in a standard graphic form.
        It indicates the tables' Primary and Foreign keys and their referrants.
        If raw data is required instead of a graphic representation - private
            .__get_tables() method should be called instead.
        returns: None
        """
        tables = self.__get_tables()
        constraints = self.__get_constraints(tables)
        
        def fkey_check(constraint, column):
            return 'fk' in constraint[0] and f'_{column}_' in constraint[0]

        # Printout config:

        width = int(TABLE_WIDTH)
        pk_indicator = ' PK |'
        fk_indicator = '| FK '

        for table_name, columns_names in tables.items():

            # Table Header:
            print(f'{"_" * width}')
            print(f'{" " * int((width - len(table_name)) / 2)}'
                  f'{table_name}'
                  f'{" " * int((width - len(table_name)) / 2)}')
            print(f'{"_" * width}')

            # Primary Key:
            for constraint in constraints[table_name]:
                if constraint[0] == f'{table_name}_pkey':
                    pk_index = constraint[3][0]
                    column_type = self.__get_data_type(table_name, columns_names[pk_index])
            print(
                f'{pk_indicator}'
                f'{" " * int((width - len(f"{columns_names[pk_index]} ({column_type})") - len(pk_indicator)) / 2)}'
                f'{columns_names[pk_index]} '
                f'({column_type})'
            )
            print(f'{"." * width}')

            # Other columns:
            if len(columns_names) > 1:
                for index, column in columns_names.items():
                    if index == pk_index:
                        continue
                    column_type = self.__get_data_type(table_name, column)
                    printed = False
                    for constraint in constraints[table_name]:
                        if fkey_check(constraint, column):
                            front_gap = int((width - len(fk_indicator) - len(f"{column} ({column_type})")) / 2)
                            end_gap = width - front_gap - len(f"{column} ({column_type})") - len(fk_indicator)
                            print(
                                f'{" " * front_gap}'
                                f'{column} '
                                f'({column_type})'
                                f'{" " * end_gap}'
                                f'{fk_indicator}'
                                f'''   REFERENCES: "{tables[constraint[2].strip('"')][constraint[4][0]]}"'''
                                f'''   from "{constraint[2].strip('"')}"'''
                            )
                            printed = True
                    if not printed:
                        print(f'{" " * int((width - len(f"{column} ({column_type})")) / 2)}{column} ({column_type})')
                    print(f'{"." * width}')
            print('\n')

    def __try_commit(self, query, message):
        """
        A service method to provide information on commits statuses
        returns: True if no exception raised, False otherwise
        """
        success = True
        try:
            self.cursor.execute(query)
            self.connection.commit()
        except psycopg2.Error as error:
            print(message)
            print(error)
            success = False
            self.connection.rollback()
        return success

    def create_table(self, name, primary_key, columns):
        """
        name - table name, str (method bruteforces lowercase for tables names)
        primary_key - a tuple(*) with (primary key name, type=SERIAL by default)
            * Has to be a tuple, even if the column type is not given!
        columns as dicts: {'name': name of column,
                           'type': type of data,
                           'constraints': [str, str, str]}
        returns: True if no exception raised, False otherwise
        """
        query = f'CREATE TABLE {name.lower()} ('
        query += f'PRIMARY KEY ({primary_key[0].lower()}), '
        query += f'{primary_key[0].lower()} ' \
                 f'{primary_key[1].upper() if len(primary_key) > 1 and primary_key[1] else "SERIAL"}, '
        for column in columns:
            query += f'{column["name"].lower()} ' \
                     f'{column["type"].upper()} ' \
                     f'{" ".join(column["constraints"]).upper()}, '

        query = query[:-2] + ');'
        success = self.__try_commit(query, '<ERROR> Postgres: Could not create table!')
        return success

    def alter_table(self, action, table, column, data=''):
        """
        The method that can add, drop or rename a column.
        'action' should be set to 'rename', 'drop' or 'add' accordingly.
        'table' - the name of the table
        'column' - the name of the target column
        'data' - str, depending on the method may contain:
            1) the new name for a column if action='rename'
            2) DATA TYPE and CONSTRAINTS as per SQL syntax if action='add'
            3) '' for action='drop'
        returns: True if no exception raised, False otherwise
        """
        if action.lower().strip() not in ('rename', 'drop', 'add'):
            print(f'<ERROR> Postgres: The "alter_table" method does not support {action}!\n'
                  f'        Please use one of the following arguments:\n'
                  f'        "add"                - add a new column\n'
                  f'        "drop"               - remove column\n'
                  f'        "rename"             - change column name')
        else:
            alter = {'add': ('ADD COLUMN', ''),
                     'rename': ('RENAME COLUMN', 'TO'),
                     'drop': ('DROP COLUMN', '')}
            query = f"""
            ALTER TABLE {table}
            {alter[action][0]} {column} {alter[action][1]} {data if data else ''};"""

            success = self.__try_commit(query, '<ERROR> Postgres: Could not modify table!')
            return success

    def drop_table(self, name):
        """
        Deletes table by name
        returns: True if no exception raised, False otherwise
        """
        query = f'DROP TABLE {name};'
        success = self.__try_commit(query, '<ERROR> Postgres: Could not delete table!')
        return success

    def show_records(self, table=None, select=None):
        """
        returns: all records from a table
        """
        records = []
        query = ''
        if table:
            query = f"""\
            SELECT * FROM {table};"""
        elif select:
            query = select
        else:
            print(f'<ERROR> Either a table name or a SELECT query must be provided!')

        if self.__try_commit(query, message='<ERROR> Postgres: SELECT request could not be executed!'):
            records = self.cursor.fetchall()
        else:
            return

        sheet_name = datetime.strftime(datetime.now(), "%d-%m-%Y %Hh %Mm %Ss")
        sheet = self.workbook.add_sheet(sheet_name)

        columns = [desc[0] for desc in self.cursor.description]
        if columns:
            for i, column in enumerate(columns):
                sheet.write(0, i, column)

        for i, record in enumerate(records, 1):
            for j, value in enumerate(record):
                sheet.write(i, j, str(value))

        index = self.workbook.sheet_index(sheet_name)
        self.workbook.set_active_sheet(index)
        self.workbook.save(TEMP_XLS_NAME)

        if os.name == 'nt':
            os.startfile(TEMP_XLS_NAME)
        else:
            with open(STD_ERROR_LOG, 'w') as error_log:
                subprocess.run(['xdg-open', TEMP_XLS_NAME], stderr=error_log)













