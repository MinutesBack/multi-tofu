"""Radial character wheel: a click-through overlay panel drawn at the cursor."""
import math
import os
import sys

import objc

from .i18n import t
from .roles import colour_for
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

    def _ensure_panel(self):
        if self.panel is not None:
            return
        outer = float(self.config.data.get("wheel_radius", 130))
        side = (outer + 30) * 2
        rect = NSMakeRect(0, 0, side, side)
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
        view = WheelView.alloc().initWithFrame_(rect)
        view.outer = outer
        view.inner = float(self.config.data.get("wheel_inner_radius", 46))
        panel.setContentView_(view)
        self.panel = panel
        self.view = view

    def show(self, cg_x, cg_y, entries, current_name=None):
        if len(entries) < 2:
            return False
        self._ensure_panel()
        self.entries = entries
        self.view.entries = entries
        self.hover = -1
        if current_name:
            for i, entry in enumerate(entries):
                if entry["name"] == current_name:
                    self.hover = i
                    break
        self.view.hover = self.hover
        nx, ny = cg_to_ns(cg_x, cg_y)
        self.center = (nx, ny)
        frame = self.panel.frame()
        self.panel.setFrameOrigin_(
            NSMakePoint(nx - frame.size.width / 2.0, ny - frame.size.height / 2.0))
        self.view.setNeedsDisplay_(True)
        self.panel.orderFrontRegardless()
        self.visible = True
        return True

    def update_pointer(self, cg_x, cg_y):
        if not self.visible or not self.entries:
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

    def hide(self):
        if self.panel is not None:
            self.panel.orderOut_(None)
        self.visible = False

    def selection(self):
        if 0 <= self.hover < len(self.entries):
            return self.entries[self.hover]["name"]
        return None
