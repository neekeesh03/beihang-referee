from __future__ import annotations
import json
from pathlib import Path


def create_app(run_root='runs'):
    try:
        from fastapi import FastAPI, HTTPException
        from fastapi.responses import HTMLResponse, FileResponse
        from fastapi.staticfiles import StaticFiles
    except ImportError as exc:
        raise RuntimeError('Server requires fastapi (`pip install .[server]`)') from exc
    from .models import PackageInspectRequest, RevisionCompareRequest, RebuttalAuditRequest, ConcernStatusRequest, AddNoteRequest
    from .events import read_events
    from ..ingestion import PackageInspector
    from ..comparison import revision_diff, audit_rebuttal_structure
    from ..documents import DocumentLoader
    from ..modes import ReviewModeRegistry
    from ..scholarly import ScholarlyRegistry
    from ..profiles import ProfileRegistry
    from ..lifecycle import RunRegistry, ReviewWorkspace
    from ..finalization import freeze_run, build_quality_snapshot
    from ..security.paths import safe_output_path
    from .._resources import resource_root

    app = FastAPI(title='Referee')
    root = Path(run_root)
    frontend = resource_root() / 'frontend'
    registry = RunRegistry(root)
    if frontend.exists():
        app.mount('/static', StaticFiles(directory=frontend), name='static')

    def run_dir(run_id: str) -> Path:
        p = safe_output_path(root, run_id)
        if not p.exists() or not p.is_dir():
            raise HTTPException(404, 'run not found')
        return p

    @app.get('/health')
    def health(): return {'status': 'ok'}

    @app.get('/capabilities')
    def capabilities():
        return {
            'review_modes': ReviewModeRegistry().names(),
            'profiles': ProfileRegistry().names(),
            'scholarly_providers': ScholarlyRegistry().names(),
            'package_inspection': True,
            'revision_diff': True,
            'rebuttal_audit': True,
            'human_workspace': True,
            'handoff_freeze': True,
        }

    @app.get('/runs')
    def runs(limit: int = 200):
        rows = registry.list(limit=limit)
        if not rows:
            registry.rebuild(); rows = registry.list(limit=limit)
        return rows

    @app.get('/runs/{run_id}')
    def run(run_id: str):
        p = run_dir(run_id) / 'state.json'
        if not p.exists(): raise HTTPException(404, 'run state not found')
        return json.loads(p.read_text(encoding='utf-8'))

    @app.get('/runs/{run_id}/summary')
    def summary(run_id: str):
        d = run_dir(run_id)
        p = d / 'state.json'
        if not p.exists(): raise HTTPException(404, 'run state not found')
        state = json.loads(p.read_text(encoding='utf-8'))
        workspace = ReviewWorkspace(d).load()
        return build_quality_snapshot(state, workspace)

    @app.get('/runs/{run_id}/events')
    def events(run_id: str, limit: int = 200):
        return read_events(run_dir(run_id) / 'events.jsonl', limit=max(1, min(limit, 2000)))

    @app.get('/runs/{run_id}/workspace')
    def workspace(run_id: str): return ReviewWorkspace(run_dir(run_id)).load()

    @app.post('/runs/{run_id}/notes')
    def add_note(run_id: str, req: AddNoteRequest):
        return ReviewWorkspace(run_dir(run_id)).add_note(req.text, author=req.author)

    @app.post('/runs/{run_id}/concerns/{concern_id}/status')
    def concern_status(run_id: str, concern_id: str, req: ConcernStatusRequest):
        try:
            return ReviewWorkspace(run_dir(run_id)).set_concern_status(concern_id, req.status, note=req.note)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc

    @app.get('/runs/{run_id}/artifacts')
    def artifacts(run_id: str):
        d = run_dir(run_id) / 'artifacts'
        if not d.exists(): raise HTTPException(404, 'run artifacts not found')
        return [{'name': p.name, 'bytes': p.stat().st_size} for p in sorted(d.iterdir()) if p.is_file()]

    @app.get('/runs/{run_id}/artifacts/{name}')
    def artifact(run_id: str, name: str):
        d = run_dir(run_id) / 'artifacts'
        try:
            p = safe_output_path(d, name)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        if not p.exists() or not p.is_file(): raise HTTPException(404, 'artifact not found')
        return FileResponse(p)

    @app.post('/runs/{run_id}/finalize')
    def finalize(run_id: str):
        try:
            return freeze_run(run_dir(run_id))
        except (ValueError, FileNotFoundError) as exc:
            raise HTTPException(400, str(exc)) from exc

    @app.post('/inspect-package')
    def inspect_package(req: PackageInspectRequest): return PackageInspector().inspect(req.paths).to_dict()

    @app.post('/compare-revision')
    def compare_revision(req: RevisionCompareRequest):
        loader = DocumentLoader(); return revision_diff(loader.load(req.old_path).text, loader.load(req.new_path).text)

    @app.post('/audit-rebuttal')
    def audit_rebuttal(req: RebuttalAuditRequest): return audit_rebuttal_structure(DocumentLoader().load(req.response_path).text)

    @app.get('/', response_class=HTMLResponse)
    def index():
        fp = frontend / 'index.html'
        return FileResponse(fp) if fp.exists() else HTMLResponse('<h1>Referee</h1><p>Use <code>/runs</code> and <code>/docs</code>.</p>')
    return app
