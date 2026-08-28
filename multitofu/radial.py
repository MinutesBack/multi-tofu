"""Radial character wheel: a click-through overlay panel drawn at the cursor."""
import math
import os
import sys

import objc

from .i18n import t
from .roles import colour_for
from .keys import describe
from AppKit import (
    NSAttributedString, NSBezierPath, NSColor, NSCompositingOperationSourceOver,
    NSFont, NSFontAttributeName, NSForegroundColorAttributeName, NSGraphicsContext,
    NSImage, NSMakeRect, NSPanel, NSScreen, NSShadow, NSSound,
    NSStrokeColorAttributeName, NSStrokeWidthAttributeName, NSView,
    NSWindowCollectionBehaviorCanJoinAllSpaces,
    NSWindowCollectionBehaviorFullScreenAuxiliary,
    NSWindowCollectionBehaviorStationary,
)
from Foundation import NSMakePoint, NSMakeSize


def _assets_dir():
    """Assets sit next to the package in a source checkout and inside the
    bundle once frozen."""
    frozen = getattr(sys, "_MEIPASS", None)
    if frozen:
        bundled = os.path.join(frozen, "multitofu", "assets")
        if os.path.isdir(bundled):
            return bundled
        return os.path.join(frozen, "assets")
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")


ASSETS = _assets_dir()
SKIN_DIR = os.path.join(ASSETS, "skin")
SOUND_DIR = os.path.join(ASSETS, "sounds")

BORDERLESS = 0
NONACTIVATING_PANEL = 1 << 7
POPUP_MENU_LEVEL = 101

_image_cache = {}
_sound_cache = {}
_font_cache = {}


def rgb(r, g, b, a=1.0):
    return NSColor.colorWithCalibratedRed_green_blue_alpha_(
        r / 255.0, g / 255.0, b / 255.0, a)


# Sticker-book palette: grape wheel, cream outlines, a sunny wedge under the
# cursor. Bright enough to read over a busy game frame without washing out the
# class sprites sitting on top of it.
GRAPE_RGB = (74, 64, 118)
GRAPE_ALT_RGB = (101, 88, 158)
GRAPE = rgb(*GRAPE_RGB, 0.95)
GRAPE_ALT = rgb(*GRAPE_ALT_RGB, 0.95)
SUNNY = rgb(255, 201, 74, 0.98)
CREAM = rgb(255, 246, 232, 0.95)
MINT = rgb(95, 224, 176, 1.0)
INK = rgb(46, 38, 80, 1.0)
MUTED = rgb(120, 110, 160, 1.0)
BADGE = rgb(255, 246, 232, 0.30)

# The panel style: a party-frame look, dark and bronze so it sits in the game.
PANEL_BG = rgb(30, 34, 45, 0.97)
PANEL_FRAME = rgb(12, 15, 22, 1.0)
BRONZE = rgb(150, 110, 64, 1.0)
GOLD_HI = rgb(240, 208, 120, 1.0)
SEL_ROW = rgb(58, 52, 34, 0.98)

PANEL_W = 250.0
ROW_H = 58.0
PANEL_PAD = 10.0
PORTRAIT_R = 20.0
PANEL_CANCEL = 80.0


def font(size, bold=True):
    """The rounded system face, which reads friendlier than the default."""
    key = (size, bold)
    if key in _font_cache:
        return _font_cache[key]
    base = (NSFont.boldSystemFontOfSize_(size) if bold
            else NSFont.systemFontOfSize_(size))
    result = base
    try:
        from AppKit import NSFontDescriptorSystemDesignRounded
        descriptor = base.fontDescriptor().fontDescriptorWithDesign_(
            NSFontDescriptorSystemDesignRounded)
        if descriptor is not None:
            rounded = NSFont.fontWithDescriptor_size_(descriptor, size)
            if rounded is not None:
                result = rounded
    except Exception:
        pass
    _font_cache[key] = result
    return result


def load_icon(slug):
    if not slug:
        slug = "character"
    if slug in _image_cache:
        return _image_cache[slug]
    if slug == "__logo__":
        path = os.path.join(ASSETS, "logo.png")
        image = NSImage.alloc().initWithContentsOfFile_(path)
        _image_cache[slug] = image
        return image
    path = os.path.join(SKIN_DIR, f"{slug}.png")
    if not os.path.exists(path):
        path = os.path.join(SKIN_DIR, "character.png")
    image = NSImage.alloc().initWithContentsOfFile_(path)
    _image_cache[slug] = image
    return image


