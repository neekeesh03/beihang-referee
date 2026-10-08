from __future__ import annotations
async def get_json(url:str,*,params:dict|None=None,headers:dict|None=None,timeout:float=20.0):
    try:import httpx
    except ImportError as exc:raise RuntimeError('HTTP scholarly providers require httpx') from exc
    async with httpx.AsyncClient(timeout=timeout,follow_redirects=True,headers=headers) as client:
        r=await client.get(url,params=params);r.raise_for_status();return r.json()
async def get_text(url:str,*,params:dict|None=None,headers:dict|None=None,timeout:float=20.0):
    try:import httpx
    except ImportError as exc:raise RuntimeError('HTTP scholarly providers require httpx') from exc
    async with httpx.AsyncClient(timeout=timeout,follow_redirects=True,headers=headers) as client:
        r=await client.get(url,params=params);r.raise_for_status();return r.text
