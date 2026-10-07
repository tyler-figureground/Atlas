"""Exercise real Atlas new-project creation in a disposable local drive."""
import argparse,datetime,json,pathlib,tempfile
from atlas.core.contacts import ContactDraft,add_contact
from atlas.core.intake import ProjectAddress,ProjectIntake,ProjectUseCase
from atlas.core.mapfile import find_map,load_map
from atlas.core.ops import new_project
from atlas.core.templates import template_dir

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--map',type=pathlib.Path,required=True);a=p.parse_args()
    with tempfile.TemporaryDirectory(prefix='atlas-reference-smoke-') as td:
        root=pathlib.Path(td);(root/'_tools').mkdir()
        (root/'_tools/test-map.json').write_bytes(a.map.read_bytes())
        m=load_map(find_map(root))
        contact=add_contact(root,ContactDraft(first_name='Test',last_name='Reference',email='test@example.com'))
        for state,city in [('CA','Napa'),('CA','Oakland'),('NY','New York')]:
            intake=ProjectIntake(project_name='Reference '+city,project_address=ProjectAddress(street='100 Test Street',city=city,state=state,postal_code='94559' if state=='CA' else '10001'),project_use_case=ProjectUseCase('Renovation'),billing_contact_id=contact.id,client_contact_id=contact.id,description=city,created=datetime.date(2026,10,6))
            project=new_project(root,m,intake).path
            agents=(project/'AGENTS.md').read_text(encoding='utf-8')
            assert agents.count('## California permit requirements')==1
            for required in ['_agent\\START_HERE.md','not statewide coverage','For non-California projects','norma <verb>','OCR','RESEARCH-INDEX.md']:
                assert required in agents,required
            assert (project/'CLAUDE.md').read_text(encoding='utf-8').strip()=='@AGENTS.md'
        print(json.dumps({'new_projects_tested':3,'locations':['Napa CA','Oakland CA','New York NY'],'templates':str(template_dir()),'status':'passed'}))

if __name__=='__main__':main()
