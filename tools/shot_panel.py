"""Render the party panel with fake accounts and screenshot just its window."""
import os, subprocess, sys, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["MULTITOFU_QUIET"] = "1"
os.environ.setdefault("MULTITOFU_CONFIG", "/tmp/mt_panel_shot.json")

from AppKit import NSApplication, NSApplicationActivationPolicyAccessory, NSApp
from Foundation import NSObject, NSTimer
from multitofu.config import Config
from multitofu.classes import to_slug
from multitofu.radial import Wheel
import Quartz

CAST = [("Fley","Forgelance","damage"),("Natsu","Iop","damage"),
        ("Yuki","Xelor","support"),("Otomai","Eniripsa","healer"),
        ("Zephyr","Sadida","scout"),("Kioko","Cra","damage")]

def entries():
    out=[]
    for n,c,r in CAST:
        out.append({"name":n,"class_name":c,"slug":to_slug(c),"role":r,
                    "pid":0,"window":None})
    return out

class Runner(NSObject):
    def go_(self, timer):
        cfg=Config(); cfg.data["wheel_style"]="panel"; cfg.data["leader_name"]="Fley"
        cfg.data["character_binds"]={"Natsu":{"keycode":96,"flags":0}}  # F5-ish
        w=Wheel(cfg)
        w.show(60, 400, entries(), "Yuki")
        # hover Otomai: compute a point inside its row
        ox,oy=w.panel_origin; pw,ph=w.panel_size
        # row 3 (Otomai), from top
        row_cy_ns = oy+ph-10-3*58-29
        # cursor in Quartz top-left coords: y_top = primary_h - ns_y
        from AppKit import NSScreen
        H=NSScreen.screens()[0].frame().size.height
        w.update_pointer(ox+120, H-row_cy_ns)
        NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            0.8, self, "grab:", w, False)
    def grab_(self, timer):
        w=timer.userInfo()
        num=w.panel.windowNumber()
        subprocess.run(["screencapture","-x","-o","-l",str(num),"/tmp/mt_panel.png"])
        print("wrote /tmp/mt_panel.png")
        NSApp.terminate_(self)

app=NSApplication.sharedApplication()
app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)
r=Runner.alloc().init()
NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(0.4, r, "go:", None, False)
app.run()
