"""Read-only exact-source preflight; never applies the proposed patch."""
from __future__ import annotations
import argparse,copy,hashlib,json,math,re,sys
from pathlib import Path


BASE=Path(__file__).resolve().parent
REPO=BASE.parents[1]


def sha(path,algorithm='sha256'):
    value=hashlib.new(algorithm)
    with path.open('rb')as stream:
        for block in iter(lambda:stream.read(1024**2),b''):value.update(block)
    return value.hexdigest()


def proposed_files(allowed):
    """Verify the actual reviewed unified diff against source, in memory only."""
    patch=(BASE/'integration.diff').read_text().splitlines(True);i=0;result={}
    while i<len(patch):
        if not patch[i].startswith('--- a/'):raise ValueError('Expected a reviewed existing-file patch')
        relative=patch[i][6:].strip();i+=1
        if relative not in allowed or patch[i]!='+++ b/'+relative+'\n':raise ValueError('Unexpected patch target')
        i+=1;source=(REPO/relative).read_text().splitlines(True);cursor=0;output=[]
        while i<len(patch)and not patch[i].startswith('--- a/'):
            match=re.fullmatch(r'@@ -(\d+)(?:,\d+)? \+\d+(?:,\d+)? @@.*\n',patch[i])
            if not match:raise ValueError('Expected bounded source patch hunk')
            start=int(match[1])-1
            if start<cursor:raise ValueError('Overlapping patch hunks')
            output+=source[cursor:start];cursor=start;i+=1
            while i<len(patch)and not patch[i].startswith(('@@ ','--- a/')):
                line=patch[i];i+=1
                if line[:1]in(' ','-'):
                    if cursor>=len(source)or source[cursor]!=line[1:]:raise ValueError('Patch context differs from current source')
                    cursor+=1
                if line[:1]in(' ','+'):output.append(line[1:])
                elif line[:1]!='-':raise ValueError('Unexpected patch operation')
        result[relative]=''.join(output+source[cursor:])
    if set(result)!=set(allowed):raise ValueError('Exactly the reviewed four overrides and one generator are required')
    return result


def verify(cache=None):
    proposal=json.loads((BASE/'proposal.json').read_text())
    if proposal['installed']or proposal['native_actions']or len(proposal['changes'])!=4:raise ValueError('Exactly four uninstalled source changes required')
    for relative,expected in proposal['canonical_structure_set_inputs'].items():
        if sha(REPO/relative)!=expected:raise ValueError('Canonical structure-set bytes changed: '+relative)
    generator=REPO/'tools/worldgen_policy.py'
    if sha(generator)!=proposal['generator_before_sha256']:raise ValueError('Worldgen generator changed; review the proposal before reuse')
    virtual=proposed_files({r['relative']for r in proposal['changes']}|{'tools/worldgen_policy.py'})
    lock=json.loads((REPO/'catalog/lock.json').read_text())
    mods={r['slug']:r for r in lock['mods']}
    for slug,expected in proposal['mods'].items():
        row=mods[slug]
        if any(row[k]!=expected[k]for k in('filename','version','size','hashes')):raise ValueError('Actual mod pin changed: '+slug)
        if cache is not None:
            path=Path(cache)/row['filename']
            if path.stat().st_size!=row['size']or any(sha(path,a)!=v for a,v in row['hashes'].items()):raise ValueError('Installed pinned JAR differs: '+slug)
    for change in proposal['changes']:
        before=json.loads((REPO/change['relative']).read_text())
        if before!=change['before']:raise ValueError('Current effective-source override differs')
        after=copy.deepcopy(before);after['placement']['spacing']=change['after_spacing_chunks']
        if after!=change['after']:raise ValueError('The proposal changed more than the exact selected spacing')
        if json.loads(virtual[change['relative']])!=after:raise ValueError('Actual patch JSON differs from the reviewed proposal')
        p0,p1=before['placement'],after['placement']
        if p0['type']!='minecraft:random_spread'or not 0<=p1['separation']<p1['spacing']or p1['spacing']>=p0['spacing']:raise ValueError('Finite moderate random-spread reduction required')
        if p0['separation']!=p1['separation']or p0.get('frequency',1)!=p1.get('frequency',1):raise ValueError('Separation and frequency must remain identical')
        increase=(p0['spacing']/p1['spacing'])**2-1
        if not 0<increase<=.12 or not math.isclose(increase,change['candidate_opportunity_increase_fraction'],rel_tol=1e-12):raise ValueError('A claimed candidate increase is wrong or exceeds this small proposal')
    namespace={'__name__':'uninstalled_structure_proposal','__file__':str(generator)}
    if str(REPO)not in sys.path:sys.path.insert(0,str(REPO))
    exec(compile(virtual['tools/worldgen_policy.py'],'<actual uninstalled reviewed patch>','exec'),namespace)
    cases=[('castle-shift','castle',92,32),('archaeology-ruins','adoberuins',76,40),('archaeology-ruins','mudpotterruin',76,40),
           ('archaeology-ruins','mudschoolruin',76,40),('archaeology-ruins','mudblacksmithruin',80,40),
           ('archaeology-ruins','ruined_desert_pyramid',96,48),('ancient-structures','german_buildings',160,64),('when-dungeons-arise','major_structures',128,64)]
    for slug,name,spacing,separation in cases:
        value=namespace['placement'](slug,name,{'type':'minecraft:random_spread','spacing':32,'separation':8,'salt':123,'frequency':.75,
          'exclusion_zone':{'other_set':'minecraft:villages','chunk_count':10}})
        if(value['spacing'],value['separation'])!=(spacing,separation)or value['salt']!=123 or value['frequency']!=.75:raise ValueError('Actual proposed generator changed an unrelated placement property')
    rings={'type':'minecraft:concentric_rings','salt':12,'distance':32,'spread':3,'count':128}
    if namespace['placement']('untouched','stronghold',rings)!=rings:raise ValueError('Unrelated ring placement changed')
    return {'selected_sets_checked':4,'actual_patch_files_checked':len(virtual),'actual_proposed_generator_cases_passed':len(cases)+1,
            'all_canonical_set_hashes_checked':len(proposal['canonical_structure_set_inputs']),'jar_pins_checked':cache is not None,
            'changes_applied':0,'worlds_opened':0,'native_actions':0,'runtime_or_performance_acceptance':False}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--cache',type=Path);args=parser.parse_args()
    print(json.dumps(verify(args.cache),indent=2))
