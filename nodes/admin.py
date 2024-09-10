from django.contrib import admin
from nodes.forms import ChunkForm, NodeForm
from nodes.models import Chunk, Node


class NodeAdmin(admin.ModelAdmin):
    model = Node
    form = NodeForm


class ChunkAdmin(admin.ModelAdmin):
    model = Chunk
    form = ChunkForm
    readonly_fields = [
        "size",
    ]


admin.site.register(Node, NodeAdmin)
admin.site.register(Chunk, ChunkAdmin)
