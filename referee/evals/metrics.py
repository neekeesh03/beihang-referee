def classification_metrics(rows):
    tp=sum(r['gold'] and r['pred'] for r in rows);fp=sum((not r['gold']) and r['pred'] for r in rows);fn=sum(r['gold'] and (not r['pred']) for r in rows);tn=sum((not r['gold']) and (not r['pred']) for r in rows)
    precision=tp/max(1,tp+fp);recall=tp/max(1,tp+fn);f1=2*precision*recall/max(1e-12,precision+recall)
    return {'tp':tp,'fp':fp,'fn':fn,'tn':tn,'precision':precision,'recall':recall,'f1':f1,'accuracy':(tp+tn)/max(1,len(rows))}
