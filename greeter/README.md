# Yozora boot login

This is an optional greetd interface. It uses the same Classic/Mainframe QML
presentation files as the desktop session lock, with a separate greetd backend.
It does not auto-login, load the user's desktop configuration, or change PAM.

On a system with greetd, its `greeter` account, and the rice's core dependencies:

```sh
./install.sh greeter-install --dry-run
./install.sh greeter-install
./install.sh greeter-check
```

Installation renders both designs offscreen and verifies the isolated Hyprland
configuration before requesting sudo for system files. It preserves the original
greetd config and never restarts the running login manager. The next boot
uses Yozora; the already-running greetd process may retain its previous command
until restarted. Noctalia remains installed for rollback. If the graphical greeter
fails before session handoff, the wrapper falls back to the installed `agreety`.

Both the greeter and desktop use `start-hyprland` with its watchdog. Desktop
startup output goes to the journal instead of drawing a logo and logs on the
login console. To inspect it, run `journalctl -b -t yozora-hyprland`. This applies
to the text-login fallback too. The greeter's custom config is passed after `--`
so the launcher does not accidentally load a default configuration.

At normal motion speed, Mainframe opens over 2.2 seconds and closes over 1.4
seconds. Classic uses a one-second entrance and exit. The final black fade is
at the end of Mainframe's CRT collapse, rather than hiding the animation as soon
as authentication succeeds. Reduced motion removes these delays. Login does not
play the session unlock's wallpaper reveal. The desktop launcher prepares the saved
wallpaper before loading QuickShell, without rebuilding colours or scanning the
wallpaper library first. A compositor replacement can still cause a brief display
handoff; this does not provide a seamless transfer of frames between compositors.

Aquamarine 0.15.1 can crash in `flushAsyncCommitEvents` during compositor
shutdown; this has been observed on this system's greeter and is reported in
[upstream issue 383](https://github.com/hyprwm/aquamarine/issues/383). Slower login
animation does not repair that library bug or hide the time needed to start the
desktop compositor. Keep diagnosis separate from appearance changes; this setup
does not patch system libraries or disable crash reporting.

The installer deploys root-owned code to `/usr/local/share/yozora-greeter` and
appearance data to `/var/lib/yozora-greeter`. The configured desktop user can
publish only into their appearance directory; they gain no privileged helper.
The selected design, clock, colours, wallpaper and avatar follow Settings →
Session automatically. Published images are intentionally readable before login.
Private settings, history, passwords and desktop screenshots are not exported.
An animated wallpaper publishes its still poster. Missing data uses Classic.

After enabling, deploy the repository's QuickShell changes using the normal
config updater, then reload that installed shell. The exporter publishes at
startup and coalesces later changes. `greeter-check` reports a missing snapshot.
Root-owned greeter presentation code is refreshed by rerunning `greeter-install`
after updating the rice; appearance changes need no sudo or reinstall.

To restore the previous boot login without ending the current session:

```sh
./install.sh greeter-uninstall
```

This restores the saved greetd configuration and preserves code/appearance
backups. It refuses to overwrite a login command edited outside Yozora. The
ordinary config uninstaller does not alter system login integration; remove the
greeter explicitly first if you want the previous login interface back.

Recovery from another TTY, if needed:

```sh
cd /path/to/DotFiles
./install.sh greeter-uninstall
```

The restore does not need a running graphical shell. No automatic reboot is
performed; real boot authentication must be checked through an actual login.