def play(name, volume):
    if volume <= 0:
        return
    sound = _sound_cache.get(name)
    if sound is None:
        path = os.path.join(SOUND_DIR, f"{name}.wav")
        if not os.path.exists(path):
            return
        sound = NSSound.alloc().initWithContentsOfFile_byReference_(path, True)
        _sound_cache[name] = sound
    if sound is None:
        return
    sound.stop()
    sound.setVolume_(max(0.0, min(1.0, volume)))
    sound.play()


def cg_to_ns(x, y):
    """Quartz global coords (top-left origin) -> Cocoa coords (bottom-left)."""
    screens = NSScreen.screens()
    if not screens:
        return x, y
    primary_height = screens[0].frame().size.height
    return x, primary_height - y


def draw_centered_image(image, x, y, size):
    image.drawInRect_fromRect_operation_fraction_(
        NSMakeRect(x - size / 2.0, y - size / 2.0, size, size),
        NSMakeRect(0, 0, 0, 0), NSCompositingOperationSourceOver, 1.0)


def outlined(text, size, fill, stroke=INK, width=-3.5):
    """Cartoon lettering: a fill with a chunky outline behind it."""
    return NSAttributedString.alloc().initWithString_attributes_(text, {
        NSFontAttributeName: font(size),
        NSForegroundColorAttributeName: fill,
        NSStrokeColorAttributeName: stroke,
        NSStrokeWidthAttributeName: width,
    })


def draw_centered(attributed, x, y):
    size = attributed.size()
    attributed.drawAtPoint_(NSMakePoint(x - size.width / 2.0,
                                        y - size.height / 2.0))


class WheelView(NSView):
    def initWithFrame_(self, frame):
        self = objc.super(WheelView, self).initWithFrame_(frame)
        if self is None:
            return None
        self.entries = []
        self.hover = -1
        self.outer = 130.0
        self.inner = 46.0
        return self

    def isFlipped(self):
        return False

    def drawRect_(self, rect):
        NSColor.clearColor().set()
        NSBezierPath.fillRect_(rect)
        if not self.entries:
            return

        bounds = self.bounds()
        cx = bounds.size.width / 2.0
        cy = bounds.size.height / 2.0
        center = NSMakePoint(cx, cy)
        count = len(self.entries)
        step = 360.0 / count
        # Cocoa angles grow anticlockwise. Subtract so the rotation reads
        # clockwise, the way anyone expects a numbered wheel to run.
        top = 90.0 + step / 2.0

        context = NSGraphicsContext.currentContext()

        # soft drop shadow under the whole sticker
        context.saveGraphicsState()
        shadow = NSShadow.alloc().init()
        shadow.setShadowColor_(NSColor.colorWithCalibratedWhite_alpha_(0.0, 0.35))
        shadow.setShadowBlurRadius_(18.0)
        shadow.setShadowOffset_(NSMakeSize(0, -5))
        shadow.set()
        disc = NSBezierPath.bezierPathWithOvalInRect_(
            NSMakeRect(cx - self.outer, cy - self.outer,
                       self.outer * 2, self.outer * 2))
        CREAM.set()
        disc.fill()
        context.restoreGraphicsState()

        for i in range(count):
            a1 = top - step * i
            a0 = a1 - step
            wedge = NSBezierPath.bezierPath()
            wedge.appendBezierPathWithArcWithCenter_radius_startAngle_endAngle_(
                center, self.outer - 5, a0, a1)
            wedge.appendBezierPathWithArcWithCenter_radius_startAngle_endAngle_clockwise_(
                center, self.inner, a1, a0, True)
            wedge.closePath()
            if i == self.hover:
                SUNNY.set()
            else:
                (GRAPE if i % 2 == 0 else GRAPE_ALT).set()
            wedge.fill()

            # role colour rides the outer rim. Tinting the whole wedge washes
            # the labels out, a rim reads just as fast and keeps them legible.
            tint = colour_for(self.entries[i].get("role"))
            if tint is not None:
                rim = NSBezierPath.bezierPath()
                rim.appendBezierPathWithArcWithCenter_radius_startAngle_endAngle_(
                    center, self.outer - 5, a0, a1)
                rim.appendBezierPathWithArcWithCenter_radius_startAngle_endAngle_clockwise_(
                    center, self.outer - 17, a1, a0, True)
                rim.closePath()
                rgb(*tint, 0.95).set()
                rim.fill()

            CREAM.set()
            wedge.setLineWidth_(3.5)
            wedge.setLineJoinStyle_(1)  # round
            wedge.stroke()

        # Segments carry the class icon and the role colour, nothing else.
        # Horizontal text cannot share a wedge with an icon at every angle
        # without colliding with one or the other, so the name goes in the hub
        # where there is room for it at any team size.
        band = self.outer - self.inner
        icon_radius = self.inner + band * 0.52
        icon_size = min(band * 0.46, 54.0)
        for i, entry in enumerate(self.entries):
            angle = math.radians(top - step * i - step / 2.0)
            ix = cx + icon_radius * math.cos(angle)
            iy = cy + icon_radius * math.sin(angle)

            badge_r = icon_size * 0.62
            badge = NSBezierPath.bezierPathWithOvalInRect_(
                NSMakeRect(ix - badge_r, iy - badge_r, badge_r * 2, badge_r * 2))
            BADGE.set()
            badge.fill()

            icon = load_icon(entry.get("slug"))
            if icon is not None:
                icon.drawInRect_fromRect_operation_fraction_(
                    NSMakeRect(ix - icon_size / 2.0, iy - icon_size / 2.0,
                               icon_size, icon_size),
                    NSMakeRect(0, 0, 0, 0), NSCompositingOperationSourceOver, 1.0)

        # hub
        hub = NSBezierPath.bezierPathWithOvalInRect_(
            NSMakeRect(cx - self.inner, cy - self.inner,
                       self.inner * 2, self.inner * 2))
        CREAM.set()
        hub.fill()
        MINT.set()
        hub.setLineWidth_(4.0)
        hub.stroke()

        if 0 <= self.hover < count:
            entry = self.entries[self.hover]
            draw_centered(outlined(entry["name"][:14], 14.0, INK, CREAM, -2.0),
                          cx, cy + 8)
            klass = entry.get("class_name")
            if klass:
                draw_centered(outlined(klass[:16], 10.5, MUTED, CREAM, -1.5),
                              cx, cy - 12)
        else:
            logo = load_icon("__logo__")
            if logo is not None:
                draw_centered_image(logo, cx, cy + 10, self.inner * 0.72)
            draw_centered(outlined(t("wheel_cancel"), 9.5, MUTED, CREAM, -1.5),
                          cx, cy - self.inner * 0.48)


