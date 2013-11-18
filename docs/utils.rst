.. _ref-utils:

=========
Utilities
=========

Included here are some of the general use bits included with Haystack.


``get_identifier``
------------------

.. function:: get_identifier(obj_or_string)

Gets an unique identifier for the object or a string representing the
object.

If not overridden, uses ``<app_label>.<object_name>.<pk>``.
