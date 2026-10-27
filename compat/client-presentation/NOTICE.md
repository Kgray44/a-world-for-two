# Presentation component notice

`LICENSE-awft.txt` applies to the project-authored Java source in `src/` and
component metadata in `resources/`. The previous immutable distribution is
`awft-client-presentation-0.2.1.jar` (SHA-256
`2614892ec05d63d8e2c51a4bf0b0424470cc1195815b6c0695130642ba51c42c`).
The component already declares MIT in its mod metadata. The full license text
accompanies that existing artifact; its immutable JAR bytes remain unchanged.

Version `0.2.2` adds a client-only Small Ships config callback correction. Its
private compilation and 16 actual-class config regression cases passed. The
10,034-byte private JAR has SHA-256
`754555b0fc47e923ff6aaeccb8d162b72d4a0056b4a04e85c06c3d5d4f06c765`.
It has not been deployed or published. Mixin transformation and native reconnect
validation remain pending.
See [the correction and deferred checks](SMALL-SHIPS-CONFIG.md).

Publish this notice and `LICENSE-awft.txt` beside the JAR, together with the
matching source revision and `tools/build_presentation.py`. This component
contains no embedded dependency JARs. Minecraft, NeoForge, mixin APIs, other
mods, menu artwork, fonts, and other third-party material retain their own
licenses and are outside this notice's grant.
