"""Continue toward deep source coverage using the owner's existing credits."""
from __future__ import annotations
import argparse
import fcntl
import json
import re
import zlib
import urllib.parse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from .expand import Expansion,CATALOG,valid_lead,work_key,wrong_podcast_guest
from .pilot import OpenAI,load_key,read_json,write_json,canonical,now,BudgetStop,caption_view,normalize,digest
from .scope import apply_scope,normalized_span

ROUTES={
 'ritchie':'Find additional original Ritchie papers, technical reports, language manuals, retrospective essays, full interviews and lectures through the Nokia personal archive, TUHS and primary conference/publisher archives. Follow actual bibliographies. Preserve coauthors; Ken Thompson or Stephen Johnson alone are not Ritchie. No pirated book copies or whole journals counted as Ritchie text.',
 'tobi':'Find full Tobi Lutke interviews and publisher transcripts across The Knowledge Project, Invest Like the Best, Acquired, Cheeky Pint, Lenny, Shopify founder/engineering talks, Ruby/Rails panels and his personal essays. Shopify engineers such as Farhan Thawar are other speakers. Prefer direct full transcript URLs rather than episode summaries.',
 'dorsey':'Find full Jack Dorsey interviews, conference talks, Stanford ETL transcripts, technical Bitcoin/Nostr/protocol conversations, authored essays and signed letters. Follow actual publisher transcript links. Do not use Block/Twitter employee material, other people discussing him, or summaries as his own views.',
 'zuckerberg':'Search the Marquette Zuckerberg Files transcript archive for original full F8/Connect/Oculus keynotes, technical Q&As and interviews; public archive records often link to a real PDF through cgi/viewcontent.cgi. Return the archive record URL and explain the linked transcript. Also find personally authored engineering/AI/platform essays and full publisher interviews. Meta employee posts and third-party commentary are not his words. Prioritize technical substance over politics or biography.',
 'casey':'Find public full Handmade Hero/Molly Rocket lessons, HandmadeCon and performance/API/debugging talks, original Casey Muratori essays, and public Computer Enhance material. Full separately published long-form lessons are eligible, but do not count clips/mirrors as separate works or treat repetition of one project as independent empirical validation. No paywall bypass.',
 'carmack':'Find additional original Carmack plan essays, authored technical posts, primary archived interviews, full QuakeCon/Oculus/Connect keynotes and Q&As across different years. A keynote and its clips/mirrors are one work. Prefer distinct first-hand essays over third-party histories.',
 'primeagen':'Find substantial original Primeagen technical tutorials, workshops, programming streams and full interviews, including older own-channel material. Avoid reactions to other authors, clips, and other people discussing Primeagen. Course chapters remain part of their whole course rather than independent works.',
 'linus':'Find distinct original Linus Torvalds technical messages and substantial full interviews/conference conversations across years. Individual messages must show From/date; do not attribute the surrounding thread or quoted replies to him. Prefer single-message URLs and original full talks rather than clips.',
}


def useful_lead(dev,candidate):
    url=canonical(candidate['url']);p=urllib.parse.urlsplit(url);reason=candidate.get('reason','')
    if not valid_lead(url):return False
    if p.hostname=='lexfridman.com':
        names={'dhh':'dhh','primeagen':'theprimeagen','dorsey':'jack-dorsey','carmack':'john-carmack','linus':'linus-torvalds','zuckerberg':'mark-zuckerberg','tobi':'tobi','ritchie':'dennis-ritchie','blow':'jonathan-blow','casey':'casey-muratori','bjarne':'bjarne-stroustrup','vitalik':'vitalik-buterin','unclebob':'robert-martin'}
        if names[dev['id']] not in p.path and url not in {canonical(u) for u in dev['seeds']}:return False
    if p.hostname in ('youtube.com','www.youtube.com','youtu.be') and reason.startswith('Actual primary index or publisher media link') and 'lexfridman.com' in reason:
        if not any(a.lower() in candidate.get('title','').lower() for a in dev.get('aliases',[dev['name']]) if len(a)>=7 or a=='DHH'):return False
    if reason.startswith('Unverified first-party hub link') and p.hostname in ('about.fb.com','www.block.xyz','developers.meta.com'):return False
    if reason.startswith('Actual technical-video search metadata'):
        title=candidate.get('title','').lower()
        if not any(a.lower() in title for a in dev.get('aliases',[dev['name']]) if len(a)>4):return False
    return True


