"""Inspect exact installed class files. Never load a class, start Minecraft or extract a mod."""
from pathlib import Path
import hashlib
import zipfile

from classfile import ClassFile


ARTIFACTS = {
    'moonlight': ('moonlight-1.21.1-3.7.2-neoforge.jar', 2299162,
                  '4a9f15108607cc70273f8a0b6eb24e1e99af8eef44bc3ae8681767ca7ce21b0f'),
    'supplementaries': ('supplementaries-1.21.1-4.0.2-neoforge.jar', 13840377,
                       '2c2e0c98e0cc21874d8b2130bc773a2a5a6cadd854b9c8163d0e1f32e2ddffb0'),
    'seedrenderer': ('Distant Horizons SeedGen 0.9.1 for 1.21.1 NeoForge.jar', 1355029,
                     '58469f92f7cf13ff3c2928659ce1a57d7d05314b30e0779cb187b6fbfdb43b4e'),
}
MOON = 'net/mehvahdjukaar/moonlight/'
PACK = MOON + 'api/resources/pack/'
SUPP = 'net/mehvahdjukaar/supplementaries/dynamicpack/ModServerDynamicResources'
CLIENT = 'mobius/seedrenderer/dh/ClientWorldgen'
ERROR_OBJECTS = 'org/apache/logging/log4j/Logger.error(Ljava/lang/String;Ljava/lang/Object;Ljava/lang/Object;)V'
ERROR_THROWABLE = 'org/apache/logging/log4j/Logger.error(Ljava/lang/String;Ljava/lang/Throwable;)V'


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def inspect(mods):
    mods = Path(mods)
    classes, proof = {}, {'format': 'awft-moonlight-native-api:1',
                          'native_execution': False, 'strict_parity_proved': False,
                          'artifacts': {}, 'classes': {}}
    wanted = {
        'moonlight': [PACK+n for n in ('CachePathPackResources', 'AbstractCachedEditableResources',
                     'DynamicResourcesProvider', 'GlobalCachedStrategy', 'ResourceSink')]
                     + [MOON+'core/pack/DynamicResourcesInternals', MOON+'api/util/FastCachedWriter',
                        MOON+'api/events/EarlyPackReloadEvent', MOON+'api/misc/IProgressTracker'],
        'supplementaries': [SUPP], 'seedrenderer': [CLIENT],
    }
    for mod, (name, size, sha) in ARTIFACTS.items():
        path = mods/name
        if path.is_symlink() or not path.is_file() or path.stat().st_size != size or digest(path) != sha:
            raise ValueError('Exact installed native artifact required: '+mod)
        before = path.stat()
        with zipfile.ZipFile(path) as jar:
            for member in wanted[mod]:
                info = jar.getinfo(member+'.class')
                if not 0 < info.file_size <= 128*1024:
                    raise ValueError('Bounded original class required')
                raw = jar.read(info)
                classes[member] = ClassFile(raw)
                proof['classes'][member] = {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
        after = path.stat()
        if (before.st_size, before.st_mtime_ns, before.st_ino) != (after.st_size, after.st_mtime_ns, after.st_ino):
            raise ValueError('Native artifact changed during read')
        proof['artifacts'][mod] = {'filename': name, 'bytes': size, 'sha256': sha}

    def method(owner, name, descriptor=None):
        found = [m for m in classes[owner].methods if m[1] == name and (descriptor is None or m[2] == descriptor)]
        if len(found) != 1:
            raise ValueError('One exact native method required: '+owner+'.'+name)
        return found[0]

    def calls(owner, name, target, descriptor=None):
        row = method(owner, name, descriptor)
        return [pc for pc, op, ref in classes[owner].instructions(row[3]['Code']) if ref == target]

    def count(owner, name, target, expected, descriptor=None):
        result = calls(owner, name, target, descriptor)
        if len(result) != expected:
            raise ValueError('Native injection point count differs: '+owner+'.'+name)
        return result

    descriptor = '(ZZ)Lnet/minecraft/core/RegistryAccess$Frozen;'
    method(CLIENT, 'attempt', descriptor)
    opened = count(CLIENT, 'attempt', 'net/minecraft/server/packs/resources/MultiPackResourceManager.<init>(Lnet/minecraft/server/packs/PackType;Ljava/util/List;)V', 1)
    loaded = count(CLIENT, 'attempt', 'net/minecraft/resources/RegistryDataLoader.load(Lnet/minecraft/server/packs/resources/ResourceManager;Lnet/minecraft/core/RegistryAccess;Ljava/util/List;)Lnet/minecraft/core/RegistryAccess$Frozen;', 2)
    if not opened[0] < min(loaded):
        raise ValueError('Resource initialization must precede registry loading')
    internal = MOON+'core/pack/DynamicResourcesInternals'
    event = 'lambda$init$2'
    refresh = count(internal, event, PACK+'GlobalCachedStrategy.refreshState(Lnet/minecraft/server/packs/PackType;Ljava/util/Collection;)V', 1)
    prepare = count(internal, event, PACK+'DynamicResourcesProvider.prepare()V', 1)
    reload = count(internal, event, PACK+'DynamicResourcesProvider.reload(Lnet/minecraft/server/packs/resources/ResourceManager;Lnet/mehvahdjukaar/moonlight/api/misc/IProgressTracker;)V', 2)
    commit = count(internal, event, PACK+'GlobalCachedStrategy.writeNewState(Lnet/minecraft/server/packs/PackType;)V', 1)
    if not refresh[0] < prepare[0] < min(reload) <= max(reload) < commit[0]:
        raise ValueError('Reviewed native lifecycle order differs')
    provider = PACK+'DynamicResourcesProvider'
    count(provider, 'reload', ERROR_OBJECTS, 1)
    count(provider, 'runGenerationPipeline', ERROR_THROWABLE, 2)
    count(provider, 'lambda$runGenerationPipeline$2', ERROR_THROWABLE, 1)
    for name in ('lambda$addSignPostRecipes$2', 'lambda$addCannonBoatRecipes$1'):
        count(SUPP, name, ERROR_OBJECTS, 1)
    sink = PACK+'ResourceSink'
    count(sink, 'addJson', ERROR_OBJECTS, 1, '(Lnet/minecraft/resources/ResourceLocation;Lcom/google/gson/JsonElement;)V')
    for name in ('addJsonUnlessPresent', 'addTextureUnlessPresent'):
        count(sink, name, ERROR_OBJECTS, 1)
    count(sink, 'addTextureIfNotPresent', ERROR_OBJECTS, 1, '(Lnet/minecraft/server/packs/resources/ResourceManager;Lnet/minecraft/resources/ResourceLocation;Ljava/util/function/Supplier;)V')
    count(sink, 'addAndCloseTexture', 'org/apache/logging/log4j/Logger.warn(Ljava/lang/String;Ljava/lang/Object;Ljava/lang/Object;Ljava/lang/Object;)V', 1,
          '(Lnet/minecraft/resources/ResourceLocation;Lnet/mehvahdjukaar/moonlight/api/resources/textures/TextureImage;Z)V')
    method(sink, 'addBytes', '(Lnet/minecraft/resources/ResourceLocation;[B)V')
    count(PACK+'CachePathPackResources', 'addResource', MOON+'api/util/FastCachedWriter.writeFast(Ljava/nio/file/Path;[B)V', 1)
    count(MOON+'api/util/FastCachedWriter', 'writeFast', 'java/nio/file/Files.write(Ljava/nio/file/Path;[B[Ljava/nio/file/OpenOption;)Ljava/nio/file/Path;', 1)
    proof['verified'] = {'seedgen_attempt_descriptor': descriptor, 'manager_constructor_offset': opened[0],
                         'registry_load_offsets': loaded, 'native_refresh_prepare_reload_commit_offsets': [*refresh, *prepare, *reload, *commit],
                         'provider_error_sites': 4, 'sink_error_sites': 4, 'sink_texture_warning_sites': 1,
                         'supplementaries_error_sites': 2, 'native_cache_writer': 'synchronous Files.write'}
    return proof


if __name__ == '__main__':
    import argparse, json
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mods', required=True, type=Path)
    print(json.dumps(inspect(parser.parse_args().mods), indent=2))
