
from haystack.forms import FacetedSearchForm


class CustomChoiceFacetedSearchForm(FacetedSearchForm):

    def get_facet_choices(self):
        return [
            ['author:daniel', 'author:daniel'],
            ['author:chris', 'author:chris']
        ]