def _panel_crown(cx, base_y):
    """Small gold crown sitting above a portrait, drawn in a flipped view so
    up is a smaller y."""
    s = 15.0
    half = s * 0.6
    peak = base_y - s * 0.7
    side = base_y - s * 0.4
    val = base_y - s * 0.06
    path = NSBezierPath.bezierPath()
    path.moveToPoint_(NSMakePoint(cx - half, base_y))
    for px, py in ((cx - half, side), (cx - half * 0.45, val), (cx, peak),
                   (cx + half * 0.45, val), (cx + half, side), (cx + half, base_y)):
        path.lineToPoint_(NSMakePoint(px, py))
    path.closePath()
    GOLD_HI.set()
    path.fill()
    INK.set()
    path.setLineWidth_(1.5)
    path.stroke()


def _draw_left(attributed, x, cy):
    """Left-aligned text, vertically centred on cy."""
    size = attributed.size()
    attributed.drawAtPoint_(NSMakePoint(x, cy - size.height / 2.0))


class PanelView(NSView):
    """The party-frame switcher: a vertical list of framed class portraits."""

    def initWithFrame_(self, frame):
        self = objc.super(PanelView, self).initWithFrame_(frame)
        if self is None:
            return None
        self.entries = []
        self.keys = []
        self.hover = -1
        self.leader = -1
        return self

    def isFlipped(self):
        return True

    def drawRect_(self, rect):
        NSColor.clearColor().set()
        NSBezierPath.fillRect_(rect)
        if not self.entries:
            return
        b = self.bounds()
        w, h = b.size.width, b.size.height

        context = NSGraphicsContext.currentContext()
        context.saveGraphicsState()
        shadow = NSShadow.alloc().init()
        shadow.setShadowColor_(NSColor.colorWithCalibratedWhite_alpha_(0.0, 0.4))
        shadow.setShadowBlurRadius_(16.0)
        shadow.setShadowOffset_(NSMakeSize(0, -3))
        shadow.set()
        body = NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(
            NSMakeRect(2, 2, w - 4, h - 4), 16.0, 16.0)
        PANEL_BG.set()
        body.fill()
        context.restoreGraphicsState()
        body.setLineWidth_(2.5)
        BRONZE.set()
        body.stroke()

        n = len(self.entries)
        for i, entry in enumerate(self.entries):
            row_top = PANEL_PAD + i * ROW_H
            row_cy = row_top + ROW_H / 2.0
            sel = (i == self.hover)

            if sel:
                srow = NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(
                    NSMakeRect(5, row_top + 3, w - 10, ROW_H - 6), 10.0, 10.0)
                SEL_ROW.set()
                srow.fill()
                GOLD_HI.set()
                NSBezierPath.fillRect_(NSMakeRect(5, row_top + 3, 4, ROW_H - 6))

            pcx, pcy, pr = 40.0, row_cy, PORTRAIT_R
            ring = NSBezierPath.bezierPathWithOvalInRect_(
                NSMakeRect(pcx - pr - 3, pcy - pr - 3, (pr + 3) * 2, (pr + 3) * 2))
            PANEL_FRAME.set()
            ring.fill()
            (GOLD_HI if sel else BRONZE).set()
            ring.setLineWidth_(2.5)
            ring.stroke()

            disc_rect = NSMakeRect(pcx - pr, pcy - pr, pr * 2, pr * 2)
            disc = NSBezierPath.bezierPathWithOvalInRect_(disc_rect)
            PANEL_FRAME.set()
            disc.fill()
            icon = load_icon(entry.get("slug"))
            if icon is not None:
                context.saveGraphicsState()
                NSBezierPath.bezierPathWithOvalInRect_(disc_rect).addClip()
                iso = pr * 2 * 1.16
                icon.drawInRect_fromRect_operation_fraction_(
                    NSMakeRect(pcx - iso / 2.0, pcy - iso / 2.0, iso, iso),
                    NSMakeRect(0, 0, 0, 0), NSCompositingOperationSourceOver, 1.0)
                context.restoreGraphicsState()

            if i == self.leader:
                _panel_crown(pcx, pcy - pr - 2)

            name = entry["name"][:12]
            colour = GOLD_HI if sel else CREAM
            _draw_left(outlined(name, 14.0, colour, INK, -2.0), pcx + pr + 16, row_cy)

            key = self.keys[i] if i < len(self.keys) else str(i + 1)
            chx = w - 34.0
            chip = NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(
                NSMakeRect(chx - 16, pcy - 15, 32, 30), 7.0, 7.0)
            PANEL_FRAME.set()
            chip.fill()
            (GOLD_HI if sel else BRONZE).set()
            chip.setLineWidth_(2.0)
            chip.stroke()
            draw_centered(outlined(key, 13.0, CREAM, INK, -1.5), chx, pcy)
        del n


