from optparse import make_option
import sys
from django.core.management.base import BaseCommand
from haystack.constants import DEFAULT_ALIAS
from pprint import pprint

class Command(BaseCommand):
    help = "Removes indexed documents that no longer correspond to objects in the Django ORM."
    
    base_options = (
        make_option('--noinput', action='store_false', dest='interactive', default=True,
            help='If provided, no prompts will be issued to the user and the data will be wiped out.'
        ),
        make_option("-u", "--using", action="store", type="string", dest="using", default=DEFAULT_ALIAS,
            help='If provided, chooses a connection to work with.'
        ),
        make_option('-b', '--batch-size', action='store', dest='batchsize',
            default=1000, type='int',
            help='Number of items to index at once.'
        ),
    )
    option_list = BaseCommand.option_list + base_options
    
    def handle(self, *args, **options):
        """Removes indexed documents that no longer correspond to objects in the Django ORM."""
        
        from haystack import connections
        from haystack.query import SearchQuerySet
        
        verbosity = int(options.get('verbosity', 1))
        using = options.get('using')
        batch_size = int(options.get('batchsize'))
        
        backend = connections[using].get_backend()
        qs = SearchQuerySet().using(using)
        
        total = qs.count()
        start = 0
        while start + batch_size <= total:
            batch = qs[start:start+batch_size]
            
            # Get primary keys by model. Force the primary keys to integers
            # because we will need to compare them with the result of in_bulk
            # later. Construct as: model_pks[model_instance][pk] = backend_identifier
            model_pks = { }
            batch_objs = { }
            for result in batch:
                model_pks.setdefault(result.model, {})[int(result.pk)] = result.id
                batch_objs[result.id] = result
                
            # Take each model separately.
            for model, pks in model_pks.items():
                # Do a batch query for objects by id.
                objs = model.objects.only('id').in_bulk(pks.keys())
                
                # Check for missing pks from objs, indicating a missing object.
                for pk, dotted_identifier in pks.items():
                    if pk not in objs:
                        print dotted_identifier, "missing:"
                        pprint(batch_objs[dotted_identifier].get_stored_fields())
                        print

                        # Without --noinput we ask to remove each one from the index.
                        if options.get('interactive', True):
                            yes_or_no = raw_input("Delete record? [y/N] ")
                            if not yes_or_no.lower().startswith('y'):
                                continue

                        # With --noinput, or the user chose yes, delete the record.
                        backend.remove(dotted_identifier)
            
            print start, total, str(100*start/total) + "%"
        
            start += batch_size
            
