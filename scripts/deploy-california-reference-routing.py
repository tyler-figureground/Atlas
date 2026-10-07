"""Preview/apply the reference instructions without downgrading deployed Atlas rules."""
from __future__ import annotations
import argparse,datetime,difflib,hashlib,json,os,pathlib,shutil,sys,tempfile,zipfile

REPO=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(REPO/'tools/atlas/src'))
from atlas.core.conform import Action,Plan,BACKFILL,DONE,SKIPPED,apply_plan
from atlas.core.mapfile import find_map,load_map
from atlas.core.ops import mkdir_below
from atlas.core.projectmd import AGENTS_BEGIN,AGENTS_END,with_agents_block,agents_block_current

HEADING='## California permit requirements'
def digest(b):return hashlib.sha256(b).hexdigest()
def without_section(text):
    if HEADING not in text:return text
    start=text.index(HEADING);end=text.find('\n## ',start+len(HEADING))
    return text[:start]+(text[end+1:] if end>=0 else '')
def meaningful(text):return [s.rstrip() for s in text.splitlines() if s.strip()]
def outside(text):
    a=text.index(AGENTS_BEGIN);b=text.index(AGENTS_END)+len(AGENTS_END)
    return text[:a],text[b:]

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--drive',type=pathlib.Path,required=True)
    p.add_argument('--wheel',type=pathlib.Path,required=True)
    p.add_argument('--apply',action='store_true');a=p.parse_args()
    root=a.drive.resolve();m=load_map(find_map(root))
    assert m.agents_rules=='agents-rules.md'
    canonical=(REPO/'tools/atlas/src/atlas/templates/project/agents-rules.md').read_text(encoding='utf-8')
    section=canonical[canonical.index(HEADING):canonical.index('## After every meeting')]
    templates={}
    with zipfile.ZipFile(a.wheel) as z:
        for name in z.namelist():
            if name.startswith('atlas/templates/project/') and name.endswith('.md'):
                templates[pathlib.PurePosixPath(name).name]=z.read(name)
    live=templates['agents-rules.md'].decode('utf-8-sig').replace('\r\r\n','\n').replace('\r\n','\n')
    live=without_section(live)
    assert '## After every meeting' in live
    templates['agents-rules.md']=live.replace('## After every meeting',section+'## After every meeting',1).encode('utf-8')
    stamp=datetime.datetime.now().strftime('%y%m%d-%H%M%S')
    report={'timestamp':stamp,'drive':str(root),'wheel':str(a.wheel),'wheel_sha256':digest(a.wheel.read_bytes()),'applied':a.apply,'projects':[]}
    with tempfile.TemporaryDirectory(prefix='atlas-reference-') as td:
        stage=pathlib.Path(td)
        for name,data in templates.items():(stage/name).write_bytes(data)
        os.environ['ATLAS_TEMPLATES']=str(stage)
        pending=[]
        # Only live top-level project roots. Never descend into archives or other sections.
        for project in sorted(root.iterdir()):
            if not project.is_dir() or project.name.startswith(('_','00 ')) or not (project/'PROJECT.md').is_file():continue
            path=project/m.agents_file;raw=path.read_bytes();text=raw.decode('utf-8-sig')
            assert (project/m.claude_file).read_text(encoding='utf-8-sig').strip()=='@AGENTS.md',project
            proposed='\n'.join(with_agents_block(text.splitlines(),m))+'\n'
            # A full block refresh must add only this section, never remove live rules.
            if meaningful(without_section(proposed))!=meaningful(without_section(text)):
                diff=''.join(difflib.unified_diff(without_section(text).splitlines(True),without_section(proposed).splitlines(True)))
                raise RuntimeError('Unrelated rule drift in '+str(project)+'\n'+diff)
            assert tuple(map(meaningful,outside(proposed)))==tuple(map(meaningful,outside(text)))
            fact_hash=digest((project/'PROJECT.md').read_bytes())
            pending.append((project,raw,text,proposed,fact_hash))
            report['projects'].append({'project':project.name,'path':str(path),'before_sha256':digest(raw),'project_facts_sha256':fact_hash,'change':'add California reference routing' if HEADING not in text else 'refresh California reference routing'})
        print(json.dumps({'preview_projects':len(pending),'only_new_section':True,'apply':a.apply}),flush=True)
        if a.apply:
            overlay=root/'_tools/atlas/templates'
            mkdir_below(root,'_tools/atlas/templates')
            backup_rel=f'_tools/atlas/deploy-backups/{stamp}'
            mkdir_below(root,backup_rel)
            for name,data in templates.items():
                target=overlay/name
                if target.exists():shutil.copy2(target,root/backup_rel/name)
                target.write_bytes(data)
            launcher=root/'_tools/Atlas.bat';raw=launcher.read_bytes()
            shutil.copy2(launcher,root/backup_rel/'Atlas.bat')
            text=raw.decode('utf-8-sig')
            line='set "ATLAS_TEMPLATES=%~dp0atlas\\templates"'
            if line not in text:
                text=text.replace('where uv >nul 2>nul',line+'\n\nwhere uv >nul 2>nul')
                launcher.write_bytes(text.replace('\r\n','\n').replace('\n','\r\n').encode('utf-8'))
            os.environ['ATLAS_TEMPLATES']=str(overlay)
            for row,(project,raw,text,proposed,fact_hash) in zip(report['projects'],pending):
                target=project/m.agents_file
                assert target.read_bytes()==raw,'Changed since preview: '+str(target)
                backup=f'{m.backups_dir}/{stamp}-AGENTS.md'
                mkdir_below(project,m.backups_dir);shutil.copy2(target,project/backup)
                result=apply_plan(root,project,m,Plan(project.name,(Action(BACKFILL,'',m.agents_file),)))
                assert result.actions[0].status in (DONE,SKIPPED),result
                after=target.read_text(encoding='utf-8-sig')
                assert agents_block_current(after,m)
                assert meaningful(without_section(after))==meaningful(without_section(text))
                assert digest((project/'PROJECT.md').read_bytes())==fact_hash
                assert (project/m.claude_file).read_text(encoding='utf-8-sig').strip()=='@AGENTS.md'
                assert with_agents_block(after.splitlines(),m)==after.splitlines()
                run=f'{m.runs_dir}/{stamp}-california-reference-routing'
                mkdir_below(project,run)
                (project/run/'RUN.md').write_text('# California reference routing\n\n- Added the shared Napa knowledge-index workflow to AGENTS.md; conditional on actual jurisdiction.\n- Project facts, permit status, drawings and project-owned instructions unchanged.\n- Backup: '+backup+'\n- Verified: generated block current, second refresh unchanged, CLAUDE pointer intact, PROJECT.md hash unchanged.\n',encoding='utf-8')
                row.update(after_sha256=digest(target.read_bytes()),backup=str(project/backup),verified=True)
            report['template_override']=str(overlay)
            report['launcher_backup']=str(root/backup_rel/'Atlas.bat')
        out=REPO/'.agent/handoff'/('california-reference-deployment-'+('applied' if a.apply else 'preview')+'.json')
        out.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
        print(str(out),flush=True)

if __name__=='__main__':main()
