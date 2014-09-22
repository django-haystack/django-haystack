.. _ref-autocomplete:

============
Autocomplete
============

Autocomplete is becoming increasingly common as an add-on to search. Haystack
makes it relatively simple to implement. There are two steps in the process,
one to prepare the data and one to implement the actual search.

Step 1. Setup The Data
======================

To do autocomplete effectively, the search backend uses n-grams (essentially
a small window passed over the string). Because this alters the way your
data needs to be stored, the best approach is to add a new field to your
``SearchIndex`` that contains the text you want to autocomplete on.

You have two choices: ``NgramField`` and ``EdgeNgramField``. Though very similar,
the choice of field is somewhat important.

* If you're working with standard text, ``EdgeNgramField`` tokenizes on
  whitespace. This prevents incorrect matches when part of two different words
  are mashed together as one n-gram. **This is what most users should use.**
* If you're working with Asian languages or want to be able to autocomplete
  across word boundaries, ``NgramField`` should be what you use.

Example (continuing from the tutorial)::

    import datetime
    from haystack import indexes
    from myapp.models import Note


    class NoteIndex(indexes.SearchIndex, indexes.Indexable):
        text = indexes.CharField(document=True, use_template=True)
        author = indexes.CharField(model_attr='user')
        pub_date = indexes.DateTimeField(model_attr='pub_date')
        # We add this for autocomplete.
        content_auto = indexes.EdgeNgramField(model_attr='content')

        def get_model(self):
            return Note

        def index_queryset(self, using=None):
            """Used when the entire index for model is updated."""
            return Note.objects.filter(pub_date__lte=datetime.datetime.now())

As with all schema changes, you'll need to rebuild/update your index after
making this change.


Step 2. Performing The Query
============================

Haystack ships with a convenience method to perform most autocomplete searches.
You simply provide a field and the query you wish to search on to the
``SearchQuerySet.autocomplete`` method. Given the previous example, an example
search would look like::

    from haystack.query import SearchQuerySet

    SearchQuerySet().autocomplete(content_auto='old')
    # Result match things like 'goldfish', 'cuckold' and 'older'.

The results from the ``SearchQuerySet.autocomplete`` method are full search
results, just like any regular filter.

If you need more control over your results, you can use standard
``SearchQuerySet.filter`` calls. For instance::

    from haystack.query import SearchQuerySet

    sqs = SearchQuerySet().filter(content_auto=request.GET.get('q', ''))

This can also be extended to use ``SQ`` for more complex queries (and is what's
being done under the hood in the ``SearchQuerySet.autocomplete`` method).


Example Implementation
======================

The above is the low-level backend portion of how you implement autocomplete.
To make it work in browser, you need both a view to run the autocomplete
and some Javascript to fetch the results.

Since it comes up often, here is an example implementation of those things.

.. warning::

    This code comes with no warranty. Don't ask for support on it. If you
    copy-paste it and it burns down your server room, I'm not liable for any
    of it.

    It worked this one time on my machine in a simulated environment.

    And yeah, semicolon-less + 2 space + comma-first. Deal with it.

A stripped-down view might look like::

    # views.py
    import simplejson as json
    from django.http import HttpResponse
    from haystack.query import SearchQuerySet


    def autocomplete(request):
        sqs = SearchQuerySet().autocomplete(content_auto=request.GET.get('q', ''))[:5]
        suggestions = [result.title for result in sqs]
        # Make sure you return a JSON object, not a bare list.
        # Otherwise, you could be vulnerable to an XSS attack.
        the_data = json.dumps({
            'results': suggestions
        })
        return HttpResponse(the_data, content_type='application/json')

The template might look like::

    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <title>Autocomplete Example</title>
    </head>
    <body>
      <h1>Autocomplete Example</h1>

      <form method="post" action="/search/" class="autocomplete-me">
        <input type="text" id="id_q" name="q">
        <input type="submit" value="Search!">
      </form>

      <script src="http://ajax.googleapis.com/ajax/libs/jquery/1.8.3/jquery.min.js"></script>
      <script type="text/javascript">
        // In a perfect world, this would be its own library file that got included
        // on the page and only the ``$(document).ready(...)`` below would be present.
        // But this is an example.
        var Autocomplete = function(options) {
          this.form_selector = options.form_selector
          this.url = options.url || '/search/autocomplete/'
          this.delay = parseInt(options.delay || 300)
          this.minimum_length = parseInt(options.minimum_length || 3)
          this.form_elem = null
          this.query_box = null
        }

        Autocomplete.prototype.setup = function() {
          var self = this

          this.form_elem = $(this.form_selector)
          this.query_box = this.form_elem.find('input[name=q]')

          // Watch the input box.
          this.query_box.on('keyup', function() {
            var query = self.query_box.val()

            if(query.length < self.minimum_length) {
              return false
            }

            self.fetch(query)
          })

          // On selecting a result, populate the search field.
          this.form_elem.on('click', '.ac-result', function(ev) {
            self.query_box.val($(this).text())
            $('.ac-results').remove()
            return false
          })
        }

        Autocomplete.prototype.fetch = function(query) {
          var self = this

          $.ajax({
            url: this.url
          , data: {
              'q': query
            }
          , success: function(data) {
              self.show_results(data)
            }
          })
        }

        Autocomplete.prototype.show_results = function(data) {
          // Remove any existing results.
          $('.ac-results').remove()

          var results = data.results || []
          var results_wrapper = $('<div class="ac-results"></div>')
          var base_elem = $('<div class="result-wrapper"><a href="#" class="ac-result"></a></div>')

          if(results.length > 0) {
            for(var res_offset in results) {
              var elem = base_elem.clone()
              // Don't use .html(...) here, as you open yourself to XSS.
              // Really, you should use some form of templating.
              elem.find('.ac-result').text(results[res_offset])
              results_wrapper.append(elem)
            }
          }
          else {
            var elem = base_elem.clone()
            elem.text("No results found.")
            results_wrapper.append(elem)
          }

          this.query_box.after(results_wrapper)
        }

        $(document).ready(function() {
          window.autocomplete = new Autocomplete({
            form_selector: '.autocomplete-me'
          })
          window.autocomplete.setup()
        })
      </script>
    </body>
    </html>
