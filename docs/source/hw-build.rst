.. _hw-build:


Build it
========

DDH come already built prepared. This procedure is just for information purposes.

- [D] do in desktop computer
- [R] do in raspberry (DDH)

[D] Clone a SSD disk from any good DDH you already have.

.. warning::

    Do NOT clone a Rpi3 from a Rpi4 or vice-versa.

[R] Set time & timezone.

.. warning::

    When asked to, use DDH power button to reboot, not ``reboot`` command.

[R] Obtain the repository with tools to install DDH.

.. code:: bash

    $ git clone https://github.com/lowellinstruments/ddh_tools.git

[R] You may need this before installing the cell shield:

.. code:: bash

    $ wget https://project-downloads.drogon.net/wiringpi-latest.deb
    $ sudo dpkg -i wiringpi-latest.deb

[R] Run the files inside the `ddh_tools` folder.

[R] For the cell shield installer:

- Select `hat` as in `6: 3G/4G Base HAT`.
- Set carrier as `wireless.twilio.com`, it `does NOT need a user and password`.
- Set port as `ttyUSB3`. Type it, do not just accept.
- Say YES to enable `auto connect/reconnect service at R.Pi boot up?`.

.. warning::

    For Twilio SIM cards, ensure them in 'Ready' state. The 'New' state is not enough.


[R] Check cell works by:

.. code:: bash

    $ ifconfig | grep ppp0

[R] Test the ``juice4halt`` by just switching off the DDH with the power button. Boot and see the J4H script is running by:

.. code:: bash

    $ systemctl status rc-local (enable in case it is not)
    $ ps -aux | grep shutdown
