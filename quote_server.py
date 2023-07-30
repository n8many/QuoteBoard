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


def fetch_and_save_database(source, sheet, cache_file, existing_db=None, cleaning_func=None):
    # generic fetch and save function for both quotes and birthday information
    new_db_raw = quote_db.get_spreadsheet(source, sheet)
    new_db = cleaning_func(new_db_raw) if cleaning_func else new_db_raw
    if (existing_db is None) or (not existing_db.equals(new_db)):
        new_db_raw.to_csv(cache_file, index=False) # we always save the raw, and no index
        print("database changed. saving to {}".format(cache_file))
    return new_db

def load_or_fetch_database(source, sheet, cache_file, cleaning_func):
    # generic load or fetch function for both quotes and birthday information
    if not os.path.isfile(cache_file):
        print('fetching database from internet and saving to {}'.format(cache_file))
        df = fetch_and_save_database(source, sheet, cache_file, cleaning_func=cleaning_func)
    else:
        print('using cache file: {}'.format(cache_file))
        df = pd.read_csv(cache_file)
        df = cleaning_func(df)
    return df

class QuoteServerBackend:
    def __init__(self, config, database) -> None:
        # Load in dicts
        self.config = config
        self.database = database

        # Set up data structures
        self.quotes=pd.DataFrame()
        self.birthdays=pd.DataFrame()
        self.current_quote_index=0
        self.recent_quotes = []

        # Get the quotes
        self.load_or_fetch_all_databases()

    def get_current_quote(self):

        n_quotes = len(self.quotes)

        chosen_quote = None

        # safety check db size
        if n_quotes > 0:
            chosen_quote = self.quotes.iloc[self.current_quote_index % n_quotes].to_dict()

        return chosen_quote

    def change_current_quote(self):
        self.current_quote_index = self.current_quote_index+1

    def fetch_and_save_all_databases(self):

        # fetch the new quotes file and save it if it is different than what we already have in memory
        self.quotes = fetch_and_save_database(self.database['quote_source'], self.database['quote_sheet'], self.config['cache_quote_file'], existing_db=self.quotes, cleaning_func=quote_db.clean_quotes)

        if 'birthday_sheet' in self.database and self.database['birthday_sheet']:
            # fetch the new birthdays file and save it if it is different than what we already have in memory
            self.birthdays = fetch_and_save_database(self.database['quote_source'], self.database['birthday_sheet'], self.config['cache_birthday_file'], existing_db=self.birthdays, cleaning_func=quote_db.clean_birthdays)

    def load_or_fetch_all_databases(self):
        self.quotes = load_or_fetch_database(self.database['quote_source'], self.database['quote_sheet'], self.config['cache_quote_file'], quote_db.clean_quotes)
        
        if 'birthday_sheet' in self.database and self.database['birthday_sheet']:
            self.birthdays = load_or_fetch_database(self.database['quote_source'], self.database['birthday_sheet'], self.config['cache_birthday_file'], quote_db.clean_birthdays)

def on_post(self, backend, config_file):
    # get the json sent to us
    content_len = int(self.headers.get('Content-Length'))
    post_body = self.rfile.read(content_len)
    incoming_dict = json.loads(post_body)
    # print("post body: " + str(incoming_dict))

    # parse the incoming dict for commands
    if 'force_quote_change' in incoming_dict and incoming_dict['force_quote_change']:
        backend.change_current_quote()

    if 'force_db_update' in incoming_dict and incoming_dict['force_db_update']:
        backend.fetch_and_save_all_databases()


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
        return
    
    # check config example file exists
    if not os.path.isfile('config-example.json'):
        print("example config file '{}' doesnt exist".format('config-example.json'))
        return
    
    # check config file exists
    if not os.path.isfile(config_file):
        print("config file '{}' doesnt exist".format(config_file))
        return
    
    # load info needed to fetch database
    with open(database_access_file, 'rb') as f:
        database_access = json.load(f)

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

        # check if we need to update the quote db
        next_db_query_s = last_db_query_s + backend.config['database_query_period_m']*60 # written this way because updates rates may change
        if current_time_s >= next_db_query_s:
            last_db_query_s = current_time_s # allows slipping but thats fine for us
            print('updating database')
            backend.fetch_and_save_all_databases()

        next_quote_change_s = last_quote_change_s + backend.config['quote_change_period_m']*60 # written this way because updates rates may change
        if current_time_s >= next_quote_change_s and not ('sfw' in backend.config and backend.config['sfw']): # Prevents updating while not displaying quotes
            last_quote_change_s = current_time_s # allows slipping but thats fine for us
            backend.change_current_quote()


if __name__ == "__main__":
    if not os.path.exists('config.json'):
        shutil.copy('config-example.json', 'config.json')
    main('database.json', 'config.json')