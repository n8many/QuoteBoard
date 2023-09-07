import os.path
import json
import shutil
import time
import pandas as pd
from http.server import BaseHTTPRequestHandler, HTTPServer
from functools import partial
import quote_updater as quote_db
from server import HTTPHandler 
from utils import merge_dict_into_dict, dict_keys_to_lowercase
from quote_picker import pick_quote, get_current_birthdays

from typing import Optional

def fetch_database(source, sheet, cleaning_func):
    try:
        new_db_raw = quote_db.get_spreadsheet(source, sheet)
        new_db = cleaning_func(new_db_raw) if cleaning_func else new_db_raw
        return new_db
    except Exception as err:
        print(f"Failed to fetch sheet data from sheet ({err})")
    return None

def load_database(cache_file, cleaning_func) -> Optional[pd.DataFrame]:
    if os.path.isfile(cache_file):
        print('using cache file: {}'.format(cache_file))
        df = pd.read_csv(cache_file)
        df = cleaning_func(df)
        return df
    else:
        return None

def save_database(db: pd.DataFrame, cache_file: str):
    db.to_csv(cache_file, index=False) # we always save the raw, and no index
    print("database changed. saving to {}".format(cache_file))

def fetch_and_save_database(source, sheet, cache_file, existing_db=None, cleaning_func=None):
    # generic fetch and save function for both quotes and birthday information
    if (new_db:=fetch_database(source, sheet, cleaning_func)) is not None:
        if (existing_db is None) or (not existing_db.equals(new_db)):
            save_database(new_db, cache_file)
            print("database changed. saving to {}".format(cache_file))
        return new_db
    return existing_db

def load_or_fetch_database(source, sheet, cache_file, cleaning_func):
    # generic load or fetch function for both quotes and birthday information
    if (df:=load_database(cache_file, cleaning_func)) is None:
        print('fetching database from internet and saving to {}'.format(cache_file))
        df = fetch_and_save_database(source, sheet, cache_file, cleaning_func=cleaning_func)
    return df

class QuoteServerBackend:
    def __init__(self, config, database: dict) -> None:
        # Load in dicts
        self.config = config
        # TODO: break database into source + sheets for better function calls below.
        self.database = database

        # Set up data structures
        self.quotes=pd.DataFrame()
        self.birthdays=pd.DataFrame()
        self.recent_quotes = []
        self.current_quote_id=0

        self.offline_mode = self.database is None or len(database)==0

        self.last_quote_change = time.time()
        self.last_database_update = time.time()

        # Get the quotes
        if self.config["query_database_on_start"]:
            self.update_databases()
        else:
            self.load_databases()
        self.change_current_quote()

    def get_current_quote(self):            
        chosen_quote = None
        
        if self.current_quote_id in self.quotes.index:
            chosen_quote = self.quotes.loc[self.current_quote_id].to_dict()

            # Add 🎂 to name (this may break certain browsers)
            if self.config['display_birthdays'] and (get_current_birthdays(self.birthdays)['Name']==chosen_quote['Who']).any():
                chosen_quote['Who'] = chosen_quote['Who'] + ' 🎂'

        else:
            # Seems the quotes have changed indices, time to get a new one
            self.change_current_quote()
            chosen_quote = self.get_current_quote()  # possibly dangerous...

        return chosen_quote

    def change_current_quote(self):
        self.last_quote_change = time.time()
        self.current_quote_id = pick_quote(self.quotes, 
                                           self.recent_quotes, 
                                           self.birthdays if self.config['enable_birthday_quotes'] else None)

        self.recent_quotes.append(self.current_quote_id)

        max_antirepeat = min(self.config['antirepeat_depth'], len(self.quotes)-1)
        if len(self.recent_quotes) > max_antirepeat:
            self.recent_quotes = self.recent_quotes[-max_antirepeat:]

    
    def load_databases(self):
        self.quotes = load_or_fetch_database(self.database['quote_source'], self.database['quote_sheet'], self.config['cache_quote_file'], quote_db.clean_quotes)
        
        if 'birthday_sheet' in self.database and self.database['birthday_sheet']:
            self.birthdays = load_or_fetch_database(self.database['quote_source'], self.database['birthday_sheet'], self.config['cache_birthday_file'], quote_db.clean_birthdays)

    def update_databases(self):
        self.last_database_update = time.time()
        # If offline, default to direct reading of cache files.
        if self.offline_mode and self.config['cache_quote_file']:
            self.quotes = load_database(self.config['cache_quote_file'], cleaning_func=quote_db.clean_quotes)
            if self.config['cache_birthday_file']:
                self.birthdays = load_database(self.config['cache_birthday_file'], cleaning_func=quote_db.clean_birthdays)
        else:
            # fetch the new quotes file and save it if it is different than what we already have in memory
            self.quotes = fetch_and_save_database(self.database['quote_source'], self.database['quote_sheet'], self.config['cache_quote_file'], self.quotes, quote_db.clean_quotes)
            if 'birthday_sheet' in self.database and self.database['birthday_sheet']:
                # fetch the new birthdays file and save it if it is different than what we already have in memory
                self.birthdays = fetch_and_save_database(self.database['quote_source'], self.database['birthday_sheet'], self.config['cache_birthday_file'], existing_db=self.birthdays, cleaning_func=quote_db.clean_birthdays)
        print("Databases updated")
    
