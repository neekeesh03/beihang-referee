from pathlib import Path
import asyncio
from referee import ReviewConfig, ReviewEngine
from referee.providers import ScriptedLLMProvider
from referee.stages.base import Stage

class CountingStage(Stage):
    stage_id='counting'
    def __init__(self,counter): self.counter=counter
    async def run(self,ctx,state):
        self.counter['n']+=1
        state.final_review={'decision_brief':{}}


def test_resume_skips_completed_stages(tmp_path):
    p=tmp_path/'p.md'; p.write_text('paper',encoding='utf-8')
    counter={'n':0}
    cfg=ReviewConfig(mode='standard',run_root=str(tmp_path/'runs'),enable_journal_calibration=False)
    engine=ReviewEngine(llm=ScriptedLLMProvider(),config=cfg,package_root=str(Path(__file__).resolve().parents[2]),stages=[CountingStage(counter)])
    asyncio.run(engine.review([str(p)],run_id='r'))
    asyncio.run(engine.review([str(p)],run_id='r',resume=True))
    assert counter['n']==1
