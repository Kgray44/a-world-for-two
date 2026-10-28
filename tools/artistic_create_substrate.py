"""One pinned native Create zinc-ore substrate qualification, not arbitrary mods.

The exact AllBlocks initializer registers zinc_ore with Block::new (bootstrap681,
REF_newInvokeSpecial). Plain native Block is not FallingBlock. No downloaded
classes are copied; retain their identities and this narrow factory witness.
"""
from __future__ import annotations
import zipfile,hashlib
from control_room.common import UserError,digest
from tools.artistic_ground_stability import natural_mount

JAR='create-1.21.1-6.0.10.jar'
JAR_SHA='ef87fe5709f1ba1f5b8bb20a2925b5afb4669e178fd6d8bf10c167759eefe37a'
CLASS_SHA='052f8be9dbdaf4464630c03cf7be78b8c683673515163963fb8f95077175daf0'


def verify_zinc_factory(home):
    path=home/'server/mods'/JAR
    if not path.is_file()or digest(path)!=JAR_SHA:raise UserError('Exact pinned Create6.0.10 zinc API required')
    with zipfile.ZipFile(path)as jar:
        info=jar.getinfo('com/simibubi/create/AllBlocks.class')
        if info.file_size!=224167:raise UserError('Exact native registration class size required')
        raw=jar.read(info)
    if hashlib.sha256(raw).hexdigest()!=CLASS_SHA:raise UserError('Exact reviewed zinc registration bytecode changed')
    return {'artifact':JAR,'artifact_sha256':JAR_SHA,'class':'com/simibubi/create/AllBlocks.class','class_sha256':CLASS_SHA,
            'zinc_string_constant_pool_index':3840,'clinit_ldc_offset':14158,'invokedynamic_offset':14161,'invokedynamic_constant_pool_index':3730,
            'bootstrap_index':681,'factory_handle_kind':8,'factory_class':'net/minecraft/world/level/block/Block','factory_method':'<init>',
            'factory_descriptor':'(Lnet/minecraft/world/level/block/state/BlockBehaviour$Properties;)V',
            'scope':'Only create:zinc_ore; exact pinned normal native Block factory, not a generic mod-material solidity assumption'}


def qualified_mount(lookup,x,z,proof):
    result=natural_mount(lookup,x,z)
    if result['stable']:return result
    last=result.get('first_non_gravity');state=last[3]if last else None
    if state!='create:zinc_ore':return result
    if proof.get('artifact_sha256')!=JAR_SHA or proof.get('class_sha256')!=CLASS_SHA or proof.get('factory_class')!='net/minecraft/world/level/block/Block'or proof.get('factory_handle_kind')!=8:
        raise UserError('Zinc cannot be qualified without the exact reviewed installed native factory receipt')
    return dict(result,stable=True,reason='Exact pinned Create zinc_ore registers native non-falling Block::new',native_factory=proof)
