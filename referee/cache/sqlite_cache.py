import sqlite3,json,time,hashlib
from pathlib import Path
class SQLiteCache:
    def __init__(self,path):
        self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True);self.db=sqlite3.connect(self.path);self.db.execute('create table if not exists cache (k text primary key, value text not null, created real not null)');self.db.commit()
    @staticmethod
    def key(namespace,payload):return hashlib.sha256((namespace+'|'+json.dumps(payload,sort_keys=True,default=str)).encode()).hexdigest()
    def get(self,k,max_age_s=None):
        row=self.db.execute('select value,created from cache where k=?',(k,)).fetchone()
        if not row:return None
        if max_age_s is not None and time.time()-row[1]>max_age_s:return None
        return json.loads(row[0])
    def put(self,k,value):self.db.execute('insert or replace into cache(k,value,created) values(?,?,?)',(k,json.dumps(value,default=str),time.time()));self.db.commit()
