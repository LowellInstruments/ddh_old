from utils.ddh_config import ddh_get_locale

lang = ddh_get_locale()

lc_db = {
    'searching for loggers': {
        'fr': 'le_xerxe'
    }
}


def _x(s):
    if s not in lc_db.keys():
        print(f"error: text '{s}' not available for translation")
        return s
    d = lc_db[s]
    if lang not in d.keys():
        print(f"error: language '{lang}' not available for text '{s}'")
        return s
    return lc_db[s][lang]
