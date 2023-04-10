.. _hw-test:


Test it
=======

Some of these tests have already been mentioned. This page collects them all in order do have a good testing framework for each DDH.


crontab
-------

Check crontab is enabled, in case you wish it to be.

.. code:: bash

    $ sudo cat /etc/crontab


juice4halt
----------

In your final DDH, just press the power button and wait for DDH to switch off. If the juice4halt has worked as expected, the file ``/home/pi/juice4halt/bin/j4h_halt_flag`` should be present upon restart. Delete it to repeat the test. In case of failure, check:

.. code:: bash

    $ systemctl status rc.local
    $ ps -aux | grep shutdown


buttons
-------

Go the DDH source folder and run:

.. code:: bash

    $ python3 scripts/check_buttons.py


GPS
---

Go to DDH source folder and run:

.. code:: bash

    $ python3 scripts/check_gps_quectel.py


cell shield
-----------

Confirm cell shield is detected and installed by:

.. code:: bash

    $ ifconfig | grep ppp0

You can check which interface is being used for Internet access by doing:

.. code:: bash

    $ ip route get 8.8.8.8

You can change such interface to wi-fi by setting a lower ppp0 priority with a higher metric.

.. code:: bash

    $ sudo ifmetric ppp0 400

Instead, you can change such interface to cell by setting a higher ppp0 priority, thus a lower metric.

.. code:: bash

    $ sudo ifmetric ppp0 0


IP raspberries
--------------

Raspberries have avahi installed. Connect to whatever wi-fi they currently are and do:

.. code:: bash

    $ ping ddh_1234567.local

Replace 1234567 with the raspberry Lowell serial number.