def on_post(self, backend: QuoteServerBackend, config_file: str):
    # get the json sent to us
    content_len = int(self.headers.get('Content-Length'))
    post_body = self.rfile.read(content_len)
    incoming_dict = json.loads(post_body)
    # print("post body: " + str(incoming_dict))

    # parse the incoming dict for commands
    if 'force_quote_change' in incoming_dict and incoming_dict['force_quote_change']:
        backend.change_current_quote()

    if 'force_db_update' in incoming_dict and incoming_dict['force_db_update']:
        backend.update_databases()

    # parse the incoming dict for settings
    merge_dict_into_dict(backend.config, incoming_dict, save_file=config_file)
    
    # build our response dict
    response_dict = {}

    # append current quote info
    chosen_quote = backend.get_current_quote()
    if chosen_quote is not None:
        response_dict['current_quote_info'] = dict_keys_to_lowercase(chosen_quote)

    # append settings
    response_dict['config'] = dict_keys_to_lowercase(backend.config)

    # send response
    self.send_response(200)
    self.send_header('Content-Type', 'application/json')
    self.end_headers()
    self.wfile.write(bytes(json.dumps(response_dict), "utf-8"))


def main(database_access_file: str, config_file: str):

    # check database file exists
    if not os.path.isfile(database_access_file):
        print("database file '{}' doesnt exist".format(database_access_file))
        print("enabling offline mode")
        database_access = None
    else:
        # load info needed to fetch database
        with open(database_access_file, 'rb') as f:
            database_access = json.load(f)
    
    # check config example file exists
    if not os.path.isfile('config-example.json'):
        print("example config file '{}' doesnt exist".format('config-example.json'))
        return
    
    # check config file exists
    if not os.path.isfile(config_file):
        print("config file '{}' doesnt exist".format(config_file))
        return

    # load config
    with open('config-example.json') as f:
        config = json.load(f)

    with open(config_file) as f:
        merge_dict_into_dict(config, json.load(f), save_file=config_file)

    # load or fetch databaseses and save to csv if not present
    backend = QuoteServerBackend(config=config, database=database_access)

    print("quotes:")
    print(backend.quotes)
    print()
    print("birthdays:")
    print(backend.birthdays)
    print()

    # start time 
    current_time_s = time.time()
    last_db_query_s     = current_time_s
    last_quote_change_s = current_time_s

    handler = partial(HTTPHandler, 
                    on_post=partial(lambda self: on_post(self, backend, config_file)), # bind additional arguments to our on_post callback
                    root_dir='root', 
                    default_index="index.html")
    

    server = HTTPServer(('', config['port']), handler) # access with http://localhost:8080

    # server.serve_forever()
    while True:

        # THIS IS BLOCKING
        server.handle_request()

        current_time_s = time.time()

        # TODO: make these checks use thread timers to run
        if backend.last_database_update + backend.config['database_query_period_m']*60 <= current_time_s:
            print('updating database')
            backend.update_databases()

        if backend.last_quote_change + backend.config['quote_change_period_m']*60 <= current_time_s and not ('sfw' in backend.config and backend.config['sfw']):
            backend.change_current_quote() # Fairly lossy in terms of time...
            


if __name__ == "__main__":
    if not os.path.exists('config.json'):
        shutil.copy('config-example.json', 'config.json')
    main('database.json', 'config.json')