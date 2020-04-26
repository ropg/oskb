oskbedit
--------

``oskbedit`` allows you to intuitively create new keyboard layouts or change existing ones. Simply open any of the built-in keyboards, modify it and save a single file that holds keyboard layout(s), complete with information on how keys should appear (size, CSS classes, stylesheet, different captions) and what it should do (single press, double press or press and hold to switch to different view, output keycode(s), be a modifier, etc)

Command line options
====================

.. argparse::
   :module: oskb.oskbedit
   :func: command_line_arguments
   :prog: oskbedit
   :nodefaultconst: