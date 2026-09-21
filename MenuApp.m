#import <AppKit/AppKit.h>

static NSString * const BundleID = @"local.lg-monitor-recovery";
static NSString * const JobLabel = @"local.lg-monitor-recovery";

@interface AppDelegate : NSObject <NSApplicationDelegate, NSMenuDelegate>
@property NSStatusItem *statusItem;
@property NSMenu *menu;
@property BOOL menuOpen;
@property id menuClickMonitor;
@property NSMenuItem *stateItem;
@property NSMenuItem *lastItem;
@property NSMenuItem *enabledItem;
@property NSMenuItem *loginItem;
@property NSMenuItem *recoverItem;
@property NSTask *worker;
@property BOOL recovering;
@property NSTimeInterval lastStart;
@property NSString *base;
@property NSString *agentPath;
@property NSWindow *settingsWindow;
@property NSTextField *statusLabel;
@property NSTextField *lastLabel;
@property NSButton *autoCheck;
@property NSButton *loginCheck;
@property NSButton *manualButton;
@end

@implementation AppDelegate
- (BOOL)enabled { return [[NSUserDefaults standardUserDefaults] boolForKey:@"AutomaticRecovery"]; }
- (NSString *)logFolder { return [NSHomeDirectory() stringByAppendingPathComponent:@"Library/Logs/LGDisplayRecovery"]; }
- (NSMenuItem *)add:(NSString *)title action:(SEL)action {
    NSMenuItem *item = [[NSMenuItem alloc] initWithTitle:title action:action keyEquivalent:@""];
    item.target = self;
    [self.menu addItem:item];
    return item;
}
- (void)applicationDidFinishLaunching:(NSNotification *)notification {
    (void)notification;
    if ([NSRunningApplication runningApplicationsWithBundleIdentifier:BundleID].count > 1) {
        [NSApp terminate:nil]; return;
    }
    [[NSUserDefaults standardUserDefaults] registerDefaults:@{@"AutomaticRecovery":@YES}];
    self.base = [NSHomeDirectory() stringByAppendingPathComponent:@"Library/Application Support/LGDisplayRecovery"];
    self.agentPath = [NSHomeDirectory() stringByAppendingPathComponent:[NSString stringWithFormat:@"Library/LaunchAgents/%@.plist", JobLabel]];
    self.statusItem = [[NSStatusBar systemStatusBar] statusItemWithLength:NSSquareStatusItemLength];
    NSImage *image = [NSImage imageWithSystemSymbolName:@"display" accessibilityDescription:@"LG Monitor Recovery"];
    image.template = YES;
    self.statusItem.button.image = image;
    self.statusItem.button.toolTip = @"LG Monitor Recovery";
    [self.statusItem.button setAccessibilityLabel:@"LG Monitor Recovery"];
    self.menu = [[NSMenu alloc] initWithTitle:@"LG Monitor Recovery"];
    self.menu.autoenablesItems = NO;
    self.menu.delegate = self;
    [self add:@"LG Monitor Recovery" action:NULL].enabled = NO;
    self.stateItem = [self add:@"Starting…" action:NULL]; self.stateItem.enabled = NO;
    self.lastItem = [self add:@"No recovery needed yet" action:NULL]; self.lastItem.enabled = NO;
    [self.menu addItem:[NSMenuItem separatorItem]];
    self.enabledItem = [self add:@"Automatic Recovery" action:@selector(toggleRecovery:)];
    self.recoverItem = [self add:@"Recover Display Now" action:@selector(recoverNow:)];
    self.loginItem = [self add:@"Start at Login" action:@selector(toggleLogin:)];
    [self.menu addItem:[NSMenuItem separatorItem]];
    [self add:@"Settings…" action:@selector(showSettings:)].keyEquivalent = @",";
    [self add:@"Open Logs…" action:@selector(openLogs:)];
    [self add:@"Show App in Finder" action:@selector(showApp:)];
    [self add:@"About LG Monitor Recovery" action:@selector(about:)];
    [self.menu addItem:[NSMenuItem separatorItem]];
    [self add:@"Quit LG Monitor Recovery" action:@selector(quit:)].keyEquivalent = @"q";
    // Let the status item anchor its menu below the menu bar on every display.
    self.statusItem.menu = self.menu;
    [self startWorker];
    [self refresh];
    [NSTimer scheduledTimerWithTimeInterval:3 target:self selector:@selector(tick:) userInfo:nil repeats:YES];
    if (![[NSUserDefaults standardUserDefaults] boolForKey:@"ShownSettings"]) {
        [[NSUserDefaults standardUserDefaults] setBool:YES forKey:@"ShownSettings"];
        [self showSettings:nil];
    }
}
- (NSTask *)taskWithArguments:(NSArray<NSString *> *)arguments {
    NSTask *task = [NSTask new];
    task.executableURL = [NSURL fileURLWithPath:@"/opt/homebrew/bin/python3"];
    task.arguments = [[NSArray arrayWithObject:[self.base stringByAppendingPathComponent:@"recovery.py"]] arrayByAddingObjectsFromArray:arguments];
    task.standardInput = [NSFileHandle fileHandleWithNullDevice];
    task.standardOutput = [NSFileHandle fileHandleWithNullDevice];
    task.standardError = [NSFileHandle fileHandleWithNullDevice];
    return task;
}
- (void)startWorker {
    if (!self.enabled || self.recovering || self.worker.running) return;
    self.lastStart = NSDate.timeIntervalSinceReferenceDate;
    self.worker = [self taskWithArguments:@[@"--parent-pid", [NSString stringWithFormat:@"%d", getpid()]]];
    NSError *error;
    if (![self.worker launchAndReturnError:&error]) {
        self.worker = nil;
        NSLog(@"Unable to start recovery: %@", error);
    }
}
- (void)stopWorker {
    if (self.worker.running) [self.worker terminate];
}
- (void)tick:(NSTimer *)timer {
    (void)timer;
    if (self.enabled && !self.worker.running && !self.recovering && NSDate.timeIntervalSinceReferenceDate - self.lastStart > 15) [self startWorker];
    [self refresh];
}
- (void)refresh {
    self.enabledItem.state = self.enabled ? NSControlStateValueOn : NSControlStateValueOff;
    self.loginItem.state = [[NSFileManager defaultManager] fileExistsAtPath:self.agentPath] ? NSControlStateValueOn : NSControlStateValueOff;
    NSString *status = self.recovering ? @"Recovering display…" : (!self.enabled ? @"Automatic recovery paused" : (self.worker.running ? @"Watching LG 27UD58-B" : @"Recovery helper unavailable"));
    self.stateItem.title = status;
    self.statusItem.button.toolTip = [@"LG Monitor Recovery — " stringByAppendingString:status];
    self.statusItem.button.appearsDisabled = !self.enabled;
    self.recoverItem.enabled = !self.recovering;
    self.enabledItem.enabled = !self.recovering;
    NSString *logs = [NSString stringWithContentsOfFile:[[self logFolder] stringByAppendingPathComponent:@"recovery.log"] encoding:NSUTF8StringEncoding error:NULL];
    for (NSString *line in [[logs componentsSeparatedByString:@"\n"] reverseObjectEnumerator]) {
        if ([line containsString:@"display_output_restart exit=0"] && line.length >= 19) {
            self.lastItem.title = [@"Last recovery: " stringByAppendingString:[line substringToIndex:19]];
            break;
        }
    }
    self.statusLabel.stringValue = status;
    self.lastLabel.stringValue = self.lastItem.title;
    self.autoCheck.state = self.enabledItem.state;
    self.loginCheck.state = self.loginItem.state;
    self.manualButton.enabled = !self.recovering;
    self.autoCheck.enabled = !self.recovering;
}
- (void)showSettings:(id)sender {
    (void)sender;
    if (!self.settingsWindow) {
        self.settingsWindow = [[NSWindow alloc] initWithContentRect:NSMakeRect(0,0,390,286)
            styleMask:NSWindowStyleMaskTitled|NSWindowStyleMaskClosable backing:NSBackingStoreBuffered defer:NO];
        self.settingsWindow.title = @"LG Monitor Recovery";
        self.settingsWindow.releasedWhenClosed = NO;
        NSView *content = self.settingsWindow.contentView;
        NSTextField *heading = [NSTextField labelWithString:@"LG 27UD58-B"];
        heading.font = [NSFont systemFontOfSize:19 weight:NSFontWeightSemibold];
        heading.frame = NSMakeRect(24,239,340,25); [content addSubview:heading];
        self.statusLabel = [NSTextField labelWithString:@"Starting…"];
        self.statusLabel.frame = NSMakeRect(24,211,340,20); [content addSubview:self.statusLabel];
        self.lastLabel = [NSTextField labelWithString:@"No recovery needed yet"];
        self.lastLabel.textColor = NSColor.secondaryLabelColor;
        self.lastLabel.font = [NSFont systemFontOfSize:11];
        self.lastLabel.frame = NSMakeRect(24,188,340,18); [content addSubview:self.lastLabel];
        NSTextField *detail = [NSTextField wrappingLabelWithString:@"Restores the signal after monitor off/on. All screens briefly sleep and wake; apps keep running."];
        detail.frame = NSMakeRect(24,137,340,40); [content addSubview:detail];
        self.autoCheck = [NSButton checkboxWithTitle:@"Automatic recovery" target:self action:@selector(toggleRecovery:)];
        self.autoCheck.frame = NSMakeRect(22,103,344,24); [content addSubview:self.autoCheck];
        self.loginCheck = [NSButton checkboxWithTitle:@"Start at login" target:self action:@selector(toggleLogin:)];
        self.loginCheck.frame = NSMakeRect(22,72,344,24); [content addSubview:self.loginCheck];
        self.manualButton = [NSButton buttonWithTitle:@"Recover Display Now" target:self action:@selector(recoverNow:)];
        self.manualButton.frame = NSMakeRect(20,23,185,32); [content addSubview:self.manualButton];
        NSButton *logs = [NSButton buttonWithTitle:@"Open Logs" target:self action:@selector(openLogs:)];
        logs.frame = NSMakeRect(245,23,124,32); [content addSubview:logs];
        [self.settingsWindow center];
    }
    [self refresh];
    [self.settingsWindow makeKeyAndOrderFront:nil];
    [NSApp activateIgnoringOtherApps:YES];
}
- (BOOL)applicationShouldHandleReopen:(NSApplication *)sender hasVisibleWindows:(BOOL)visible {
    (void)sender; (void)visible; [self showSettings:nil]; return YES;
}
- (void)menuWillOpen:(NSMenu *)menu {
    (void)menu;
    self.menuOpen = YES;
    [self refresh];
    // Consume a second press on the icon before AppKit can reopen the menu.
    // Listen on mouse-down, so releasing that same click cannot open it again.
    __weak AppDelegate *weakSelf = self;
    self.menuClickMonitor = [NSEvent addLocalMonitorForEventsMatchingMask:
        NSEventMaskLeftMouseDown | NSEventMaskRightMouseDown handler:^NSEvent *(NSEvent *event) {
        AppDelegate *delegate = weakSelf;
        NSStatusBarButton *button = delegate.statusItem.button;
        if (!delegate.menuOpen || !button.window) return event;
        NSRect iconRect = [button.window convertRectToScreen:[button convertRect:button.bounds toView:nil]];
        NSPoint point = event.window ? [event.window convertPointToScreen:event.locationInWindow] : NSEvent.mouseLocation;
        if (NSPointInRect(point, iconRect)) {
            [delegate.menu cancelTrackingWithoutAnimation];
            return nil;
        }
        return event;
    }];
}
- (void)menuDidClose:(NSMenu *)menu {
    (void)menu;
    self.menuOpen = NO;
    if (self.menuClickMonitor) {
        [NSEvent removeMonitor:self.menuClickMonitor];
        self.menuClickMonitor = nil;
    }
}
- (void)toggleRecovery:(id)sender {
    (void)sender;
    BOOL next = !self.enabled;
    [[NSUserDefaults standardUserDefaults] setBool:next forKey:@"AutomaticRecovery"];
    if (next) [self startWorker]; else [self stopWorker];
    [self refresh];
}
- (void)recoverNow:(id)sender {
    (void)sender;
    if (self.recovering) return;
    self.recovering = YES;
    [self stopWorker];
    [self refresh];
    NSTask *oldWorker = self.worker;
    dispatch_async(dispatch_get_global_queue(QOS_CLASS_USER_INITIATED, 0), ^{
        if (oldWorker.running) [oldWorker waitUntilExit];
        NSTask *manual = [self taskWithArguments:@[@"--recover-once"]];
        NSError *error;
        if ([manual launchAndReturnError:&error]) [manual waitUntilExit];
        dispatch_async(dispatch_get_main_queue(), ^{
            self.recovering = NO;
            self.worker = nil;
            [self startWorker];
            [self refresh];
        });
    });
}
- (void)toggleLogin:(id)sender {
    (void)sender;
    NSError *error = nil;
    NSFileManager *fm = NSFileManager.defaultManager;
    if ([fm fileExistsAtPath:self.agentPath]) {
        [fm removeItemAtPath:self.agentPath error:&error];
    } else {
        NSDictionary *plist = @{@"Label":JobLabel, @"RunAtLoad":@YES,
            @"ProgramArguments":@[@"/usr/bin/open", @"-g", NSBundle.mainBundle.bundlePath]};
        NSData *data = [NSPropertyListSerialization dataWithPropertyList:plist format:NSPropertyListXMLFormat_v1_0 options:0 error:&error];
        [fm createDirectoryAtPath:self.agentPath.stringByDeletingLastPathComponent withIntermediateDirectories:YES attributes:nil error:&error];
        if (data && !error) [data writeToFile:self.agentPath options:NSDataWritingAtomic error:&error];
    }
    if (error) {
        NSAlert *alert = [NSAlert new]; alert.messageText = @"Couldn’t change login startup";
        alert.informativeText = error.localizedDescription; [alert runModal];
    }
    [self refresh];
}
- (void)openLogs:(id)sender {
    (void)sender;
    [[NSWorkspace sharedWorkspace] openURL:[NSURL fileURLWithPath:[self logFolder]]];
}
- (void)showApp:(id)sender {
    (void)sender;
    [[NSWorkspace sharedWorkspace] activateFileViewerSelectingURLs:@[NSBundle.mainBundle.bundleURL]];
}
- (void)about:(id)sender {
    (void)sender;
    NSAlert *alert = [NSAlert new];
    alert.messageText = @"LG Monitor Recovery";
    alert.informativeText = @"Restores the video signal after your LG 27UD58-B is turned off and on.\n\nWhen the monitor starts responding again, the app briefly sleeps and wakes only the display output. Your Mac and apps keep running.\n\nAutomatic recovery supports multiple external displays. All screens briefly sleep and wake during recovery. Normal display sleep cancels pending recovery.\n\nVersion 1.4.2 • Built for this Mac and monitor.\nUses m1ddc (MIT license).";
    [alert addButtonWithTitle:@"OK"];
    [alert runModal];
}
- (void)quit:(id)sender { (void)sender; [NSApp terminate:nil]; }
- (void)applicationWillTerminate:(NSNotification *)notification { (void)notification; [self stopWorker]; }
@end

int main(void) {
    @autoreleasepool {
        NSApplication *app = [NSApplication sharedApplication];
        [app setActivationPolicy:NSApplicationActivationPolicyAccessory];
        AppDelegate *delegate = [AppDelegate new];
        app.delegate = delegate;
        [app run];
    }
    return 0;
}
