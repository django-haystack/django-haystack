.. _ref-signal_processors:

=================
Signal Processors
=================

Keeping data in sync between the (authoritative) database & the
(non-authoritative) search index is one of the more difficult problems when
using Haystack. Even frequently running the ``update_index`` management command
still introduces lag between when the data is stored & when it's available
for searching.

A solution to this is to incorporate Django's signals (specifically
``models.db.signals.post_save`` & ``models.db.signals.post_delete``), which then
trigger *individual* updates to the search index, keeping them in near-perfect
sync.

Older versions of Haystack (pre-v2.0) tied the ``SearchIndex`` directly to the
signals, which caused occasional conflicts of interest with third-party
applications.

To solve this, starting with Haystack v2.0, the concept of a ``SignalProcessor``
has been introduced. In it's simplest form, the ``SignalProcessor`` listens
to whatever signals are setup & can be configured to then trigger the updates
without having to change any ``SearchIndex`` code.

.. warning::

    Incorporating Haystack's ``SignalProcessor`` into your setup **will**
    increase the overall load (CPU & perhaps I/O depending on configuration).
    You will need to capacity plan for this & ensure you can make the tradeoff
    of more real-time results for increased load.


Default - ``BaseSignalProcessor``
=================================

The default setup is configured to use the
``haystack.signals.BaseSignalProcessor`` class, which includes all the
underlying code necessary to handle individual updates/deletes, **BUT DOES NOT
HOOK UP THE SIGNALS**.

This means that, by default, **NO ACTION IS TAKEN BY HAYSTACK** when a model is
saved or deleted. The ``BaseSignalProcessor.setup`` &
``BaseSignalProcessor.teardown`` methods are both empty to prevent anything
from being setup at initialization time.

This usage is configured very simply (again, by default) with the
``HAYSTACK_SIGNAL_PROCESSOR`` setting. An example of manually setting this
would look like::

    HAYSTACK_SIGNAL_PROCESSOR = 'haystack.signals.BaseSignalProcessor'

This class forms an excellent base if you'd like to override/extend for more
advanced behavior. Which leads us to...


Realtime - ``RealtimeSignalProcessor``
======================================

The other included ``SignalProcessor`` is the
``haystack.signals.RealtimeSignalProcessor`` class. It is an extremely thin
extension of the ``BaseSignalProcessor`` class, differing only in that
in implements the ``setup/teardown`` methods, tying **ANY** Model
``save/delete`` to the signal processor.

If the model has an associated ``SearchIndex``, the ``RealtimeSignalProcessor``
will then trigger an update/delete of that model instance within the search
index proper.

Configuration looks like::

    HAYSTACK_SIGNAL_PROCESSOR = 'haystack.signals.RealtimeSignalProcessor'

This causes **all** ``SearchIndex`` classes to work in a realtime fashion.

.. note::

    These updates happen in-process, which if a request-response cycle is
    involved, may cause the user with the browser to sit & wait for indexing to
    be completed. Since this wait can be undesirable, especially under load,
    you may wish to look into queued search options. See the
    :ref:`ref-other_apps` documentation for existing options.


Custom ``SignalProcessors``
===========================

The ``BaseSignalProcessor`` & ``RealtimeSignalProcessor`` classes are fairly
simple/straightforward to customize or extend. Rather than forking Haystack to
implement your modifications, you should create your own subclass within your
codebase (anywhere that's importable is usually fine, though you should avoid
``models.py`` files).

For instance, if you only wanted ``User`` saves to be realtime, deferring all
other updates to the management commands, you'd implement the following code::

    from django.contrib.auth.models import User
    from django.db import models
    from haystack import signals


    class UserOnlySignalProcessor(signals.BaseSignalProcessor):
        def setup(self):
            # Listen only to the ``User`` model.
            models.signals.post_save.connect(self.handle_save, sender=User)
            models.signals.post_delete.connect(self.handle_delete, sender=User)

        def teardown(self):
            # Disconnect only for the ``User`` model.
            models.signals.post_save.disconnect(self.handle_save, sender=User)
            models.signals.post_delete.disconnect(self.handle_delete, sender=User)

For other customizations (modifying how saves/deletes should work), you'll need
to override/extend the ``handle_save/handle_delete`` methods. The source code
is your best option for referring to how things currently work on your version
of Haystack.
