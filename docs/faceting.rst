.. _ref-faceting:

========
Faceting
========

What Is Faceting?
-----------------

Faceting is a way to provide users with feedback about the number of documents
which match terms they may be interested in. At its simplest, it gives
document counts based on words in the corpus, date ranges, numeric ranges or
even advanced queries.

Faceting is particularly useful when trying to provide users with drill-down
capabilities. The general workflow in this regard is:

  #. You can choose what you want to facet on.
  #. The search engine will return the counts it sees for that match.
  #. You display those counts to the user and provide them with a link.
  #. When the user chooses a link, you narrow the search query to only include
     those conditions and display the results, potentially with further facets.

.. note::

    Faceting can be difficult, especially in providing the user with the right
    number of options and/or the right areas to be able to drill into. This
    is unique to every situation and demands following what real users need.
    
    You may want to consider logging queries and looking at popular terms to
    help you narrow down how you can help your users.

Haystack provides functionality so that all of the above steps are possible.
From the ground up, let's build a faceted search setup. This assumes that you 
have been to work through the :doc:`tutorial` and have a working Haystack
installation. The same setup from the :doc:`tutorial` applies here.

1. Determine Facets And ``SearchQuerySet``
------------------------------------------

Determining what you want to facet on isn't always easy. For our purposes,
we'll facet on the ``author`` field.

In order to facet effectively, the search engine should store both a standard
representation of your data as well as exact version to facet on. This is
generally accomplished by duplicating the field and storing it via two
different types. Duplication is suggested so that those fields are still
searchable in the standard ways.

To inform Haystack of this, you simply pass along a ``faceted=True`` parameter
on the field(s) you wish to facet on. So to modify our existing example::

    class NoteIndex(SearchIndex, indexes.Indexable):
        text = CharField(document=True, use_template=True)
        author = CharField(model_attr='user', faceted=True)
        pub_date = DateTimeField(model_attr='pub_date')

Haystack quietly handles all of the backend details for you, creating a similar
field to the type you specified with ``_exact`` appended. Our example would now
have both a ``author`` and ``author_exact`` field, though this is largely an
implementation detail.

To pull faceting information out of the index, we'll use the
``SearchQuerySet.facet`` method to setup the facet and the
``SearchQuerySet.facet_counts`` method to retrieve back the counts seen.

Experimenting in a shell (``./manage.py shell``) is a good way to get a feel
for what various facets might look like::

    >>> from haystack.query import SearchQuerySet
    >>> sqs = SearchQuerySet().facet('author')
    >>> sqs.facet_counts()
    {
        'dates': {},
        'fields': {
            'author': [
                ('john', 4),
                ('daniel', 2),
                ('sally', 1),
                ('terry', 1),
            ],
        },
        'queries': {}
    }

.. note::

    Note that, despite the duplication of fields, you should provide the
    regular name of the field when faceting. Haystack will intelligently
    handle the underlying details and mapping.

As you can see, we get back a dictionary which provides access to the three
types of facets available: ``fields``, ``dates`` and ``queries``. Since we only
faceted on the ``author`` field (which actually facets on the ``author_exact``
field managed by Haystack), only the ``fields`` key has any data
associated with it. In this case, we have a corpus of eight documents with four
unique authors.

.. note::
    Facets are chainable, like most ``SearchQuerySet`` methods. However, unlike
    most ``SearchQuerySet`` methods, they are *NOT* affected by ``filter`` or
    similar methods. The only method that has any effect on facets is the
    ``narrow`` method (which is how you provide drill-down).

Configuring facet behaviour
~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can configure the behaviour of your facets by passing options
for each facet in your SearchQuerySet. These options can be backend specific.

**limit**
*tested on Solr*

The ``limit`` parameter limits the results for each query. On Solr, the default `facet.limit`_ is 100 and a
negative number removes the limit.

.. _facet.limit: https://wiki.apache.org/solr/SimpleFacetParameters#facet.limit

Example usage::

    >>> from haystack.query import SearchQuerySet
    >>> sqs = SearchQuerySet().facet('author', limit=-1)
    >>> sqs.facet_counts()
    {
        'dates': {},
        'fields': {
            'author': [
                ('abraham', 1),
                ('benny', 2),
                ('cindy', 1),
                ('diana', 5),
            ],
        },
        'queries': {}
    }

    >>> sqs = SearchQuerySet().facet('author', limit=2)
    >>> sqs.facet_counts()
    {
        'dates': {},
        'fields': {
            'author': [
                ('abraham', 1),
                ('benny', 2),
            ],
        },
        'queries': {}
    }

**sort**
*tested on Solr*

The ``sort`` parameter will sort the results for each query. Solr's default
`facet.sort`_ is ``index``, which will sort the facets alphabetically. Changing
the parameter to ``count`` will sort the facets by the number of results for
each facet value.

.. _facet.sort: https://wiki.apache.org/solr/SimpleFacetParameters#facet.sort


