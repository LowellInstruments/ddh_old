.. _hw-access:


Access it
=========

Download `dwagent.sh`, in the ``/home/pi/Downloads`` folder if you have not until now. This allows to access DDH worldwide. But first, let's configure SSH.

You will need to connect once via SSH to this DDH in order to add it to your known SSH hosts file. Next, you can automate tasks on it with tools like ``parallel-ssh``. The ``phosts.txt`` file has one line entries in the format ``pi@X.X.X.X``.

If you set SSH public key authentication, you can use ``parallel-ssh`` as follows. The -i flag means display std output and std error as execution of the command on each server complete.

.. code:: bash

    $ parallel-ssh -h phosts.txt -i "uptime"

If you did not set SSH public key authentication, you can use ``parallel-ssh`` as follows. The -A flag asks for a password. The -P flag prints immediately. You can also try -i flag.

.. code:: bash

    $ parallel-ssh -h phosts.txt -A -P "uptime"

Finally, install DWService. If you cloned this DDH from an existing one, run the 2 lines next. Otherwise, you only need to run the second one:

.. code:: bash

    $ sudo ./dwagent.sh uninstall
    $ sudo ./dwagent.sh -silent user=<YOUR_USER@HERE> password=<YOUR_PASS_HERE> name=<DDH_UNIQUE_SERIAL_NAME_HERE>

And should appear in your DWService Agents page.

.. note::

    Your DDH already has cell-network features enabled, so be careful with data usage, if any request to Internet is done. The data usage for 24 hours when only DWService is active and no other network activity on the DDH was measured to be 0.450 MB down, 0.291 MB up, so less than 1 MB per day.

.. warning::

    Recall removing your wi-fi networks from the cloned DDH, if so.