class Wheel:
    """Owns the overlay panel and the hover maths."""

    def __init__(self, config):
        self.config = config
        self.panel = None
        self.view = None
        self.entries = []
        self.hover = -1
        self.center = (0.0, 0.0)
        self.visible = False
        self.built_style = None
        self.panel_origin = (0.0, 0.0)
        self.panel_size = (0.0, 0.0)

    def _new_panel(self, rect):
        panel = NSPanel.alloc().initWithContentRect_styleMask_backing_defer_(
            rect, BORDERLESS | NONACTIVATING_PANEL, 2, False)
        panel.setOpaque_(False)
        panel.setBackgroundColor_(NSColor.clearColor())
        panel.setLevel_(POPUP_MENU_LEVEL)
        panel.setHasShadow_(False)
        panel.setIgnoresMouseEvents_(True)
        panel.setHidesOnDeactivate_(False)
        panel.setCollectionBehavior_(
            NSWindowCollectionBehaviorCanJoinAllSpaces
            | NSWindowCollectionBehaviorStationary
            | NSWindowCollectionBehaviorFullScreenAuxiliary)
        return panel

    def _screen_at(self, nx, ny):
        for screen in NSScreen.screens():
            f = screen.frame()
            if (f.origin.x <= nx <= f.origin.x + f.size.width
                    and f.origin.y <= ny <= f.origin.y + f.size.height):
                return screen
        return NSScreen.mainScreen() or NSScreen.screens()[0]

    def _ensure_panel(self):
        style = self.config.data.get("wheel_style", "wheel")
        if self.panel is not None and self.built_style == style:
            return
        if self.panel is not None:
            self.panel.orderOut_(None)
            self.panel = None
            self.view = None
        if style == "panel":
            rect = NSMakeRect(0, 0, PANEL_W, 400)
            view = PanelView.alloc().initWithFrame_(rect)
        else:
            outer = float(self.config.data.get("wheel_radius", 130))
            side = (outer + 30) * 2
            rect = NSMakeRect(0, 0, side, side)
            view = WheelView.alloc().initWithFrame_(rect)
            view.outer = outer
            view.inner = float(self.config.data.get("wheel_inner_radius", 46))
        panel = self._new_panel(rect)
        panel.setContentView_(view)
        self.panel = panel
        self.view = view
        self.built_style = style

    def show(self, cg_x, cg_y, entries, current_name=None):
        # one entry draws a single full-circle segment; zero would divide by
        # zero in the angle maths, so that is the only case we refuse
        if not entries:
            return False
        self._ensure_panel()
        self.entries = entries
        cur = -1
        if current_name:
            for i, entry in enumerate(entries):
                if entry["name"] == current_name:
                    cur = i
                    break
        if self.built_style == "panel":
            return self._show_panel(cg_x, cg_y, entries, cur)
        self.view.entries = entries
        self.hover = cur
        self.view.hover = cur
        nx, ny = cg_to_ns(cg_x, cg_y)
        self.center = (nx, ny)
        frame = self.panel.frame()
        self.panel.setFrameOrigin_(
            NSMakePoint(nx - frame.size.width / 2.0, ny - frame.size.height / 2.0))
        self.view.setNeedsDisplay_(True)
        self.panel.orderFrontRegardless()
        self.visible = True
        return True

    def _show_panel(self, cg_x, cg_y, entries, cur):
        cbinds = self.config.data.get("character_binds", {})
        keys = []
        for i, entry in enumerate(entries):
            bind = cbinds.get(entry["name"])
            if bind and bind.get("keycode") is not None:
                keys.append(describe(bind)[:4])
            else:
                keys.append(str(i + 1))
        leader_name = self.config.data.get("leader_name", "")
        leader = next((i for i, e in enumerate(entries)
                       if e["name"] == leader_name), -1)
        n = len(entries)
        pw, ph = PANEL_W, n * ROW_H + 2 * PANEL_PAD
        nx, ny = cg_to_ns(cg_x, cg_y)
        screen = self._screen_at(nx, ny)
        sf = screen.frame()
        ox = sf.origin.x + 24.0
        oy = sf.origin.y + (sf.size.height - ph) / 2.0
        self.panel.setFrame_display_(NSMakeRect(ox, oy, pw, ph), False)
        self.view.setFrame_(NSMakeRect(0, 0, pw, ph))
        self.view.entries = entries
        self.view.keys = keys
        self.view.leader = leader
        self.hover = cur
        self.view.hover = cur
        self.panel_origin = (ox, oy)
        self.panel_size = (pw, ph)
        self.view.setNeedsDisplay_(True)
        self.panel.orderFrontRegardless()
        self.visible = True
        return True

    def update_pointer(self, cg_x, cg_y):
        if not self.visible or not self.entries:
            return
        if self.built_style == "panel":
            self._update_panel(cg_x, cg_y)
            return
        nx, ny = cg_to_ns(cg_x, cg_y)
        dx = nx - self.center[0]
        dy = ny - self.center[1]
        distance = math.hypot(dx, dy)
        inner = float(self.config.data.get("wheel_inner_radius", 46))
        if distance < inner:
            new_hover = -1
        else:
            count = len(self.entries)
            step = 360.0 / count
            angle = math.degrees(math.atan2(dy, dx))
            offset = ((90.0 + step / 2.0) - angle) % 360.0
            new_hover = int(offset // step) % count
        if new_hover != self.hover:
            self.hover = new_hover
            self.view.hover = new_hover
            self.view.setNeedsDisplay_(True)
            if new_hover >= 0 and self.config.data.get("wheel_sounds", True):
                play("hover", self.config.data.get("volume_level", 50) / 100.0)

    def _update_panel(self, cg_x, cg_y):
        nx, ny = cg_to_ns(cg_x, cg_y)
        ox, oy = self.panel_origin
        pw, ph = self.panel_size
        n = len(self.entries)
        if (nx > ox + pw + PANEL_CANCEL or nx < ox - PANEL_CANCEL
                or ny > oy + ph + PANEL_CANCEL or ny < oy - PANEL_CANCEL):
            new_hover = -1
        else:
            rel = (oy + ph) - PANEL_PAD - ny
            new_hover = max(0, min(n - 1, int(rel // ROW_H)))
        if new_hover != self.hover:
            self.hover = new_hover
            self.view.hover = new_hover
            self.view.setNeedsDisplay_(True)
            if new_hover >= 0 and self.config.data.get("wheel_sounds", True):
                play("hover", self.config.data.get("volume_level", 50) / 100.0)

    def hide(self):
        if self.panel is not None:
            self.panel.orderOut_(None)
        self.visible = False

    def selection(self):
        if 0 <= self.hover < len(self.entries):
            return self.entries[self.hover]["name"]
        return None
