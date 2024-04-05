from datetime import datetime

from pysondb import getDb
from pysondb.errors import DataNotFoundError

from utils.ddh_shared import get_ddh_folder_gpq


class DBGPQ:

    def __init__(self, qt: datetime, lat, lon):
        # qt_s: datetime of the query to string
        qt_s = qt.strftime('%Y%m%d%H%M%S')
        # one file per day
        f = f'{get_ddh_folder_gpq()}/{qt_s[:8]}.json'
        self.db = getDb(f)
        a = {
            # all of these are strings
            "utc_time": qt_s,
            "lat": lat,
            "lon": lon
        }
        q = {"utc_time": qt_s}
        try:
            self.db.updateByQuery(db_dataset=q, new_dataset=a)
        except (IndexError, DataNotFoundError):
            self.db.add(a)

    def get_all(self, n) -> list:
        return sorted(self.db.getAll()[:n], key=lambda x: x["utc_time"], reverse=True)

    def delete_all(self):
        self.db.deleteAll()


if __name__ == '__main__':
    db = DBGPQ(datetime.now(), 'at2', 'lon2')
    print(db.get_all(5))
