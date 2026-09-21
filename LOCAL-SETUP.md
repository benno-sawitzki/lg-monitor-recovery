# LG Monitor Recovery

Installed app: `/Applications/LG Monitor Recovery.app`.

Left-click or right-click its monitor icon to open the same native menu,
including Settings and Quit. Click the icon again to close the menu.
Settings lets you pause automatic recovery,
turn login startup on/off, or recover the display manually. Opening the app from
Applications also opens Settings. Closing Settings leaves the menu app running;
Quit stops automatic recovery for this session.

## What it does

This is an automatic software recovery for the LG 27UD58-B reporting “No signal”
after its power button is turned off and on. It does not modify monitor firmware.

The helper queries the monitor's DDC power state. After two consecutive missing/off
responses and two valid on responses, it sleeps only the Mac's display output and
wakes it half a second after macOS reports the output asleep, holding a
display-awake assertion for ten seconds. If sleep cannot be confirmed, the wake
request falls back to approximately two seconds. The ten-second assertion holds
the display awake; it does not postpone the picture.
It resets each detected cycle once, rather than
imposing a cooldown that would skip a second intentional power cycle.

It is restricted to monitor identity `7789:23305:YOUR_MONITOR_SERIAL`, ignores isolated read
errors, and cancels pending recovery on unplug, normal display sleep, or a change
in display count or target display ID. Multiple external displays are supported;
recovery briefly sleeps and wakes all connected screens. Between probes it waits
one second normally and 150 ms during a detected power cycle. Polling pauses during its
own six-second recovery sequence. Very fast power toggles may be too short to
detect. A separate wake process survives the helper exiting mid-recovery.

## Files and requirements

- `MenuApp.m`: native AppKit menu app source.
- `recovery.py`: recovery logic and process supervision.
- `wake_display.py`: independent delayed display wake.
- `source/`: m1ddc source and binary, with local reply validation and status probe.
- `test_recovery.py`: regression tests for detection and suppression.
- `test_wake.py`: regression tests for early wake and timeout fallback.
- `wake-status.json`: timing and sleep confirmation for the latest wake request.
- `~/Library/Logs/LGDisplayRecovery/recovery.log`: rotating local log (3 × 128 KiB).
- `~/Library/LaunchAgents/local.lg-monitor-recovery.plist`: login startup.

Requires the existing Homebrew Python at `/opt/homebrew/bin/python3` and macOS 13+.
There is no network access or telemetry in the helper or menu app.
The installed menu app is locally ad-hoc signed.

The m1ddc code is derived from https://github.com/waydabber/m1ddc,
commit `04d949794102eb8df01ad3681afff6464a3eede2`, under the MIT license in
`source/LICENSE`. Local changes validate the returned VCP feature and checksum,
allow 50 ms communication delays, and expose read-only display status.

## Validation

Run `python3 -m unittest -v test_recovery.py test_wake.py` from this folder.
Run `python3 recovery.py --probe` for a read-only live status check.

The user confirmed the prototype restored the image after a physical power cycle.
The first installed version incorrectly skipped subsequent cycles for 60 seconds;
that restriction was removed and a regression test added. The user then confirmed
two successive cycles recovered, but suspected mouse movement was needed. After
extending the explicit display-awake assertion to ten seconds, the user confirmed
a recovery returned the picture with no mouse or keyboard input.
The original eight regression tests passed; additional tests now cover multiple
displays, manual recovery, and cancellation during the final recheck. The user
also confirmed that the faster polling and
adaptive wake timing reduced the time for the picture to return without mouse input.
Native Settings controls were visually inspected;
pausing stopped the worker, resuming restarted it, and the login toggle removed
and recreated its LaunchAgent file. Automatic recovery and login startup were left
enabled. Physical results are separate from unit tests and driver command success.

Version 1.4 passes all 15 regression tests. With two LG monitors connected, manual
recovery completed, automatic monitoring resumed, and the user confirmed both
screens showed a picture. Automatic recovery after a physical power cycle with
both monitors connected still needs confirmation.

Version 1.4.2 keeps the menu below the menu bar icon and closes it when the icon
is clicked again. The owner confirmed both placement and dismissal work.

## Disable or remove

For a pause, uncheck Automatic Recovery in the menu. To disable across logins,
also uncheck Start at Login, then Quit. For removal, do those steps first, then
move the app and this support folder to Trash. Logs can also be moved to Trash.
