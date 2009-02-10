==============
ModelIndex API
==============

The ModelIndex class allows the application developer a way to provide data to
the backend in a structured format. Developers familiar with Django's ``Form``
or ``Model`` classes should find the syntax for indexes familiar.


Quick Start
===========

For the impatient::

    import datetime
    from haystack import indexes
    from haystack.sites import site
    from myapp.models import Note
    
    
    class NoteIndex(indexes.ModelIndex):
        text = indexes.ContentField()
        author = indexes.CharField('user')
        pub_date = indexes.DateTimeField('pub_date')
        
        def get_query_set(self):
            "Used when the entire index for model is updated."
            return Note.objects.filter(pub_date__lte=datetime.datetime.now())
    
    
    site.register(Note, NoteIndex)
