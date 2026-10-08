from __future__ import annotations
import argparse,json
from pathlib import Path
from referee.evals import prepare_blinded_study

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--system',action='append',required=True,help='name=JSON file containing a concern list');ap.add_argument('--out',default='expert_study');ap.add_argument('--seed',type=int,default=17);args=ap.parse_args();systems={}
    for item in args.system:
        name,path=item.split('=',1);obj=json.loads(Path(path).read_text());systems[name]=obj.get('major_comments',obj.get('admitted_concerns',obj)) if isinstance(obj,dict) else obj
    print(json.dumps(prepare_blinded_study(systems,args.out,seed=args.seed),indent=2))
if __name__=='__main__':main()
