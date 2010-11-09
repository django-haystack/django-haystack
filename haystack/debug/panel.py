from debug_toolbar.panels import DebugPanel
from django.template import Template, Context
from haystack.backends import queries

class HaystackSearchPanel(DebugPanel):
    """
    Panel that displays information about the executed searches.
    """
    name = 'Haystack'
    has_content = True

    def __init__(self, *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)
        self.queries = []

    def nav_title(self):
        return ('Haystack')

    def nav_subtitle(self):
        global queries
        num_queries = len(queries)
        total_time = sum([q.get('time', 0) for q in queries])

        return "%d %s in %.2fms" % (
            num_queries,
            (num_queries == 1) and 'query' or 'queries',
            total_time)

    def title(self):
        return 'SearchQuerySet Queries'

    def url(self):
        return ''

    def content(self):
        global queries
        context = self.context.copy()
        context.update({
            'queries': queries,
        })

        return panel_template.render(Context(context))

panel_template = Template('''
{% load i18n %}
<table>
  <thead>
    <tr>
      <th>{% trans "Time" %}&nbsp;(ms)</th>
      <th>{% trans 'Stacktrace' %}</th>
      <th>{% trans 'Query' %}</th>
    </tr>
  </thead>
  <tbody>
    {% for query in queries %}
      <tr class="{% cycle 'djDebugOdd' 'djDebugEven' %}">
        <td>{{ query.time|floatformat:"3" }}</td>
        <td>
          {% if query.stacktrace %}
             <div class="djHaystackShowStacktraceDiv"><a href="#" onclick="javascript:$(this).parents('tr').find('.djHaystackStacktraceDiv').toggle();">Toggle Stacktrace</a></div>
          {% endif %}
        </td>
      <td class="syntax">
        <div class="djDebugSqlWrap">
          <div class="djDebugSql">{{ query.query_string }}</div>
            {% if query.stacktrace %}
                <div class="djHaystackStacktraceDiv" style="display:none;">
                <table>
                  <tr>
                    <th>{% trans "Line" %}</th>
                    <th>{% trans "Method" %}</th>
                    <th>{% trans "File" %}</th>
                  </tr>
                  {% for file, line, method in query.stacktrace %}
                    <tr>
                      <td>{{ line }}</td>
                      <td><code>{{ method|escape }}</code></td>
                      <td><code>{{ file|escape }}</code></td>
                    </tr>
                  {% endfor %}
                </table>
              </div>
            {% endif %}
          </div>
        </td>
      </tr>
    {% endfor %}
  </tbody>
</table>
''')
