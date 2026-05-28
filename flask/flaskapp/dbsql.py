import sqlite3

import click
from flask import current_app, g


def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(
            current_app.config['DATABASE'],
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row

    return g.db

def close_db(e=None):
    db = g.pop('db', None)

    if db is not None:
        db.close()

def init_db():
    db = get_db()

    with current_app.open_resource('sql/schema.sql') as f:
        db.executescript(f.read().decode('utf8'))
    with current_app.open_resource('sql/adminsetup.sql') as f:
        db.executescript(f.read().decode('utf8'))

def set_admin_data(answersViewable: int, evalsViewable: int):
    db = get_db()
    new_admin_data = {
        'adminID': 1, # There is only 1 admin in use of this program (run locally), so use 1 by default
        'answersViewable': answersViewable,
        'evalsViewable': evalsViewable
    }
    cursor = db.cursor()
    # A cursor is a pointer to a specific row within a query's result set,
    # allowing you to traverse and process data row-by-row rather than all at once

    cursor.execute('''
        UPDATE ADMIN_DATA
        SET AnswersAreViewable = :answersViewable, EvalsAreViewable = :evalsViewable
        WHERE AdminID = :adminID;
    ''', new_admin_data)

@click.command('init-db')
def init_db_command():
    """Clear the existing data and create new tables."""
    init_db()
    click.echo('The SQL database has been initialized.')

@click.command(name='set-admin')
@click.option(
    '-a', '--answers',
    type=click.BOOL,
    help='''Set visibility of the user/tutee\'s finalized answers to the tutees after they submit them.\n
    Set to 1, true, t, yes, y, on to make answers visible to them.\n
    Set to 0, false, f, no, n, off to make them invisible.'''
)
@click.option(
    '-e', '--evals',
    type=click.BOOL,
    help='''Set visibility of the evaluation results for the user/tutee\'s answers to the tutees after they submit them.\n
    Set to 1, true, t, yes, y, on to make the evaluation results visible to them.\n
    Set to 0, false, f, no, n, off to make them invisible.'''
)
def set_admin_command(answers, evals):
    """Sets custom admin data: viewability of answers and evaluation results."""
    if answers is None and evals is None:
        raise click.UsageError('You must provide at least one option: --answers or --evals')
    click.echo('Setting admin data...')
    set_admin_data(answersViewable=int(answers), evalsViewable=int(evals))
    click.echo('New admin data has been set!')

def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)