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


class DbHis:

    def __init__(self, path_to_file):
        self.f = path_to_file
        self._db = DB(keys=[
            "mac",
            "SN",
            "e",
            "lat",
            "lon",
            "ep_loc",
            "ep_utc",
            "rerun"
        ])
        self._db.load(self.f)

    def add(self, mac, sn, e, lat, lon, ep_loc, ep_utc, rerun):
        a = {
            # all of these are strings
            "mac": mac,
            "SN": sn,
            # e: string "ok", "error"
            "e": e,
            "lat": lat,
            "lon": lon,
            "ep_loc": ep_loc,
            "ep_utc": ep_utc,
            "rerun": str(rerun)
        }
        q = {"SN": sn}
        try:
            _ids = self._db.update_by_query(q, a)
            if not _ids:
                self._db.add(a)
        except (IndexError, KeyError) as ex:
            print(f"error: db_his -=> {ex}")
        self._db.commit(self.f)

    def get_all(self) -> dict:
        return self._db.get_all()

    def delete_all(self):
        self._db.delete_all()
        self._db.commit(self.f)


if __name__ == '__main__':
    db = DbHis('pepi.json')
    db.add('mac2', 'sn1', 'e1', 'lat1', 'lon1', 'ep_loc1', 'ep_utc1', True)
    rr = db.get_all(3).values()
    print(rr)