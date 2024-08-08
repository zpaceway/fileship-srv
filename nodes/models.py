import os
import datetime
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
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def representation(self):
        base_node = {
            "id": self.id,
            "name": self.name,
            "size": self.size,
            "url": None,
            "children": None,
            "createdAt": self.created_at.isoformat(),
            "updatedAt": self.updated_at.isoformat(),
        }

        if self.data is not None:
            base_node["url"] = os.path.join("nodes", str(self.id), "download")
            del base_node["children"]

        else:
            del base_node["url"]
            base_node["children"] = [
                child.representation() for child in self.children.all()
            ]

        return base_node

    @staticmethod
    def tree():
        return [
            node.representation()
            for node in Node.objects.filter(
                parent=None,
            )
        ]

    def __str__(self) -> str:
        path_chunks = []
        parent_node = self.parent

        while parent_node:
            path_chunks.append(parent_node.name)
            parent_node = parent_node.parent

        path_chunks.append(self.name)

        return "/".join(path_chunks)
