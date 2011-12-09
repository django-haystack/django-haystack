import sys
import re
import unicodedata
from haystack.constants import ID, DJANGO_CT, DJANGO_ID
from haystack.utils.highlighting import Highlighter

try:
    from pymmseg import mmseg
except OSError:
    print >>sys.stderr, "Cannot import mmseg for Chinese tokenization support."
    mmseg = None

from django.utils.html import strip_tags
try:
    set
except NameError:
    from sets import Set as set


IDENTIFIER_REGEX = re.compile('^[\w\d_]+\.[\w\d_]+\.\d+$')

SEP = re.compile(r'[\s,.()\[\]|\-]')


def normalize(text):
    """
    Utility method that converts strings to tokenizable strings.
    """
    # Remove accents and lowercase:
    text = ''.join((c for c in unicodedata.normalize('NFD', unicode(text)) if unicodedata.category(c) != 'Mn')).lower()
    # Tokenizer (Chinese aware):
    if mmseg:
        text = ' '.join([' '.join(SEP.split(tok.text)) for tok in mmseg.Algorithm(text)])
    else:
        text = ' '.join(SEP.split(text))
    return text


def get_model_ct(model):
    return "%s.%s" % (model._meta.app_label, model._meta.module_name)


def get_identifier(obj_or_string):
    """
    Get an unique identifier for the object or a string representing the
    object.
    
    If not overridden, uses <app_label>.<object_name>.<pk>.
    """
    if isinstance(obj_or_string, basestring):
        if not IDENTIFIER_REGEX.match(obj_or_string):
            raise AttributeError("Provided string '%s' is not a valid identifier." % obj_or_string)
        
        return obj_or_string
    
    return u"%s.%s.%s" % (obj_or_string._meta.app_label, obj_or_string._meta.module_name, obj_or_string._get_pk_val())


def get_facet_field_name(fieldname):
    if fieldname in [ID, DJANGO_ID, DJANGO_CT]:
        return fieldname
    
    return "%s_exact" % fieldname
