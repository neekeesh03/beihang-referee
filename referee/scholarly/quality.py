def source_quality(record)->dict:
    score=0;reasons=[]
    if getattr(record,'doi',None):score+=2;reasons.append('doi')
    if getattr(record,'abstract',None):score+=1;reasons.append('abstract')
    if getattr(record,'venue',None):score+=1;reasons.append('venue')
    if getattr(record,'authors',None):score+=1;reasons.append('authors')
    if getattr(record,'year',None):score+=1;reasons.append('year')
    return {'score':score,'max_score':6,'signals':reasons,'grade':'high' if score>=5 else 'moderate' if score>=3 else 'low'}
