"""Exact temporary NON-BE support restoration for the current12 eastern cases.

No game calls. Native factory/hierarchy facts are read from the installed game
classes, without starting Java. All runtime proofs and mutations remain separate.
"""
from __future__ import annotations
import copy,hashlib,json,struct,time,zipfile
from pathlib import Path
from control_room.common import UserError,digest,read_json
from tools.artistic_east_tortuga_retrofit import checked
from tools.artistic_bridge_refinement import flatten
from tools.artistic_captains_hall import native_payload
from tools.artistic_eastern_urban_custody import canonical
from tools.native_relocation_request import reference
from tools.playtest import guard

MIB=1024**2
PIPE='staging/eastern98-ordinary-pipeline-1793225758764645900/pipeline-SOURCE-ONLY.json'
PIPE_SHA='d9c3d55dcb35617805956d7f0ca60c417dc18615d7b65ed8d3bafe8a43f01638'
CAT='staging/eastern-final-floor-catalog-1793225720648710600/approved98-capsules-PRIVATE.json'
CAT_SHA='879c7a3894df08e541c083b4a0a8bfb75bc7fd6b3017e8898befe4c7ceefaf14'

def class_parts(raw):
    if raw[:4]!=b'\xca\xfe\xba\xbe' or len(raw)>512*1024:raise UserError('Finite exact class required')
    u2=lambda p:int.from_bytes(raw[p:p+2],'big');u4=lambda p:int.from_bytes(raw[p:p+4],'big')
    cp=[None]*u2(8);p=10;i=1
    sizes={3:4,4:4,5:8,6:8,7:2,8:2,9:4,10:4,11:4,12:4,15:3,16:2,17:4,18:4,19:2,20:2}
    while i<len(cp):
        tag=raw[p];p+=1
        if tag==1:n=u2(p);p+=2;cp[i]=(tag,raw[p:p+n].decode('utf8'));p+=n
        elif tag in sizes:cp[i]=(tag,raw[p:p+sizes[tag]]);p+=sizes[tag]
        else:raise UserError('Unknown native constant type')
        i+=2 if tag in(5,6) else 1
    def name(i):return cp[int.from_bytes(cp[i][1],'big')][1]
    parent=name(u2(p+4));p+=6;p+=2+2*u2(p)
    def attrs(p):
        count=u2(p);p+=2;result={}
        for _ in range(count):n=cp[u2(p)][1];size=u4(p+2);p+=6;result[n]=raw[p:p+size];p+=size
        return result,p
    fields=u2(p);p+=2
    for _ in range(fields):p+=6;_,p=attrs(p)
    methods={};count=u2(p);p+=2
    for _ in range(count):
        n,d=cp[u2(p+2)][1],cp[u2(p+4)][1];p+=6;at,p=attrs(p)
        if 'Code'in at:c=at['Code'];methods[n,d]=c[8:8+int.from_bytes(c[4:8],'big')]
    return cp,parent,methods

def instructions(code):
    p=0
    while p<len(code):
        start=p;op=code[p];p+=1;n=0
        if op in(0xaa,0xab):
            p+=(4-p%4)%4
            if op==0xaa:lo,hi=struct.unpack('>ii',code[p+4:p+12]);n=12+4*(hi-lo+1)
            else:n=8+8*int.from_bytes(code[p+4:p+8],'big')
        elif op==0xc4:n=5 if code[p]==0x84 else 3
        elif op in(0xb9,0xba,0xc8,0xc9):n=4
        elif op==0xc5:n=3
        elif op in(0x11,0x13,0x14,0x84,0xbb,0xbd,0xc0,0xc1,0xc6,0xc7)or 0x99<=op<=0xa8 or 0xb2<=op<=0xb8:n=2
        elif op in(0x10,0x12,0xa9,0xbc)or 0x15<=op<=0x19 or 0x36<=op<=0x3a:n=1
        if p+n>len(code):raise UserError('Truncated native code')
        yield start,op,code[p:p+n];p+=n