class Deepening(Expansion):
    def scope_archived_blog(self,dev,record):
        if dev['id']!='tobi' or record.get('source_scope'):return
        match=re.fullmatch(r'https://web\.archive\.org/web/\d+(?:id_)?/(https?://blog\.leetsoft\.com(?::80)?/(?:articles/)?\d{4}/\d{1,2}/\d{1,2}/[^/?]+/?)',record['url'])
        if not match:return
        original=match.group(1);slug=urllib.parse.urlsplit(original).path.rstrip('/').split('/')[-1]
        simplified=lambda value:re.sub(r'[^a-z0-9]','',value.lower())
        title=simplified(record.get('metadata',{}).get('title',''))
        if not title or not title.startswith(simplified(slug)):
            raise ValueError('Archived article title does not establish the requested original post; reflected/spam URLs are excluded')
        raw=(self.root/dev['id']/'sources'/record['source_id']/'source.txt').read_text()
        byline=re.search(r'(?im)^Posted by tobi(?:[ \t]+[—–-][^\n]*)?[ \t]*$',raw)
        end=re.search(r'(?im)^(?:Comments|Trackbacks)\s*$',raw[byline.end():]) if byline else None
        if not byline or not end:raise ValueError('Archived blog lacks an explicit target byline or a verifiable article/comment boundary')
        ranges=[normalized_span(raw,byline.start(),byline.end()+end.start())]
        apply_scope(record,raw,ranges,'Coverage includes the explicitly bylined archived article and its date. Archive toolbar, reader comments, trackbacks and navigation are excluded; the full snapshot is retained.')
        if record['coverage_words']<80:raise ValueError('Archived article contains too little substantive original text')
        a,b=ranges[0];identity='tobi-archived-post-'+digest(normalize(raw)[a:b])[:20]
        record['candidate']['verified_work_key']=identity;record['work_key']=identity
        record.update(status='pending',parts_done=[])

    def prepare(self,dev,candidate):
        record=super().prepare(dev,candidate)
        if record['status']=='pending':
            try:self.scope_archived_blog(dev,record)
            except ValueError as exc:record.update(status='held_out',issues=[str(exc)])
            write_json(self.root/dev['id']/'sources'/record['source_id']/'evidence.json',record)
        return record

    def screen_pending(self,dev):
        for record in self.records(dev):
            if record['status']!='pending':continue
            candidate=dict(record['candidate'],title=record.get('metadata',{}).get('title') or record['candidate'].get('title',''))
            if not useful_lead(dev,candidate) or wrong_podcast_guest(dev,record):
                record.update(status='held_out',issues=['Known unrelated publisher/sidebar/index source; remaining parts are not mapped.'])
                write_json(self.root/dev['id']/'sources'/record['source_id']/'evidence.json',record)

    def replay_source_cache(self,since):
        """Apply recorded current-epoch batch results left unapplied by interruption."""
        developers={d['id']:d for d in self.config['developers']};recovered=0
        for dev in developers.values():self.screen_pending(dev)
        for key,job in self.ledger.data['jobs'].items():
            if job['stage']!='extract_batch' or job['status']!='recorded' or job.get('started_at','')<since:continue
            response=read_json(self.root/'responses'/(key+'.json'),{})
            if response.get('status')!='completed':continue
            output=[c['text'] for o in response.get('output',[]) if o.get('type')=='message' for c in o.get('content',[]) if c.get('type')=='output_text']
            try:result=json.loads(''.join(output))
            except (ValueError,TypeError):continue
            dev=developers[job['developer']]
            available={r['source_id']:r for r in self.records(dev)}
            for item in result.get('items',[]):
                r=available.get(item.get('source_id'))
                if not r or r['status']!='pending' or item['part'] in r.get('parts_done',[]):continue
                if r.get('metadata',{}).get('retrieved_at','')>job['started_at']:continue
                self.scope_mail(dev,r)
                part=next((p for p in self.parts(dev,r) if p['part']==item['part']),None)
                if part is None:continue
                x=item['extraction'];good,bad=self.verified_part(dev,r,part,x)
                r['evidence']=list({e['id']:e for e in r['evidence']+good}.values());r['rejected_evidence']+=bad
                r.setdefault('extractions',[]).append(dict(x,part=item['part']));r.setdefault('parts_done',[]).append(item['part']);r['issues']+=x.get('limitations',[])
                r['status']=('accepted' if r['evidence'] else 'held_out') if len(set(r['parts_done']))==r['total_chunks'] else 'pending'
                if r.get('metadata',{}).get('duration_seconds'):r['caption_evidence_version']='caption-prose-v1'
                write_json(self.root/dev['id']/'sources'/r['source_id']/'evidence.json',r)
                if r['status']=='accepted':self.group_video_overlap(dev,r)
                recovered+=1
        print(f'Recovered {recovered} unapplied source parts from recorded responses without paid calls.',flush=True)

    def map_work(self,dev,catalog):
        self.screen_pending(dev)
        return super().map_work(dev,catalog)

    def add_primary_archive(self,dev,catalog):
        index=read_json(self.root/dev['id']/'continuation-primary-index-links.json',{})
        known={canonical(r['url']) for r in catalog['sources']}
        added=[r for r in index.get('sources',[]) if canonical(r['url']) not in known and valid_lead(r['url'])]
        if added:
            catalog['sources']=(catalog['sources']+added)[:self.config['max_candidates']]
            write_json(self.root/dev['id']/'catalog-all.json',catalog)
        return catalog

    def video_signature(self,dev,record):
        cache=getattr(self,'_video_signatures',None)
        if cache is None:self._video_signatures={};cache=self._video_signatures
        key=(record['source_id'],record['text_sha256'])
        if key not in cache:
            raw=(self.root/dev['id']/'sources'/record['source_id']/'source.txt').read_text()
            words=re.findall(r'\w+',caption_view(raw)[0].lower());grams=set()
            for i in range(len(words)-7):
                value=zlib.crc32(' '.join(words[i:i+8]).encode())
                if value%16==0:grams.add(value)
            cache[key]=grams
        return cache[key]

    def group_video_overlap(self,dev,record):
        if not record.get('metadata',{}).get('duration_seconds') or record.get('overlap_check_version')=='caption-eight-gram-v1':return
        signature=self.video_signature(dev,record);matches=[]
        records=self.records(dev)
        for other in records:
            if other['status']!='accepted' or other['source_id']==record['source_id'] or not other.get('metadata',{}).get('duration_seconds'):continue
            reference=self.video_signature(dev,other)
            n=min(len(signature),len(reference))
            if n>=30:
                overlap=len(signature&reference)/n
                if overlap>=.75:matches.append((other,overlap))
        record['overlap_check_version']='caption-eight-gram-v1'
        if matches:
            identities={record['work_key']}|{other['work_key'] for other,_ in matches}
            identity=min(identities)
            # Merge entire existing families, including representations whose
            # different excerpts do not directly overlap this new upload.
            for other in records:
                if other['status']!='accepted' or other['work_key'] not in identities:continue
                other['candidate']['verified_work_key']=identity;other['work_key']=identity
                write_json(self.root/dev['id']/'sources'/other['source_id']/'evidence.json',other)
            record['candidate']['verified_work_key']=identity;record['work_key']=identity
            record['overlap_grouping']=[{'source_id':other['source_id'],'shorter_sample_overlap':round(score,4)} for other,score in matches]
            print(f"{dev['id']}: grouped an overlapping video representation with {len(matches)} retained sources",flush=True)
        write_json(self.root/dev['id']/'sources'/record['source_id']/'evidence.json',record)

    def extract_batch(self,dev,parts,records):
        super().extract_batch(dev,parts,records)
        for record in records.values():
            if record['status']=='accepted':self.group_video_overlap(dev,record)

    def add_actual_media(self,dev,catalog):
        metadata=read_json(self.root/dev['id']/'continuation-media-metadata.json',{})
        known={canonical(r['url']) for r in catalog['sources']};new=[]
        for r in metadata.get('entries',[]):
            if not r.get('id') or (r.get('duration') or 0)<600:continue
            title=r.get('title') or '';channel=r.get('channel') or ''
            if re.search(r'\b(?:clips?|highlights?|reacts|reaction|part\s+\d+)\b',title+' '+channel,re.I):continue
            if metadata.get('kind')=='search' and not any(a.lower() in title.lower() for a in dev.get('aliases',[dev['name']]) if len(a)>4 or a=='DHH'):continue
            url='https://www.youtube.com/watch?v='+r['id']
            if url in known:continue
            new.append({'url':url,'title':title,'work_key':'youtube-'+r['id'],'reason':f"Actual {'own-channel' if metadata.get('kind')=='channel' else 'named-advisor search'} metadata; duration {r['duration']} seconds; channel {channel}. Original captions, target speaker and substantive technical reasoning still require verification."})
            known.add(url)
        if new:
            incidental=('Unverified first-party hub link','Actual primary index','Actual technical-video search metadata','Actual long-form own-channel metadata','Actual own-channel video metadata')
            curated=[r for r in catalog['sources'] if not r.get('reason','').startswith(incidental)]
            old=[r for r in catalog['sources'] if r not in curated]
            catalog.update(sources=(curated+new+old)[:self.config['max_candidates']])
            write_json(self.root/dev['id']/'catalog-all.json',catalog)
            print(f"{dev['id']}: added {len(new)} real long-form media leads",flush=True)
        return catalog

    def catalog(self,dev):
        path=self.root/dev['id']/'catalog-all.json'
        catalog=read_json(path,{'sources':[],'gaps':[]})
        works,words=self.stats(dev)
        if works>=80 and words>=500000:return catalog
        for round_no in range(2):
            saved=self.root/dev['id']/f'credit-continuation-discovery-{round_no+1}.json'
            result=read_json(saved)
            if result is None:
                prompt=(f'Continue a DEEP FIRST-HAND technical source collection for {dev["name"]}. Focus: {dev["focus"]}\n'
                        f'Current coverage: {works} distinct works, {words:,} words; target at least 80 distinct works AND 500,000 words. '
                        'Find up to 65 NEW substantial original works, preferably long essays, papers, full talks or complete publisher transcripts. '
                        'Search broadly across years and technical subjects; identify concrete new primary URLs. Return fewer when actual sources cannot be established. '
                        'A landing page is a lead only: identify the actual accessible transcript/PDF/media link in the reason. '
                        'Exclude navigation, author indexes, third-party recaps and other developers at the same company. Preserve coauthors. '
                        'Use the same work_key for alternate uploads, transcripts, excerpts and mirrors of one work. No source-count padding or guessed URLs. '
                        'Avoid already attempted or catalogued URLs below. Missing source dates are acceptable when explicitly unknown; missing authorship is not. '
                        +ROUTES.get(dev['id'],'Follow original personal writing archives, authored papers and primary full technical talks/interviews. ')+'\n'
                        +json.dumps({'round':round_no+1,'seeds':dev['seeds'],'existing_urls':list(dict.fromkeys([r['url'] for r in catalog['sources']]+[r['url'] for r in self.records(dev)]))},ensure_ascii=False))
                result=self.call(dev['id'],'discover',prompt,CATALOG,search=True,max_output_tokens=11000)
                write_json(saved,result)
            existing={canonical(r['url']):r for r in catalog['sources']}
            new=[]
            for r in result['sources']:
                url=canonical(r['url'])
                if url not in existing and useful_lead(dev,r):
                    item=dict(r,url=url);new.append(item);existing[url]=item
            catalog.update(sources=(new+catalog['sources'])[:self.config['max_candidates']],gaps=list(dict.fromkeys(catalog.get('gaps',[])+result.get('gaps',[]))),continuation_discovered_at=now())
            write_json(path,catalog)
            print(f"{dev['id']}: continuation round {round_no+1} added {len(new)} primary leads",flush=True)
        # Keep historical candidates on disk; don't pay to map known unrelated publisher sidebar links.
        catalog=self.add_actual_media(dev,catalog)
        catalog=self.add_primary_archive(dev,catalog)
        titles={canonical(r['url']):r.get('metadata',{}).get('title') for r in self.records(dev)}
        sources=[dict(r,title=titles.get(canonical(r['url'])) or r.get('title','')) for r in catalog['sources']]
        return dict(catalog,sources=[r for r in sources if useful_lead(dev,r)])


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--discover-only',action='store_true');args=parser.parse_args()
    project=Path(__file__).resolve().parents[1];cfg=read_json(project/'collection/roster.json')
    if cfg['budget_usd']!=51.5 or cfg['model']!='gpt-6.1-terra':raise ValueError('Existing-credit continuation allocation and Terra required')
    root=project/'.collection/pilot'
    with (root/'run.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        client=OpenAI(load_key(project/'.env'));client.preflight(cfg['model'])
        collector=Deepening(project,cfg,client);collector.ledger.reconcile_tool_fees();collector.ledger.reconcile_cache_prices()
        collector.repair_work_identities()
        epoch=read_json(root/'continuation-source-epoch.json')
        if epoch:collector.replay_source_cache(epoch['started_at'])
        if args.discover_only:
            order=sorted(cfg['developers'],key=lambda d:collector.stats(d)[1]);deferred=[]
            with ThreadPoolExecutor(max_workers=2) as pool:
                futures=[(d,pool.submit(collector.catalog,d)) for d in order]
                for dev,future in futures:
                    try:future.result()
                    except BudgetStop:deferred.append(dev)
            for dev in deferred:collector.catalog(dev)
            report=collector.full_report('continuation catalogs prepared')
            print('Discovery completed; cumulative',report['cumulative_estimated_usd'],flush=True);return
        report=collector.run_full(catalog_only=args.discover_only)
        print('Continuation',report['status'],'cumulative',report['cumulative_estimated_usd'],flush=True)
        if report['status'].startswith('stopped'):raise SystemExit(2)


if __name__=='__main__':main()
