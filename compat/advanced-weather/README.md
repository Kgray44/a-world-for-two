# Advanced Weather 0.1.2 compatibility candidate

This is an explicit, reproducible candidate repair of the MIT-licensed author artifact,
not an upstream release. The original downloaded JAR is never modified.

Observed dedicated-server failures, preserved under `evidence/runtime/`:

1. `BlockFrictionMixin` is registered as common but uses `LocalPlayer` and
   `ClientWeatherState` exclusively. Move this unchanged class's declaration to
   the client mixin list. Injection requirements remain intact.
2. Common initialization uses the YACL serializer. Declare YACL on both sides.
3. Mercury intentionally has `.noBucket()`, but Registrate's default fluid-properties
   supplier still looks up `mercury_bucket` during fluid-tag initialization. Explicitly
   supply `Items.AIR`, preserving the intended absence of a placeable mercury bucket.

Only the third correction needs compilation. `tools.weather_patch` compiles that
one source against the exact installed NeoForge, Minecraft and embedded Registrate
libraries using Java 21. The build checks all unchanged archive entries for byte identity.
It records the upstream SHA-256, changed entries and source provenance in the output.

Upstream source inspected: `Antop90fr1/AdvancedWeather1.21.1`,
`50fe9990e03ac24638343703792797f8991b5266`. Original source is MIT; embedded
libraries retain their respective licenses. Distribution remains gated on successful
server/client testing and preservation of the full third-party notices.

No original world, source repository, downloaded author JAR, or mod safety assertion
is overwritten. This candidate is not yet a production compatibility claim.
