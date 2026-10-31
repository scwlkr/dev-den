"""Expand all 13 advisor collections against roast-room's deep benchmark."""
from __future__ import annotations

import argparse
import collections
from concurrent.futures import ThreadPoolExecutor
import fcntl
import json
from pathlib import Path
import re
import subprocess
import urllib.parse

from .pilot import (Pilot, OpenAI, load_key, read_json, write_json, digest, normalize,
                    canonical, get_page, get_source, is_course_index, is_transcript_archive, is_transcript_landing, verify_evidence,
                    object_schema, STRING, STRINGS, EXTRACTION, COMPILATION,
                    SECTIONS, BudgetStop, UncertainCharge, now,caption_view,source_words,work_coverage,collection_fingerprint)
from .scope import mail_sender_scope,apply_scope

CATALOG = object_schema({"sources": {"type": "array", "items": object_schema({
    "url": STRING, "title": STRING, "work_key": STRING, "reason": STRING})}, "gaps": STRINGS})
BATCH = object_schema({"items": {"type": "array", "items": object_schema({
    "source_id": STRING, "part": {"type": "integer"}, "extraction": EXTRACTION})}})
TARGETS = {"frameworks": (12,25), "principles": (15,30), "positions": (20,40), "stories": (10,20)}


def source_id(dev, url):
    return dev["id"] + "-" + digest(canonical(url))[:14]


def wrong_podcast_guest(dev,record):
    meta=record.get('metadata',{})
    channel=re.sub(r'[^a-z0-9]','',(meta.get('channel') or '').lower())
    if channel not in ('lexfridman','lexfridmanpodcast'):return False
    title=re.sub(r'[^a-z0-9]','',str(meta.get('title','')).lower())
    aliases=[re.sub(r'[^a-z0-9]','',a.lower()) for a in dev.get('aliases',[dev['name']]) if len(a)>=7 or a=='DHH']
    return not any(a and a in title for a in aliases)


def work_key(candidate):
    if candidate.get('verified_work_key'):return candidate['verified_work_key']
    url = canonical(candidate.get('original_work_url') or candidate["url"])
    if url in ("https://www.youtube.com/watch?v=tNZnLkRBYA8", "https://lexfridman.com/theprimeagen-transcript/", "https://lexfridman.com/theprimeagen/"):
        return "primeagen-lex-461"
    groups={
        'carmack-quakecon-2013':tuple('https://www.youtube.com/watch?v='+v for v in ('W3RsQCGiTgA','Uooh0Y9fC_M','cWA_9L70moE','1PhArSujR_A')),
        'carmack-quakecon-2011':tuple('https://www.youtube.com/watch?v='+v for v in ('4zgYG-_ha28','RccQUHZLC4o','8nHGfdBH3pQ')),
        'carmack-functional-programming':('https://cbarrete.com/carmack.html','https://www.gamedeveloper.com/programming/in-depth-functional-programming-in-c-'),
        'casey-clean-code-performance':tuple('https://www.youtube.com/watch?v='+v for v in ('czr1L3JocOI','jHLbL1Eg4gM')),
        'dhh-rails-world-2026':tuple('https://www.youtube.com/watch?v='+v for v in ('cMX-u9ltG5Q','vDjW_dRyKXY')),
        'dorsey-b-word':tuple('https://www.youtube.com/watch?v='+v for v in ('6CdncY4DecY','e7-enQoCozs')),
        'dorsey-bitcoin-miami-2021':tuple('https://www.youtube.com/watch?v='+v for v in ('KZWYL1ccBt8','QNSfynBCzmk')),
        'linus-dirk-hohndel-ai':tuple('https://www.youtube.com/watch?v='+v for v in ('YKkEe-PxW10','InvaowP8XH8','kRHqRWINWFQ')),
        'tobi-uncapped-50':('https://www.youtube.com/watch?v=tH95ZCciOqk','https://uncappedpod.com/p/tobi-lutke-building-shopify-and-the'),
        'zuckerberg-dwarkesh-2025-04':('https://www.youtube.com/watch?v=rYXeQbTuVl0','https://www.youtube.com/watch?v=21lk0bFhoCs','https://www.dwarkesh.com/p/mark-zuckerberg-2')}
    for key,urls in groups.items():
        if url in urls:return key
    p=urllib.parse.urlsplit(url)
    for course in ('fem-git','fem-algos','ts-go-rust','rust-for-typescript-devs'):
        if (p.hostname=='theprimeagen.github.io' and (p.path.rstrip('/')=='/'+course or p.path.startswith('/'+course+'/'))) or (p.hostname=='github.com' and (p.path.rstrip('/').lower()=='/theprimeagen/'+course or p.path.lower().startswith('/theprimeagen/'+course+'/'))):
            return 'primeagen-course-'+course
    if p.hostname in ('youtube.com','www.youtube.com','youtu.be'):
        video=dict(urllib.parse.parse_qsl(p.query)).get('v')
        if video:return 'youtube-'+video
    return candidate.get("work_key") or url


def valid_lead(url):
    p = urllib.parse.urlsplit(url)
    if p.scheme not in ("http","https") or not p.hostname:
        return False
    if p.hostname=='github.com' and re.match(r'^/(?:features|security|solutions|resources|enterprise|customer-stories|platform|pricing|marketplace)(?:/|$)',p.path):
        return False
    if re.search(r"\.(?:png|jpg|jpeg|gif|svg|css|js|woff|zip|tar|gz|mp3|mp4|webm)$",p.path,re.I):
        return False
    if re.search(r'(?:^|/)(?:feed|rss)(?:[./]|$)|\.(?:atom|rss)$',p.path,re.I):return False
    return not re.search(r"/(?:tags?|categories|search|login|privacy|terms|contact|subscribe|signup|feed)(?:/|$)",p.path,re.I)


def collection_gaps(gaps):
    """Stage-local section omissions do not describe the assembled seven-section brain."""
    cleaned=[]
    for gap in gaps:
        if (re.match(r'^(?:Only (?:the |frameworks|positions)|The (?:request|instruction)|The requested separate|The evidence comprises .+?The requested standalone)',gap,re.I)
                and re.search(r'section|restriction|restricts|restricted',gap,re.I)):
            # Preserve an independently useful coverage sentence in a mixed note.
            if gap.startswith('The evidence comprises '):cleaned.append(gap.split('. ')[0]+'.')
            continue
        cleaned.append(gap)
    return list(dict.fromkeys(cleaned))


def coverage_gaps(gaps,records):
    """Replace writer-context volume with the audited scoped coverage figure."""
    _,words=work_coverage(records)
    raw=sum(r['words'] for r in records)
    counts={raw,sum(source_words(r) for r in records),round(raw,-3)}
    def scoped(match):
        value=int(match[1].replace(',',''))
        return f'{words:,} scoped source words' if value in counts and value!=words else match[0]
    return [re.sub(r'\b([\d,]+) (?:source )?words\b',scoped,g) for g in collection_gaps(gaps)]


