import os
import datetime
from django.db import models
from django.db.models.manager import BaseManager


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

    def representation(self, order_by=["name"]):
        self.children: BaseManager[Node]
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
            files = [
                child.representation(order_by)
                for child in self.children.filter(
                    data__isnull=False,
                ).order_by(*order_by)
            ]
            folders = [
                child.representation(order_by)
                for child in self.children.filter(
                    data__isnull=True,
                ).order_by(*order_by)
            ]

            base_node["children"] = [
                *folders,
                *files,
            ]

        return base_node

    @staticmethod
    def tree(order_by=["name"]):
        files = [
            node.representation(order_by)
            for node in Node.objects.filter(
                parent=None,
                data__isnull=False,
            ).order_by(*order_by)
        ]

        folders = [
            node.representation(order_by)
            for node in Node.objects.filter(
                parent=None,
                data__isnull=True,
            ).order_by(*order_by)
        ]

        return [
            *folders,
            *files,
        ]

    def __str__(self) -> str:
        path_chunks = []
        parent_node = self.parent

        while parent_node:
            path_chunks.append(parent_node.name)
            parent_node = parent_node.parent

        path_chunks.append(self.name)

        return "/".join(path_chunks)
