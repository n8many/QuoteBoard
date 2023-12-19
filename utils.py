import json
import http.client as httplib
from netifaces import interfaces, ifaddresses, AF_INET
from threading import Timer

def dict_keys_to_lowercase(d):
    return {k.lower(): v for k, v in d.items()}

def merge_dict_into_dict(dst, src, save_file=None):
    changed = False
    for key in dst.keys():
        if key in src:
            try:
                new_value = src[key]
                old_value = dst[key]
                # For whatever reason it gets unhappy if the types are already the same and bools
                if old_value == new_value:
                    continue
                # Coerce strings to bools and ints
                convert_value = type(old_value)(new_value)

                # handle Booleans specially
                if type(old_value) == bool and type(new_value) == str:
                    convert_value = ('TRUE' == new_value.upper()) or ('T' == new_value.upper())

                # Don't write again if they are the same
                if old_value == convert_value:
                    continue
                
                dst[key] = convert_value

                print("setting key '{}' to {} (converted from \"{}\")".format(key, convert_value, new_value))
                changed = True
            except Exception as e:
                print("had error casting the given type to the destination type. key: '{}', source type: {}, destination type: {}. exception: {}".format(key, type(src[key]), type(dst[key]), e))
                
    # write new config to disk
    if changed and save_file:
        print('overwriting file {}'.format(save_file))
        print('')
        json_obj = json.dumps(dst, indent = 4) 
        with open(save_file, "w") as f:
            f.write(json_obj)

# Shamelessly stolen from https://stackoverflow.com/a/166591
def get_server_ip():
    for ifaceName in interfaces():
        addresses = [i['addr'] for i in ifaddresses(ifaceName).setdefault(AF_INET, [{'addr':'No IP addr'}] )]
        if addresses[0] == 'No IP addr' or addresses[0][0:3]=='127':
            continue
        else:
            return addresses[0]
    return ""

# Shamelessly stolen from https://stackoverflow.com/a/29854274
def check_internet_access(ext_ip='8.8.8.8'):
    conn = httplib.HTTPSConnection(ext_ip, timeout=1)
    try:
        conn.request('HEAD', '/')
        return True
    except Exception:
        return False

class RepeatTimer(Timer):
    def run(self):
        while not self.finished.wait(self.interval):
            self.function(*self.args, **self.kwargs)
