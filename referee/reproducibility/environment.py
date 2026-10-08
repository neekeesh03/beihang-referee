from pathlib import Path
ENV_NAMES={'requirements.txt','pyproject.toml','poetry.lock','uv.lock','environment.yml','environment.yaml','renv.lock','project.toml','manifest.toml','dockerfile','compose.yml','compose.yaml','package-lock.json'}
def detect_environment_files(files):
    matches=[]
    for p in files:
        name=Path(p).name.lower()
        if name in ENV_NAMES:matches.append(str(p))
    return {'files':matches,'reproducible_environment_declared':bool(matches),'lockfile_present':any(Path(x).name.lower().endswith('.lock') or Path(x).name.lower()=='package-lock.json' for x in matches)}
