"""Correct only the two NEW empty street barrel tag representations.

Frozen failed proposals/executables stay intact. No world operation is issued.
"""
from __future__ import annotations
import argparse
from copy import deepcopy
import json
from pathlib import Path
from control_room.common import UserError,digest,utcnow
from tools.artistic_pirate_spit import tag_snbt
from tools.artistic_quay_prototype import bounded,context,member,write_bundle
from tools.showcase_coverage import SNBT
from tools.playtest import guard

SOURCE='staging/west-crooked-street-furniture-0d7-20261028T0306Z'
SOURCE_SHA='f077698ff67446d37fa81e4e593e42f4d1aec08f1aa8c15f8315a17c39be38a9'
STOCK={(1027,64,-1272),(1039,64,-1250)}


def correct_tags(doc):
    fixed=deepcopy(doc);rows=fixed['block_entities']
    if len(rows)!=2 or {tuple(r['pos'])for r in rows}!=STOCK:raise UserError('Only the two exact NEW street barrels are admitted')
    for row in rows:
        old=row['nbt']
        if not isinstance(old,dict)or set(old)!={'id','Items','CustomName'}or old['id']!='minecraft:barrel'or old['Items']!=[]or not isinstance(old['CustomName'],str):
            raise UserError('Preserve the exact original empty-container/name intent')
        text=tag_snbt(old)
        if not isinstance(text,str)or len(text)>16384 or SNBT(text).read()!=old:raise UserError('Existing SNBT serializer must preserve every original field exactly')
        row['nbt']=text
    compare=deepcopy(fixed)
    for a,b in zip(compare['block_entities'],doc['block_entities']):a['nbt']=b['nbt']
    if compare!=doc:raise UserError('Only the literal NBT representation may change')
    return fixed


def prepare(home,output):
    reserve=guard(2*1024**2,8*1024**2);home,output,current,registry=context(home,output)
    folder=home/SOURCE;source=bounded(folder/'manifest.json')
    if digest(folder/'manifest.json')!=SOURCE_SHA or source['checkpoint_sha256']!=current['sha256']:
        raise UserError('Exact original failed source/current checkpoint required')
    docs={n:member(folder,source,n)for n in source['files']}
    for n in ('street-and-furniture-PROPOSAL.json','complete-after-VERIFY-ONLY.json'):docs[n]=correct_tags(docs[n])
    result=deepcopy(source);result.pop('files',None)
    result.update(created=utcnow(),source_sha256=digest(Path(__file__)),stock_nbt_correction={'original_relative':SOURCE,'original_manifest_sha256':SOURCE_SHA,
        'reason':'Native admission requires block_entities[].nbt SNBT string, not JSON object; prior place rejected before world operation',
        'exact_corrected_new_empty_barrels':[list(q)for q in sorted(STOCK)],'geometry_or_names_or_items_changed':False,
        'actual_native_snbt_parse':'PENDING actual parent admission; existing serializer + bounded SNBT readback passed'},storage_guard=reserve)
    return write_bundle(output,docs,result)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('home','output'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();print(json.dumps(prepare(a.home,a.output),indent=2))
