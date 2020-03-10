Documentation for ``oskb``
==========================

   ...   the On-Screen KeyBoard
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^


Introduction
------------

I started writing oskb because really good on-screen keyboards for Linux seemed to be missing. I was playing around with embedded Linux boards and small touch screens and found that the lack of a phone/tablet quality keyboard was a limiting factor. Because oskb is written in Python and uses Qt, parts of it can already be used on different operating systems. At the time of writing this, oskb consists of three parts:

* ``oskb`` is the command to start the keyboard. At this point, the keyboard will take up the lower 1/3 of the screen, show a us layout keyboard and switch the underlying X11 system to use a US key layout as well. Various command line options can be used to select a different keyboard, change where it shows on the screen and how the keyboard behaves.

* ``oskbedit`` allows you to intuitively create new keyboard layouts or change existing ones. Simply open any of the built-in keyboards, modify it and save a single file that holds keyboard layout(s), complete with information on how keys should appear (size, CSS classes, stylesheet, different captions) and what it should do (single press, double press or press and hold to switch to different view, output keycode(s), be a modifier, etc)

* Want to show a keyboard as part of your messaging app, embedded project or some other Qt project? ``oskb.Keyboard(QWidget)`` is a Qt ``QWidget`` that you can use in your own code. It shows a keyboard and can either handle the keypress events at various levels itself or be told what function should handle them externally. Both ``oskb`` and ``oskbedit`` rely on this widget, using it in different ways.

``oskb`` can be used to make virtual keyboards that behave very much like a physical computer keyboard as well as very complex keyboards that have many different views and clever shortcuts. The code to insert the keypresses into the operating system is pluggable, but presently only ``uinput`` for Linux is available. The ``oskbedit`` keyboard editor an be used anywhere where PyQt5 runs (Windows, MacOS, ...) but the 'Key Wizard' (to conveniently get keycode and key caption in one keypress) is presently Linux-only.

Installation
------------

The latest version can be downloaded from PyPI_. oskb needs Python3. Development and issue reporting happens at the oskb github_ repository. 

.. code-block:: bash

    $ pip install oskb
    
License
-------

This package is released under the terms of the `BSD License`_.

.. _`BSD License`: https://raw.github.com/ropg/oskb/master/LICENSE



.. _PyPI:              https://pypi.python.org/pypi/oskb
.. _github:            https://github.com/ropg/oskb
