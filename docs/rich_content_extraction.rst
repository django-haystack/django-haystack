.. _ref-rich_content_extraction:

=======================
Rich Content Extraction
=======================

For some projects it is desirable to index text content which is stored in
structured files such as PDFs, Microsoft Office documents, images, etc.
Currently only Solr's `ExtractingRequestHandler`_ is directly supported by
Haystack but the approach below could be used with any backend which supports
this feature.

.. _`ExtractingRequestHandler`: http://wiki.apache.org/solr/ExtractingRequestHandler

Extracting Content
==================

:meth:`SearchBackend.extract_file_contents` accepts a file or file-like object
and returns a dictionary containing two keys: ``metadata`` and ``contents``. The
``contents`` value will be a string containing all of the text which the backend
managed to extract from the file contents. ``metadata`` will always be a
dictionary but the keys and values will vary based on the underlying extraction
engine and the type of file provided.

Indexing Extracted Content
==========================

Generally you will want to include the extracted text in your main document
field along with everything else specified in your search template. This example
shows how to override a hypothetical ``FileIndex``'s ``prepare`` method to
include the extract content along with information retrieved from the database::

    def prepare(self, obj):
        data = super(FileIndex, self).prepare(obj)

        # This could also be a regular Python open() call, a StringIO instance
        # or the result of opening a URL. Note that due to a library limitation
        # file_obj must have a .name attribute even if you need to set one
        # manually before calling extract_file_contents:
        file_obj = obj.the_file.open()

        extracted_data = self.get_backend().extract_file_contents(file_obj)

        # Now we'll finally perform the template processing to render the
        # text field with *all* of our metadata visible for templating:
        t = loader.select_template(('search/indexes/myapp/file_text.txt', ))
        data['text'] = t.render(Context({'object': obj,
                                         'extracted': extracted_data}))

        return data

This allows you to insert the extracted text at the appropriate place in your
template, modified or intermixed with database content as appropriate:

.. code-block:: html+django

    {{ object.title }}
    {{ object.owner.name }}

    …

    {% for k, v in extracted.metadata.items %}
        {% for val in v %}
            {{ k }}: {{ val|safe }}
        {% endfor %}
    {% endfor %}

    {{ extracted.contents|striptags|safe }}