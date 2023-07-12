import os.path
import json
import shutil
import time
import pandas as pd
from http.server import BaseHTTPRequestHandler, HTTPServer
import quote_updater as quote_db

CONFIG = {}
QUOTES = pd.DataFrame()
BIRTHDAYS = pd.DataFrame()
CURRENT_QUOTE_INDEX = 0

def get_current_quote():

    # TODO, nathan im sure youre gonna rewrite this so im gonna do the bare minimum here

    global CURRENT_QUOTE_INDEX

    n_quotes = len(QUOTES)

    chosen_quote = None

    # safety check db size
    if n_quotes > 0:
        chosen_quote = QUOTES.iloc[CURRENT_QUOTE_INDEX % n_quotes].to_dict()
    
    # increment index
    # CURRENT_QUOTE_INDEX = CURRENT_QUOTE_INDEX+1

    return chosen_quote

def change_quote():
    global CURRENT_QUOTE_INDEX
    CURRENT_QUOTE_INDEX = CURRENT_QUOTE_INDEX+1


def dict_keys_to_lowercase(d):
    return {k.lower(): v for k, v in d.items()}

class Handler(BaseHTTPRequestHandler):
    def __init__(self, *args, root_dir='root', default_index="index.html", **kwargs):
        self._root_dir = root_dir
        self._default_index = default_index
        self._file_type_to_header_type = {'.html':'text/html', 
                                          '.ico':'image/x-icon',
                                          '.jpg':'image/jpeg',
                                          '.css':'text/css',
                                          '.js':'text/javascript'}
                                          
        super().__init__(*args, **kwargs)

    def do_POST(self):

        # get the json sent to us
        content_len = int(self.headers.get('Content-Length'))
        post_body = self.rfile.read(content_len)
        incoming_dict = json.loads(post_body)
        # print("post body: " + str(incoming_dict))

        # parse this body for settings
        config_changed = False
        global CONFIG
        for key in CONFIG.keys():
            if key in incoming_dict:
                new_value = incoming_dict[key]
                old_value = CONFIG[key]

                # try to match the type. got this is bad. dont look!
                try:
                    convert_value = type(old_value)(new_value)
                    print("setting key '{}'' to {}".format(key, convert_value))
                    CONFIG[key] = convert_value
                    config_changed = True
                except Exception as e:
                    print("had error casting the given type to the destination type. key: '{}', source type: {}, destination type: {}".format(key, type(new_value), type(old_value)))
        
        # write new config to disk
        if config_changed:
            print('overwriting config file')
            global CONFIG_FILE
            json_obj = json.dumps(CONFIG, indent = 4) 
            with open(CONFIG_FILE, "w") as f:
                f.write(json_obj)

        # build our response dict
        response_dict = {}

        # append current quote info
        chosen_quote = get_current_quote()
        if chosen_quote is not None:
            response_dict['current_quote_info'] = dict_keys_to_lowercase(chosen_quote)

        # append settings
        response_dict['config'] = dict_keys_to_lowercase(CONFIG)

        # send response
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(bytes(json.dumps(response_dict), "utf-8"))

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
            print('serving file {}'.format(file_path))
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

def main(database_file: str, config_file: str):

    global CONFIG
    global QUOTES
    global BIRTHDAYS
    global CONFIG_FILE

    CONFIG_FILE = config_file

    # check database file exists
    if not os.path.isfile(database_file):
        print("database file '{}' doesnt exist".format(database_file))
        return
    
    # check config file exists
    if not os.path.isfile(config_file):
        print("config file '{}' doesnt exist".format(config_file))
        return
    
    # load info needed to fetch database
    with open(database_file, 'rb') as f:
        database_metadata = json.load(f)

    # load config
    with open(CONFIG_FILE, 'rb') as f:
        CONFIG = json.load(f)

    # load quotes and save to csv if not present. this is mostly for debugging
    if not os.path.isfile(CONFIG['cache_quote_file']):
        print('fetching quotes from internet')
        QUOTES = quote_db.update_quotes(database_metadata['quote_source'], database_metadata['quote_sheet'], CONFIG['cache_quote_file'])
    else:
        print('using cache file: {}'.format(CONFIG['cache_quote_file']))
        QUOTES = pd.read_csv(CONFIG['cache_quote_file']).fillna('')
    print(QUOTES)


    if CONFIG['enable_birthday_quotes']:
        if not os.path.isfile(CONFIG['cache_birthday_file']):
            print('fetching birthdays from internet')
            BIRTHDAYS = quote_db.update_birthdays(database_metadata['quote_source'], database_metadata['birthday_sheet'], CONFIG['cache_birthday_file'])
        else:
            print('using cache file: {}'.format(CONFIG['cache_birthday_file']))
            BIRTHDAYS = pd.read_csv(CONFIG['cache_birthday_file']).fillna('')
        print(BIRTHDAYS)

    # start time 
    current_time_s = time.time()
    last_db_query_s     = current_time_s
    last_quote_change_s = current_time_s

    server = HTTPServer(('', 8080), Handler) # access with http://localhost:8080

    # server.serve_forever()
    while True:

        # THIS IS BLOCKING
        server.handle_request()

        current_time_s = time.time()

        # check if we need to update the quote db
        next_db_query_s = last_db_query_s + CONFIG['database_query_period_m']*60 # written this way because updates rates may change
        if current_time_s >= next_db_query_s:
            last_db_query_s = current_time_s # allows slipping but thats fine for us
            print('updating database')

            QUOTES = quote_db.update_quotes(database_metadata['quote_source'], database_metadata['quote_sheet'])

            if CONFIG['enable_birthday_quotes']:
                BIRTHDAYS = quote_db.update_birthdays(database_metadata['quote_source'], database_metadata['birthday_sheet'])

        next_quote_change_s = last_quote_change_s + CONFIG['quote_change_period_m']*60 # written this way because updates rates may change
        if current_time_s >= next_quote_change_s:
            last_quote_change_s = current_time_s # allows slipping but thats fine for us
            change_quote()


if __name__ == "__main__":
    main('database.json', 'config.json')