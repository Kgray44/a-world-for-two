# OpenAI setup in Character Studio

Use the existing **Characters → AI Provider Settings** panel. Minecraft needs the
matching Living World **0.2.0** adapter, Smart Villagers AI and Chatting Villagers on
the coordinated server/client candidate. The master serializes installation and
the gameplay window with Pirate City construction.

## Configure the account securely

1. Choose OpenAI and the preferred **GPT-6 Luna** preset. New configurations keep
   external AI disabled until a connection test succeeds. A preset documents a model;
   it does not prove access through the owner's account.
2. Enter the owner's API key once in the panel's masked credential field. Submit it
   directly to the loopback Control Room; never paste it into Codex or a profile.
   The response reports configuration status and never returns the credential.
3. The credential is encrypted with Windows user-bound DPAPI outside the runtime,
   registry, Packwiz, Prism exports and world backups. The same Windows user and
   runtime home are needed to open it. Existing `SMARTVILLAGERS_API_KEY` takes
   precedence; the panel identifies environment-managed credentials. An unrelated
   `OPENAI_API_KEY` is not adopted as the game's credential.
4. Save provider settings, consent to the tiny context-free connection test, then
   choose **Test Connection**. The test checks the account's model list and submits
   a small request to the selected text endpoint. It sends no player dialogue or
   world lore. Errors remain visible; an unavailable model is not silently replaced.
5. Enable external conversations only after successful verification. Credential
   changes require a normal dedicated-server restart so its process receives the
   new credential. Scripted mode remains usable when a key is absent or unavailable.

The supported OpenAI endpoint is
`https://api.openai.com/v1/chat/completions`. Custom model IDs can be tested there.
Custom proxy endpoints are unavailable. Anthropic's existing preview integration
is separate from the OpenAI connection-verification and native provider controls.

## Models and request controls

Luna supports `none` reasoning, which is the quick-dialogue preset. Sol starts at
`low`; it does not support `none`. Temperature is sent only when supported by the
effective model and reasoning setting. Response-token budgets include reasoning;
keep the displayed dialogue short and give reasoning models sufficient token budget.

Global settings provide the fallback. An individual character can select a tested
model override, with its matching verified policy and prices. Test the character's
selected model before using it in game. Model-specific overrides are reported as
available only when the current authenticated adapter advertises that capability.

[Luna model and rates](https://developers.openai.com/api/docs/models/gpt-6-luna),
[Sol model and rates](https://developers.openai.com/api/docs/models/gpt-6.1-sol),
[GPT-6 parameter compatibility](https://developers.openai.com/api/docs/guides/latest-model),
[account model listing](https://developers.openai.com/api/reference/resources/models/methods/list).

## Usage, limits and fallback

The panel distinguishes returned provider token counts, conservative reservations
and estimated costs. The configured daily allowance covers this integration's
preview, connection-test and game reservations together. These are local estimates;
the OpenAI account's billing and other applications' usage remain outside that cap.
Changing processing tiers or prices requires reviewing the configured rates.

Request frequency, daily counts, cooldowns, response limits and bounded per-runtime
concurrency keep intentional conversations controlled. Exhausted local allowances,
busy workers, failed requests and missing consent use scripted fallback. Ambient
jokes remain local and make no OpenAI requests.

## Demonstrate one real villager first

1. In the master's suitable execution window, spawn or select one real Tortuga
   villager and bind Barnacle Bill's profile to its actual UUID.
2. Edit his personality, approved Tortuga lore and scripted greetings in Studio.
   Save and Apply; inspect the exact configuration acknowledgement.
3. Observe a custom scripted reply through the real Minecraft client.
4. Change a line in Studio, apply again, and observe that new line in Minecraft.
5. With a verified owner credential and player consent, enable Bill's AI and
   initiate an intentional conversation. Record the actual provider model/usage
   and the response displayed in Minecraft. A dashboard probe is not this test.
6. Verify a subsequent personality change, normal restart persistence and basic
   two-player behavior before expanding to the remaining approved population.

An older, absent or unauthenticated adapter receives an AI-disabled runtime export.
Start the matching updated adapter, then Apply again. Desired saved settings remain
available; an old acknowledgement does not establish application of a new snapshot.

Source and browser checks are separate from this gameplay demonstration. Keep the
actual native results on PR #11; do not label external AI verified before a real
authorized provider request succeeds, or integrated before installation is proved.
