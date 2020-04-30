oskb - the on-screen keyboard
-----------------------------

``oskb`` will let you type on a touch screen. It will plug a virtual keyboard into the Linux operating system and show a keyboard on the screen. It comes with a set of layouts for different countries, both in full format as well as a smartphone format. There is also an editor to make your own keyboard layouts, and an API to use the keyboard functionality as part of your own Python Qt projects.

This project came about as I was playing around with regular Linux distributions on embedded Linux boards and small touch screens and found the lack of a phone/tablet quality keyboard to be a limiting factor. Because oskb is written in Python and uses Qt, parts of it can already be used on different operating systems. And because it plugs in a virtual keyboard into the underlying Linux OS, it should also be useful for embedded projects that do not use X-Windows. 


.. toctree::
    :maxdepth: 2

    install
    oskb
    oskbedit
    api

License
-------

This package is released under the terms of the `BSD License`_.

.. _`BSD License`: https://raw.github.com/ropg/oskb/master/LICENSE