def vanilla_fact(home,ids):
    games=list((home/'server/libraries/net/minecraft/server').rglob('*-srg.jar'))
    if len(games)!=1:raise UserError('One installed native base game required')
    version=read_json(home/'server/installed.json')['neoforge']
    if version!='21.1.262':raise UserError('Exact current installed native patched game required')
    patched=home/f'server/libraries/net/neoforged/neoforge/{version}/neoforge-{version}-server.jar'
    if not patched.is_file()or patched.is_symlink():raise UserError('Exact installed native patched game missing')
    archives=[zipfile.ZipFile(patched),zipfile.ZipFile(games[0])];cache={}
    def raw(name):
        path=name+'.class'
        for archive in archives:
            if path in archive.namelist():
                info=archive.getinfo(path)
                if not 0<info.file_size<=512*1024:raise UserError('Finite native class exceeded')
                return archive.read(path)
        raise UserError('Required actual native class missing')
    try:
        owner='net/minecraft/world/level/block/Blocks';braw=raw(owner);cp,parent,methods=class_parts(braw)
        def text(i):
            tag,v=cp[i]
            return v if tag==1 else cp[int.from_bytes(v,'big')][1]
        def ref(i):
            _,v=cp[i];cl,nt=struct.unpack('>HH',v);n,d=struct.unpack('>HH',cp[nt][1]);return text(cl),text(n),text(d)
        code=methods['<clinit>','()V'];ops=list(instructions(code));facts={}
        for ident in sorted(ids):
            if not ident.startswith('minecraft:'):raise UserError('No generic mod solidity assumption: '+ident)
            word=ident.split(':',1)[1];matches=[]
            for i,(offset,op,arg) in enumerate(ops):
                if op in(0x12,0x13)and cp[int.from_bytes(arg,'big')][0]==8 and text(int.from_bytes(arg,'big'))==word:matches.append(i)
            if len(matches)!=1:raise UserError('Exact unique native block registration not resolved: '+ident)
            segment=[]
            for x in ops[matches[0]+1:matches[0]+65]:
                segment.append(x)
                if x[1]==0xb3:break
            else:raise UserError('Bounded actual registration target absent')
            classes=[];factory=[]
            for offset,op,arg in segment:
                if op==0xbb:classes.append(text(int.from_bytes(arg,'big')))
                if op==0xb8:
                    target,n,d=ref(int.from_bytes(arg,'big'))
                    if target==owner and n not in('register',):
                        m=methods.get((n,d))
                        if m is not None:
                            found=[text(int.from_bytes(a,'big'))for _,o,a in instructions(m)if o==0xbb]
                            if found:classes.extend(found);factory.append({'method':n,'descriptor':d,'code_sha256':hashlib.sha256(m).hexdigest()})
            classes=list(dict.fromkeys(classes))
            if len(classes)!=1:raise UserError('Unique native constructor class not proved: '+ident+' '+str(classes))
            klass=classes[0];lineage=[];current=klass
            for _ in range(12):
                r=raw(current);_,p,declared=class_parts(r);lineage.append({'class':current,'sha256':hashlib.sha256(r).hexdigest()})
                if current=='net/minecraft/world/level/block/FallingBlock':raise UserError('Falling native bottom must not lose its temporary support')
                if any(name=='canSurvive'for name,desc in declared):raise UserError('Native bottom overrides survival; preserve its support instead')
                if current=='net/minecraft/world/level/block/Block':break
                current=p
            else:raise UserError('Finite native non-falling hierarchy not proved')
            behavior=raw('net/minecraft/world/level/block/state/BlockBehaviour');_,_,behavior_methods=class_parts(behavior)
            survival=[code for(name,desc),code in behavior_methods.items()if name=='canSurvive']
            if survival!=[b'\x04\xac']:raise UserError('Exact native unconditional inherited survival body not proved')
            facts[ident]={'native_registry_owner_sha256':hashlib.sha256(braw).hexdigest(),'registration_ldc_offset':ops[matches[0]][0],
                'native_constructor_class':klass,'native_factory':factory,'native_class_hierarchy':lineage,'not_a_native_FallingBlock':True,
                'inherited_survival_unconditional_true':True,'native_BlockBehaviour_sha256':hashlib.sha256(behavior).hexdigest(),
                'actual_post_restore_native_survival_and_stability_still_required':True,'full_cube_not_assumed':True}
        return facts
    finally:
        for a in archives:a.close()

