# oskb

On-Screen keyboard for Linux, written in python with qt

Screenshots, more documentation, all will show up soon. Consider this a very early alpha, although the keyboard works for me.

## Instructions:

* pip3 install oskb (to use the version from PyPI)

* If you want the keyboard to not only show up on the screen but actually put the keys you type into your kernel, you'll need to run a small daemon as root. This dameon is called oskbdaemon and is wherever pip placed the scripts. This might be in ~/.local/bin if you did not run pip as root. Assuming this is the case, run `sudo -H .local/bin/oskbdaemon --user <your_username>` from your home directory, replacing <your_username> with the username you want to give the right to stick keypresses into the kernel using this daemon.

* Now run `oskb` to use the keyboard.

## Tips

* Since the current default keyboard is a phone layout meant for small portrait screens, you might get a better feel for it if you type `oskb --width 480`

* `oskb --off` turns the keyboard off again

* `oskb -h` gives you a list of command line options

* Try `oskb phoney-us phoney-de` and long-pressing the '123/ABC' key on the bottom left.