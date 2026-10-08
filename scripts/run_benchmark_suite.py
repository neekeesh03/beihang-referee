from __future__ import annotations
import argparse,asyncio,json,os
from pathlib import Path
from referee import ReviewConfig,ReviewEngine
from referee.providers.openai_compatible import OpenAICompatibleProvider
from referee.providers.scholarly_search import FederatedScholarlySearchProvider
from referee.evals.full_suite import run_full_suite

def main():
    ap=argparse.ArgumentParser(description='Run Referee end-to-end hidden-gold benchmark suite')
    ap.add_argument('--model',default=os.getenv('REFEREE_MODEL'));ap.add_argument('--limit-per-corpus',type=int,default=10);ap.add_argument('--full',action='store_true');ap.add_argument('--output',default='benchmark_results.json');ap.add_argument('--with-literature',action='store_true');ap.add_argument('--mode',choices=['standard','deep','exhaustive'],default='deep');ap.add_argument('--repeats',type=int,default=1,help='Repeat initial-review cases to measure detection/severity stability')
    args=ap.parse_args()
    if not args.model:raise SystemExit('Pass --model or set REFEREE_MODEL')
    llm=OpenAICompatibleProvider(default_model=args.model)
    search=FederatedScholarlySearchProvider() if args.with_literature else None
    def factory(review_mode,run_root):
        cfg=ReviewConfig(mode=args.mode,review_mode=review_mode,run_root=str(run_root),model=args.model,enable_literature_search=args.with_literature,enable_journal_calibration=False)
        return ReviewEngine(llm=llm,search=search,config=cfg)
    result=asyncio.run(run_full_suite(factory,limit_per_corpus=None if args.full else args.limit_per_corpus,repeats=max(1,args.repeats)))
    Path(args.output).write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8');print(args.output)
if __name__=='__main__':main()
