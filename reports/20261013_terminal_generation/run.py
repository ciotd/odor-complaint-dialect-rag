"""Generate the already audited terminal-retrieval requests, with frozen evidence."""
import importlib.util,json,shutil,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
AUDIT=ROOT/'reports/20261013_terminal_retrieval'
BASE=ROOT/'reports/20261012_construction_generation'
spec=importlib.util.spec_from_file_location('generation_runner',BASE/'run.py')
runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner);runner.HERE=HERE
read=runner.read;save=runner.save;sha=runner.sha

def prepare():
    assert not (HERE/'protocol.json').exists()
    for n,h in read(AUDIT/'current_hashes.json').items():assert sha(ROOT/n)==h,n
    for src,dst in [('jobs.json','jobs.json'),('retrieval.json','retrieval.json'),('baseline_analysis.json','analysis.json')]:
        shutil.copyfile(AUDIT/src,HERE/dst)
    shutil.copyfile(BASE/'final_outputs.json',HERE/'baseline_outputs.json')
    deps=list((ROOT/'kg_v2').glob('*.py'))+[ROOT/'kg_v2'/n for n in ['facts.jsonl','graph.json','advisory_rules.json']]
    hashes={}
    for p in deps:
        out=HERE/'snapshot'/p.name;out.parent.mkdir(exist_ok=True);shutil.copyfile(p,out);hashes[p.name]=sha(out)
    jobs=read(HERE/'jobs.json');old={j['id']:j for j in read(BASE/'jobs.json')}
    for j in jobs:
        before=old[j['id']]['request'];after=j['request']
        assert after['messages'][0]==before['messages'][0]
        assert {k:v for k,v in after.items() if k!='messages'}=={k:v for k,v in before.items() if k!='messages'}
    b=read(BASE/'protocol.json')
    save(HERE/'protocol.json',{'status':'prepared','inputs':len(jobs),'config':b['config'],
        'design':'Fresh generation after terminal-function retrieval repair; compare to construction baseline and full saved history.',
        'analysis_policy':'Reuse prior Qwen analysis and the audited current retrieval requests; no new analysis calls.',
        'quality_policy':b['quality_policy'],
        'snapshot_hashes':hashes,'job_sha256':sha(HERE/'jobs.json'),
        'baseline_path':str(BASE.relative_to(ROOT)),'baseline_sha256':sha(BASE/'final_outputs.json'),
        'baseline_endpoint_sha256':b['endpoint_sha256'],'analysis_calls':0,
        'baseline_runner_sha256':sha(BASE/'run.py'),
        'changed_requests':[j['id'] for j in jobs if j['request']!=old[j['id']]['request']],
        'target_style_prompt_added':False,
        'limitations':['Generation quality is separate from retrieval correctness.',
                      'Historical runs vary in KG, retrieval, prompt packaging and repair policy.',
                      'Style-only experiment is a side branch, not the primary control.',
                      'Same seed does not guarantee server determinism; no independent speaker gold.']})
    print('PREPARED70 audited requests; original system/model/settings retained; no age-profile sentence.',flush=True)

def generate():
    assert sha(BASE/'run.py')==read(HERE/'protocol.json')['baseline_runner_sha256']
    runner.generate()

if __name__=='__main__':globals()[sys.argv[1]]()