Example usage::

    >>> from haystack.query import SearchQuerySet
    >>> sqs = SearchQuerySet().facet('author', sort='index', )
    >>> sqs.facet_counts()
    {
        'dates': {},
        'fields': {
            'author': [
                ('abraham', 1),
                ('benny', 2),
                ('cindy', 1),
                ('diana', 5),
            ],
        },
        'queries': {}
    }

    >>> sqs = SearchQuerySet().facet('author', sort='count', )
    >>> sqs.facet_counts()
    {
        'dates': {},
        'fields': {
            'author': [
                ('diana', 5),
                ('benny', 2),
                ('abraham', 1),
                ('cindy', 1),
            ],
        },
        'queries': {}
    }


Now that we have the facet we want, it's time to implement it.

2. Switch to the ``FacetedSearchView`` and ``FacetedSearchForm``
----------------------------------------------------------------

There are three things that we'll need to do to expose facets to our frontend.
The first is construct the ``SearchQuerySet`` we want to use. We should have
that from the previous step. The second is to switch to the
``FacetedSearchView``. This view is useful because it prepares the facet counts
and provides them in the context as ``facets``.

Optionally, the third step is to switch to the ``FacetedSearchForm``. As it
currently stands, this is only useful if you want to provide drill-down, though
it may provide more functionality in the future. We'll do it for the sake of
having it in place but know that it's not required.

In your URLconf, you'll need to switch to the ``FacetedSearchView``. Your
URLconf should resemble::

    from django.conf.urls import url
    from haystack.forms import FacetedSearchForm
    from haystack.views import FacetedSearchView
    
    
    urlpatterns = [
        url(r'^$', FacetedSearchView(form_class=FacetedSearchForm, facet_fields=['author']), name='haystack_search'),
    ]

The ``FacetedSearchView`` will now instantiate the ``FacetedSearchForm``.
The specified ``facet_fields`` will be present in the context variable
``facets``. This is added in an overridden ``extra_context`` method.


3. Display The Facets In The Template
-------------------------------------

Templating facets involves simply adding an extra bit of processing to display
the facets (and optionally to link to provide drill-down). An example template
might look like this::

    <form method="get" action=".">
        <table>
            <tbody>
                {{ form.as_table }}
                <tr>
                    <td>&nbsp;</td>
                    <td><input type="submit" value="Search"></td>
                </tr>
            </tbody>
        </table>
    </form>
    
    {% if query %}
        <!-- Begin faceting. -->
        <h2>By Author</h2>
    
        <div>
            <dl>
                {% if facets.fields.author %}
                    <dt>Author</dt>
                    {# Provide only the top 5 authors #}
                    {% for author in facets.fields.author|slice:":5" %}
                        <dd><a href="{{ request.get_full_path }}&amp;selected_facets=author_exact:{{ author.0|urlencode }}">{{ author.0 }}</a> ({{ author.1 }})</dd>
                    {% endfor %}
                {% else %}
                    <p>No author facets.</p>
                {% endif %}
            </dl>
        </div>
        <!-- End faceting -->
    
        <!-- Display results... -->
        {% for result in page.object_list %}
            <div class="search_result">
                <h3><a href="{{ result.object.get_absolute_url }}">{{ result.object.title }}</a></h3>
            
                <p>{{ result.object.body|truncatewords:80 }}</p>
            </div>
        {% empty %}
            <p>Sorry, no results found.</p>
        {% endfor %}
    {% endif %}

Displaying the facets is a matter of looping through the facets you want and
providing the UI to suit. The ``author.0`` is the facet text from the backend
and the ``author.1`` is the facet count.

4. Narrowing The Search
-----------------------

We've also set ourselves up for the last bit, the drill-down aspect. By
appending on the ``selected_facets`` to the URLs, we're informing the
``FacetedSearchForm`` that we want to narrow our results to only those
containing the author we provided.

For a concrete example, if the facets on author come back as::

    {
        'dates': {},
        'fields': {
            'author': [
                ('john', 4),
                ('daniel', 2),
                ('sally', 1),
                ('terry', 1),
            ],
        },
        'queries': {}
    }

You should present a list similar to::

    <ul>
        <li><a href="/search/?q=Haystack&selected_facets=author_exact:john">john</a> (4)</li>
        <li><a href="/search/?q=Haystack&selected_facets=author_exact:daniel">daniel</a> (2)</li>
        <li><a href="/search/?q=Haystack&selected_facets=author_exact:sally">sally</a> (1)</li>
        <li><a href="/search/?q=Haystack&selected_facets=author_exact:terry">terry</a> (1)</li>
    </ul>

.. warning::

    Haystack can automatically handle most details around faceting. However,
    since ``selected_facets`` is passed directly to narrow, it must use the
    duplicated field name. Improvements to this are planned but incomplete.

This is simply the default behavior but it is possible to override or provide
your own form which does additional processing. You could also write your own
faceted ``SearchView``, which could provide additional/different facets based
on facets chosen. There is a wide range of possibilities available to help the
user navigate your content.
