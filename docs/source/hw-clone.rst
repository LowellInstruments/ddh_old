.. _hw-clone:


Clone it
========

Prepare a DDH SSD with the instructions in :ref:`hw-build`. The rest of DDH will be cloned from it.


1st way to clone
----------------

In your desktop computer, connect the prepared SSD, it will assign ``/dev/sda`` to it and a blank one, which will be assigned as ``/dev/sdb``. Mind the order. Then:

.. code:: bash

    $ sudo dd if=/dev/sda of=/dev/sdb bs=4M status=progress


2nd way to clone
----------------

In your DDH, install rpi-clone from github.

.. code:: bash

    $ git clone https://github.com/billw2/rpi-clone.git
    $ cd rpi-clone
    $ sudo cp rpi-clone rpi-clone-setup /usr/local/sbin

In your DDH, connect another SSD to USB port and:

.. code:: bash

    $ rpi-clone sdb


First time ever you boot a newly cloned SSD you may find a blank screen. Just unplug the power. Wait 5 minutes (ensure the RPI red led is off) and try again.

So, now you have and original and one cloned DDH. You can proceed to section :ref:`hw-access`.


.. warning::

    Do NOT clone a Rpi3 from a Rpi4 or vice-versa.
