from __future__ import annotations
from .roster import REVIEWER_ROSTER

def route_reviewers(classification:dict,claims:list[dict],limit:int=16)->list[str]:
    requested=list(classification.get('specialists') or [])
    text=' '.join(str(x) for x in [classification]+claims).lower()
    rules=[
        ('randomized','rct_intervention'),('randomised','rct_intervention'),('cohort','observational_epidemiology'),('diagnostic','diagnostic_prognostic'),
        ('qualitative','qualitative'),('meta-analysis','systematic_review_meta'),('simulation','simulation'),('machine learning','ml_ai'),('neural','ml_ai'),('instrument','measurement_instrument'),
        ('electrochem','electrochemistry_fuel_cells'),('fuel cell','electrochemistry_fuel_cells'),('microbial fuel','electrochemistry_fuel_cells'),('mfc','electrochemistry_fuel_cells'),
        ('materials','materials_characterization'),('sem','materials_characterization'),('xrd','materials_characterization'),('raman','materials_characterization'),('ftir','materials_characterization'),
        ('wastewater','environmental_process'),('water treatment','environmental_process'),('reactor','environmental_process'),('hydraulic retention','environmental_process'),
        ('biofilm','microbiology_omics'),('microbiome','microbiology_omics'),('16s','microbiology_omics'),('metagenom','microbiology_omics'),
        ('life cycle','energy_lca_tea'),('techno-economic','energy_lca_tea'),('net energy','energy_lca_tea'),
        ('finite element','computational_science'),('cfd','computational_science'),('numerical model','computational_science'),
        ('machine learning','ml_science'),('deep learning','ml_science'),('artificial intelligence','ml_science'),
        ('calibration','metrology_measurement'),('limit of detection','metrology_measurement'),('uncertainty budget','metrology_measurement'),
    ]
    base=['methods_design','statistics_causal','literature_novelty','numerical_equation_auditor','figures_tables','reporting_guidelines']
    out=[]
    for r in requested+base+[v for k,v in rules if k in text]:
        if r in REVIEWER_ROSTER and r not in out:out.append(r)
    return out[:limit]
