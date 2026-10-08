def calibration_report(reviewer_outputs:list[dict])->dict:
    majors=[sum(1 for c in r.get('concerns',[]) if c.get('severity') == 'major') for r in reviewer_outputs]
    if not majors:return {'status':'no_outputs'}
    mean=sum(majors)/len(majors);spread=max(majors)-min(majors)
    return {'mean_major_comments':mean,'range_major_comments':[min(majors),max(majors)],'severity_dispersion':spread,'flag':spread>=5}
