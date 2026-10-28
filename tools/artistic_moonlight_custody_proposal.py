"""Produce an isolated exact Moonlight adapter integration; no active edits."""
from pathlib import Path
import difflib
import json

from control_room.common import UserError,digest,utcnow
from tools.playtest import guard

BASE='092b095e841972280caa48b866e26fa0ae28bf77507517efe14cce6f8d5dc8df'
HELPER='''    /** Strict folder bytes plus the exact original cached provider's public API.
     * Manually declared empty namespaces are legal; undisclosed raw namespaces,
     * a partial/stale native trie or a missing selected resource are not. */
    private static void moonlightInventory(PackResources pack,MoonlightCachePackCustody.View view,
            Accumulator out,TreeSet<ResourceLocation> ids,TreeSet<String> rawNames)throws IOException {
        out.text("moonlight-cached-folder:1");out.text(view.delegate.getClass().getName());
        out.text(PackType.SERVER_DATA.name());
        out.number(view.rootBytes.size());
        for(String name:new TreeSet<>(view.rootBytes.keySet())){
            var source=pack.getRootResource(name.split("/",-1));
            if(source==null)throw new IOException("Original Moonlight root resource disappeared");
            out.resource("moonlight-root/"+name,source);
        }
        Path data=view.root.resolve("data");
        var actualNamespaces=pathNamespaces(data,out);
        if(!view.namespaces.containsAll(actualNamespaces))throw new IOException("Moonlight raw data has undisclosed namespaces");
        for(String namespace:new TreeSet<>(view.namespaces))
            ids.addAll(pathIds(namespace,data.resolve(namespace),out,rawNames));
        var found=new TreeSet<ResourceLocation>();int[] visits={0};
        PackResources.ResourceOutput collect=(id,supplier)->{
            if(++visits[0]>MAX_ENTRIES||System.nanoTime()-out.deadline>=0||supplier==null||!found.add(id))
                throw new IllegalStateException("Moonlight native resource enumeration is duplicate/partial/unbounded");
        };
        if(view.delegate.getClass()==PathPackResources.class){
            var cachedNamespaces=new TreeSet<>(view.delegate.getNamespaces(PackType.SERVER_DATA));
            if(!cachedNamespaces.equals(actualNamespaces))throw new IOException("Moonlight native path namespaces changed");
            // Normal PathPackResources uses nonempty prefixes. Root-level files
            // are still independently walked/hashed and read by getResource.
            var dirs=new TreeMap<String,TreeSet<String>>();var nested=new TreeSet<ResourceLocation>();
            for(var id:ids){int split=id.getPath().indexOf('/');if(split>=0){
                String prefix=id.getPath().substring(0,split);
                if(prefix.isEmpty()||prefix.equals(".")||prefix.equals(".."))throw new IOException("Moonlight native path prefix requires separate custody");
                dirs.computeIfAbsent(id.getNamespace(),ignored->new TreeSet<>()).add(prefix);nested.add(id);
            }}
            for(var entry:dirs.entrySet())for(String prefix:entry.getValue())
                pack.listResources(PackType.SERVER_DATA,entry.getKey(),prefix,collect);
            if(!found.equals(nested))throw new IOException("Moonlight original path resource inventory is incomplete");
        }else{
            // The pinned wrapper owns its namespace set. Its FastSearch
            // delegate reports an empty namespace set even for populated
            // indices; that method is not the wrapper's namespace authority.
            // Exact original list/get coverage below must still equal EVERY
            // independently walked native ID, so a stale trie still refuses.
            for(String namespace:new TreeSet<>(view.namespaces))
                pack.listResources(PackType.SERVER_DATA,namespace,"",collect);
            if(!found.equals(ids))throw new IOException("Moonlight original cached trie is stale or incomplete");
        }
        view.unchanged();
    }
'''


def replace_once(text,old,new):
    if text.count(old)!=1:raise UserError('Exact frozen native48 resource boundary changed')
    return text.replace(old,new)


def transform(old):
    text=old
    text=replace_once(text,'var runtimeIds=YungLocatePackCustody.matches(pack)?YungLocatePackCustody.inventory(pack):null;',
        'var runtimeIds=YungLocatePackCustody.matches(pack)?YungLocatePackCustody.inventory(pack):null;\n            var moonlight=MoonlightCachePackCustody.matches(pack)?MoonlightCachePackCustody.inspect(pack):null;\n            if(moonlight!=null)out.cachedViews.add(moonlight);')
    text=replace_once(text,'&&type!=FilePackResources.class&&type!=EmptyPackResources.class&&runtimeIds==null)',
        '&&type!=FilePackResources.class&&type!=EmptyPackResources.class&&runtimeIds==null&&moonlight==null)')
    text=replace_once(text,'            }else if(runtimeIds!=null) {',
        '            }else if(moonlight!=null) {\n                moonlightInventory(pack,moonlight,out,ids,rawNames);\n            }else if(runtimeIds!=null) {')
    text=replace_once(text,'            return new Inventory(ids,Map.copyOf(readable));',
        '            if(moonlight!=null)moonlight.unchanged();\n            return new Inventory(ids,Map.copyOf(readable));')
    text=replace_once(text,'        return new Attestation(identities,HexFormat.of().formatHex(out.digest.digest()),out.entries,out.bytes);',
        '        for(var view:out.cachedViews)view.unchanged();\n        return new Attestation(identities,HexFormat.of().formatHex(out.digest.digest()),out.entries,out.bytes);')
    text=replace_once(text,'    private static BasicFileAttributes attributes(Path path)throws IOException {',
        HELPER+'    private static BasicFileAttributes attributes(Path path)throws IOException {')
    text=replace_once(text,'    private static final class Accumulator {',
        '    private static final class Accumulator {\n        final ArrayList<MoonlightCachePackCustody.View> cachedViews=new ArrayList<>();')
    return text


def prepare():
    root=Path(__file__).resolve().parents[1]
    source=root/'compat/control-bridge/src/worldfortwo/bridge/LithostitchedSeedgenResources.java'
    if digest(source)!=BASE:raise UserError('Active48 resource source differs; no implicit rebase')
    output=root/'compat/proposals/resource-custody-moonlight49'
    if (output/'LithostitchedSeedgenResources.java').exists():raise UserError('Preserve the original proposal bytes')
    reserve=guard(2*1024**2,0);old=source.read_text();text=transform(old)
    (output/'LithostitchedSeedgenResources.java').write_text(text,encoding='utf-8',newline='\n')
    patch=''.join(difflib.unified_diff(old.splitlines(True),text.splitlines(True),fromfile='native48/LithostitchedSeedgenResources.java',tofile='proposal/LithostitchedSeedgenResources.java'))
    (output/'integration.diff').write_text(patch,encoding='utf-8',newline='\n')
    (output/'integration-custody.json').write_text(json.dumps({'created':utcnow(),'base_sha256':BASE,
        'generator_sha256':digest(Path(__file__)),'native_actions':0,'active_files_edited':0,
        'reserve_guard':reserve,'proposed_source_sha256':digest(output/'LithostitchedSeedgenResources.java')},indent=2)+'\n')
    return {'output':str(output),'proposed_source_sha256':digest(output/'LithostitchedSeedgenResources.java')}


if __name__=='__main__':print(json.dumps(prepare(),indent=2))
