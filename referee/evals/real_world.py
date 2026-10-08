from __future__ import annotations
import json
from pathlib import Path
from .scoring import match_gold


def load_adjudicated_benchmark(path:str|Path)->list[dict]:
    rows=[json.loads(x) for x in Path(path).read_text(encoding="utf-8").splitlines() if x.strip()]
    for r in rows:
        if not r.get("paper_id") or not isinstance(r.get("atomic_concerns"),list):raise ValueError("Each real-paper row requires paper_id and atomic_concerns")
        for c in r["atomic_concerns"]:
            if not (c.get("required_mechanism_concepts") or c.get("category")):
                raise ValueError("Real-paper atomic concerns require structured mechanism concepts/category; lexical-only judging is prohibited")
    return rows


def evaluate_real_paper_row(gold_row:dict,predicted:list[dict])->dict:
    hits=[]
    for gold in gold_row["atomic_concerns"]:
        match,score=match_gold(gold,gold.get("category"),predicted);hits.append({"gold_id":gold.get("concern_id"),"matched":bool(match and score>0),"mechanism_confidence":score,"predicted_concern_id":match.get("concern_id") if match else None})
    recall=sum(x["matched"] for x in hits)/max(1,len(hits));matched_ids={x["predicted_concern_id"] for x in hits if x["matched"]};precision=len(matched_ids)/max(1,len(predicted))
    return {"paper_id":gold_row["paper_id"],"atomic_concern_recall":round(recall,4),"major_concern_precision":round(precision,4),"matches":hits,"lexical_similarity_used":False}
