.. Add new releases at the top to keep important stuff directly visible.

Release notes
=============

unreleased [2.x]
----------------

* The format of the influxdb pattern file is simplified. The procedure to
  edit patterns is also changed to modifying the pattern file and calling:
  ``artiq_rpctool.py ::1 3248 call scan_patterns`` (or restarting the bridge)
  The patterns can be converted to the new format using this code snippet::

    from artiq.protocols import pyon
    patterns = pyon.load_file("influxdb_patterns.pyon")
    for p in patterns:
        print(p)

* The "GUI" has been renamed the "dashboard".
* When flashing NIST boards, use "-m nist_qcX" or "-m nist_clock" instead of
  just "-m qcX" or "-m clock" (#290).
* Applet command lines now use templates (e.g. $python) instead of formats
  (e.g. {python}).
* On Windows, GUI applications no longer open a console. For debugging
  purposes, the console messages can still be displayed by running the GUI
  applications this way::

    python3.5 -m artiq.frontend.artiq_browser
    python3.5 -m artiq.frontend.artiq_dashboard

  (you may need to replace python3.5 with python)
  Please always include the console output when reporting a GUI crash.
* Closing the core device communications before pausing is done automatically.
  Experiments no longer need to do it explicitly.
* The result folders are formatted "%Y-%m-%d/%H instead of "%Y-%m-%d/%H-%M".
  (i.e. grouping by day and then by hour, instead of by day and then by minute)
* GUI tools save their state file in the user's home directory instead of the
  current directory.
* The ``parent`` keyword argument of ``HasEnvironment`` (and ``EnvExperiment``)
  has been replaced. Pass the parent as first argument instead.
* In the dashboard's experiment windows, partial or full argument recomputation
  takes into account the repository revision field.
* By default, ``NumberValue`` and ``Scannable`` infer the scale from the unit
  for common units.


1.1 (unreleased)
----------------

* TCA6424A.set converts the "outputs" value to little-endian before programming
  it into the registers.


1.0
---

No further notes.


1.0rc4
------

* setattr_argument and setattr_device add their key to kernel_invariants.


1.0rc3
------

* The HDF5 format has changed.

  * The datasets are located in the HDF5 subgroup ``datasets``.
  * Datasets are now stored without additional type conversions and annotations
    from ARTIQ, trusting that h5py maps and converts types between HDF5 and
    python/numpy "as expected".

* NumberValue now returns an integer if ``ndecimals`` = 0, ``scale`` = 1 and
  ``step`` is integer.


1.0rc2
------

* The CPU speed in the pipistrello gateware has been reduced from 83 1/3 MHz to
  75 MHz. This will reduce the achievable sustained pulse rate and latency
  accordingly. ISE was intermittently failing to meet timing (#341).
* set_dataset in broadcast mode no longer returns a Notifier. Mutating datasets
  should be done with mutate_dataset instead (#345).


1.0rc1
------

* Experiments (your code) should use ``from artiq.experiment import *``
  (and not ``from artiq import *`` as previously)
* Core device flash storage has moved due to increased runtime size.
  This requires reflashing the runtime and the flash storage filesystem image
  or erase and rewrite its entries.
* ``RTIOCollisionError`` has been renamed to ``RTIOCollision``
* the new API for DDS batches is::

    with self.core_dds.batch:
       ...

  with ``core_dds`` a device of type ``artiq.coredevice.dds.CoreDDS``.
  The dds_bus device should not be used anymore.
* LinearScan now supports scanning from high to low. Accordingly,
  its arguments ``min/max`` have been renamed to ``start/stop`` respectively.
  Same for RandomScan (even though there direction matters little).
