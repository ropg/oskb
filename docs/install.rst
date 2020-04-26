Installation
------------

The latest version can be downloaded from PyPI_. oskb needs Python3. Development and issue reporting happens at the oskb github_ repository.

.. code-block:: bash

    pip install oskb

In order to work, oskb needs to plug a virtual keyboard into your machine. Generally the user account that you use X-Windows with is not allowed to do this. If you want to make your own keyboards (using `oskbedit`), you must also allow your user account to listen to the system keyboard if you want to use the `Key Wizard` function of oskbedit. To test oskb and oskbedit, do:

.. code-block:: bash

    USER=`whoami`; sudo setfacl -m m::rw -m u:$USER:rw /dev/uinput /dev/input/*

This will allow you to test all the functionality of oskb and oskbedit. But the effect of these statements will disappear once you reboot. To make this permanent, add a line to your system crontab like this:

.. code-block:: bash

    USER=`whoami`
    CMD="@reboot root (sleep3; setfacl -m m::rw -m u:$USER:rw /dev/uinput /dev/input/*) &"
    echo $CMD | sudo tee -a /etc/crontab

.. _PyPI:              https://pypi.python.org/pypi/oskb
.. _github:            https://github.com/ropg/oskb