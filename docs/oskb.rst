Using the on-screen keyboard
============================

To start using the keyboard, simply enter ``oskb``. There are many settings you can tweak, but the default should present you with a keyboard that covers the lower one-third of your primary display. The default keyboard will be a familiar keyboard layout. On startup, oskb will attempt to load a keyboard that uses the same keyboard mapping that is already set on the computer. So if you have a german keyboard configured, it will show a german keyboard. If no built-in keyboard for your keyboard setting is provided with oskb, a US keyboard will be shown, and the X-Windows keyboard settings adjusted accordingly.

.. note::  If you have a very narrow display of less than 600 pixels wide, oskb will default to a phone layout instead of a computer keyboard layout.

Command line options
--------------------

.. argparse::
   :module: oskb.cli
   :func: command_line_arguments
   :prog: oskb
   :nodefaultconst: