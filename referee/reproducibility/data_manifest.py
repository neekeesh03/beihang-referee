from pathlib import Path
import hashlib
DATA_EXT={'.csv','.tsv','.json','.parquet','.feather','.xlsx','.xls','.h5','.hdf5','.npy','.npz','.rds','.sav','.dta'}
def build_data_manifest(files):
    out=[]
    for p in map(Path,files):
        if p.suffix.lower() not in DATA_EXT:continue
        h=hashlib.sha256(p.read_bytes()).hexdigest();out.append({'path':str(p),'bytes':p.stat().st_size,'extension':p.suffix.lower(),'sha256':h})
    return {'files':out,'count':len(out),'total_bytes':sum(x['bytes'] for x in out)}
