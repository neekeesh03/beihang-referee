from __future__ import annotations
import argparse,asyncio,json,os
from pathlib import Path
from referee import ReviewConfig,ReviewEngine
from referee.providers.openai_compatible import OpenAICompatibleProvider
from referee.providers.scholarly_search import FederatedScholarlySearchProvider
from referee.stages import stages_for_mode
from referee.evals import load_corpus,run_end_to_end_cases
from referee.evals.ablation_runtime import StructuralOnlyProvenanceStage,BypassIndependentVerifierStage,AblationAdmissionStage

def build_stages(name):
    stages=stages_for_mode('initial')
    if name=='no_redteam_steelman':return [s for s in stages if s.stage_id!='09_redteam_steelman']
    if name=='no_evidence_entailment':return [StructuralOnlyProvenanceStage() if s.stage_id=='10_provenance_gate' else s for s in stages]
    if name=='no_independent_verifier':
        out=[]
        for s in stages:
            if s.stage_id=='11_concern_verification':out.append(BypassIndependentVerifierStage())
            elif s.stage_id=='12_concern_admission':out.append(AblationAdmissionStage())
            else:out.append(s)
        return out
    return stages

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--model',default=os.getenv('REFEREE_MODEL'));ap.add_argument('--limit',type=int,default=20);ap.add_argument('--output',default='ablation_results.json');ap.add_argument('--with-literature',action='store_true');args=ap.parse_args()
    if not args.model:raise SystemExit('Pass --model or set REFEREE_MODEL')
    llm=OpenAICompatibleProvider(default_model=args.model);search=FederatedScholarlySearchProvider() if args.with_literature else None;cases=load_corpus('scientific')[:args.limit]
    configs=['full_system','no_redteam_steelman','no_evidence_entailment','no_independent_verifier','no_literature_search','single_specialist']
    async def run():
        results={}
        for name in configs:
            def factory(run_root):
                cfg=ReviewConfig(mode='deep',run_root=str(run_root),model=args.model,enable_literature_search=args.with_literature and name!='no_literature_search',enable_journal_calibration=False,specialist_limit=1 if name=='single_specialist' else 10)
                return ReviewEngine(llm=llm,search=search,config=cfg,stages=build_stages(name))
            results[name]=await run_end_to_end_cases(cases,factory)
        return results
    result=asyncio.run(run());Path(args.output).write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8');print(args.output)
if __name__=='__main__':main()
