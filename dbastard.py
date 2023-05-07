#!/usr/bin/env python3

from os import path, makedirs
from sys import exit
import argparse

from config import *
from postgres import Postgres

parser = argparse.ArgumentParser(description='DBastard')

parser.add_argument('-db', '--database', type=str, help='database name')
parser.add_argument('-p', '--password', type=str, help='database password')
parser.add_argument('-u', '--user', type=str, help='database user')

args = parser.parse_args()


def execute_script(con):
    print()
    script_path = input(f'Please enter path to the SQL Script: ')
    script_path = script_path.strip().replace('\\', '/')
    if con.execute_script(script_path):
        print()
        print(f'Script {script_path.rpartition("/")[-1]} successfully executed.')


def display_tables(con):
    con.show_tables()


def drop_table(con):
    print()
    print('NOTE: DATA WILL NOT BE RECOVERABLE\n'
          'Enter table name to delete or type "abort" to return to menu:')
    while True:
        table_name = input()
        if table_name.lower().strip() == 'abort':
            return
        if table_name in [item for couple in con.show_tables() for item in couple]:
            break
        else:
            print(f'Table {table_name} not found. Please re-enter or type "abort" to return to menu:')

    if con.drop_table(table_name):
        print()
        print(f'Table {table_name} has been deleted.')


def alter_table(con):
    print()
    tables = con._Postgres__get_tables()

    table = enter_table(tables)
    if table == 'abort':
        return

    action = ''
    print()
    print('Please choose what changes to introduce:\n'
          '    1. add a new column\n'
          '    2. remove column\n'
          '    3. change column name')

    while not action or not action.isdigit() or int(action) not in range(1, 4):
        action = input('').strip()
        if table == 'abort':
            return
    else:
        actions = {1: 'add',
                   2: 'drop',
                   3: 'rename'}
        action = actions[int(action)]

    data = ''
    if action in ('drop', 'rename'):
        column = enter_column(tables, table)
        if column == 'abort':
            return
        if action == 'rename':
            print()
            data = input(f'Please enter the new name for '
                         f'{"".join([col for col in tables[table].values() if col == column])}: ')
            if data == 'abort':
                return
            else:
                data = data.lower().replace(' ', '_')

    elif action == 'add':
        column_details = set_column_details()
        column = column_details['name']
        data = column_details['type'] + ' ' + ' '.join(column_details['constraints'])

    if con.alter_table(action, table, column, data):
        print(f'Table {table} has been successfully modified.')


def create_table(con):
    print()
    name = input('Enter the table name: ').lower().strip().replace(' ', '_')
    pk_name = input('Enter the name of the PRIMARY KEY column: ').lower().strip().replace(' ', '_')
    print('Enter PK DATA TYPE: ', end='')
    pk_type = input().upper().strip()
    columns = []
    while True:
        print()
        print(f'Table name: {name}\n\n'
              f'Primary key: {pk_name}\n'
              f'Data type: {pk_type}\n')
        for column in columns:
            print(f'Column name: {column["name"]}\n'
                  f'Data type: {column["type"]}\n'
                  f'Constraints: {" ".join(column["constraints"])}')
            print()
        command = input('Type "commit" to create the table, "abort" to return to menu. \n'
                        'Press "enter" to add another column: ')
        if command == 'commit':
            break
        elif command == 'abort':
            return
        else:
            columns.append(set_column_details())

    if con.create_table(name, (pk_name, pk_type), columns):
        print('Successfully created.')


def set_column_details():
    column = {}
    print('Please enter the column name:')
    column['name'] = input().lower().strip().replace(' ', '_')
    column['type'] = input('Enter DATA TYPE: ').upper().strip()
    column['constraints'] = []
    print('Keep entering Constraints (one by one), type "done" to finish:')
    while True:
        constraint = input().strip()
        if constraint == 'done':
            break
        else:
            column['constraints'].append(constraint)
    return column


def cmd_not_found(*args):
    print('Command not recognized. Please use one of the following commands:\n'
          ' "show tables" - display all user-created tables\n'
          ' "create table" - create new table\n'
          ' "drop table" - remove existing table\n'
          ' "alter table" - change existing table\n'
          ' "execute script" - run SQL script from a file\n'
          ' "show records" - display all records from a specific table\n'
          ' "quit" - leave the program'
          )


def show_records(con):
    print('Enter the name of the table or a SELECT query.\n'
          'Multi-line input is active. Press "enter" twice to submit:')

    user_input = ""
    while True:
        line = input()
        if not line:
            break
        user_input += line + "\n"

    if user_input.lower().strip() in con._Postgres__get_tables():
        con.show_records(table=user_input)
    else:
        con.show_records(select=user_input)


def enter_table(tables):
    table = ''
    while table not in tables and table != 'abort':
        table = input('Please enter the name of the table: ')
    return table


def enter_column(tables, table):
    column = ''
    while column not in tables[table].values() and column not in ('abort', 'done'):
        column = input(f'Please enter the name of the column: ')
    return column


def read_cmd(cmd):
    cmd = cmd.lower().strip()
    if cmd in ('quit', 'q', 'e', 'exit'):
        exit()

    cmd_dict = {'show tables': display_tables,
                'create table': create_table,
                'drop table': drop_table,
                'alter table': alter_table,
                'execute script': execute_script,
                'show records': show_records,
                '404': cmd_not_found}

    return (cmd_dict['404'], cmd_dict.get(cmd))[cmd in cmd_dict]


def launch():
    print()
        
    pass_path = PASSWORD_PATH.replace('\\', '/')
    if path.exists(pass_path):
        with open(pass_path, 'rt', encoding='UTF-8') as filehandle:
            password = filehandle.read()
    else:
        password = input(f'Enter password for "{USERNAME}" to access "{DATABASE}" database: ')
        if not path.exists(pass_path.rpartition('/')[0]):
            makedirs(pass_path.rpartition('/')[0])
        with open(pass_path, 'wt', encoding='UTF-8') as filehandle:
            filehandle.writelines(password)
            
        print('IMPORTANT NOTE: This app does not create the DB! '
              'You are required to execute "createdb" command manually before you can proceed. '
              'Please ensure names and paths listed in "config.py" are set to actual values.')        


    database = args.database if args.database else DATABASE
    user = args.user if args.user else USERNAME
    if args.password:
        password = args.password
        
    con = Postgres(database, user, password)
    return con


if __name__ == '__main__':
    connector = launch()

    while True:
        print()
        read_cmd(input('>>> '))(connector)

