from __future__ import annotations
from referee.stages.base import Stage
from referee.contracts import normalize_concern
from referee.validation import validate_major_comment
from referee.verification import verify_anchor_integrity, assess_closure_test

class StructuralOnlyProvenanceStage(Stage):
    stage_id='10_provenance_gate'
    async def run(self,ctx,state):
        anchors={a.get('anchor_id') for a in state.evidence_anchors if isinstance(a,dict)}
        claims={c.get('claim_id') for c in state.claims if isinstance(c,dict)}
        integrity=verify_anchor_integrity(state.evidence_anchors,state.document_map.get('documents',[]))
        imap={r.get('anchor_id'):r for r in integrity.get('anchors',[])}
        passed=[];rejected=[]
        for raw in state.proposed_concerns:
            c=normalize_concern(raw);errors=validate_major_comment(c,anchors,claims)
            for aid in c.get('evidence_anchor_ids',[]):
                if (imap.get(aid) or {}).get('status') not in {'verified','external_verified'}:
                    errors.append(f'anchor integrity failed: {aid}')
            if not assess_closure_test(c.get('closure_criterion','')).get('actionable'):
                errors.append('closure criterion not actionable')
            c['provenance_gate']={'status':'passed' if not errors else 'failed','errors':errors,'ablation':'no_evidence_entailment'}
            (passed if not errors else rejected).append(c)
        state.provenance_candidates=passed;state.rejected_concerns.extend(rejected)

class BypassIndependentVerifierStage(Stage):
    stage_id='11_concern_verification'
    async def run(self,ctx,state):
        state.verification_candidates=list(state.provenance_candidates)
        state.verification_records=[]
        for c in state.verification_candidates:
            state.verification_records.append({'concern_id':c.get('concern_id'),'verification_status':'verified','ablation_bypass':True})

class AblationAdmissionStage(Stage):
    stage_id='12_concern_admission'
    async def run(self,ctx,state):
        state.admitted_concerns=[]
        for c in state.verification_candidates[:ctx.config.max_major_comments]:
            c=dict(c);c['status']='admitted_ablation';state.admitted_concerns.append(c)
        ctx.checkpoints.write_artifact('concern_admission_log.json', {'admitted': state.admitted_concerns, 'rejected': state.rejected_concerns, 'ablation': True})

class SteelmanOnlyAblationStage(Stage):
    """Keep adversarial self-checking but prohibit creation of new red-team concerns."""
    stage_id='09_redteam_steelman'
    async def run(self,ctx,state):
        import json
        from referee.stages.core import _call
        from referee.contracts import schemas as S
        out=await _call(ctx,'ablation_steelman_only','You are a steelman analyst. Do not invent any new concern. For each supplied concern, return the same concern_id with the strongest reasonable author-favorable interpretation and whether the existing concern survives.','Return the canonical concerns array only for the supplied concerns. Do not add concerns.\n'+json.dumps(state.proposed_concerns,ensure_ascii=False)[:26000],schema=S.REDTEAM_RESULT,agent_id='ablation-steelman-only')
        if not isinstance(out,dict): return
        by_id={c.get('concern_id'):c for c in state.proposed_concerns if c.get('concern_id')}
        by_local={c.get('source_local_id'):c for c in state.proposed_concerns if c.get('source_local_id')}
        for raw in out.get('concerns',[]):
            target=by_id.get(raw.get('concern_id')) or by_local.get(raw.get('concern_id'))
            if target:
                for k in ('steelman','steelman_survives','steelman_survival_reason'):
                    if k in raw: target[k]=raw[k]

class RedTeamOnlyAblationStage(Stage):
    """Generate adversarial concerns without a substantive steelman reasoning pass."""
    stage_id='09_redteam_steelman'
    async def run(self,ctx,state):
        import json
        from referee.stages.core import _call, _append_proposed_concern
        from referee.contracts import schemas as S
        from referee.validation.identifiers import append_evidence_anchors, anchor_alias_map, claim_alias_map, remap_concern_references
        out=await _call(ctx,'ablation_redteam_only','Red-team the central scientific claims. Do not perform a steelman analysis. Populate required steelman fields with the literal placeholder [disabled by ablation] so downstream structural contracts remain comparable.','Claims:\n'+json.dumps(state.claims,ensure_ascii=False)[:10000]+'\nExisting concerns:\n'+json.dumps(state.proposed_concerns,ensure_ascii=False)[:18000],schema=S.REDTEAM_RESULT,agent_id='ablation-redteam-only')
        if not isinstance(out,dict): return
        amap=append_evidence_anchors(state,out.get('evidence_anchors',[]),source_stage='REDTEAM_ABLATION',reviewer_id='redteam-only')
        for raw in out.get('concerns',[]):
            c=remap_concern_references(raw,claim_map=claim_alias_map(state),anchor_map={**anchor_alias_map(state),**amap})
            c['steelman']='[disabled by ablation]';c['steelman_survives']=True;c['steelman_survival_reason']='[disabled by ablation]'
            _append_proposed_concern(state,c,source_agent='ablation_redteam_only',trace={},anchor_map=amap)
