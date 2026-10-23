"""Audit all tracked Markdown repository links; external websites are out of scope."""
import json,re,subprocess,urllib.parse,unicodedata
from pathlib import Path
from functools import lru_cache
ROOT=Path(__file__).resolve().parents[1];REPO='ciotd/odor-complaint-dialect-rag'
tracked=set(subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).decode().split('\0'))
md=sorted(x for x in tracked if x.endswith('.md'))
@lru_cache(None)
def git_text(ref,path):
 r=subprocess.run(['git','show',f'{ref}:{path}'],capture_output=True,cwd=ROOT)
 return r.stdout.decode(errors='replace') if r.returncode==0 else None
@lru_cache(None)
def git_exists(ref,path):return subprocess.run(['git','cat-file','-e',f'{ref}:{path}'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,cwd=ROOT).returncode==0

def slug(s):
 s=re.sub(r'!?(?:\[([^]]+)\])\([^)]*\)',r'\1',s)
 s=re.sub(r'<[^>]+>','',s).strip().lower()
 return ''.join('-'if c.isspace()else c for c in s if c.isspace() or c in '_-' or unicodedata.category(c)[0]in 'LNM')
@lru_cache(None)
def anchors(text):
 out=set();counts={};fence=False
 lines=text.splitlines()
 for i,line in enumerate(lines):
  if re.match(r'^\s*(`{3,}|~{3,})',line):fence=not fence;continue
  if fence:continue
  m=re.match(r'^ {0,3}#{1,6}\s+(.*?)\s*#*$',line)
  heading=m.group(1)if m else lines[i-1]if i and re.match(r'^ {0,3}(=+|-+)\s*$',line)and lines[i-1].strip()else None
  if heading is not None:
   base=slug(heading);n=counts.get(base,0);counts[base]=n+1;out.add(base+(f'-{n}'if n else ''))
 out.update(re.findall(r'(?:id|name)=["\x27]([^"\x27]+)',text))
 return out

def links(text):
 # Repository documents use inline links plus a few reference definitions.
 fenced=False
 for lineno,line in enumerate(text.splitlines(),1):
  if re.match(r'^\s*(`{3,}|~{3,})',line):fenced=not fenced;continue
  if fenced:continue
  for m in re.finditer(r'\]\((<[^>]+>|(?:[^()\\]|\\.|\([^()]*\))+?)\)',line):
   raw=m.group(1);dest=raw[1:-1]if raw.startswith('<')else re.sub(r'\s+["\x27].*$', '',raw)
   yield lineno,dest,m.start(1),m.end(1)
  for m in re.finditer(r'(?:href|src)=["\x27]([^"\x27]+)',line):yield lineno,m.group(1),m.start(1),m.end(1)
  m=re.match(r'^ {0,3}\[[^]]+\]:\s*(<[^>]+>|\S+)',line)
  if m:yield lineno,m.group(1).strip('<>'),m.start(1),m.end(1)

def check(file,dest):
 u=urllib.parse.urlsplit(dest);frag=urllib.parse.unquote(u.fragment);path=urllib.parse.unquote(u.path)
 if u.scheme in {'http','https'}:
  if u.netloc not in {'github.com','www.github.com'}or not path.startswith('/'+REPO+'/'):return {'status':'external_not_checked'}
  bits=path[len('/'+REPO+'/'):].split('/',2)
  if len(bits)<2 or bits[0]not in {'blob','tree'}:return {'status':'external_not_checked'}
  ref=bits[1];target=bits[2]if len(bits)>2 else ''
  if not target:return {'status':'git_history','target':target,'ref':ref}
  if not git_exists(ref,target):return {'status':'missing_git_path','target':target,'ref':ref}
  body=git_text(ref,target)if frag and bits[0]=='blob'else None
  status='git_history'
 elif u.scheme:return {'status':'non_file_scheme'}
 else:
  targetpath=(ROOT/file).parent/path if path else ROOT/file
  if path.startswith('/'):targetpath=ROOT/path.lstrip('/')
  targetpath=targetpath.resolve()
  try:target=str(targetpath.relative_to(ROOT))
  except ValueError:return {'status':'outside_repository','target':str(targetpath)}
  if not targetpath.exists():return {'status':'missing_local_path','target':target}
  published=target in tracked or targetpath.is_dir()and any(f.startswith(target.rstrip('/')+'/')for f in tracked)
  if not published:return {'status':'local_only_not_published','target':target}
  body=targetpath.read_text(errors='replace')if frag and targetpath.is_file()else None
  status='local_ok';ref=None
 if frag and body is not None:
  m=re.fullmatch(r'L(\d+)(?:-L?(\d+))?',frag)
  if m:
   if max(map(int,[g for g in m.groups()if g]))>len(body.splitlines()):status='missing_line_anchor'
  elif target.endswith('.md')and frag not in anchors(body)and frag.removeprefix('user-content-')not in anchors(body):status='missing_heading_anchor'
 return {'status':status,'target':target,**({'ref':ref}if ref else {})}

def audit():
 rows=[]
 for file in md:
  text=(ROOT/file).read_text()
  for line,dest,_,_ in links(text):rows.append({'file':file,'line':line,'destination':dest,**check(file,dest)})
 from collections import Counter
 return {'scope':'All Git-tracked Markdown; local targets must also be tracked for public links. Repository Git URLs and heading/line anchors are checked against local Git objects. External HTTP availability is not checked.','markdown_files':len(md),'links':len(rows),'counts':dict(Counter(r['status']for r in rows)),'rows':rows}
if __name__=='__main__':
 import sys
 result=audit();out=Path(sys.argv[1]if len(sys.argv)>1 else str(ROOT/'reports/markdown_link_audit.json'));out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print({k:v for k,v in result.items()if k!='rows'})
 for r in result['rows']:
  if r['status']not in {'local_ok','git_history','external_not_checked','non_file_scheme'}:print(r['status'],r['file']+':'+str(r['line']),r['destination'])

 if any(r["status"] not in {"local_ok","git_history","external_not_checked","non_file_scheme"} for r in result["rows"]):sys.exit(1)
