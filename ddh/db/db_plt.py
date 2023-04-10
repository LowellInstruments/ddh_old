import json
import sqlite3


class DBPlt:
    def __init__(self, db_n="db_plt.db"):
        self.name = db_n
        db = sqlite3.connect(self.name)
        c = db.cursor()
        c.execute(
            "CREATE TABLE IF NOT EXISTS records\
            ( \
            id              INTEGER PRIMARY KEY, \
            mac             TEXT, \
            start_time      TEXT, \
            end_time        TEXT, \
            time_span       TEXT, \
            metric          TEXT, \
            the_times       TEXT, \
            the_values      TEXT  \
            )"
        )
        db.commit()
        c.close()
        db.close()

    # v is a list which gets converted to string
    def add_record(self, w, s, e, p, m, t, v):
        db = sqlite3.connect(self.name)
        c = db.cursor()
        c.execute(
            "INSERT INTO records("
            "mac, start_time, end_time, time_span,"
            "metric, the_times, the_values) "
            "VALUES(?,?,?,?,?,?,?)",
            (w, s, e, p, m, json.dumps(t), json.dumps(v)),
        )
        db.commit()
        c.close()
        db.close()

    def delete_record(self, record_id):
        db = sqlite3.connect(self.name)
        c = db.cursor()
        c.execute("DELETE FROM records where id=?", (record_id,))
        db.commit()
        c.close()
        db.close()

    def list_all_records(self):
        db = sqlite3.connect(self.name)
        c = db.cursor()
        c.execute("SELECT * from records")
        records = c.fetchall()
        c.close()
        db.close()
        return records

    def get_record_by_id(self, record_id):
        db = sqlite3.connect(self.name)
        c = db.cursor()
        c.execute("SELECT * from records WHERE id=?", (record_id,))
        records = c.fetchall()
        c.close()
        db.close()
        return records[0]

    def get_record_values(self, i) -> dict:
        s = self.get_record_by_id(i)[7]
        return json.loads(s)

    def get_record_times(self, i) -> dict:
        s = self.get_record_by_id(i)[6]
        return json.loads(s)

    def get_record_id(self, w, s, e, p, m):
        db = sqlite3.connect(self.name)
        c = db.cursor()
        c.execute(
            "SELECT id from records WHERE mac=? AND "
            "start_time=? AND end_time=? AND time_span=?"
            "AND metric=?",
            (w, s, e, p, m),
        )
        records = c.fetchall()
        c.close()
        db.close()
        return records[0][0]

    def does_cache_record_exist(self, w, s, e, p, m):
        db = sqlite3.connect(self.name)
        c = db.cursor()
        c.execute(
            "SELECT EXISTS(SELECT 1 from records WHERE mac=? AND "
            "start_time=? AND end_time=? AND time_span=?"
            "AND metric=?)",
            (w, s, e, p, m),
        )
        records = c.fetchall()
        c.close()
        db.close()
        return records[0][0]