def prepare(home):
    home=Path(home).resolve();reserve=guard(2*MIB,16*MIB);pipeline=checked(home/PIPE,PIPE_SHA,16*MIB);cat=checked(home/CAT,CAT_SHA,2*MIB);rows={r['id']:r for r in cat['capsules']}
    registry=read_json(home/'dashboard/settlement/registry.json');receipt=read_json(home/'dashboard/settlement/backup-receipt.json');out=home/'staging'/('eastern-support-restoration-'+str(time.time_ns()));out.mkdir();records=[];bottoms=set()
    for row in pipeline['room_assessments']:
        if not row['additional_floor_source_holds']:continue
        r=rows[row['capsule_id']];d=r['translation_xyz'];source=flatten(checked(home/r['source_original']['path'],r['source_original']['sha256'],MIB))
        before=flatten(checked(home/row['files']['supports-current-before']['path'],row['files']['supports-current-before']['sha256'],MIB));support=flatten(checked(home/row['files']['support-plane-DELTA']['path'],row['files']['support-plane-DELTA']['sha256'],MIB))
        restore={};cells=[]
        for hold in row['additional_floor_source_holds']:
            q=tuple(hold['position']);sp=(q[0]-d[0],q[1]+1-d[1],q[2]-d[2]);state=source[sp];ident=state.split('[',1)[0];bottoms.add(ident)
            if hold['reason'].startswith('Destination support patch changes OWN'):raise UserError('Own source conflict cannot be temporarily overwritten')
            if q not in support or 'waterlogged=true'in before[q]or before[q].startswith(('minecraft:water','minecraft:lava')):raise UserError('Only owned dry NONBE support patch targets')
            restore[q]=before[q];cells.append({'position':list(q),'original_state':before[q],'temporary_state':support[q],'actual_copied_bottom_position':[q[0],q[1]+1,q[2]],'copied_bottom_state':state,'source_captures_requiring_restoration':hold['requires_native_source_captures']})
        index=len(records);files={}
        for name,field in [('temporary-support-before',restore),('temporary-support-DELTA',{q:support[q]for q in restore}),('temporary-support-after-MOVE', {q:support[q]for q in restore}),('RESTORE-original-NONBE-DELTA',restore),('restored-support-VERIFY',restore)]:
            path=out/(f'{index:02d}-'+name+'.json');path.write_bytes(native_payload(registry,field,receipt['sha256'],'FORBIDDEN forecast ordinary '+name+'; fresh exact native BEFORE and custody gates required'));files[name]=reference(home,path)
        records.append({'capsule_id':row['capsule_id'],'cells':cells,'files':files,'floor_holds_resolved_only_after_actual_restore':True,
            'sequence':['Fresh exact complete native source/target/preparation proof','Place verified ordinary temporary supports, no inventory target',
            'Fresh source/empty destination/support native proofs, actual INSPECT, exactly ONE MOVE','Require genuine clean MOVE terminal plus full real native tags/slots/components conservation',
            'Fresh temporary support before proof; restore literal original nonBE states ONLY','Normal native neighbor settle of restored support and entire copied room; at least20 fresh native ticks',
            'Reverify restored source contexts and moved room states; inspect-moved proves all real tags/slots again','Only then capture any affected still-unmoved source room; preserve every failure; never retry a clone'],
            'automatic_execution':False,'native_actions':0})
    facts=vanilla_fact(home,bottoms)
    for r in records:
        for cell in r['cells']:cell['native_bottom_factory']=facts[cell['copied_bottom_state'].split('[',1)[0]]
    data={'format':'awft-eastern-ordinary-support-restoration:1','pipeline_sha256':PIPE_SHA,'catalog_sha256':CAT_SHA,'checkpoint_sha256':receipt['sha256'],
        'records':records,'source_sha256':digest(Path(__file__)),'restoration_targets':sum(len(r['cells'])for r in records),'native_bottom_facts':facts,
        'construction_forbidden':True,'native_actions':0,'reserve_guard':reserve}
    p=out/'protocol-SOURCE-ONLY.json';p.write_bytes(canonical(data)+b'\n');return {'folder':str(out),'protocol_sha256':digest(p),'rooms':len(records),'cells':data['restoration_targets'],'native_actions':0}

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--home',type=Path,required=True);a=p.parse_args();print(json.dumps(prepare(a.home),indent=2))
