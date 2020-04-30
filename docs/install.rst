Installation
------------

To use oskb you will need ``python3`` and ``pip``, the python installer. Use the package manager to install these if they aren't on your system already. Then install the latest version of oskb from PyPI_ as follows: 

.. code-block:: bash

    pip install oskb

In order to work, oskb needs to plug a virtual keyboard into your machine. Generally the user account that you use X-Windows with is not allowed to do this. If you want to make your own keyboards (using `oskbedit`), you must also allow your user account to listen to the system keyboard if you want to use the `Key Wizard` function of oskbedit. To test oskb and oskbedit, do:

.. code-block:: bash

    USER=`whoami`; sudo setfacl -m m::rw -m u:$USER:rw /dev/uinput /dev/input/*

This will allow you to test all the functionality of oskb and oskbedit, but the effect of these statements will disappear once you reboot. To make this permanent, add a line to your system crontab like this:

.. code-block:: bash

    USER=`whoami`
    CMD="@reboot root (sleep 3; setfacl -m m::rw -m u:$USER:rw /dev/uinput /dev/input/*) &"
    echo $CMD | sudo tee -a /etc/crontab
    
.. note:: The above is needed because oskb plugs a virtual keyboard into the underlying Linux OS, other virtual keyboards may hand off the keystrokes to X-Windows only. The user shouldn't notice any difference one way or the other. The advantage of doing it this way is that the keyboard can also be used when there is no X-Windows, such as on embedded projects that write to the screen directly. The interface with the underlying OS is written as a plugin internally and the Qt framework that was used to make oskb runs on many platforms, so oskb might work on Windows or Macs in the future. Those both have excellent on-screen keyboards however, so that wasn't a priority.

.. _PyPI:              https://pypi.python.org/pypi/oskb
.. _github:            https://github.com/ropg/oskb