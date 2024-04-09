# from pysondb import getDb
# from pysondb.errors import DataNotFoundError


# class DBHis:
#
#     def __init__(self, hf):
#         # hf: path to history file
#         self.db = getDb(hf)
#
#     def add(self, mac, sn, e, lat, lon, ep_loc, ep_utc):
#         a = {
#             # all of these are strings
#             "mac": mac,
#             "SN": sn,
#             # e: string "ok", "error"
#             "e": e,
#             "lat": lat,
#             "lon": lon,
#             "sws_time": ep_loc,
#             "utc_epoch": ep_utc
#         }
#         q = {"SN": sn}
#         try:
#             self.db.updateByQuery(db_dataset=q, new_dataset=a)
#         except (IndexError, DataNotFoundError):
#             self.db.add(a)
#
#     def get_all(self, n) -> list:
#         return sorted(self.db.getAll()[:n], key=lambda x: x["sws_time"], reverse=True)
#
#     def delete_all(self):
#         self.db.deleteAll()


from pysondb import DB


class DBHis:

    def __init__(self, path_to_file):
        self.db = DB(keys=[
            "mac",
            "SN",
            "e",
            "lat",
            "lon",
            "ep_loc",
            "ep_utc"
        ])
        self.db.load(path_to_file)

    def add(self, mac, sn, e, lat, lon, ep_loc, ep_utc):
        a = {
            # all of these are strings
            "mac": mac,
            "SN": sn,
            # e: string "ok", "error"
            "e": e,
            "lat": lat,
            "lon": lon,
            "sws_time": ep_loc,
            "utc_epoch": ep_utc
        }
        q = {"SN": sn}
        try:
            self.db.update_by_query(q, a)
        except (IndexError, KeyError):
            self.db.add(a)

    def get_all(self, n) -> list:
        return sorted(self.db.get_all()[:n],
                      key=lambda x: x["sws_time"], reverse=True)

    def delete_all(self):
        self.db.delete_all()
