import os.path
import json
import shutil
import time
import pandas as pd
from http.server import BaseHTTPRequestHandler, HTTPServer
from functools import partial
import quote_updater as quote_db

CURRENT_QUOTE_INDEX = 0

def get_current_quote(quotes):

    # TODO, nathan im sure youre gonna rewrite this so im gonna do the bare minimum here

    global CURRENT_QUOTE_INDEX

    n_quotes = len(quotes)

    chosen_quote = None

    # safety check db size
    if n_quotes > 0:
        chosen_quote = quotes.iloc[CURRENT_QUOTE_INDEX % n_quotes].to_dict()
    
    # increment index
    # CURRENT_QUOTE_INDEX = CURRENT_QUOTE_INDEX+1

    return chosen_quote


def change_current_quote():
    global CURRENT_QUOTE_INDEX
    CURRENT_QUOTE_INDEX = CURRENT_QUOTE_INDEX+1


def dict_keys_to_lowercase(d):
    return {k.lower(): v for k, v in d.items()}


def merge_dict_into_config(config, new_config, save_file=None):
    config_changed = False
    for key in config.keys():
        if key in new_config:
            try:
                new_value = new_config[key]
                old_value = config[key]
                # For whatever reason it gets unhappy if the types are already the same and bools
                if old_value == new_value:
                    continue
                # Coerce strings to bools and ints
                convert_value = type(old_value)(new_value)

                # handle Booleans specially
                if type(old_value) == type(True):
                    if new_config[key].isnumeric():
                        convert_value = bool(int(new_value))
                    else:
                        convert_value = ('TRUE' == new_value.upper()) or ('T' == new_value.upper())

                # Don't write again if they are the same
                if old_value == convert_value:
                    continue
                
                config[key] = convert_value

                print("setting key '{}' to {} (converted from \"{}\")".format(key, convert_value, new_value))
                config_changed = True
            except Exception as e:
                print("had error casting the given type to the destination type. key: '{}', source type: {}, destination type: {}. exception: {}".format(key, type(new_config[key]), type(config[key]), e))
                
    # write new config to disk
    if config_changed and save_file:
        print('overwriting config file')
        print('')
        json_obj = json.dumps(config, indent = 4) 
        with open(save_file, "w") as f:
            f.write(json_obj)


# fetch the new quotes file and save it if it is different than what we already have in memory
def fetch_and_save_database(source, sheet, cache_file, existing_db=None, cleaning_func=None):
    new_db_raw = quote_db.get_spreadsheet(source, sheet)
    new_db = cleaning_func(new_db_raw) if cleaning_func else new_db_raw
    if (existing_db is None) or (not existing_db.equals(new_db)):
        new_db_raw.to_csv(cache_file, index=False) # we always save the raw, and no index
        print("database changed. saving to {}".format(cache_file))
    return new_db


def fetch_and_save_all_databases(config, database_access):

    # fetch the new quotes file and save it if it is different than what we already have in memory
    quotes = fetch_and_save_database(database_access['quote_source'], database_access['quote_sheet'], config['cache_quote_file'], existing_db=quotes, cleaning_func=quote_db.clean_quotes)

    birthdays = None
    if config['enable_birthday_quotes']:
        # fetch the new birthdays file and save it if it is different than what we already have in memory
        birthdays = fetch_and_save_database(database_access['quote_source'], database_access['birthday_sheet'], config['cache_birthday_file'], existing_db=birthdays, cleaning_func=quote_db.clean_birthdays)

    return quotes, birthdays

def load_or_fetch_database(source, sheet, cache_file, cleaning_func):

    if not os.path.isfile(cache_file):
        print('fetching database from internet and saving to {}'.format(cache_file))
        df = fetch_and_save_database(source, sheet, cache_file, cleaning_func=cleaning_func)
    else:
        print('using cache file: {}'.format(cache_file))
        df = pd.read_csv(cache_file)
        df = cleaning_func(df)
    return df


def load_or_fetch_all_databases(config, database_access):
    quotes = load_or_fetch_database(database_access['quote_source'], database_access['quote_sheet'], config['cache_quote_file'], quote_db.clean_quotes)

    birthdays = None
    if config['enable_birthday_quotes']:
        birthdays = load_or_fetch_database(database_access['quote_source'], database_access['birthday_sheet'], config['cache_birthday_file'], quote_db.clean_birthdays)

    return quotes, birthdays

