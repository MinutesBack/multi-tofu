// A stand-in Dofus client: one native process, one window, a Dofus-shaped
// title. Launched several times from one bundle so each copy gets its own pid
// while sharing a bundle id, exactly like real Dofus clients.
#import <Cocoa/Cocoa.h>

int main(int argc, const char *argv[]) {
    @autoreleasepool {
        NSString *title = @"Account 1 - Iop - 3.6.10.11 - Release";
        NSRect frame = NSMakeRect(100, 100, 420, 240);

        for (int i = 1; i < argc; i++) {
            if (strcmp(argv[i], "--title") == 0 && i + 1 < argc) {
                title = [NSString stringWithUTF8String:argv[i + 1]];
            } else if (strcmp(argv[i], "--pos") == 0 && i + 1 < argc) {
                NSArray *p = [[NSString stringWithUTF8String:argv[i + 1]]
                              componentsSeparatedByString:@","];
                if (p.count == 2) {
                    frame.origin.x = [p[0] doubleValue];
                    frame.origin.y = [p[1] doubleValue];
                }
            }
        }

        NSApplication *app = [NSApplication sharedApplication];
        [app setActivationPolicy:NSApplicationActivationPolicyRegular];

        NSWindow *window = [[NSWindow alloc]
            initWithContentRect:frame
                      styleMask:(NSWindowStyleMaskTitled | NSWindowStyleMaskClosable |
                                 NSWindowStyleMaskMiniaturizable | NSWindowStyleMaskResizable)
                        backing:NSBackingStoreBuffered
                          defer:NO];
        [window setTitle:title];
        [window setBackgroundColor:[NSColor colorWithCalibratedRed:0.11 green:0.13 blue:0.17 alpha:1.0]];

        NSTextField *field = [[NSTextField alloc] initWithFrame:NSMakeRect(20, 96, 380, 48)];
        [field setStringValue:[[title componentsSeparatedByString:@" - "] firstObject]];
        [field setBezeled:NO];
        [field setDrawsBackground:NO];
        [field setEditable:NO];
        [field setSelectable:NO];
        [field setTextColor:[NSColor whiteColor]];
        [field setFont:[NSFont boldSystemFontOfSize:28]];
        [[window contentView] addSubview:field];

        [window makeKeyAndOrderFront:nil];
        [app run];
    }
    return 0;
}
