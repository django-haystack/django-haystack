.. _ref-best-practices:

==============
Best Practices
==============

What follows are some general recommendations on how to improve your search.
Some tips represent performance benefits, some provide a better search index.
You should evaluate these options for yourself and pick the ones that will
work best for you. Not all situations are created equal and many of these
options could be considered mandatory in some cases and unnecessary premature
optimizations in others. Your mileage may vary.


Good Search Needs Good Content
==============================

Most search engines work best when they're given corpuses with predominantly
text (as opposed to other data like dates, numbers, etc.) in decent quantities
(more than a couple words). This is in stark contrast to the databases most
people are used to, which rely heavily on non-text data to create relationships
and for ease of querying.

To this end, if search is important to you, you should take the time to
carefully craft your ``SearchIndex`` subclasses to give the search engine the
best information you can. This isn't necessarily hard but is worth the
investment of time and thought. Assuming you've only ever used the
``BasicSearchIndex``, in creating custom ``SearchIndex`` classes, there are
some easy improvements to make that will make your search better:

* For your ``document=True`` field, use a well-constructed template.
* Add fields for data you might want to be able to filter by.
* If the model has related data, you can squash good content from those
  related models into the parent model's ``SearchIndex``.
* Similarly, if you have heavily de-normalized models, it may be best
  represented by a single indexed model rather than many indexed models.

Well-Constructed Templates
--------------------------

A relatively unique concept in Haystack is the use of templates associated with
``SearchIndex`` fields. These are data templates, will never been seen by users
and ideally contain no HTML. They are used to collect various data from the
model and structure it as a document for the search engine to analyze and index.

.. note::

    If you read nothing else, this is the single most important thing you can
    do to make search on your site better for your users. Good templates can
    make or break your search and providing the search engine with good content
    to index is critical.

Good templates structure the data well and incorporate as much pertinent text
as possible. This may include additional fields such as titles, author
information, metadata, tags/categories. Without being artificial, you want to
construct as much context as you can. This doesn't mean you should necessarily
include every field, but you should include fields that provide good content
or include terms you think your users may frequently search on.

Unless you have very unique numbers or dates, neither of these types of data
are a good fit within templates. They are usually better suited to other
fields for filtering within a ``SearchQuerySet``.

Additional Fields For Filtering
-------------------------------

Documents by themselves are good for generating indexes of content but are
generally poor for filtering content, for instance, by date. All search engines
supported by Haystack provide a means to associate extra data as
attributes/fields on a record. The database analogy would be adding extra
columns to the table for filtering.

Good candidates here are date fields, number fields, de-normalized data from
related objects, etc. You can expose these things to users in the form of a
calendar range to specify, an author to look up or only data from a certain
series of numbers to return.

You will need to plan ahead and anticipate what you might need to filter on,
though with each field you add, you increase storage space usage. It's generally
**NOT** recommended to include every field from a model, just ones you are
likely to use.

Related Data
------------

Related data is somewhat problematic to deal with, as most search engines are
better with documents than they are with relationships. One way to approach this
is to de-normalize a related child object or objects into the parent's document
template. The inclusion of a foreign key's relevant data or a simple Django
``{% for %}`` templatetag to iterate over the related objects can increase the
salient data in your document. Be careful what you include and how you structure
it, as this can have consequences on how well a result might rank in your
search.


Avoid Hitting The Database
==========================

A very easy but effective thing you can do to drastically reduce hits on the
database is to pre-render your search results using stored fields then disabling
the ``load_all`` aspect of your ``SearchView``.

.. warning::

    This technique may cause a substantial increase in the size of your index
    as you are basically using it as a storage mechanism.

To do this, you setup one or more stored fields (`indexed=False`) on your
``SearchIndex`` classes. You should specify a template for the field, filling it
with the data you'd want to display on your search results pages. When the model
attached to the ``SearchIndex`` is placed in the index, this template will get
rendered and stored in the index alongside the record.

.. note::

    The downside of this method is that the HTML for the result will be locked
    in once it is indexed. To make changes to the structure, you'd have to
    reindex all of your content. It also limits you to a single display of the
    content (though you could use multiple fields if that suits your needs).

The second aspect is customizing your ``SearchView`` and its templates. First,
pass the ``load_all=False`` to your ``SearchView``, ideally in your URLconf.
This prevents the ``SearchQuerySet`` from loading all models objects for results
ahead of time. Then, in your template, simply display the stored content from
your ``SearchIndex`` as the HTML result.