def on_post(self, config, config_file, quotes, birthdays):
    # get the json sent to us
    content_len = int(self.headers.get('Content-Length'))
    post_body = self.rfile.read(content_len)
    incoming_dict = json.loads(post_body)
    # print("post body: " + str(incoming_dict))

    # parse the incoming dict for commands
    if 'force_quote_change' in incoming_dict and incoming_dict['force_quote_change']:
        change_current_quote()


    # parse the incoming dict for settings
    merge_dict_into_config(config, incoming_dict, save_file=config_file)
    
    # build our response dict
    response_dict = {}

    # append current quote info
    chosen_quote = get_current_quote(quotes)
    if chosen_quote is not None:
        response_dict['current_quote_info'] = dict_keys_to_lowercase(chosen_quote)

    # append settings
    response_dict['config'] = dict_keys_to_lowercase(config)

    # send response
    self.send_response(200)
    self.send_header('Content-Type', 'application/json')
    self.end_headers()
    self.wfile.write(bytes(json.dumps(response_dict), "utf-8"))


class Handler(BaseHTTPRequestHandler):
    def __init__(self, *args, on_post=None, root_dir='root', default_index="index.html", **kwargs):
        self._on_post = on_post
        self._root_dir = root_dir
        self._default_index = default_index
        self._file_type_to_header_type = {'.html':'text/html', 
                                          '.ico':'image/x-icon',
                                          '.jpg':'image/jpeg',
                                          '.css':'text/css',
                                          '.js':'text/javascript'}
                                          
        super().__init__(*args, **kwargs)

    def do_POST(self):
        if self._on_post:
            self._on_post(self)

    def _send_file(self, file_path):

        # get the ".html" or ".ico", etc
        file_type = os.path.splitext(file_path)[1]
        content_type = self._file_type_to_header_type[file_type] if file_type in self._file_type_to_header_type else 'Not Found'
        status = 200

        if file_type not in self._file_type_to_header_type:
            print('sorry, i dont recognize the desired file type and consequently dont know what to set the html contet type to. maybe we wouldnt have this problem if i didnt try rolling my own webserver')

        # check if file exists
        if not os.path.exists(file_path):
            file_path = os.path.join(self._root_dir, "404.html")
            content_type = 'Not Found'
            status = 404

        self.send_response(status)
        self.send_header("Content-type", content_type)
        self.end_headers()

        # send desired file
        if os.path.exists(file_path):
            with open(file_path, 'rb') as f:
                self.wfile.write(f.read())

    def do_GET(self):        

        # security check against accessing files higher in the dir
        if ".." in self.path:
            return
        
        desired_file = self.path.lstrip('/') # needed for os.path.join()
        # server index.html if no file was specified
        desired_file = self._default_index if desired_file == "" else desired_file

        # prepend root dir to desired file path
        file_path = os.path.join(self._root_dir, desired_file )

        # send response
        self._send_file(file_path, )

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
        merge_dict_into_config(config, new_config=json.load(f), save_file=config_file)

    # load or fetch databaseses and save to csv if not present

    quotes = pd.DataFrame()
    birthdays = pd.DataFrame()
    quotes, birthdays = load_or_fetch_all_databases(config, database_access)
    print("quotes:")
    print(quotes)
    print()
    print("birthdays:")
    print(birthdays)
    print()


    # start time 
    current_time_s = time.time()
    last_db_query_s     = current_time_s
    last_quote_change_s = current_time_s

    handler = partial(Handler, 
                      on_post=partial(lambda self: on_post(self, config, config_file, quotes, birthdays)), # bind additional arguments to our on_post callback
                      root_dir='root', 
                      default_index="index.html")
    server = HTTPServer(('', config['port']), handler) # access with http://localhost:8080

    # server.serve_forever()
    while True:

        # THIS IS BLOCKING
        server.handle_request()

        #
        # there is no strong reason to multithread this. 
        # if the website isnt requesting a quote, there's no need to maintain the databases
        #

        current_time_s = time.time()

        # check if we need to update the quote db
        next_db_query_s = last_db_query_s + config['database_query_period_m']*60 # written this way because updates rates may change
        if current_time_s >= next_db_query_s:
            last_db_query_s = current_time_s # allows slipping but thats fine for us
            print('updating database')
            quotes, birthdays = fetch_and_save_all_databases(config, database_access)

        next_quote_change_s = last_quote_change_s + config['quote_change_period_m']*60 # written this way because updates rates may change
        if current_time_s >= next_quote_change_s:
            last_quote_change_s = current_time_s # allows slipping but thats fine for us
            change_current_quote()


if __name__ == "__main__":
    if not os.path.exists('config.json'):
        shutil.copy('config-example.json', 'config.json')
    main('database.json', 'config.json')