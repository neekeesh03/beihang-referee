import csv
def export_concerns_csv(concerns,path):
    fields=['concern_id','severity','title','claim_ids','evidence_anchor_ids','failure_mechanism','scientific_consequence','minimum_resolution','closure_criterion','reviewer_confidence','steelman','steelman_survival_reason','status']
    with open(path,'w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
        for c in concerns:
            row={k:c.get(k,'') for k in fields};row['claim_ids']=';'.join(row['claim_ids']) if isinstance(row['claim_ids'],list) else row['claim_ids'];row['evidence_anchor_ids']=';'.join(row['evidence_anchor_ids']) if isinstance(row['evidence_anchor_ids'],list) else row['evidence_anchor_ids'];w.writerow(row)
