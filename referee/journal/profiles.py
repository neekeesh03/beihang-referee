import json
from pathlib import Path
class JournalProfileStore:
    def __init__(self,root):self.root=Path(root)
    def list(self):return sorted(p.stem for p in self.root.glob('*.json'))
    def load(self,name):return json.loads((self.root/f'{name}.json').read_text(encoding='utf-8'))
