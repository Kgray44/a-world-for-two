"""Only the owner's exact retained Create chain-conveyor32->128 config delta.

Read-only adapter for a future fresh mill request. It grants no world, client,
restart, inventory or historical-mechanism replay authority.
"""
from copy import deepcopy
import hashlib
from pathlib import Path
import tomllib

BEFORE_SHA = '36216a05f3ed63106ba587c8c24ed6315385829e7f3dae695dcf545aba41a270'
AFTER_SHA = '240471ba821bd0f5208ea11960d79aacdfeb25a40c6a689a2d6518d689d890ac'
RECEIPT_SHA = '2d1d800d95cbb249587fe8d00d8794a425da4e4f2952ccc74196cfe7936ecc20'
OWNER_FOLDER = 'staging/owner-chain-conveyor128-1793230774200615600'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def validate_pair(before, after):
    if not 0 < len(before) <= 65536 or not 0 < len(after) <= 65536:
        raise ValueError('Bounded complete owner config bytes required')
    if sha(before) != BEFORE_SHA or sha(after) != AFTER_SHA:
        raise ValueError('Only the exact approved Create before/after hashes are accepted')
    old = tomllib.loads(before.decode('utf-8'))
    new = tomllib.loads(after.decode('utf-8'))
    expected = deepcopy(old)
    value = old['kinetics']['maxChainConveyorLength']
    if type(value) is not int or value != 32:
        raise ValueError('Exact original chain-conveyor integer32 required')
    expected['kinetics']['maxChainConveyorLength'] = 128
    if type(new['kinetics']['maxChainConveyorLength']) is not int or new != expected:
        raise ValueError('Every other TOML value must remain unchanged')
    token = b'maxChainConveyorLength = 32'
    if before.count(token) != 1 or before.replace(token, b'maxChainConveyorLength = 128') != after:
        raise ValueError('Only the single approved literal value replacement is accepted')


def binding(home, original_sha, current_sha):
    """Bind CURRENT bytes plus retained owner evidence; never rewrite a config."""
    if original_sha != BEFORE_SHA or current_sha != AFTER_SHA:
        raise ValueError('Not the exact approved Create chain-conveyor delta')
    home = Path(home).resolve()
    def read(relative, cap):
        path = home / relative
        if path.resolve() != path or path.is_symlink() or not path.is_file() or not 0 < path.stat().st_size <= cap:
            raise ValueError('Canonical bounded owner config/evidence file required')
        with path.open('rb') as stream:
            raw = stream.read(cap + 1)
        if len(raw) > cap:
            raise ValueError('Owner evidence exceeded its read allocation')
        return raw
    before_path = OWNER_FOLDER + '/create-server-before.toml'
    receipt_path = OWNER_FOLDER + '/receipt.json'
    before = read(before_path, 65536)
    after = read('server/config/create-server.toml', 65536)
    receipt = read(receipt_path, 4096)
    validate_pair(before, after)
    if sha(receipt) != RECEIPT_SHA:
        raise ValueError('Exact retained owner approval receipt required')
    return {
        'before': {'path': before_path, 'bytes': len(before), 'sha256': BEFORE_SHA},
        'receipt': {'path': receipt_path, 'bytes': len(receipt), 'sha256': RECEIPT_SHA},
    }


def adapt_producer(source):
    old = "    configs=[]\n"
    new = "    from tools.transport_owner_create_delta import binding as owner_create_binding\n    configs=[];owner_create_delta=None\n"
    check = "        if not any(row.get('file')==name and row.get('sha256')==value['sha256'] for row in systems['sources']):raise ValueError('Pinned actual native policy changed')"
    replacement = """        if not any(row.get('file')==name and row.get('sha256')==value['sha256'] for row in systems['sources']):
            approved=[row['sha256'] for row in systems['sources'] if row.get('file')==name]
            if name!='create-server.toml' or len(approved)!=1:raise ValueError('Pinned actual native policy changed')
            owner_create_delta=owner_create_binding(home,approved[0],value['sha256'])"""
    end = "    if inspection_ref:request.update(native_inventory_inspection=inspection_ref,native_inventory_inspection_complete=inspection_marker_ref)"
    for anchor in (old, check, end):
        if source.count(anchor) != 1:
            raise ValueError('Producer context changed; do not broadly replace admission logic')
    return source.replace(old, new).replace(check, replacement).replace(end,
        "    if owner_create_delta is not None:request['owner_create_chain_limit_delta']=owner_create_delta\n" + end)


