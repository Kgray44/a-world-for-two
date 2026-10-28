# Additive bee guard/recovery correction

The six sealed `native44-tree-bee` files and private `bb2fe53c…` receipt remain unchanged. This exact-source recipe emits a new four-file private source bundle, changing only the derived tree scope and controller. It neither edits active43 nor launches Java or Minecraft.

The scoped setter now catches any bee policy refusal and passes it through the existing `denied(scope, reason)` function before rethrowing, retaining the original refusal as a suppressed cause. `scope.violation` is therefore latched even if an upstream feature catches the thrown exception. Existing subsequent-write and end-of-grow checks still refuse the attempt; no alternate-variant retry or suppression is introduced.

The read-only bee audit is definitely initialized before the growth scope is created, its write witness is invoked, or any owned growth setter runs. Initialization failure records its primary error and explicitly records that this growth has not invoked its owned setter. Any preexisting mutated/residual state remains quarantined. The original error stays the cause of the failure. There is no nullable audit passed into restoration, so a later null dereference cannot replace that primary initialization failure.

After mutation, the same audit still runs before removal and after exact restoration inside the recovery try. Unknown/released entities, changed old BEs and failed restoration retain quarantine. This revision changes no native bee/occupant policy, descriptor, growth envelope, class pin, old inventory, noAI/ownership flag, normal native API or cleanup lease.

Four light source-custody/assembly fixtures passed: only the two reviewed outputs differ, all six originals remain exact, changed pins/anchors refuse, and old receipts cannot be overwritten. These are **source assembly evidence**, not executed Java guard behavior. Compilation, swallowed-native-refusal regression, actual hive/partial-failure restoration, restart and native appearance remain pending a safe parent-owned resource window. No Java was launched for this revision during KG's preview.
