"""Independent advisor creation acceptance; never touches the real corpus or network."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

REPO=Path(__file__).resolve().parents[1]
class AdvisorAcceptance(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(prefix='dod-advisor-acceptance-');self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
  (self.root/'collection').mkdir();(self.root/'collection/roster.json').write_text(json.dumps({'developers':[]}))
 def cli(self,*args,ok=True):
  r=subprocess.run([sys.executable,'-B','-m','collection.advisor','--project',str(self.root),*map(str,args)],cwd=REPO,text=True,capture_output=True)
  if ok:self.assertEqual(r.returncode,0,r.stderr+'\n'+r.stdout)
  try:return json.loads(r.stdout)
  except json.JSONDecodeError:
   if ok:self.fail('Expected machine-readable JSON: '+r.stdout+r.stderr)
   return {'exit':r.returncode,'error':r.stderr or r.stdout}
 def prepare(self):return self.cli('prepare','--id','fixture','--name','Fixture Developer','--focus','Data structures and technical decision tests','--depth','quick')
 def imported(self):
  self.prepare();self.text='Use a small working experiment to test the real constraints before committing to an irreversible rewrite. Measure the outcome and retain a way to recover the original data.'
  f=self.root/'authored.txt';f.write_text(self.text)
  r=self.cli('import','--id','fixture','--url','https://example.org/fixture-design','--text-file',f,'--title','Fixture design','--author','Fixture Developer','--date','2025-01-01');self.sid=r['source_id'];return r
 def extracted(self):
  self.imported();e={'eligible':True,'attribution':'sole_author','attribution_reason':'An explicitly authored controlled fixture.','title':'Fixture design','date':'2025-01-01','topics':['experiments'],'limitations':['One controlled source, not a real advisor.'],'evidence':[{'kind':'principle','claim':'Use a working experiment before an irreversible rewrite.','quote':self.text,'context':'Technical trade-offs in a controlled source.','speaker':'Fixture Developer'}]}
  p=self.root/'extraction.json';p.write_text(json.dumps(e));self.cli('extraction-submit','--id','fixture','--source-id',self.sid,'--file',p)
  packet=self.cli('compilation-packet','--id','fixture');self.assertTrue(packet['evidence']);return packet
 def compiled(self):
  packet=self.extracted();eid=packet['evidence'][0]['id'];item={'text':'Use a small working experiment before committing to a rewrite.','basis':'documented','evidence_ids':[eid]};c={'sections':[{'name':n,'items':[item] if n!='books' else []} for n in ['_hot','frameworks','principles','positions','stories','voice','books']],'gaps':['A single controlled source; far below quick depth.']};p=self.root/'compiled-input.json';p.write_text(json.dumps(c));self.cli('compilation-submit','--id','fixture','--file',p);return c
 def test_complete_build_register_and_runtime_loader(self):
  self.compiled();self.cli('register','--id','fixture','--allow-gaps')
  code="import {advisor,packet} from './app/lib/knowledge.mjs';import {Store} from './app/lib/sessions.mjs';import {nextStep} from './app/lib/protocol.mjs';import {fixtureCard} from './app/lib/demo.mjs';import {report} from './app/lib/report.mjs';const root=process.argv[1],a=advisor('fixture',root);if(!a.evidence.length)throw Error('No usable evidence');const p=packet('fixture',{question:'Should I rewrite?',options:['Keep','Rewrite']},root);if(!p.evidence.length)throw Error('No packet evidence');const store=new Store(root+'/sessions',root);const s=store.create({question:'Should I rewrite?',options:['Keep','Rewrite'],context:'Controlled example application.',constraints:'One developer with a weekend.',success:'Measure a working slice.'},[{id:'fixture',weight:1,reason:'Controlled fixture'}],'consult');let current=store.read(s.id),step;while(step=nextStep(current)){store.submit(s.id,step.key,fixtureCard(current,step));current=store.read(s.id);}if(current.status!=='complete'||!report(current).sources.length)throw Error('Registered advisor cannot complete a cited consultation');console.log(JSON.stringify({works:a.works,status:current.status}));"
  r=subprocess.run(['node','--input-type=module','-e',code,str(self.root)],cwd=REPO,text=True,capture_output=True);self.assertEqual(r.returncode,0,r.stderr)
  self.assertIn('working experiment',(self.root/'knowledge/fixture/principles.md').read_text())
 def test_register_refuses_uncompiled_build_without_touching_roster(self):
  self.prepare();before=(self.root/'collection/roster.json').read_bytes();r=self.cli('register','--id','fixture',ok=False);self.assertNotEqual(r.get('status'),'registered');self.assertEqual((self.root/'collection/roster.json').read_bytes(),before)
 def test_extraction_rejects_wrong_speaker(self):
  self.imported();p=self.root/'bad.json';p.write_text(json.dumps({'eligible':True,'attribution':'speaker','attribution_reason':'Controlled mismatch','evidence':[{'kind':'principle','claim':'Test experiments.','quote':self.text,'context':'Different speaker.','speaker':'Another Developer'}]}));r=self.cli('extraction-submit','--id','fixture','--source-id',self.sid,'--file',p,ok=False);self.assertEqual(r.get('status'),'rejected')
 def test_empty_evidence_compilation_cannot_register(self):
  self.prepare();p=self.root/'empty.json';p.write_text(json.dumps({'sections':[{'name':n,'items':[]} for n in ['_hot','frameworks','principles','positions','stories','voice','books']],'gaps':[]}));self.cli('compilation-submit','--id','fixture','--file',p,ok=False);r=self.cli('register','--id','fixture',ok=False);self.assertNotEqual(r.get('status'),'registered')
 def test_real_depth_is_required_without_explicit_override(self):
  self.compiled();r=self.cli('register','--id','fixture',ok=False);self.assertNotEqual(r.get('status'),'registered');self.assertEqual(json.loads((self.root/'collection/roster.json').read_text())['developers'],[])
 def test_publication_failure_preserves_roster_and_existing_path(self):
  self.compiled();dest=self.root/'.collection/pilot/fixture';dest.parent.mkdir(parents=True);dest.write_text('Protected preexisting user data');before=(self.root/'collection/roster.json').read_bytes();r=self.cli('register','--id','fixture','--allow-gaps',ok=False);self.assertNotEqual(r.get('status'),'registered');self.assertEqual((self.root/'collection/roster.json').read_bytes(),before);self.assertEqual(dest.read_text(),'Protected preexisting user data');self.assertFalse((self.root/'knowledge/fixture').exists())
 def test_changed_source_hash_is_rejected_before_registration(self):
  self.compiled();f=self.root/'.collection/advisor-builds/fixture/sources'/self.sid/'source.txt';f.write_text('Tampered source with no retained evidence.');before=(self.root/'collection/roster.json').read_bytes();r=self.cli('register','--id','fixture','--allow-gaps',ok=False);self.assertNotEqual(r.get('status'),'registered');self.assertEqual((self.root/'collection/roster.json').read_bytes(),before)
 def test_import_requires_a_public_source_url_even_for_local_text(self):
  self.prepare();f=self.root/'text.txt';f.write_text('A controlled first-hand fixture about experiments.');r=self.cli('import','--id','fixture','--url','file:///etc/passwd','--text-file',f,'--author','Fixture Developer',ok=False);self.assertNotEqual(r.get('status'),'imported')
 def test_default_board_intent_and_safe_update_retain_registered_sources(self):
  self.compiled()
  self.cli('prepare','--id','fixture','--name','Fixture Developer','--focus','Data structures and technical decision tests','--depth','quick','--update','--default-board')
  self.cli('register','--id','fixture','--allow-gaps')
  prefs=json.loads((self.root/'.den/board.json').read_text());self.assertEqual(prefs['default'],['fixture'])
  source=self.root/'.collection/pilot/fixture/sources'/self.sid/'source.txt';before=source.read_bytes()
  self.cli('update','--id','fixture');self.cli('register','--id','fixture','--update','--allow-gaps')
  self.assertEqual(source.read_bytes(),before);self.assertEqual(len(json.loads((self.root/'collection/roster.json').read_text())['developers']),1)
  self.assertFalse(list(self.root.glob('adv-stage-*')))
 def test_unrelated_manifest_cannot_replace_an_existing_advisor(self):
  self.compiled();p=self.root/'collection/roster.json';p.write_text(json.dumps({'developers':[{'id':'fixture','name':'Protected Advisor'}]}));before=p.read_bytes()
  r=self.cli('register','--id','fixture','--update','--allow-gaps',ok=False);self.assertNotEqual(r.get('status'),'registered');self.assertEqual(p.read_bytes(),before)
if __name__=='__main__':unittest.main()
