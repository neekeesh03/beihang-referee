from __future__ import annotations
import argparse,asyncio,json,os,tempfile,time
from pathlib import Path
from referee import ReviewConfig,ReviewEngine
from referee.providers.openai_compatible import OpenAICompatibleProvider
from referee.providers.scholarly_search import FederatedScholarlySearchProvider
from referee.evals import load_corpus,evaluate_counterfactual_pair

def main():
    ap=argparse.ArgumentParser(description='Run paired defect->fixed counterfactual benchmark');ap.add_argument('--model',default=os.getenv('REFEREE_MODEL'));ap.add_argument('--limit',type=int,default=20);ap.add_argument('--full',action='store_true');ap.add_argument('--output',default='mutation_results.json');ap.add_argument('--with-literature',action='store_true');args=ap.parse_args()
    if not args.model:raise SystemExit('Pass --model or set REFEREE_MODEL')
    llm=OpenAICompatibleProvider(default_model=args.model);search=FederatedScholarlySearchProvider() if args.with_literature else None
    pairs=load_corpus('revision');sources={r['case_id']:r for r in load_corpus('scientific')};pairs=pairs if args.full else pairs[:args.limit]
    async def run():
        rows=[]
        with tempfile.TemporaryDirectory(prefix='referee-mutation-') as td:
            base=Path(td)
            for i,pair in enumerate(pairs):
                source=sources.get(pair.get('source_case'))
                if not source:continue
                states=[]
                for label,text in [('defective',pair['old_text']),('fixed',pair['new_text'])]:
                    p=base/f'{i}-{label}.md';p.write_text(text,encoding='utf-8')
                    cfg=ReviewConfig(mode='deep',run_root=str(base/'runs'),model=args.model,enable_literature_search=args.with_literature,enable_journal_calibration=False)
                    state=await ReviewEngine(llm=llm,search=search,config=cfg).review([str(p)],query='Counterfactual mutation benchmark')
                    states.append(state)
                r=evaluate_counterfactual_pair(source['gold_concern'],source['category'],states[0].admitted_concerns,states[1].admitted_concerns);r['pair_id']=pair['pair_id'];rows.append(r)
        return {'pairs':len(rows),'causal_sensitivity_rate':round(sum(x['causal_sensitivity_pass'] for x in rows)/max(1,len(rows)),4),'rows':rows,'gold_hidden_from_review_pipeline':True}
    result=asyncio.run(run());Path(args.output).write_text(json.dumps(result,indent=2),encoding='utf-8');print(args.output)
if __name__=='__main__':main()