JAVA_METHOD = '''    private boolean approveOwnerChain128(String file,String original,JsonObject binding)throws Exception{
        if(!file.equals("create-server.toml")||!original.equals("BEFORE_HASH")||!binding.get("sha256").getAsString().equals("AFTER_HASH"))return false;
        if(!request.has("owner_create_chain_limit_delta"))return false;
        JsonObject delta=request.getAsJsonObject("owner_create_chain_limit_delta");
        if(!delta.keySet().equals(Set.of("before","receipt")))throw new IllegalStateException("Closed exact owner config delta required");
        JsonObject before=delta.getAsJsonObject("before"),receiptRef=delta.getAsJsonObject("receipt");
        if(!before.get("path").getAsString().equals("OWNER_PATH/create-server-before.toml")||!before.get("sha256").getAsString().equals("BEFORE_HASH")
            ||!receiptRef.get("path").getAsString().equals("OWNER_PATH/receipt.json")||!receiptRef.get("sha256").getAsString().equals("RECEIPT_HASH"))throw new IllegalStateException("Exact retained owner provenance required");
        byte[] originalBytes=readBounded(owned(before.get("path").getAsString()),65536);
        if(originalBytes.length!=before.get("bytes").getAsInt()||!sha(originalBytes).equals("BEFORE_HASH"))throw new IllegalStateException("Retained complete original Create config differs");
        JsonObject approval=readRef(receiptRef,4096);
        if(!approval.get("format").getAsString().equals("awft-owner-create-chain-limit:1")||!approval.get("only_changed_setting").getAsString().equals("kinetics.maxChainConveyorLength")
            ||approval.get("old_value").getAsInt()!=32||approval.get("new_value").getAsInt()!=128
            ||!approval.get("before_sha256").getAsString().equals("BEFORE_HASH")||!approval.get("after_sha256").getAsString().equals("AFTER_HASH"))throw new IllegalStateException("Exact approved32-to128 delta required");
        report.put("owner_create_chain_limit_delta",Map.of("before_sha256","BEFORE_HASH","after_sha256","AFTER_HASH","all_other_config_bytes_preserved",true,"runtime_effective_value_observed",false));
        return true;
    }
'''.replace('BEFORE_HASH', BEFORE_SHA).replace('AFTER_HASH', AFTER_SHA).replace('RECEIPT_HASH', RECEIPT_SHA).replace('OWNER_PATH', OWNER_FOLDER)


def adapt_native(source):
    old = 'if(approved==null||!approved.equals(binding.get("sha256").getAsString()))throw new IllegalStateException("Native configuration differs from the authored contract");'
    new = 'if(approved==null||(!approved.equals(binding.get("sha256").getAsString())&&!approveOwnerChain128(file,approved,binding)))throw new IllegalStateException("Native configuration differs from the authored contract");'
    end = '        if(!requiredConfigs.isEmpty())throw new IllegalStateException("Missing native configuration custody");'
    anchor = '    private void requireHydraulics()'
    for text in (old, end, anchor):
        if source.count(text) != 1:
            raise ValueError('Native context changed; do not weaken other admission guards')
    return source.replace(old, new).replace(end, end + '\n        if(request.has("owner_create_chain_limit_delta")&&!report.containsKey("owner_create_chain_limit_delta"))throw new IllegalStateException("Unused owner delta refused");').replace(anchor, JAVA_METHOD + anchor)
