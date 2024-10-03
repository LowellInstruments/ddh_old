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
        'pt': '--',
        'fr': 'cherchant sondes',
        'ca': 'buscant loggers'
    },
    STR_CONNECTING_LOGGER: {
        'pt': '--',
        'fr': 'en cours de connexion',
        'ca': 'connectant'
    },
    STR_SYNCING_GPS_TIME: {
        'pt': '--',
        'fr': 'synchronisation GPS',
        'ca': 'esperant GPS'
    },
    STR_DDH_UPDATED: {
        'pt': '--',
        'fr': "DDH actualisé!",
        'ca': '--'
    },
    STR_DDH_BOOTING: {
        'pt': '--',
        'fr': "--",
        'ca': '--'
    },
    STR_DOWNLOADING_LOGGER: {
        'pt': '--',
        'fr': "téléchargement en cours",
        'ca': '--'
    },
    STR_DOWNLOADING_LOGGER_DONE: {
        'pt': '--',
        'fr': "complété",
        'ca': '--'
    },
    STR_STOPPED_AUTOWAKE_OFF: {
        'pt': '--',
        'fr': "arrêté, auto-réveille éteint",
        'ca': '--'
    },
    STR_RETRYING_LOGGER: {
        'pt': '--',
        'fr': "nouvel essai",
        'ca': '--'
    },
    STR_LOGGER_FAILURE: {
        'pt': '--',
        'fr': "erreur de sonce",
        'ca': '--'
    },
    STR_LOGGER_ERROR_OX_SENSOR: {
        'pt': '--',
        'fr': "erreur du capteur OX",
        'ca': '--'
    },
    STR_LOGGER_ERROR_TP_SENSOR: {
        'pt': '--',
        'fr': "erreur TP",
        'ca': '--'
    },
    STR_LOGGER_ERROR_RUN: {
        'pt': '--',
        'fr': "erreur RUN sonde",
        'ca': '--'
    },
    STR_LOGGER_ERROR_RADIO: {
        'pt': '--',
        'fr': "erreur du signal radio",
        'ca': '--'
    },
    STR_RADIO_IS_DISABLED: {
        'pt': '--',
        'fr': "signal radio désactivé",
        'ca': '--'
    },
    STR_NEED_GPS: {
        'pt': '--',
        'fr': "aucun signal GPS",
        'ca': '--'
    },
    STR_APP_RESTING: {
        'pt': '--',
        'fr': "prêt",
        'ca': '--'
    },
    STR_WAITING_GPS_SECONDS: {
        'pt': '--',
        'fr': "en attente du GPS",
        'ca': '--'
    },
    STR_NO_BLE_SERVICE: {
        'pt': '--',
        'fr': "service BLE manquant",
        'ca': '--'
    },
    STR_DDS_BAD_CONF: {
        'pt': '--',
        'fr': "erreur de config, voir log",
        'ca': '--'
    },
    STR_WE_ARE_IN_PORT: {
        'pt': '--',
        'fr': "dans port",
        'ca': '--'
    },
    STR_WAIT_POWER_CYCLE_GPS: {
        'pt': '--',
        'fr': "attendez, redémarrage GPS",
        'ca': '--'
    },
    STR_LOGGER_LOW_BATTERY: {
        'pt': '--',
        'fr': "batterie faible!",
        'ca': '--'
    },
    STR_NO_LOGGERS_ASSIGNED: {
        'pt': '--',
        'fr': "aucune sonde attribué",
        'ca': '--'
    },
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
