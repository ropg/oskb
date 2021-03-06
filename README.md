# oskb - On-Screen Keyboard

### (Python & PyQt, Linux-only at the moment)

![](images/oskb-screenshots.png)

## Introduction

I was working on a handheld Linux project and much disliked the on-screen keyboards for Linux I tried. So I wrote a new one. Good way to learn Qt and get a little bit more experience in Python. It's all somewhat preliminary, please test and file issues with comments and feature requests.

## Instructions:

* You'll need python3, there are no oskb packages for your Linux distro yet. It's all very fresh.

* `pip3 install oskb` to use the version from PyPI.

* oskb does not hand its keypresses to X11 but to the underlying Linux kernel. (This is pluggable, it's just the only inputmethod currently supported). This means it will in future also work without X11, for instance when writing to the framebuffer directly. (Which is great for embedded devices.) What this also means is it needs to connect a virtual keyboard to your machine. The user you are logged in as is probably not allowed to do that. The easiest way to solve this if you want to test oskb is to type `sudo setfacl -m m::rw -m u:<username>:rw /dev/uinput`, replacing `<username>` with your username. This gives the user you use X with permission to plug in the oskb virtual keyboard.

* Now run `oskb` to use the keyboard and see if you like it. There is presently only a phone-like layout, which is a bit too sparse for a large portrait-oriented display. You may want to run `oskb --width 480` to get a better feel for what the present default layout should look like. There will be pad-like keyboards and full-size keyboards available soon.

* Full documentation, screenshots, it is all coming. This is alpha software, all typed in very very recently. Try `oskb --help` for some command line options that might be of help.

* It's written to be embedded. Have a look at cli.py to see how oskb gives you a QWidget that you can do with whatever you want. You can also send the keypresses to your own functions, that will be documented later.

* Do try `oskb phoney-us phoney-de --width 480 --center --start minimized` and then pressing and holding one of the keys with blue symbols on them... 

* The change to /dev/uinput does not stick, so lacking proper Linux packages for the various distributions, you might want to add `@reboot sleep 10 && setfacl -m m::rw -m u:<username>:rw /dev/uinput` at the beginning of root's crontab. (Again replacing `<username>` with your username.)

* Not happy with the layout? Try entering `oskbedit phoney-us`. This editor comes with a Key Wizard feature to read the keycodes for keys directly from the keyboard. For that to work, you need to allow access to your keyboard. Enter `oskbedit --inputlist` and follow instructions. Then, assuming your keyboard is at `/dev/input/event2`, try typing `oskbedit --input /dev/input/event2 phoney-us` select a key and hit Ctrl-K. Things should be somewhat self-explanatory, but documentation will be done soon...

* It is possibly a bit early to use this for anything too serious. But progress has been happening fast, and it beats any of the exsting keyboards on small handheld touch-screens for me.

* Please tell me what you think.