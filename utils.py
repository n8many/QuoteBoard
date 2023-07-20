import json

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
                if type(old_value) == type(True):
                    if src[key].isnumeric():
                        convert_value = bool(int(new_value))
                    else:
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