class Expansion(Pilot):
    def repair_work_identities(self):
        count=0
        for dev in self.config['developers']:
            groups=collections.defaultdict(list)
            for r in self.records(dev):
                if r['status']!='accepted':continue
                r['work_key']=work_key(r['candidate']);groups[r['work_key']].append(r)
            for group in groups.values():
                for r in group:
                    write_json(self.root/dev['id']/'sources'/r['source_id']/'evidence.json',r)
                count+=len(group)-1
        print(f'Work-identity check groups {count} alternate representations without discarding cited passages.',flush=True)

    def records(self, dev):
        return [read_json(p) for p in sorted((self.root/dev["id"]/"sources").glob("*/evidence.json"))]

    def stats(self, dev):
        rows = self.records(dev)
        accepted = [r for r in rows if r["status"]=="accepted"]
        return work_coverage(accepted)

    def catalog(self, dev):
        folder=self.root/dev["id"]
        path=folder/"catalog-all.json"
        saved=read_json(path)
        if saved is not None:
            if dev['id']=='primeagen' and not saved.get('channel_metadata_checked'):
                return self.add_primeagen_videos(dev,saved,path)
            return saved
        leads_path=folder/"hub-links.json"
        leads=read_json(leads_path)
        if leads is None:
            leads=[]
            for seed in dev["seeds"]:
                try:
                    page=get_page(seed)
                    for link in page.get("links",[]):
                        url=canonical(link["url"])
                        if valid_lead(url):
                            # A course collection is one work, not a separate source per chapter.
                            p=urllib.parse.urlsplit(url)
                            course="https://theprimeagen.github.io/"+p.path.strip('/').split('/')[0]+"/"
                            if p.hostname=="theprimeagen.github.io" and is_course_index(course):
                                url=course
                            leads.append({"url":url,"title":link.get("title","")[:200]})
                except Exception as exc:
                    print(f"{dev['id']}: seed unavailable ({type(exc).__name__}): {seed}",flush=True)
            leads=list({r["url"]:r for r in leads}.values())
            write_json(leads_path,leads)
        old=read_json(folder/"candidates.json",{"sources":[],"gaps":[]})
        unique={canonical(s["url"]):dict(s,url=canonical(s["url"])) for s in old["sources"]}
        gaps=list(old.get("gaps",[]))
        for round_no in range(self.config.get("discovery_rounds",2)):
            prompt=(f"Research a DEEP source collection for {dev['name']}. Focus: {dev['focus']}\n"
                    "Roast-room's deep benchmark is 80+ distinct works and 500,000+ words. Find up to 65 ADDITIONAL substantial first-hand works in this round. "
                    "Prioritize original essays, papers, detailed authored technical documentation, full talks, keynotes, own-channel long-form video, "
                    "and long interviews with publisher transcripts. Cover multiple years, frameworks, principles, concrete cases, changed views, limitations and distinctive voice. "
                    "Use primary/publisher sources. Do not treat a company employee's work as the named founder's words. Preserve coauthorship. "
                    "No pirated/paywalled book text. Do not fabricate URLs, pad with irrelevant material, count chapters or clips/mirrors of one work independently. "
                    "Supply a stable work_key shared by alternate editions/transcripts of the SAME work, and explain attribution. "
                    "Prefer material we can retrieve as text/captions. Include full technical conference videos where appropriate. "
                    +("ThePrimeagen specifically needs much stronger VIDEO coverage: prioritize his own talks/lectures/technical streams and real full-length interviews, not other people discussing him or reaction compilations. " if dev["id"]=="primeagen" else "")
                    +f"Round {round_no+1}; existing works must not be repeated. Return fewer if no verified primary leads exist; identify gaps.\n"
                    +json.dumps({"seeds":dev["seeds"],"existing_urls":list(unique),"unverified_hub_links":leads[:320]},ensure_ascii=False))
            result=self.call(dev["id"],"discover",prompt,CATALOG,search=True,max_output_tokens=10500)
            for item in result["sources"]:
                url=canonical(item["url"])
                if valid_lead(url): unique.setdefault(url,dict(item,url=url))
            gaps.extend(result["gaps"])
            write_json(folder/f"discovery-{round_no+1}.json",result)
        # First-party hub leads remain unverified candidates; Terra must assess each source's actual content.
        hosts={urllib.parse.urlsplit(u).hostname for u in dev["seeds"]}
        for link in leads:
            p=urllib.parse.urlsplit(link["url"])
            if p.hostname in hosts and p.path.strip('/') and len(link["title"].split())>=3:
                unique.setdefault(link["url"],dict(link,reason="Unverified first-party hub link; must establish actual author and substantive content."))
        result={"sources":list(unique.values())[:self.config["max_candidates"]],"gaps":gaps,"created_at":now()}
        write_json(path,result)
        if dev['id']=='primeagen':return self.add_primeagen_videos(dev,result,path)
        print(f"{dev['id']}: catalogued {len(result['sources'])} candidates",flush=True)
        return result

    def add_primeagen_videos(self,dev,catalog,path):
        cache=self.root/dev['id']/'channel-videos.json'
        metadata=read_json(cache)
        if metadata is None:
            try:
                p=subprocess.run(['yt-dlp','--ignore-config','--no-cache-dir','--flat-playlist','--playlist-items','1:120','--dump-single-json','https://www.youtube.com/@ThePrimeagen/videos'],capture_output=True,text=True,timeout=100)
                metadata=json.loads(p.stdout)
                write_json(cache,{'entries':[{k:r.get(k) for k in ('id','title','duration','url')} for r in metadata.get('entries',[])],'retrieved_at':now()})
                metadata=read_json(cache)
            except Exception as exc:
                catalog['gaps'].append('Own-channel video listing unavailable: '+type(exc).__name__)
                metadata={'entries':[]}
        unique={canonical(r['url']):r for r in catalog['sources']}
        added=0
        for entry in metadata.get('entries',[]):
            if not entry.get('id'):continue
            url='https://www.youtube.com/watch?v='+entry['id']
            if url not in unique:
                unique[url]={'url':url,'title':entry.get('title',''),'work_key':'youtube-'+entry['id'],'reason':'Actual own-channel video metadata; caption content, duration and speaker still require verification.'};added+=1
        catalog.update(sources=list(unique.values())[:self.config['max_candidates']],channel_metadata_checked=True)
        write_json(path,catalog)
        print(f"primeagen: own-channel metadata added {added} video candidates",flush=True)
        return catalog

    def expand_primary_links(self,dev,catalog):
        """Follow actual primary indexes and publisher talk embeds, never invented URLs."""
        if catalog.get('linked_media_checked'):return catalog
        hosts={urllib.parse.urlsplit(u).hostname for u in dev['seeds']}
        probes=list(dev['seeds'])
        for c in catalog['sources']:
            p=urllib.parse.urlsplit(c['url'])
            if (p.hostname in hosts and re.search(r'contents|talks|product/index|papers|archive',p.path)) or p.hostname=='lexfridman.com':
                probes.append(c['url'])
            if len(probes)>=12:break
        unique={canonical(r['url']):r for r in catalog['sources']}
        for url in dict.fromkeys(probes):
            try:page=get_page(url)
            except Exception:continue
            for link in page.get('links',[]):
                target=canonical(link['url']);p=urllib.parse.urlsplit(target)
                video=p.hostname in ('www.youtube.com','youtube.com') and p.path=='/watch'
                authored=p.hostname in hosts and len(link['title'].split())>=3
                if valid_lead(target) and (video or authored):
                    unique.setdefault(target,{'url':target,'title':link['title'],'reason':'Actual primary index or publisher media link from '+url+'; substantive content and speaker still require verification.'})
        catalog.update(sources=list(unique.values())[:self.config['max_candidates']],linked_media_checked=True)
        write_json(self.root/dev['id']/'catalog-all.json',catalog)
        print(f"{dev['id']}: primary-link catalog {len(catalog['sources'])} candidates",flush=True)
        return catalog

    def expand_video_search(self,dev,catalog):
        """Retrieve real long-form video metadata; Terra still verifies each speaker."""
        if not dev.get('video_query') or catalog.get('technical_video_search_checked')=='long-form-2':return catalog
        cache=self.root/dev['id']/'technical-video-search.json'
        metadata=read_json(cache)
        if metadata is None:
            p=subprocess.run(['yt-dlp','--ignore-config','--no-cache-dir','--flat-playlist','--dump-single-json','ytsearch30:'+dev['video_query']],capture_output=True,text=True,timeout=120)
            if not p.stdout.strip():raise ValueError('Video metadata search unavailable; no URLs invented')
            raw=json.loads(p.stdout)
            metadata={'query':dev['video_query'],'retrieved_at':now(),'entries':[{k:r.get(k) for k in ('id','title','duration','url','channel')} for r in raw.get('entries',[]) if r]}
            write_json(cache,metadata)
        old={canonical(r['url']):r for r in catalog['sources'] if not r.get('reason','').startswith('Actual technical-video search metadata')}
        videos=[]
        for r in metadata['entries']:
            if not r.get('id') or (r.get('duration') or 0)<600:continue
            if re.search(r'\b(?:clips?|highlights?|reacts|reaction)\b',str(r.get('channel',''))+' '+str(r.get('title','')),re.I):continue
            url='https://www.youtube.com/watch?v='+r['id']
            if url not in old:
                videos.append({'url':url,'title':r.get('title',''),'work_key':'youtube-'+r['id'],
                               'reason':'Actual technical-video search metadata, duration '+str(r['duration'])+' seconds; full captions and target speaker require verification; channel '+str(r.get('channel',''))})
        # Curated discoveries and new long-form video precede unverified hub links.
        curated=[r for r in old.values() if not r.get('reason','').startswith(('Unverified first-party hub link','Actual primary index'))]
        hub=[r for r in old.values() if r not in curated]
        catalog.update(sources=(curated+videos+hub)[:self.config['max_candidates']],technical_video_search_checked='long-form-2')
        write_json(self.root/dev['id']/'catalog-all.json',catalog)
        print(f"{dev['id']}: added {len(videos)} real long-form video candidates",flush=True)
        return catalog

    def expand_own_channel(self,dev,catalog):
        channel=dev.get('video_channel')
        if not channel or catalog.get('own_channel_checked'):return catalog
        cache=self.root/dev['id']/'own-channel-videos.json';metadata=read_json(cache)
        if metadata is None:
            p=subprocess.run(['yt-dlp','--ignore-config','--no-cache-dir','--flat-playlist','--playlist-items','1:120','--dump-single-json',channel],capture_output=True,text=True,timeout=120)
            if not p.stdout.strip():raise ValueError('Own-channel metadata unavailable')
            raw=json.loads(p.stdout)
            metadata={'channel_url':channel,'retrieved_at':now(),'entries':[{k:r.get(k) for k in ('id','title','duration','url')} for r in raw.get('entries',[]) if r]}
            write_json(cache,metadata)
        unique={canonical(r['url']):r for r in catalog['sources']};added=0
        for entry in metadata['entries']:
            if not entry.get('id') or (entry.get('duration') or 0)<600:continue
            url='https://www.youtube.com/watch?v='+entry['id']
            if url not in unique:
                unique[url]={'url':url,'title':entry.get('title',''),'work_key':'youtube-'+entry['id'],
                             'reason':'Actual long-form own-channel metadata from '+channel+'; captions, target speaker and distinct-work identity still require verification.'};added+=1
        catalog.update(sources=list(unique.values())[:self.config['max_candidates']],own_channel_checked=True)
        write_json(self.root/dev['id']/'catalog-all.json',catalog)
        print(f"{dev['id']}: added {added} own-channel long-form candidates",flush=True)
        return catalog

    def prepare(self, dev, candidate):
        candidate=dict(candidate,url=canonical(candidate["url"]))
        sid=source_id(dev,candidate["url"])
        folder=self.root/dev["id"]/"sources"/sid
        record=read_json(folder/"evidence.json")
        video=urllib.parse.urlsplit(candidate["url"]).hostname in ('youtube.com','www.youtube.com','youtu.be')
        # Retry the old caption simulation failure once with the corrected retrieval path.
        refresh_video=bool(record and record['status']=='held_out' and video and not record.get('caption_fix_attempted'))
        refresh_tutorial=bool(record and record['status']=='held_out' and 300<=record.get('metadata',{}).get('duration_seconds',0)<540 and record.get('words',0)>=800
                              and any('Video shorter' in issue for issue in record.get('issues',[])))
        refresh_archive=bool(record and record['status']=='held_out' and is_transcript_landing(candidate['url']) and not record.get('transcript_fix_attempted'))
        if record and record['status'] in ('accepted','duplicate','held_out') and not (refresh_video or refresh_tutorial or refresh_archive):
            return record
        folder.mkdir(parents=True,exist_ok=True)
        record=record or {"source_id":sid,"developer":dev['id'],"url":candidate['url'],"candidate":candidate,"evidence":[],"rejected_evidence":[],"issues":[],"parts_done":[],"extractions":[]}
        try:
            if (folder/'source.txt').exists() and (folder/'source.json').exists() and not (refresh_video or refresh_archive):
                text=(folder/'source.txt').read_text();meta=read_json(folder/'source.json')
            else:
                page=get_source(candidate['url']);text,meta=page['text'],page['metadata']
                if len(text.split())<80: raise ValueError('Source extraction is too short to establish substantial first-hand reasoning')
                (folder/'source.txt').write_text(text);write_json(folder/'source.json',meta)
            if refresh_archive:
                record.setdefault('prior_archive_extractions',[]).extend(record.get('extractions',[]))
                record.update(evidence=[],rejected_evidence=[],issues=[],parts_done=[],extractions=[],transcript_fix_attempted=True)
            if meta.get('original_work_url'):candidate['original_work_url']=meta['original_work_url']
            words=len(caption_view(text)[0].split()) if meta.get('duration_seconds') else len(text.split())
            record['candidate']=candidate
            record.update(metadata=meta,words=words,text_sha256=digest(normalize(text)),work_key=work_key(candidate),status='pending',caption_fix_attempted=video)
            if wrong_podcast_guest(dev,record):raise ValueError('Publisher metadata identifies a different podcast guest, not the requested advisor')
            self.scope_mail(dev,record)
            if meta.get('duration_seconds') and (meta['duration_seconds']<300 or (meta['duration_seconds']<540 and words<800)):
                raise ValueError('Video shorter than five minutes, or a short item with fewer than 800 caption words; held out in favor of substantial full works')
            write_json(folder/'evidence.json',record)
            return record
        except Exception as exc:
            record.update(status='held_out',caption_fix_attempted=video,transcript_fix_attempted=is_transcript_landing(candidate['url']),issues=[str(exc)[:300]])
            write_json(folder/'evidence.json',record)
            return record

    def scope_mail(self,dev,record):
        if urllib.parse.urlsplit(record['url']).hostname!='lore.kernel.org' or record.get('source_scope'):return
        raw=(self.root/dev['id']/'sources'/record['source_id']/'source.txt').read_text()
        if not re.search(r'(?m)^From:.* @ \d{4}-\d{2}-\d{2}',raw):
            if record['words']>10000:raise ValueError('Large thread archive has no verifiable target-sender scope')
            return
        ranges,note=mail_sender_scope(raw,dev.get('aliases',[dev['name']]))
        apply_scope(record,raw,ranges,note)
        if record['coverage_words']<80:raise ValueError('Too little unquoted target-author material in the thread for a substantial source')
        record.update(status='pending',parts_done=[],scope_partition_version='normalized-ranges-v1')

    def parts(self, dev, record):
        text=(self.root/dev['id']/'sources'/record['source_id']/'source.txt').read_text()
        if record.get('source_scope'):
            full=normalize(text);pieces=[(full[a:min(a+115000,b)],a) for start,b in record['source_scope']['normalized_ranges'] for a in range(start,b,115000)]
            record['total_chunks']=len(pieces);done=set(record.get('parts_done',[]))
            opening=pieces[0][0][:2000] if pieces else ''
            return [{'source_id':record['source_id'],'part':i,'developer':dev['id'],'candidate':record['candidate'],'metadata':record['metadata'],
                     'source_opening_for_attribution_only':opening,'text':chunk,'normalized_start':start,'evidence_budget':min(28,max(6,len(chunk.split())//650))}
                    for i,(chunk,start) in enumerate(pieces) if i not in done]
        chunks=[text[i:i+115000] for i in range(0,len(text),115000)]
        record['total_chunks']=len(chunks)
        done=set(record.get('parts_done',[]))
        return [{"source_id":record['source_id'],"part":i,"developer":dev['id'],"candidate":record['candidate'],
                 "metadata":record['metadata'],"source_opening_for_attribution_only":text[:2000],"text":chunk,
                 "char_start":i*115000,"evidence_budget":min(28,max(6,len(chunk.split())//650))}
                for i,raw_chunk in enumerate(chunks) if i not in done
                for chunk in [caption_view(raw_chunk)[0] if record['metadata'].get('duration_seconds') else raw_chunk]]

    def verified_part(self,dev,r,part,x):
        raw=(self.root/dev['id']/'sources'/r['source_id']/'source.txt').read_text()
        video=bool(r['metadata'].get('duration_seconds'))
        if 'normalized_start' in part:
            full=normalize(raw);cues=[];text=part['text'];base=part['normalized_start']
        elif video:
            full,cues=caption_view(raw)
            text=caption_view(part['text'])[0]
            x=dict(x,evidence=[dict(e,quote=caption_view(e['quote'])[0]) for e in x.get('evidence',[])])
            prefix=caption_view(raw[:part.get('char_start',0)])[0]
            base=len(prefix)
        else:
            full=normalize(raw);cues=[];text=part['text']
            prefix=raw[:part.get('char_start',0)];base=len(normalize(prefix))
            if prefix and text and (prefix[-1].isspace() or text[0].isspace()):base+=1
        good,bad=verify_evidence(r['source_id'],dev['id'],text,x,dev.get('aliases',[dev['name']]))
        located=[]
        for ev in good:
            offset=base+ev['passage_offset']
            if full[offset:offset+len(ev['quote'])]!=ev['quote']:
                radius=24 if video else 2
                offset=full.find(ev['quote'],max(0,base-radius),base+len(normalize(text))+radius)
                if offset<0:
                    bad.append({'reason':'Quote not located inside its actual source part after formatting normalization','claim':ev['claim']});continue
            ev.update(chunk_index=part['part'],passage_offset=offset,source_url=r['metadata']['url'])
            if r.get('source_scope') and not any(a<=offset and offset+len(ev['quote'])<=b for a,b in r['source_scope']['normalized_ranges']):
                bad.append({'reason':'Passage outside verified primary-author scope','claim':ev['claim']});continue
            if video:ev['passage_view']='caption-prose-v1'
            sections=re.findall(r'SOURCE SECTION: (https?://\S+)',full[:offset])
            if sections and sections[-1] in {p['url'] for p in r['metadata'].get('parts',[])}:ev['source_url']=sections[-1]
            stamps=[stamp for position,stamp in cues if position<=offset]
            if stamps:
                stamp=stamps[-1];hh,mm,ss=map(int,stamp.split(':'));seconds=hh*3600+mm*60+ss
                if seconds<=r['metadata']['duration_seconds']+1:
                    ev['timestamp']=stamp
                    if urllib.parse.urlsplit(ev['source_url']).hostname in ('youtube.com','www.youtube.com'):ev['source_url']+='&t='+str(seconds)
            located.append(ev)
        return located,bad

    def repair_caption_evidence(self):
        """Recheck cached extractions without paid requests; retain original timed text."""
        recovered=0
        for dev in self.config['developers']:
            for r in self.records(dev):
                if r['status']=='duplicate' or not r.get('metadata',{}).get('duration_seconds') or not r.get('extractions') or r.get('caption_evidence_version')=='caption-prose-v1':continue
                raw=(self.root/dev['id']/'sources'/r['source_id']/'source.txt').read_text()
                good=[];bad=[]
                for x in r['extractions']:
                    index=x.get('part',0);start=index*115000
                    a,b=self.verified_part(dev,r,{'part':index,'text':raw[start:start+115000],'char_start':start},x)
                    good+=a;bad+=b
                was=r['status'];r.setdefault('rejected_evidence_before_caption_fix',r.get('rejected_evidence',[]))
                r.update(evidence=list({e['id']:e for e in good}.values()),rejected_evidence=bad,caption_evidence_version='caption-prose-v1',words=len(caption_view(raw)[0].split()))
                complete=len(set(r.get('parts_done',[])))==r.get('total_chunks',1)
                r['status']=('accepted' if good else 'held_out') if complete else 'pending'
                if was!='accepted' and r['status']=='accepted':recovered+=1
                write_json(self.root/dev['id']/'sources'/r['source_id']/'evidence.json',r)
        print(f'Caption formatting recheck recovered {recovered} full works without paid calls.',flush=True)

    def extract_batch(self, dev, parts, records):
        prompt=(f"Read these source parts IN FULL and extract {dev['name']}'s technical reasoning. Focus: {dev['focus']}\n"
                "Return one item for EVERY supplied source_id/part, preserving IDs exactly. Assess each source separately. "
                "For each part return up to its evidence_budget diverse, substantive evidence items: named/unnamed frameworks and their steps, decision rules, technical positions, thresholds/conditions, cases and lessons, books discussed and distinctive voice. Preserve distinct reasoning across the full part, without padding. "
                "Prioritize useful reasoning over isolated facts. Copy short exact contiguous quotations from that part's text, with actual author/speaker and context. Do not quote the attribution-only opening as evidence for another part. "
                "No claims from other speakers, quoted critics, third-party summaries or merely nearby company material. Distinguish coauthored positions. "
                "A third-party reaction, recap, compilation or reading of quotations is not an eligible primary work merely because it contains a short target-speaker clip. Prefer the original full work. "
                "Unlabelled captions require a clearly established target speaker; note transcription uncertainty and missing diagrams/code. "
                "A home/index/navigation page is not evidence of a position. Mark ineligible when attribution or substantive support is absent. "
                "Preserve dates only when actually supplied, changes of mind, exceptions, self-criticism and disagreement. Never invent to meet counts.\n"
                +json.dumps({"source_parts":parts},ensure_ascii=False))
        result=self.call(dev['id'],'extract_batch',prompt,BATCH,max_output_tokens=19000)
        expected={(p['source_id'],p['part']):p for p in parts}
        returned=set()
        for item in result['items']:
            key=(item['source_id'],item['part'])
            if key not in expected or key in returned: raise ValueError('Batch changed or duplicated source/part identity')
            returned.add(key)
            part=expected[key];r=records[item['source_id']];x=item['extraction']
            good,bad=self.verified_part(dev,r,part,x)
            if r['metadata'].get('duration_seconds'):r['caption_evidence_version']='caption-prose-v1'
            r['evidence']=list({e['id']:e for e in r['evidence']+good}.values())
            r['rejected_evidence']+=bad
            r.setdefault('extractions',[]).append(dict(x,part=item['part']))
            r.setdefault('parts_done',[]).append(item['part'])
            r['issues']+=x.get('limitations',[])
            r['status']=('accepted' if r['evidence'] else 'held_out') if len(set(r['parts_done']))==r['total_chunks'] else 'pending'
            write_json(self.root/dev['id']/'sources'/r['source_id']/'evidence.json',r)
        if returned!=set(expected): raise ValueError('Batch omitted a source part; retained completed parts, stopped for inspection')
        print(f"{dev['id']}: extracted {len(parts)} source parts; {self.stats(dev)} works/words; usage ${self.ledger.exposure():.3f}",flush=True)

    def map_work(self, dev, catalog):
        current=self.records(dev)
        fingerprints={r.get('text_sha256') for r in current if r['status']=='accepted'}
        works={r.get('work_key',work_key(r['candidate'])) for r in current if r['status']=='accepted'}
        pending=[]
        for r in current:
            if r['status']!='pending':continue
            if wrong_podcast_guest(dev,r):
                r.update(status='held_out',issues=['Publisher metadata identifies a different podcast guest; remaining parts are not mapped.'])
                write_json(self.root/dev['id']/'sources'/r['source_id']/'evidence.json',r);continue
            try:self.scope_mail(dev,r)
            except ValueError as exc:
                r.update(status='held_out',issues=[str(exc)]);write_json(self.root/dev['id']/'sources'/r['source_id']/'evidence.json',r);continue
            if r['text_sha256'] in fingerprints or r['work_key'] in works:
                r.update(status='duplicate',issues=['Same work or source text already retained for this advisor'])
                write_json(self.root/dev['id']/'sources'/r['source_id']/'evidence.json',r)
                continue
            fingerprints.add(r['text_sha256']);works.add(r['work_key']);pending.append(r)
        # Drain prepared archives in bounded groups so one prolific advisor does
        # not monopolize the shared worker pool or source allowance.
        pending=pending[:self.config.get('batch_sources',8)]
        candidates=[]
        for c in catalog['sources']:
            p=self.root/dev['id']/'sources'/source_id(dev,c['url'])/'evidence.json'
            old=read_json(p)
            is_old_video=bool(old and old['status']=='held_out' and urllib.parse.urlsplit(c['url']).hostname in ('youtube.com','www.youtube.com','youtu.be') and not old.get('caption_fix_attempted'))
            is_old_archive=bool(old and old['status']=='held_out' and is_transcript_landing(c['url']) and not old.get('transcript_fix_attempted'))
            if work_key(c) in works:continue
            if old is None or is_old_video or is_old_archive:candidates.append(c)
        # Retrieval is free and bounded; model work remains serialized under the common ledger.
        slots=max(0,self.config.get('batch_sources',8)-len(pending))
        with ThreadPoolExecutor(max_workers=4) as pool:
            fetched=list(pool.map(lambda c:self.prepare(dev,c),candidates[:slots]))
        records={r['source_id']:r for r in pending}
        for r in fetched:
            if r['status']!='pending':continue
            if r['text_sha256'] in fingerprints or r['work_key'] in works:
                r.update(status='duplicate',issues=['Same work or source text already retained for this advisor'])
                write_json(self.root/dev['id']/'sources'/r['source_id']/'evidence.json',r)
                continue
            fingerprints.add(r['text_sha256']);works.add(r['work_key']);records[r['source_id']]=r
        batch=[];size=0
        for r in records.values():
            for part in self.parts(dev,r):
                n=len(part['text'])
                if batch and (size+n>self.config['batch_chars'] or len(batch)>=self.config['batch_sources']):
                    self.extract_batch(dev,batch,records);batch=[];size=0
                batch.append(part);size+=n
        if batch:self.extract_batch(dev,batch,records)
        return bool(candidates or pending)

    def deep_compile(self, dev):
        records=[r for r in self.records(dev) if r['status']=='accepted']
        previous=read_json(self.root/dev['id']/'compiled.json',{})
        if previous.get('source_fingerprint')==collection_fingerprint(records):
            self.export(dev,records,previous);return
        evidence={e['id']:e for r in records for e in r['evidence']}
        if not evidence:
            write_json(self.root/dev['id']/'compiled.json',{'sections':[], 'gaps':['No accepted first-hand evidence; advisor is unavailable']})
            return
        works,coverage=work_coverage(records)
        context={"evidence":list(evidence.values()),"source_count":works,"source_words":coverage,
                 "deep_benchmark":{"works":80,"words":500000},"sources":[{'source_id':r['source_id'],'title':r.get('metadata',{}).get('title') or r['candidate'].get('title'),
                      'dates':sorted({x['date'] for x in r.get('extractions',[]) if x.get('date')}),'limitations':list(dict.fromkeys(r.get('issues',[])))[:6]} for r in records]}
        if works!=len(records):
            context.update(source_count=works,source_words=coverage,
                           work_identity={r['source_id']:r['work_key'] for r in records},
                           counting_note='Alternate uploads, excerpts and republications of one work are NOT independent corroboration. Count work_identity groups, not source records.')
        groups=[('frameworks','principles','books'),('positions','stories'),('voice',)]
        sections=[];gaps=[]
        budgets=("frameworks: 12-25 substantive entries, each with name (mark unnamed when appropriate), parts/steps, when useful, decision/scoring guidance grounded in their thresholds or explicitly inferred, and supporting evidence IDs. "
                 "principles: 15-30 distinct decision rules, qualifications, source support/confidence (high only with 3+ independent works, medium 2, low 1). "
                 "positions: 20-40 TECHNICAL topics, with stance, conditions, source date where available, and old/new views together when evidence changed. "
                 "stories: 10-20 distinct concrete cases, the developer's role, lesson and limits. "
                 "voice: 400-550 words on cadence, vocabulary, analogies, arguing, disagreeing and conceding, with evidence IDs from at least 8 independent works when available as voice anchors. The renderer adds exact short quotations from these IDs. "
                 "books: one entry per book/major essay series actually established by evidence, with thesis and taught frameworks; do not invent books or reproduce text. ")
        budgets+=("Where evidence warrants it, aim for 120-220 words per framework, 70-130 per principle, 80-140 per position and 120-220 per case. "
                  "Explain mechanisms, conditions, exceptions and practical application. Do not stretch thin evidence to a word quota. ")
        for group in groups:
            kinds={'framework','principle','book','position'} if group[0]=='frameworks' else {'position','story','principle','framework'} if group[0]=='positions' else {'voice'}
            selected={i:e for i,e in evidence.items() if e['kind'] in kinds}
            # Voice needs a representative language sample even when a mapper categorized it as a rule.
            if group==('voice',):
                for r in records:
                    for e in r['evidence'][:2]:selected.setdefault(e['id'],e)
            if not selected:selected=evidence
            # Writers need the claim, exact passage, context and attribution.
            # Keep mechanical audit/location fields in the retained records and
            # renderer instead of repeating them in every compilation request.
            audit_fields={'developer','source_url','passage_offset','verification','chunk_index','passage_view','timestamp'}
            writer_context=dict(context,evidence=[{k:v for k,v in e.items() if k not in audit_fields} for e in selected.values()])
            group_budgets=("voice: 400-550 words on cadence, vocabulary, analogies, arguing, disagreeing and conceding, with evidence IDs from at least 8 independent works when available as voice anchors. The renderer adds exact short quotations from these IDs. Return only one voice section. " if group==('voice',) else budgets)
            prompt=(f"Write a DEEP, operational advisor brain for {dev['name']}. Technical lens: {dev['focus']}\n"
                    f"Write ONLY these sections exactly once: {', '.join(group)}. " +group_budgets+
                    "These are roast-room's structural targets, not permission to pad or invent. Where evidence is insufficient, produce fewer and explicitly record that gap. "
                    "Capture how this person decides, including trade-offs, disagreements, mistakes and when their experience does not transfer. This is not a biography. "
                    "Every item needs valid existing evidence_ids. Each paragraph is paraphrase: do not introduce direct quotation marks. Actual quotations will be supplied from verified passages. "
                    "Label synthesis inferred; do not assign unsupported historical positions. Merge duplicate ideas across works and cite independent corroboration. "
                    "Use plain English. Make entries rich enough for a council agent to apply, not slogans or one-line generalities. Do not guess support counts; citations are counted by code.\n"+json.dumps(writer_context,ensure_ascii=False))
            result=self.call(dev['id'],'compile_deep',prompt,COMPILATION,max_output_tokens=4500 if group==('voice',) else 18000)
            assigned=[s for s in result['sections'] if s['name'] in group]
            if sorted(s['name'] for s in assigned)!=sorted(group):raise ValueError('Deep writer omitted or duplicated an assigned section')
            extra=len(assigned)!=len(result['sections'])
            for s in assigned:
                keep=[]
                for item in s['items']:
                    if not item['evidence_ids'] or any(i not in evidence for i in item['evidence_ids']) or re.search(r'[“”"]',item['text']):
                        gaps.append('Held out a compiled item with invalid evidence references or unverified quotation formatting.')
                    else:keep.append(item)
                s['items']=keep
            sections+=assigned
            gaps += ([g for g in result['gaps'] if re.search(r'voice|speaker|transcript|audio|cadence|style|tone|vocabulary|communication|humou?r',g,re.I)] if extra and group==('voice',) else result['gaps'])
        hot=self.compile_hot(dev,records,sections)
        compiled={'sections':hot['sections']+sections,'gaps':coverage_gaps(gaps+hot['gaps'],records),'source_fingerprint':collection_fingerprint(records)}
        if works<80 or coverage<500000:
            compiled['gaps'].append(f"Deep source benchmark not met: {works} works and {coverage:,} words versus 80+ works / 500,000+ words.")
        for s in sections:
            if s['name'] in TARGETS and len(s['items'])<TARGETS[s['name']][0]:
                compiled['gaps'].append(f"{s['name']} has {len(s['items'])} supported entries; upstream target is {TARGETS[s['name']][0]}-{TARGETS[s['name']][1]}.")
        self.export(dev,records,compiled)

    def compile_hot(self,dev,records,sections):
        evidence={e['id']:e for r in records for e in r['evidence']}
        works,coverage=work_coverage(records)
        referenced={i for s in sections for item in s['items'] for i in item['evidence_ids']}
        source_map={i:{'source_id':evidence[i]['source_id'],'attribution':evidence[i]['attribution']} for i in sorted(referenced)}
        if works!=len(records):
            identities={r['source_id']:r['work_key'] for r in records}
            for item in source_map.values():item['work_key']=identities[item['source_id']]
        hot_prompt=(f"Write ONLY _hot for {dev['name']}, 600-750 words. This is the operational working context for a technical decision advisor. "
                    "Include the lens/pillar and decision question, corpus size and limits, a three-sentence worldview, eight sourced decision rules, five key frameworks, "
                    "a five/six-step decision loop, signature questions, a five-line voice guide, and a mandatory clearly named Where this lens misfires passage. "
                    "Every item cites existing evidence_ids. Paraphrase without quotation marks; label inferences. No unsupported expertise. "
                    "Use the substantive written sections below, and only their sources. Return one _hot section, with gaps if support is insufficient.\n"
                    +json.dumps({'sections':sections,'source_map':source_map,
                                 'coverage_notes':[r['source_scope']['note'] for r in records if r.get('source_scope')],
                                 'source_count':works,'source_words':coverage},ensure_ascii=False))
        hot=self.call(dev['id'],'compile_hot',hot_prompt,COMPILATION,max_output_tokens=7000)
        hot['sections']=[s for s in hot['sections'] if s['name']=='_hot']
        if len(hot['sections'])!=1:raise ValueError('Hot writer omitted or duplicated its assigned section')
        for s in hot['sections']:
            s['items']=[i for i in s['items'] if i['evidence_ids'] and all(e in referenced for e in i['evidence_ids']) and not re.search(r'[“”"]',i['text'])]
        return hot

    def full_report(self,status):
        ledger=self.ledger.data['jobs']
        result={'status':status,'generated_at':now(),'cumulative_estimated_usd':self.ledger.exposure(),'budget_usd':self.ledger.cap,'original_pilot_ceiling_usd':25,'developers':[]}
        lines=['# Full roster source collection','',f"Status: {status}",'',f"Cumulative estimated API usage, INCLUDING the pilot: **${self.ledger.exposure():.4f} / ${self.ledger.cap:.2f}**.",'',
               'Roast-room deep benchmark: 80+ distinct works and 500,000+ words per advisor. Standard: 30-50 works and 250,000+ words. Counts are evidence targets, not permission to pad.','',
               '| Advisor | Works | Source words | Matched passages | Captioned videos | Talk/interview works | Source tier |','| --- | ---: | ---: | ---: | ---: | ---: | --- |']
        result['budget_status']='exceeded' if self.ledger.exposure()>self.ledger.cap else 'within ceiling'
        details=[]
        for dev in self.config['developers']:
            all_rows=self.records(dev);rs=[r for r in all_rows if r['status']=='accepted'];works,words=work_coverage(rs)
            video=len({r.get('work_key',r['url']) for r in rs if r.get('metadata',{}).get('duration_seconds',0)>0 and urllib.parse.urlsplit(r.get('metadata',{}).get('url',r['url'])).hostname in ('youtube.com','www.youtube.com','youtu.be')})
            spoken=len({r.get('work_key',r['url']) for r in rs if any(x.get('eligible') and x.get('attribution')=='speaker' for x in r.get('extractions',[]))})
            compiled=read_json(self.root/dev['id']/'compiled.json',{})
            catalog=read_json(self.root/dev['id']/'catalog-all.json',{'sources':[]})
            attempted={canonical(r['url']) for r in all_rows}
            entries={s['name']:len(s['items']) for s in compiled.get('sections',[])}
            compiled_words={s['name']:sum(len(i['text'].split()) for i in s['items']) for s in compiled.get('sections',[])}
            voice_path=self.project/'knowledge'/dev['id']/'voice.md'
            voice_anchors=len(re.findall(r'^> ',voice_path.read_text(),re.M)) if voice_path.exists() else 0
            tier='deep' if works>=80 and words>=500000 else 'standard' if works>=30 and words>=250000 else 'quick' if works>=12 and words>=80000 else 'limited'
            record={'id':dev['id'],'name':dev['name'],'works':works,'source_representations':len(rs),'words':words,'full_retrieved_words':sum(r['words'] for r in rs),'matched_passages':sum(len(r['evidence']) for r in rs),'captioned_videos':video,'talk_or_interview_works':spoken,'source_tier':tier,'entries':entries,
                    'compilation_current':compiled.get('source_fingerprint')==collection_fingerprint(rs),
                    'cost_usd':sum(j.get('cost_usd',j['reserved_usd']) for j in ledger.values() if j['developer']==dev['id']),
                    'compiled_words':compiled_words,
                    'voice_anchors':voice_anchors,
                    'pending_sources':sum(r['status']=='pending' for r in all_rows),
                    'unattempted_candidates':sum(canonical(r['url']) not in attempted for r in catalog['sources']),
                    'gaps':compiled.get('gaps',['Compilation not yet available']), 'held_out':sum(r['status']=='held_out' for r in all_rows),
                    'retrieval_gaps':dict(collections.Counter(issue for r in all_rows if r['status']=='held_out' for issue in r.get('issues',[])[:1]))}
            result['developers'].append(record)
            lines.append(f"| {dev['name']} | {works} | {words:,} | {record['matched_passages']} | {video} | {spoken} | {tier} |")
            details += ['',f"## {dev['name']}",'',f"Entry counts: {entries}. Working context: {compiled_words.get('_hot',0):,} words; voice guidance: {compiled_words.get('voice',0):,} prose words plus {voice_anchors} verified anchors. Estimated API usage: ${record['cost_usd']:.4f}. Held-out sources: {record['held_out']}. Queue remaining: {record['pending_sources']} partial/unreviewed retrieved works and {record['unattempted_candidates']} unattempted candidates.",'']+[f"- {g}" for g in record['gaps']]
            details += [f"- Retrieval/eligibility gap ({count} sources): {issue}" for issue,count in record['retrieval_gaps'].items()]
        result['totals']={key:sum(d[key] for d in result['developers']) for key in ('works','words','matched_passages','captioned_videos')}
        result['totals']['advisors']=len(result['developers'])
        totals=result['totals']
        deep=sum(d['source_tier']=='deep' for d in result['developers'])
        result['totals']['current_compilations']=sum(d['compilation_current'] for d in result['developers'])
        lines[6:6]=[f"Prepared {totals['advisors']} advisors from {totals['works']:,} advisor/work counts, {totals['words']:,} scoped source words and {totals['matched_passages']:,} text-matched evidence passages. {totals['current_compilations']} of {totals['advisors']} compilations match the current accepted evidence. {deep} advisors meet both deep source thresholds.",'']
        baseline=read_json(self.root/'continuation-baseline.json',{})
        if baseline:
            result['continuation']={'estimated_usd':round(self.ledger.exposure()-baseline['cumulative_estimated_usd'],8),
                                    **{key:totals[key]-baseline['totals'][key] for key in ('works','words','matched_passages','captioned_videos')}}
            delta=result['continuation']
            lines[6:6]=[f"Net change during this existing-credit continuation: {delta['works']:,} advisor/work counts, {delta['words']:,} scoped source words and {delta['matched_passages']:,} matched passages for an estimated additional ${delta['estimated_usd']:.4f}. These figures include the effect of correcting earlier duplicate groupings.",'']
        if self.ledger.cap>25:
            lines[6:6]=['The owner subsequently authorized continuation using existing API credits. The current cumulative allocation includes all prior charges; it does not reset the ledger. The initial $23.724864 estimate was corrected to $27.286261 after including cache-write premiums, exceeding the original $25 ceiling by $2.286261. That historical overrun remains recorded.','']
        elif result['budget_status']=='exceeded':
            lines[6:6]=[f"**Budget correction:** the earlier $23.724864 estimate omitted cache-write premiums. Repricing saved usage under documented default 30-minute cache rates gives ${self.ledger.exposure():.6f}, ${self.ledger.exposure()-self.ledger.cap:.6f} above the original cap. Prior per-request estimates are preserved in the ledger. Further paid requests are blocked; no additional allowance has been authorized. This remains an estimate, not an account invoice.",'']
        lines+=details+['','## Evidence and budget notes','','Totals sum each advisor’s collection; a shared panel can appear in more than one advisor’s count. Source words count retained primary works, including interview questions and coauthored text. Explicit source scopes exclude unrelated archive messages and reader comments; original full snapshots remain local for audit. They are not a count of words spoken exclusively by the advisor. Alternate uploads, keynote parts and republications share a work identity and contribute only the largest scoped representation to word coverage; their cited passages remain retained. Talk/interview works and captioned videos also count unique work identities. Quotation checks establish normalized text membership and source identity. Attribution and semantic support are model-assessed. Course chapters are one work. Video-caption text is not audio-verified; missing visual/code context remains a limitation.','',
                                        'The original pilot ledger is reused, including all prior charges and any unresolved reservations. The current allocation reflects the owner’s latest authorization to use existing credits. Costs are token/tool estimates, not invoices. Raw source text, metadata, model outputs and passage evidence remain local and Git-ignored.']
        lines+=['','Principle corroboration is computed from cited distinct work identities: high for three or more, medium for two, low for one. It measures repeat support, not factual truth. The depth and structure comparisons come from [roast-room’s workflow](https://github.com/nateherkai/roast-room/blob/main/.claude/skills/newroaster/SKILL.md) and [brain specification](https://github.com/nateherkai/roast-room/blob/main/.claude/skills/newroaster/references/brain-spec.md). The installed summarize tool was evaluated in five extraction-only cases and not adopted; see [the evaluation](README.md#summarize-evaluation).']
        lines+=['','New retrieval rejects translated English caption tracks and retains the selected underlying language. Earlier caption snapshots did not retain track-level language metadata; their original-language provenance cannot be certified retrospectively from the local records. No claim of audio verification is made.']
        write_json(self.root/'full-report.json',result)
        (self.project/'collection'/'FULL-REPORT.md').write_text('\n'.join(lines).rstrip()+'\n')
        return result

    def run_full(self,catalog_only=False):
        status='completed'
        try:
            # New advisors first; retained pilot catalogs remain available throughout.
            order=sorted(self.config['developers'],key=lambda d:self.stats(d)[1])
            catalogs={}
            for dev in order:
                try:catalogs[dev['id']]=self.catalog(dev)
                except ValueError as exc:
                    print(f"{dev['id']}: discovery output held out: {exc}",flush=True)
                    catalogs[dev['id']]=read_json(self.root/dev['id']/'catalog-all.json',{'sources':[],'gaps':[str(exc)]})
            if catalog_only:return self.full_report('catalogs prepared')
            for dev in order:catalogs[dev['id']]=self.expand_primary_links(dev,catalogs[dev['id']])
            for dev in order:catalogs[dev['id']]=self.expand_video_search(dev,catalogs[dev['id']])
            for dev in order:catalogs[dev['id']]=self.expand_own_channel(dev,catalogs[dev['id']])
            exhausted=set();workers=min(3,max(1,self.config.get('workers',3)))
            with ThreadPoolExecutor(max_workers=workers) as pool:
                while True:
                    choices=[]
                    for dev in self.config['developers']:
                        works,words=self.stats(dev)
                        if dev['id'] not in exhausted and (works<self.config['target_sources'] or words<self.config['target_words']):
                            choices.append(((works/self.config['target_sources']+words/self.config['target_words'])/2,dev))
                    if not choices:break
                    chosen=sorted(choices,key=lambda x:x[0])[:workers]
                    futures=[(d,pool.submit(self.map_work,d,catalogs[d['id']])) for _,d in chosen]
                    budget_stop=False
                    for dev,future in futures:
                        try:
                            if not future.result():exhausted.add(dev['id'])
                        except BudgetStop:budget_stop=True
                        except ValueError as exc:
                            exhausted.add(dev['id'])
                            print(f"{dev['id']}: mapping paused after an invalid model result; completed evidence retained: {exc}",flush=True)
                    if budget_stop:
                        # A parallel reservation may fit after the other workers
                        # record their actual costs. Try once without competition.
                        try:
                            if self.map_work(chosen[0][1],catalogs[chosen[0][1]['id']]):continue
                        except BudgetStop:pass
                        print('Source budget reserve reached; compiling retained evidence.',flush=True);break
                # One task per advisor keeps its writers and source state ordered.
                futures=[(d,pool.submit(self.deep_compile,d)) for d in self.config['developers']]
                deferred=[]
                for dev,future in futures:
                    try:future.result()
                    except BudgetStop:deferred.append(dev)
                    except ValueError as exc:
                        status='completed with compilation gaps'
                        print(f"{dev['id']}: compilation held out: {exc}",flush=True)
            # A reservation blocked by active writers may fit after they finish.
            for dev in deferred:self.deep_compile(dev)
        except Exception as exc:
            status='stopped: '+str(exc)
        return self.full_report(status)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--catalog-only',action='store_true');p.add_argument('--report-only',action='store_true');args=p.parse_args()
    project=Path(__file__).resolve().parents[1];cfg=read_json(project/'collection/roster.json')
    if len(cfg['developers'])!=13 or not 0<cfg['budget_usd']<=51.5 or cfg['model']!='gpt-6.1-terra':raise ValueError('All-13 Terra scope and the currently authorized $51.50 cumulative allocation required')
    root=project/'.collection/pilot';root.mkdir(parents=True,exist_ok=True)
    with (root/'run.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if args.report_only:
            previous=read_json(root/'full-report.json',{})
            Expansion(project,cfg,None).full_report(previous.get('status','report refreshed'));return
        client=OpenAI(load_key(project/'.env'));client.preflight(cfg['model'])
        collector=Expansion(project,cfg,client)
        collector.ledger.reconcile_tool_fees()
        collector.ledger.reconcile_cache_prices()
        collector.repair_work_identities()
        collector.repair_caption_evidence()
        report=collector.run_full(args.catalog_only)
        print(f"Expansion {report['status']}; cumulative usage ${report['cumulative_estimated_usd']:.4f}",flush=True)
        if report['status'].startswith('stopped'):raise SystemExit(2)


if __name__=='__main__':main()
