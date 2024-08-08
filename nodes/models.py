import json
from django.db import models


class Node(models.Model):
    parent = models.ForeignKey(
        "nodes.Node",
        related_name="children",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
    )
    name = models.CharField(max_length=256)
    size = models.BigIntegerField(default=0)
    data = models.TextField(blank=True, null=True)

    def representation(self):
        base_node = {
            "id": self.id,
            "name": self.name,
            "size": self.size,
            "children": None,
        }

        if self.data is not None:
            del base_node["children"]

        else:
            base_node["children"] = [
                child.representation() for child in self.children.all()
            ]

        return base_node

    @staticmethod
    def tree(base: str = ""):
        path_chunks = [path_chunk for path_chunk in base.split("/") if path_chunk]
        parent_node = None
        for path_chunk in path_chunks:
            parent_node = Node.objects.get(parent=parent_node, name=path_chunk)

        return [
            node.representation() for node in Node.objects.filter(parent=parent_node)
        ]

    def __str__(self) -> str:
        path_chunks = []
        parent_node = self.parent

        while parent_node:
            path_chunks.append(parent_node.name)
            parent_node = parent_node.parent

        path_chunks.append(self.name)

        return "/".join(path_chunks)
