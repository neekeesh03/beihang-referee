from .base import ReviewModeSpec
MODES={
'initial':ReviewModeSpec('initial','First-pass scientific peer review',('manuscript',),('review','evidence_graph')),
'revision':ReviewModeSpec('revision','Audit a revised manuscript against an earlier version',('manuscript','prior_manuscript'),('revision_matrix','review'),True,False),
'rebuttal':ReviewModeSpec('rebuttal','Audit author response against reviewer comments and revision',('manuscript','reviewer_comments','rebuttal'),('response_audit','unresolved_comments'),True,True),
'meta_review':ReviewModeSpec('meta_review','Synthesize multiple reviewer reports without inventing consensus',('reviewer_comments',),('disagreement_map','meta_review')),
'editorial_screen':ReviewModeSpec('editorial_screen','Pre-review scientific completeness and fatal-flaw screen',('manuscript',),('screening_report','missing_artifacts')),
'reproducibility':ReviewModeSpec('reproducibility','Audit data/code/environment/package reproducibility',('manuscript',),('reproducibility_report',)),
}
class ReviewModeRegistry:
    def names(self):return sorted(MODES)
    def get(self,name):
        if name not in MODES:raise KeyError(name)
        return MODES[name]
