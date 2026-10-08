import difflib
def revision_diff(old:str,new:str)->dict:
    old_lines=old.splitlines();new_lines=new.splitlines();diff=list(difflib.unified_diff(old_lines,new_lines,lineterm=''))
    ratio=difflib.SequenceMatcher(None,old,new).ratio();added=sum(1 for x in diff if x.startswith('+') and not x.startswith('+++'));removed=sum(1 for x in diff if x.startswith('-') and not x.startswith('---'))
    return {'similarity':round(ratio,4),'added_lines':added,'removed_lines':removed,'diff':diff[:5000]}
