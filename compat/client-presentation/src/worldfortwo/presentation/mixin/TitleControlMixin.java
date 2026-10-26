package worldfortwo.presentation.mixin;

import worldfortwo.presentation.Presentation;

import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.client.gui.components.AbstractWidget;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

/** Set both drawing and hitbox coordinates after higher-priority menu adapters. */
@Mixin(value=AbstractWidget.class, remap=false, priority=500)
public abstract class TitleControlMixin {
    @Inject(method="render(Lnet/minecraft/client/gui/GuiGraphics;IIF)V", at=@At("HEAD"))
    private void awftToolbar(GuiGraphics graphics, int mouseX, int mouseY, float delta, CallbackInfo callback) {
        Presentation.layoutControl((AbstractWidget)(Object)this);
    }
}
