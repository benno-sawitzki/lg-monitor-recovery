# LG Monitor Recovery for macOS — DisplayPort No Signal Fix

A lightweight macOS menu bar app that automatically recovers an **LG 27UD58-B
stuck on “No Signal” after being turned off and on over DisplayPort**. Built and
tested on an Apple Silicon Mac mini, it restores the display output without
manually unplugging the cable or restarting your Mac.

**Source build • Apple Silicon • LG 27UD58-B • Local processing**

Monitor configuration is required before building. Other LG models and connection
types have not been validated.

## The problem

On the tested Mac mini M4, the LG displayed **No signal** after a monitor power
cycle. macOS still reported the DisplayPort connection as active. Physically
unplugging and reconnecting the DisplayPort cable restored the picture.
The issue also occurred with a direct Mac connection.

The monitor's DDC controls stopped responding while it was off and returned when
it powered on, even when the picture remained missing. The app uses that
transition to briefly sleep and wake the Mac's display output. Applications keep
running. This is an automatic recovery workaround; the underlying fault has not
been isolated to monitor firmware, cable, or macOS display handling.

## Features

- Automatic recovery after a confirmed monitor off/on cycle.
- Faster polling during recovery and an early wake once macOS reports display sleep.
- A ten-second display-awake hold so mouse movement is unnecessary.
- Left-click or right-click the menu bar icon to open the same native menu,
  including Quit, Settings, automatic recovery, manual recovery, and logs.
- Click the icon again to close the menu; native positioning keeps the icon visible.
- Optional start at login.
- Separate wake process that survives the recovery helper exiting.
- Supports multiple external displays while watching the configured monitor by identity.
- Ignores isolated DDC errors; cancels pending recovery on normal sleep, unplug,
  or a change in display count or target display ID.
- Recovery briefly sleeps and wakes all connected screens; applications keep running.
- Local rotating logs; no network requests or telemetry.

## Scope and requirements

The recovery sequence has been physically tested on this setup:

- Apple Silicon Mac, tested on a Mac mini M4 with macOS 26.6.2.
- LG 27UD58-B over USB-C to DisplayPort, tested at 4K/60 Hz.
- Homebrew Python 3 at `/opt/homebrew/bin/python3`.
- Xcode Command Line Tools (`clang`, `make`, and `codesign`) to build.

The app declares macOS 13 as its minimum version, but older releases and other
hardware have not been physically tested. The app is locally signed, not notarized.

## Build and install

### 1. Select your monitor

Build the included display communication tool and list connected monitors:

```sh
make -C source
source/m1ddc display list
```

In **both** `recovery.py` and `wake_display.py`, replace
`basic=7789:23305:YOUR_MONITOR_SERIAL` with your monitor's full basic identifier
(`basic=VENDOR:MODEL:SERIAL`). The published source contains a placeholder, not a
real device serial. Keep your configured copies private.

### 2. Build and test

```sh
bash build.sh
python3 -m unittest -v test_recovery.py test_wake.py
```

The build creates the app and its support files without changing the running
installation. To install, first quit any running copy from its menu bar menu.
Back up an existing app and support folder before replacing them, then run:

```sh
mkdir -p "$HOME/Library/Application Support/LGDisplayRecovery/source"
cp build/support/recovery.py build/support/wake_display.py "$HOME/Library/Application Support/LGDisplayRecovery/"
cp build/support/source/m1ddc build/support/source/LICENSE "$HOME/Library/Application Support/LGDisplayRecovery/source/"
ditto "build/LG Monitor Recovery.app" "/Applications/LG Monitor Recovery.app"
open "/Applications/LG Monitor Recovery.app"
```

Enable **Start at Login** in Settings for automatic startup. The app needs its
support folder as well as the `.app` bundle; moving only the bundle to another
Mac is insufficient.

For a read-only check on the installed monitor:

```sh
python3 "$HOME/Library/Application Support/LGDisplayRecovery/recovery.py" --probe
```

## Validation

Fifteen regression tests cover detection, repeated power cycles with multiple displays,
manual recovery, cancellation on normal sleep/disconnect or display changes,
the final pre-recovery check, early wake, and timeout fallback.
The owner physically confirmed repeated automatic recovery, recovery without
mouse input, and faster picture return after the timing update. Actual picture
recovery is distinct from a successful system command or unit test.

With version 1.4, the owner confirmed both LG screens showed a picture after
manual recovery with two external monitors connected. Automatic recovery after
a physical monitor power cycle with both connected still needs confirmation.

With version 1.4.2, the owner confirmed the menu stays below the icon and closes
when the icon is clicked again.

See [LOCAL-SETUP.md](LOCAL-SETUP.md) for implementation timing, installation paths,
validation history, and disable/remove instructions.

## Frequently asked questions

### Why does my LG monitor say “No Signal” after I turn it back on?

In the tested setup, macOS still considered the DisplayPort connection active
while the monitor was not showing a picture. Reconnecting the cable restored the
signal. The exact underlying cause has not been isolated; this app automates a
display-output sleep/wake sequence that recovered that setup.

### Does this restart or put my Mac to sleep?

It briefly sleeps and wakes all connected screens. Your Mac and applications keep
running. Normal macOS display sleep cancels pending automatic recovery.

### Is this an LG driver or firmware update?

No. It is an independent utility built around DDC monitor communication and
macOS display sleep/wake commands. It does not modify monitor firmware and is
not affiliated with LG or Apple.

### Will it work with every LG monitor or on Intel Macs?

Only the Apple Silicon and LG 27UD58-B setup described above has been physically
validated. This build uses m1ddc and targets Apple Silicon; HDMI, Intel Macs,
and other models are outside the validated scope. Multiple external monitors are
supported by the recovery logic; the configured monitor alone triggers recovery,
and the sleep/wake cycle affects all screens. Manual recovery has been physically
confirmed with two LG monitors; automatic recovery in that setup still needs
physical confirmation.

### Does it collect data?

The app and helper make no network requests and send no telemetry. Diagnostic
logs stay on your Mac. Device identifiers, logs, credentials, and local app
preferences are not included in this public repository.

## Source and attribution

`MenuApp.m` is the AppKit menu app. The Python scripts implement detection and
wake behavior. `source/` vendors [waydabber/m1ddc](https://github.com/waydabber/m1ddc)
at commit `04d949794102eb8df01ad3681afff6464a3eede2`, with local DDC response
validation, a longer communication delay, and a read-only status probe.
The upstream MIT license is retained at [source/LICENSE](source/LICENSE).
