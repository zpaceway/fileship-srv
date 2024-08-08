from django.contrib import admin
from nodes.forms import NodeForm
from nodes.models import Node


class NodeAdmin(admin.ModelAdmin):
    model = Node
    form = NodeForm
    readonly_fields = [
        "size",
        "data",
    ]


admin.site.register(Node, NodeAdmin)
