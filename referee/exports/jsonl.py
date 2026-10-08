import json
def write_jsonl(items,path):
    with open(path,'w',encoding='utf-8') as f:
        for x in items:f.write(json.dumps(x,ensure_ascii=False,default=str)+'\n')
