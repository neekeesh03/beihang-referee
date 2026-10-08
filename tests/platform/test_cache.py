from referee.cache import SQLiteCache

def test_sqlite_cache_roundtrip(tmp_path):
    c=SQLiteCache(tmp_path/'c.db');k=c.key('x',{'a':1});c.put(k,{'v':2});assert c.get(k)=={'v':2}
