"""Existing local model endpoint, with an explicit timeout for longer analysis calls."""
import ast
import hashlib
import json
import os
from pathlib import Path
import urllib.request

ROOT=Path(__file__).resolve().parent.parent


def connection(timeout=180):
    settings={}
    for node in ast.parse((ROOT/'test.py').read_text()).body:
        if isinstance(node,ast.Assign):
            for target in node.targets:
                if isinstance(target,ast.Name) and target.id in {'LLM_BASE_URL','GATEWAY_TOKEN'}:
                    settings[target.id]=ast.literal_eval(node.value)
    token=os.environ.get('VLLM_API_KEY') or settings.get('GATEWAY_TOKEN','')
    if not token and (ROOT/'.env').exists():
        for line in (ROOT/'.env').read_text().splitlines():
            key,sep,value=line.strip().removeprefix('export ').partition('=')
            if sep and key.strip()=='VLLM_API_KEY':token=value.strip().strip('"\'');break
    url=settings['LLM_BASE_URL'].rstrip('/')
    def call(route,payload=None):
        req=urllib.request.Request(url+route,data=None if payload is None else json.dumps(payload).encode(),
             headers={'Content-Type':'application/json','Authorization':'Bearer '+token})
        with urllib.request.urlopen(req,timeout=timeout) as response:return json.load(response)
    return call,hashlib.sha256(url.encode()).hexdigest()
