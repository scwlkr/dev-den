import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor,wait,FIRST_COMPLETED

from collection.expand import Expansion,source_id,work_key,collection_gaps
from collection.pilot import Ledger,BudgetStop,UncertainCharge,get_source,write_json,digest,normalize,PageText,object_schema,caption_view,work_coverage
from test_collection import config,QUOTE,TEXT
from collection.scope import mail_sender_scope,apply_scope


class ExpansionBehavior(unittest.TestCase):
    def test_cache_write_reconciliation_preserves_history_and_blocks_further_spending(self):
        with tempfile.TemporaryDirectory(prefix='dod-expand-test-') as tmp:
            root=Path(tmp);usage={'input_tokens':200000,'input_tokens_details':{'cached_tokens':10000,'cache_write_tokens':180000},'output_tokens':1000}
            write_json(root/'ledger.json',{'jobs':{'old':{'status':'recorded','reserved_usd':1,'cost_usd':.205,'usage':usage,'search_calls':1}}})
            ledger=Ledger(root,.23,config()['pricing']);ledger.reconcile_cache_prices();ledger.reconcile_cache_prices()
            self.assertAlmostEqual(ledger.exposure(),.2505)
            self.assertEqual(ledger.data['jobs']['old']['cost_before_cache_write_reconciliation_usd'],.205)
            with self.assertRaises(BudgetStop):ledger.reserve('new','test','compile',{'max_output_tokens':1})

    def test_keynote_parts_and_republications_do_not_inflate_coverage(self):
        urls=['https://www.youtube.com/watch?v='+v for v in ('W3RsQCGiTgA','Uooh0Y9fC_M','cWA_9L70moE')]
        records=[{'status':'accepted','work_key':work_key({'url':u}),'words':n} for u,n in zip(urls,(33000,33100,5700))]
        self.assertEqual(work_coverage(records),(1,33100))
        self.assertNotEqual(work_key({'url':'https://www.youtube.com/watch?v=P6UKhR0T6cs'}),records[0]['work_key'])
        self.assertEqual(work_key({'url':'https://cbarrete.com/carmack.html'}),work_key({'url':'https://www.gamedeveloper.com/programming/in-depth-functional-programming-in-c-'}))

    def test_assembled_brain_gaps_preserve_source_limits_not_writer_scope_notes(self):
        self.assertEqual(collection_gaps(['Only positions and stories are included, following the explicit section restriction.',
                                         'Captions omit diagrams and need audio verification.']),['Captions omit diagrams and need audio verification.'])

    def test_comments_and_other_mail_authors_do_not_inflate_primary_coverage(self):
        parser=PageText();parser.feed('<article>'+TEXT+'</article><section id="comments"><article class="comment"><p>Unrelated reader material.</p></article></section>')
        self.assertIn(QUOTE,parser.text());self.assertNotIn('Unrelated reader',parser.text())
        other='This technical claim belongs to another author, not the advisor.'
        raw='From: Other Developer @ 2026-10-01 10:00 UTC\n'+other+'\n^ permalink raw reply\nFrom: Test Developer @ 2026-10-02 10:00 UTC\n> '+other+'\n'+QUOTE+'\n^ permalink raw reply\n'
        full=normalize(raw);r={'text_sha256':digest(full),'words':len(raw.split()),'status':'accepted','evidence':[{'id':str(i),'quote':q,'passage_offset':full.index(q)} for i,q in enumerate((QUOTE,other))],'rejected_evidence':[]}
        ranges,note=mail_sender_scope(raw,['Test Developer']);rejected=apply_scope(r,raw,ranges,note)
        self.assertEqual(rejected,1);self.assertEqual(len(r['evidence']),1)
        self.assertLess(r['coverage_words'],r['words'])

    def test_copying_a_report_without_the_charged_ledger_cannot_restart_budget(self):
        with tempfile.TemporaryDirectory(prefix='dod-expand-test-') as tmp:
            project=Path(tmp);(project/'collection').mkdir()
            (project/'collection/FULL-REPORT.md').write_text('Cumulative usage: **$12.4000 / $25.00**.')
            with self.assertRaises(UncertainCharge):Expansion(project,config(),None)

    def test_actual_video_catalog_omits_clips_reactions_and_short_items(self):
        with tempfile.TemporaryDirectory(prefix='dod-expand-test-') as tmp:
            cfg=config();cfg['max_candidates']=20;dev=dict(cfg['developers'][0],video_query='real technical talks')
            collector=Expansion(Path(tmp),cfg,None)
            entries=[{'id':ident,'title':title,'duration':duration,'channel':channel} for ident,title,duration,channel in
                     [('full','Full technical keynote',3600,'Conference'),('clip','Technical advice',1000,'Developer Clips'),
                      ('react','Someone reacts to a talk',2400,'Channel'),('short','Short video',400,'Conference')]]
            write_json(collector.root/dev['id']/'technical-video-search.json',{'entries':entries})
            catalog=collector.expand_video_search(dev,{'sources':[],'gaps':[]})
            self.assertEqual([r['url'] for r in catalog['sources']],['https://www.youtube.com/watch?v=full'])

    def test_legacy_web_tool_charges_include_opens_and_reconcile_only_once(self):
        with tempfile.TemporaryDirectory(prefix='dod-expand-test-') as tmp:
            root=Path(tmp)
            write_json(root/'ledger.json',{'jobs':{'old':{'developer':'test','stage':'discover','status':'recorded','reserved_usd':1,'cost_usd':.02,'search_calls':1}}})
            write_json(root/'responses/old.json',{'output':[{'type':'web_search_call','action':{'type':x}} for x in ('search','open_page','find_in_page')]})
            ledger=Ledger(root,25,config()['pricing']);ledger.reconcile_tool_fees();ledger.reconcile_tool_fees()
            self.assertAlmostEqual(ledger.exposure(),.04)
            self.assertEqual(ledger.data['jobs']['old']['search_calls'],3)

    def test_parallel_requests_share_one_durable_budget_without_lost_charges(self):
        with tempfile.TemporaryDirectory(prefix='dod-expand-test-') as tmp:
            cfg=config();cfg.update(budget_usd=.06,compilation_margin_usd=0)
            release=threading.Event();started=threading.Event();calls=[]
            def provider(request):
                calls.append(request)
                if len(calls)==2:started.set()
                if not release.wait(3):raise TimeoutError('test synchronization failed')
                return {'status':'completed','usage':{'input_tokens':1000,'output_tokens':100},'output':[{'type':'message','content':[{'type':'output_text','text':'{}'}]}]}
            collector=Expansion(Path(tmp),cfg,provider)
            with ThreadPoolExecutor(max_workers=3) as pool:
                futures=[pool.submit(collector.call,str(i),'extract_batch','x'*5000,object_schema({}),max_output_tokens=100) for i in range(3)]
                try:
                    self.assertTrue(started.wait(2));self.assertLessEqual(collector.ledger.exposure(),.06)
                    done,_=wait(futures,timeout=2,return_when=FIRST_COMPLETED)
                    self.assertEqual(len(done),1)
                    self.assertIsInstance(next(iter(done)).exception(),BudgetStop)
                finally:release.set()
                blocked=0
                for f in futures:
                    try:f.result()
                    except BudgetStop:blocked+=1
            self.assertEqual((len(calls),blocked),(2,1))
            saved=json.loads((collector.root/'ledger.json').read_text())['jobs']
            self.assertEqual(len(saved),2)
            self.assertTrue(all(j['status']=='recorded' for j in saved.values()))
            self.assertAlmostEqual(collector.ledger.exposure(),.003)

    def test_publisher_embedded_video_becomes_a_real_candidate_link(self):
        parser=PageText();parser.feed('<iframe src="https://www.youtube-nocookie.com/embed/real-id?start=5" title="Full technical talk"></iframe>')
        self.assertEqual(parser.links,[{'url':'https://www.youtube.com/watch?v=real-id','title':'Full technical talk'}])

    def test_expansion_reuses_original_spend_and_reserves_compilation_margin(self):
        with tempfile.TemporaryDirectory(prefix='dod-expand-test-') as tmp:
            root=Path(tmp);root.mkdir(exist_ok=True)
            write_json(root/'ledger.json',{'jobs':{'pilot':{'reserved_usd':2,'cost_usd':2,'status':'recorded'}}})
            ledger=Ledger(root,25,config()['pricing'],compilation_margin=6)
            self.assertEqual(ledger.exposure(),2)
            # Conservative reservation cannot consume the compilation allowance.
            with self.assertRaises(BudgetStop):
                ledger.reserve('large','test','extract_batch',{'input':'x'*9_000_000,'max_output_tokens':100})
            self.assertEqual(ledger.exposure(),2)

    def test_batch_quote_cannot_borrow_words_from_another_source(self):
        with tempfile.TemporaryDirectory(prefix='dod-expand-test-') as tmp:
            project=Path(tmp);(project/'collection').mkdir()
            cfg=config();dev=cfg['developers'][0]
            def provider(request):
                rows=[]
                for n in range(2):
                    rows.append({'source_id':f'test-source-{n}','part':0,'extraction':{'eligible':True,'attribution':'sole_author','attribution_reason':'Known author',
                        'title':'Source','date':'','topics':['simplicity'],'limitations':[],
                        'evidence':[{'kind':'principle','claim':'Prefer simplicity','quote':QUOTE,'context':'Within constraints','speaker':'Test Developer'}]}})
                return {'status':'completed','usage':{'input_tokens':100,'output_tokens':100},'output':[{'type':'message','content':[{'type':'output_text','text':json.dumps({'items':rows})}]}]}
            collector=Expansion(project,cfg,provider)
            parts=[];records={}
            for n,text in enumerate([TEXT,'This is entirely different source material. '*30]):
                sid=f'test-source-{n}';folder=collector.root/dev['id']/'sources'/sid;folder.mkdir(parents=True)
                (folder/'source.txt').write_text(text)
                record={'source_id':sid,'developer':'test','url':f'https://example.org/{n}','candidate':{'url':f'https://example.org/{n}'},'metadata':{'url':f'https://example.org/{n}'},
                        'text_sha256':digest(normalize(text)),'words':len(text.split()),'evidence':[],'rejected_evidence':[],'issues':[],'parts_done':[],'extractions':[],'total_chunks':1,'status':'pending'}
                records[sid]=record
                parts.append({'source_id':sid,'part':0,'text':text})
            collector.extract_batch(dev,parts,records)
            self.assertEqual(records['test-source-0']['status'],'accepted')
            self.assertEqual(records['test-source-1']['status'],'held_out')
            self.assertEqual(records['test-source-1']['evidence'],[])

    def test_caption_metadata_printing_does_not_simulate_caption_downloads(self):
        def fake_run(command,**kwargs):
            self.assertIn('--no-simulate',command)
            self.assertIn('--skip-download',command)
            self.assertIn('--no-cache-dir',command)
            folder=Path(command[command.index('--paths')+1])
            (folder/'source.en-orig.json3').write_text(json.dumps({'events':[{'tStartMs':0,'segs':[{'utf8':QUOTE}]}]}))
            return subprocess.CompletedProcess(command,0,stdout=json.dumps({'title':'A technical talk','channel':'Test Developer','duration':1200,'requested_subtitles':{'en-orig':{'url':'https://www.youtube.com/api/timedtext?lang=en&kind=asr'}}}),stderr='')
        with patch('collection.pilot.subprocess.run',side_effect=fake_run):
            source=get_source('https://www.youtube.com/watch?v=example')
        self.assertIn(QUOTE,source['text'])
        self.assertEqual(source['metadata']['duration_seconds'],1200)

    def test_translated_english_track_is_not_promoted_as_original_words(self):
        def fake_run(command,**kwargs):
            folder=Path(command[command.index('--paths')+1])
            (folder/'source.en.json3').write_text(json.dumps({'events':[{'tStartMs':0,'segs':[{'utf8':QUOTE}]}]}))
            return subprocess.CompletedProcess(command,0,stdout=json.dumps({'requested_subtitles':{'en':{'url':'https://www.youtube.com/api/timedtext?lang=ar&tlang=en'}}}),stderr='')
        with patch('collection.pilot.subprocess.run',side_effect=fake_run):
            with self.assertRaisesRegex(ValueError,'Original English'):get_source('https://www.youtube.com/watch?v=example')

    def test_interview_video_and_publisher_transcript_are_one_work(self):
        self.assertEqual(work_key({'url':'https://www.youtube.com/watch?v=tNZnLkRBYA8'}),work_key({'url':'https://lexfridman.com/theprimeagen-transcript/'}))
        self.assertEqual(work_key({'url':'https://www.youtube.com/watch?v=tH95ZCciOqk'}),work_key({'url':'https://uncappedpod.com/p/tobi-lutke-building-shopify-and-the'}))
        self.assertEqual(work_key({'url':'https://www.youtube.com/watch?v=rYXeQbTuVl0'}),work_key({'url':'https://www.dwarkesh.com/p/mark-zuckerberg-2'}))
        self.assertEqual(work_key({'url':'https://github.com/ThePrimeagen/fem-git'}),work_key({'url':'https://theprimeagen.github.io/fem-git/'}))
        self.assertEqual(work_key({'url':'https://theprimeagen.github.io/fem-git/lessons/intro/intro'}),work_key({'url':'https://theprimeagen.github.io/fem-git/'}))

    def test_later_video_part_uses_its_actual_offset_and_timestamp(self):
        with tempfile.TemporaryDirectory(prefix='dod-expand-test-') as tmp:
            project=Path(tmp);(project/'collection').mkdir();cfg=config();dev=cfg['developers'][0]
            extraction={'eligible':True,'attribution':'speaker','attribution_reason':'Identified target speaker','title':'Talk','date':'','topics':[],
                        'limitations':[],'evidence':[{'kind':'principle','claim':'Prefer simplicity','quote':QUOTE,'context':'Within constraints','speaker':'Test Developer'}]}
            def provider(request):
                return {'status':'completed','usage':{'input_tokens':100,'output_tokens':100},'output':[{'type':'message','content':[{'type':'output_text',
                         'text':json.dumps({'items':[{'source_id':'talk','part':1,'extraction':extraction}]})}]}]}
            collector=Expansion(project,cfg,provider);folder=collector.root/dev['id']/'sources/talk';folder.mkdir(parents=True)
            prefix='[00:00:01] '+QUOTE+'\n'+('Other context. '*30)+'\n'
            part='[00:12:03] '+QUOTE+'\nLater context.';text=prefix+part;(folder/'source.txt').write_text(text)
            record={'source_id':'talk','developer':dev['id'],'url':'https://www.youtube.com/watch?v=test','candidate':{'url':'https://www.youtube.com/watch?v=test'},
                    'metadata':{'url':'https://www.youtube.com/watch?v=test','duration_seconds':1200},'words':len(text.split()),'evidence':[],
                    'rejected_evidence':[],'issues':[],'parts_done':[0],'extractions':[],'total_chunks':2,'status':'pending'}
            collector.extract_batch(dev,[{'source_id':'talk','part':1,'text':part,'char_start':len(prefix)}],{'talk':record})
            ev=record['evidence'][0];full=caption_view(text)[0]
            self.assertGreater(ev['passage_offset'],full.index(QUOTE))
            self.assertEqual(full[ev['passage_offset']:ev['passage_offset']+len(QUOTE)],QUOTE)
            self.assertEqual(ev['timestamp'],'00:12:03')
            self.assertTrue(ev['source_url'].endswith('&t=723'))

    def test_caption_quote_can_span_cues_but_not_invent_words(self):
        with tempfile.TemporaryDirectory(prefix='dod-expand-test-') as tmp:
            cfg=config();dev=cfg['developers'][0];collector=Expansion(Path(tmp),cfg,None)
            folder=collector.root/dev['id']/'sources/talk';folder.mkdir(parents=True)
            text='[00:02:00] Choose the simplest implementation\n[00:02:03] that meets the actual requirements.'
            (folder/'source.txt').write_text(text)
            r={'source_id':'talk','metadata':{'url':'https://www.youtube.com/watch?v=test','duration_seconds':600}}
            x={'eligible':True,'attribution':'speaker','attribution_reason':'Identified speaker','evidence':[
               {'kind':'principle','claim':'Simplicity','context':'Requirements','speaker':'Test Developer','quote':QUOTE},
               {'kind':'principle','claim':'Fabrication','context':'Wrong','speaker':'Test Developer','quote':'Choose the most complicated implementation that meets the actual requirements.'}]}
            good,bad=collector.verified_part(dev,r,{'part':0,'char_start':0,'text':text},x)
            self.assertEqual(len(good),1);self.assertEqual(len(bad),1)
            self.assertEqual(good[0]['quote'],QUOTE)
            self.assertEqual(good[0]['timestamp'],'00:02:00')
            self.assertEqual(good[0]['passage_view'],'caption-prose-v1')
            r.update(developer=dev['id'],url=r['metadata']['url'],candidate={'url':r['metadata']['url']},text_sha256=digest(normalize(text)),words=0,
                     evidence=[],rejected_evidence=bad,issues=[],status='held_out',parts_done=[0],total_chunks=1,extractions=[dict(x,part=0)])
            write_json(folder/'evidence.json',r)
            collector.repair_caption_evidence()
            recovered=json.loads((folder/'evidence.json').read_text())
            self.assertEqual(recovered['status'],'accepted')
            self.assertEqual(recovered['words'],len(QUOTE.split()))
            self.assertEqual(len(recovered['evidence']),1)
            collector.repair_caption_evidence()
            self.assertEqual(recovered,json.loads((folder/'evidence.json').read_text()))


if __name__=='__main__':unittest.main()
