from __future__ import annotations
import hashlib, json, os, subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from .._resources import resource_root

BASE_RELEASE = "Beihang-Referee-Validation"


def _sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def sha_file(path: Path) -> str:
    return _sha_bytes(path.read_bytes())

def hash_tree(root: Path, *, patterns: tuple[str,...] = ("*",)) -> str:
    h=hashlib.sha256()
    files=[]
    for pattern in patterns:
        files.extend(p for p in root.rglob(pattern) if p.is_file())
    for p in sorted(set(files), key=lambda x:x.relative_to(root).as_posix()):
        rel=p.relative_to(root).as_posix().encode()
        h.update(rel+b"\0"+hashlib.sha256(p.read_bytes()).digest())
    return h.hexdigest()

def repo_root() -> Path:
    here=Path(__file__).resolve().parents[2]
    if (here/"pyproject.toml").exists(): return here
    return resource_root()

def runtime_code_sha256() -> str:
    # Python scientific runtime only; generated validation manifest/assets are excluded
    pkg=Path(__file__).resolve().parents[1]
    return hash_tree(pkg,patterns=("*.py",))

def _git_commit(root: Path) -> str | None:
    try:
        r=subprocess.run(["git","rev-parse","HEAD"],cwd=root,capture_output=True,text=True,timeout=3)
        return r.stdout.strip() if r.returncode==0 else None
    except Exception:return None

def frozen_components(root: Path|None=None) -> dict[str,Any]:
    root=root or repo_root(); assets=resource_root()
    core=assets/"core"; schemas=assets/"schemas" if (assets/"schemas").exists() else root/"schemas"; bench=assets/"benchmark_corpus" if (assets/"benchmark_corpus").exists() else root/"benchmark_corpus"; validation=assets/"validation" if (assets/"validation").exists() else root/"validation"
    files={
      "peer_review_prompt_sha256":sha_file(core/"PEER_REVIEW_PROMPT.md"),
      "verifier_prompt_sha256":sha_file(core/"INDEPENDENT_VERIFIER_PROMPT.md"),
      "core_reviewer_prompt_sha256":sha_file(core/"CORE_REVIEWER_PROMPT.md"),
      "specialist_executor_prompt_sha256":sha_file(core/"SPECIALIST_EXECUTOR_PROMPT.md"),
      "core_verifier_prompt_sha256":sha_file(core/"CORE_VERIFIER_PROMPT.md"),
      "diagnostic_scorecard_prompt_sha256":sha_file(core/"DIAGNOSTIC_SCORECARD_PROMPT.md"),
      "target_journal_calibrator_prompt_sha256":sha_file(core/"TARGET_JOURNAL_CALIBRATOR_PROMPT.md"),
      "evaluator_prompt_sha256":sha_file(core/"BENCHMARK_JUDGE_PROMPT.md"),
      "adjudicator_prompt_sha256":sha_file(core/"BENCHMARK_ADJUDICATOR_PROMPT.md"),
      "schemas_sha256":hash_tree(schemas,patterns=("*.json",)),
      "benchmark_manifest_sha256":hash_tree(bench,patterns=("*.jsonl","*.json","*.md")),
      "benchmark_gold_sha256":sha_file(bench/"structured_gold.jsonl"),
      "success_criteria_sha256":sha_file(validation/"SUCCESS_CRITERIA.json"),
      "runtime_code_sha256":runtime_code_sha256(),
    }
    defaults=root/"config"/"defaults.json"
    if defaults.exists(): files["runtime_defaults_sha256"]=sha_file(defaults)
    else:
        cfg=assets/"config"/"defaults.json"; files["runtime_defaults_sha256"]=sha_file(cfg) if cfg.exists() else None
    benchmark_profiles = (root/"config"/"benchmark_profiles") if (root/"config"/"benchmark_profiles").exists() else (assets/"config"/"benchmark_profiles")
    journal_profiles = (root/"config"/"journal_profiles") if (root/"config"/"journal_profiles").exists() else (assets/"config"/"journal_profiles")
    files["benchmark_profiles_sha256"] = hash_tree(benchmark_profiles, patterns=("*.json",)) if benchmark_profiles.exists() else None
    files["journal_profile_templates_sha256"] = hash_tree(journal_profiles, patterns=("*.json",)) if journal_profiles.exists() else None
    return files