.. warning::

    To do this, you must absolutely avoid using ``{{ result.object }}`` or any
    further accesses beyond that. That call will hit the database, not only
    nullifying your work on lessening database hits, but actually making it
    worse as there will now be at least query for each result, up from a single
    query for each type of model with ``load_all=True``.


Content-Type Specific Templates
===============================

Frequently, when displaying results, you'll want to customize the HTML output
based on what model the result represents.

In practice, the best way to handle this is through the use of ``include``
along with the data on the ``SearchResult``.

Your existing loop might look something like::

    {% for result in page.object_list %}
        <p>
            <a href="{{ result.object.get_absolute_url }}">{{ result.object.title }}</a>
        </p>
    {% empty %}
        <p>No results found.</p>
    {% endfor %}

An improved version might look like::

    {% for result in page.object_list %}
        {% if result.content_type == "blog.post" %}
        {% include "search/includes/blog/post.html" %}
        {% endif %}
        {% if result.content_type == "media.photo" %}
        {% include "search/includes/media/photo.html" %}
        {% endif %}
    {% empty %}
        <p>No results found.</p>
    {% endfor %}

Those include files might look like::

    # search/includes/blog/post.html
    <div class="post_result">
        <h3><a href="{{ result.object.get_absolute_url }}">{{ result.object.title }}</a></h3>

        <p>{{ result.object.tease }}</p>
    </div>

    # search/includes/media/photo.html
    <div class="photo_result">
        <a href="{{ result.object.get_absolute_url }}">
        <img src="http://your.media.example.com/media/{{ result.object.photo.url }}"></a>
        <p>Taken By {{ result.object.taken_by }}</p>
    </div>

You can make this even better by standardizing on an includes layout, then
writing a template tag or filter that generates the include filename. Usage
might looks something like::

    {% for result in page.object_list %}
        {% with result|search_include as fragment %}
        {% include fragment %}
        {% endwith %}
    {% empty %}
        <p>No results found.</p>
    {% endfor %}


Real-Time Search
================

If your site sees heavy search traffic and up-to-date information is very
important, Haystack provides a way to constantly keep your index up to date.

You can enable the ``RealtimeSignalProcessor`` within your settings, which
will allow Haystack to automatically update the index whenever a model is
saved/deleted.

You can find more information within the :doc:`signal_processors` documentation.


Use Of A Queue For A Better User Experience
===========================================

By default, you have to manually reindex content, Haystack immediately tries to merge
it into the search index. If you have a write-heavy site, this could mean your
search engine may spend most of its time churning on constant merges. If you can
afford a small delay between when a model is saved and when it appears in the
search results, queuing these merges is a good idea.

You gain a snappier interface for users as updates go into a queue (a fast
operation) and then typical processing continues. You also get a lower churn
rate, as most search engines deal with batches of updates better than many
single updates. You can also use this to distribute load, as the queue consumer
could live on a completely separate server from your webservers, allowing you
to tune more efficiently.

Implementing this is relatively simple. There are two parts, creating a new
``QueuedSignalProcessor`` class and creating a queue processing script to
handle the actual updates.

For the ``QueuedSignalProcessor``, you should inherit from
``haystack.signals.BaseSignalProcessor``, then alter the ``setup/teardown``
methods to call an enqueuing method instead of directly calling
``handle_save/handle_delete``. For example::

    from haystack import signals


    class QueuedSignalProcessor(signals.BaseSignalProcessor):
        # Override the built-in.
        def setup(self):
            models.signals.post_save.connect(self.enqueue_save)
            models.signals.post_delete.connect(self.enqueue_delete)

        # Override the built-in.
        def teardown(self):
            models.signals.post_save.disconnect(self.enqueue_save)
            models.signals.post_delete.disconnect(self.enqueue_delete)

        # Add on a queuing method.
        def enqueue_save(self, sender, instance, **kwargs):
            # Push the save & information onto queue du jour here
            ...

        # Add on a queuing method.
        def enqueue_delete(self, sender, instance, **kwargs):
            # Push the delete & information onto queue du jour here
            ...

For the consumer, this is much more specific to the queue used and your desired
setup. At a minimum, you will need to periodically consume the queue, fetch the
correct index from the ``SearchSite`` for your application, load the model from
the message and pass that model to the ``update_object`` or ``remove_object``
methods on the ``SearchIndex``. Proper grouping, batching and intelligent
handling are all additional things that could be applied on top to further
improve performance.
