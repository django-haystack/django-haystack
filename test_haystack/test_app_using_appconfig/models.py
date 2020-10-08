from django.db.models import CharField, Model


class MicroBlogPost(Model):
    text = CharField(max_length=140)