def build_release_manifest(root: Path|None=None) -> dict[str,Any]:
    root=root or repo_root(); comp=frozen_components(root)
    return {
      "validation_release":BASE_RELEASE,
      "freeze_policy":"Protocol/gold/evaluator/code hashes are frozen before official benchmark result interpretation. Any material change creates a new experimental configuration.",
      "created_at":datetime.now(timezone.utc).isoformat(),
      "code_commit":_git_commit(root) or "uncommitted-source-bundle",
      **comp,
      "temperature":0.0,
      "required_model_configuration_fields":["review_model","verifier_model","judge_model_a","judge_model_b","adjudicator_model"],
      "required_search_configuration_fields":["search_backend","scholarly_providers"],
    }

def write_release_manifest(path: str|Path, root: Path|None=None) -> dict[str,Any]:
    data=build_release_manifest(root); Path(path).write_text(json.dumps(data,indent=2,ensure_ascii=False)+"\n",encoding="utf-8"); return data

def verify_release_manifest(path: str|Path|None=None) -> dict[str,Any]:
    assets=resource_root(); default=(assets/"validation"/"VALIDATION_RELEASE.json")
    p=Path(path) if path else default
    if not p.exists(): return {"valid":False,"errors":[f"missing frozen validation manifest: {p}"]}
    frozen=json.loads(p.read_text(encoding="utf-8")); current=frozen_components(repo_root()); errors=[]
    for k,v in current.items():
        if frozen.get(k)!=v: errors.append(f"frozen component changed: {k}")
    if frozen.get("validation_release")!=BASE_RELEASE: errors.append("unexpected validation release identity")
    return {"valid":not errors,"errors":errors,"manifest":frozen,"manifest_sha256":sha_file(p)}



def classify_evaluator_independence(review_model:str, verifier_model:str|None, judge_model_a:str, judge_model_b:str, adjudicator_model:str, *, family_map:dict[str,str]|None=None) -> dict[str,Any]:
    """Classify evaluator independence without overstating same-model validation.

    Model-family labels can be supplied by the caller; absent labels, distinct
    model identifiers qualify as cross-model but not cross-family.
    """
    verifier=verifier_model or review_model
    models={"review_model":review_model,"verifier_model":verifier,"judge_model_a":judge_model_a,"judge_model_b":judge_model_b,"adjudicator_model":adjudicator_model}
    judge_distinct=(judge_model_a!=review_model) or (judge_model_b!=review_model)
    if not judge_distinct:
        level="same_model_fresh_context"
    else:
        level="cross_model"
    if family_map:
        rf=family_map.get(review_model)
        jf={family_map.get(judge_model_a),family_map.get(judge_model_b)}-{None}
        if rf and jf and all(x!=rf for x in jf): level="cross_family"
    external_ok=level in {"cross_model","cross_family"}
    return {"level":level,**models,"external_independent_validation":external_ok,"label":"independent_validation" if external_ok else "internal_validation"}

def build_experiment_manifest(*,release_verification:dict[str,Any],review_model:str,verifier_model:str|None,judge_model_a:str,judge_model_b:str,adjudicator_model:str,search_backend:str,scholarly_providers:list[str],repeats:int,ablation_names:list[str],random_seed:int=0) -> dict[str,Any]:
    independence=classify_evaluator_independence(review_model,verifier_model,judge_model_a,judge_model_b,adjudicator_model)
    obj={
      "validation_release":BASE_RELEASE,
      "validation_release_manifest_sha256":release_verification.get("manifest_sha256"),
      "models":{"review_model":review_model,"verifier_model":verifier_model or review_model,"judge_model_a":judge_model_a,"judge_model_b":judge_model_b,"adjudicator_model":adjudicator_model},
      "evaluation_independence":independence,
      "temperature":0.0,"random_seed":random_seed,
      "search":{"search_backend":search_backend,"scholarly_providers":scholarly_providers},
      "repeats":repeats,"ablations":ablation_names,
      "frozen_component_hashes":{k:v for k,v in (release_verification.get("manifest") or {}).items() if k.endswith("_sha256")},
    }
    obj["experimental_configuration_id"]="EXP-"+_sha_bytes(json.dumps(obj,sort_keys=True,separators=(",",":")).encode())[:16]
    return obj
