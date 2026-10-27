# Native ridge expectations for the complete neighborhoods

The first native Signal Lane depth verification retained 46 inherited Macaw
roof-top part differences. The original builders supplied a generic straight
part along entire ridges, including their ends and intersections. This affects
the verification expectation; it does not require replaying the new depth layer.
The failed native receipt remains retained.

`tools.artistic_neighborhood_roofs` derives canonical `part` values from the
complete original geometry and pinned Macaw Roofs2.3.2
`RoofTopNew.StairState/getRoofPart` algorithm. Only cardinal neighbors at the same
height with the **same actual block identity** connect. Different roofing
materials do not connect merely because both are ridge blocks. The native rule
distinguishes four ends, four outer corners, four T joins, a four-way join and
straight ridges; an isolated ridge uses the native switched0 default.

The source derives 47 Signal, 14 court and 28 Bramble part corrections. It keeps
every position, material, orientation, window, bed, inventory/NBT expectation and
command exact. The difference between the 47 canonical Signal corrections and
the first observed 46 failures is not hidden: an existing live ridge may require
a real normal neighbor update. No observed residue is copied into expectations
to manufacture a pass.

Exports are **verification only**, with construction forbidden. Separate small
ridge-only inputs are for normal native neighbor reconciliation and verification,
not placement: 171 Signal, 60 court and 118 Bramble targets. The shared native
operation must scope any derived-part exemption to the actual known window or
ridge classes; a bed's head/foot part remains structural. It must not replay
source states, NBT, inventories or commands.

Fresh strict complete native verification remains required after normal settling.
Pure semantic/rotation tests cover all sixteen cardinal masks, same-ID behavior,
unchanged unrelated properties/NBT and rejection of unregistered parts. These
tests and the derived files do not claim native graphical or owner acceptance.
