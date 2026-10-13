"""One-factor prompt experiment: frozen requests plus one speaker-profile sentence."""
import copy,hashlib,importlib.util,json,shutil,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
BASE=ROOT/'reports/20261012_construction_generation'
ADDITION='목표 말투는 경북 지역의 40대 이상 화자가 사용하는 사투리입니다.'
spec=importlib.util.spec_from_file_location('frozen_generation_runner',BASE/'run.py')
runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)
runner.HERE=HERE
read=runner.read;save=runner.save;sha=runner.sha

def prepare():
    assert not (HERE/'protocol.json').exists()
    baseline=read(BASE/'protocol.json');assert baseline['status']=='completed'
    old=read(BASE/'jobs.json');new=copy.deepcopy(old)
    checks=[]
    for before,after in zip(old,new):
        after['condition']='gyeongbuk40_system_only'
        messages=after['request']['messages']
        assert messages[0]['role']=='system'
        messages[0]['content']+='\n'+ADDITION
        restored=copy.deepcopy(after['request'])
        restored['messages'][0]['content']=before['request']['messages'][0]['content']
        assert restored==before['request']
        assert after['request']['messages'][1:]==before['request']['messages'][1:]
        checks.append({'id':after['id'],'only_system_suffix_changed':True,
                       'user_message_identical':True,'model_and_sampling_identical':True})
    save(HERE/'jobs.json',new);save(HERE/'request_diff_audit.json',checks)
    for name in ['analysis.json','retrieval.json']:
        shutil.copyfile(BASE/name,HERE/name)
    shutil.copyfile(BASE/'final_outputs.json',HERE/'baseline_outputs.json')
    shutil.copytree(BASE/'snapshot',HERE/'snapshot')
    cfg=copy.deepcopy(baseline['config']);cfg['system_prompt']+='\n'+ADDITION
    save(HERE/'protocol.json',{
        'status':'prepared','config':cfg,'inputs':len(new),'added_system_sentence':ADDITION,
        'design':'Change only system speaker profile; same frozen user messages, KG retrieval, model and sampling.',
        'analysis_policy':'Reuse exact previous analysis AND morphology/retrieval/user messages; no new retrieval.',
        'quality_policy':baseline['quality_policy'],
        'primary_comparison':'first output vs previous first output; final selected output comparison is secondary',
        'snapshot_hashes':baseline['snapshot_hashes'],'job_sha256':sha(HERE/'jobs.json'),
        'baseline_path':str(BASE.relative_to(ROOT)),'baseline_sha256':sha(BASE/'final_outputs.json'),
        'baseline_jobs_sha256':sha(BASE/'jobs.json'),'baseline_runner_sha256':sha(BASE/'run.py'),
        'baseline_endpoint_sha256':baseline['endpoint_sha256'],
        'frozen_files_sha256':{n:sha(HERE/n) for n in ['analysis.json','retrieval.json','baseline_outputs.json']},
        'analysis_calls':0,'changed_requests':[j['id'] for j in new],
        'limitations':['One historical baseline and one treatment run, not repeated randomized trials.',
                      'Same seed does not guarantee endpoint determinism.',
                      'Speaker age/region authenticity requires speaker assessment; automatic flags are not accuracy.',
                      'Repair logic is identical but the number and content of repairs depend on first outputs.']})
    print('PREPARED70: only system suffix changed;70 user messages and all generation parameters identical.',flush=True)

def generate():
    p=read(HERE/'protocol.json')
    assert sha(BASE/'run.py')==p['baseline_runner_sha256']
    assert sha(BASE/'jobs.json')==p['baseline_jobs_sha256']
    for name,h in p['frozen_files_sha256'].items():assert sha(HERE/name)==h
    runner.generate()

if __name__=='__main__':globals()[sys.argv[1]]()
