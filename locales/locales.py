# ----------------------------------------
# this will be moved to gettext module,
# but it did not work for me when I tried
# ----------------------------------------
from locales.strings import *
from utils.ddh_shared import (set_ddh_language_file_content,
                              get_ddh_language_file_content)


g_lang = get_ddh_language_file_content()

lang_msg_db = {
    STR_SEARCHING_FOR_LOGGERS: {
        'fr': 'cherchant sondes',
        'ca': 'buscant loggers'
    },
    STR_CONNECTING_LOGGER: {
        'fr': 'en cours de connexion',
        'ca': 'connectant'
    },
    STR_SYNCING_GPS_TIME: {
        'fr': 'synchronisation GPS',
        'ca': 'esperant GPS'
    }
}


def locales_change_language(s):
    set_ddh_language_file_content(s)
    global g_lang
    g_lang = get_ddh_language_file_content()
    return g_lang


def _x(s):
    # putting this here allows for dynamic changing of language
    if s not in lang_msg_db.keys():
        print(f"error: no translation for text '{s}'")
        return s
    if g_lang == 'en':
        return s
    d_s = lang_msg_db[s]
    if g_lang not in d_s.keys():
        print(f"error: no language '{g_lang}' for text '{s}'")
        return s
    return lang_msg_db[s][g_lang]
