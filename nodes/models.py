import os
import json
from typing import List, Literal, Union
from django.db import models
from django.db.models.manager import BaseManager


class Node(models.Model):
    chunks: BaseManager["Chunk"]
    children: BaseManager["Node"]

    id = models.TextField(primary_key=True)
    parent = models.ForeignKey(
        "nodes.Node",
        related_name="children",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
    )
    name = models.CharField(max_length=256)
    size = models.BigIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def get_size(self):
        if self.chunks.count() > 0:
            return self.size

        full_size = sum([child.get_size() for child in self.children.all()])

        return full_size

    def uploaded(self):
        if self.chunks.count() > 0:
            return all(chunk.uploaded() for chunk in self.chunks.all())

        return all([child.uploaded() for child in self.children.all()])

    def representation(self, order_by=["name"]):
        self.children: BaseManager[Node]

        base_node = {
            "id": self.id,
            "name": self.name,
            "fullname": self.get_fullname("id"),
            "size": self.get_size(),
            "url": None,
            "children": None,
            "uploaded": self.uploaded(),
            "createdAt": self.created_at.isoformat(),
            "updatedAt": self.updated_at.isoformat(),
        }

        if self.chunks.count() > 0:
            base_node["url"] = os.path.join("nodes", str(self.id), "download")
            del base_node["children"]

        else:
            del base_node["url"]

            base_node["children"] = [
                child.representation(order_by)
                for child in self.children.filter().order_by(*order_by)
            ]

        return base_node

    @staticmethod
    def tree(order_by=["name"]):
        return [
            node.representation(order_by)
            for node in Node.objects.filter(
                parent=None,
            ).order_by(*order_by)
        ]

    def get_fullname(self, property: Literal["name", "id"] = "name") -> str:
        path_chunks: List[str] = [self.name if property == "name" else self.id]
        parent_node: Node = self.parent

        while parent_node:
            path_chunks.append(parent_node.name if property == "name" else self.id)
            parent_node = parent_node.parent

        path_chunks.reverse()

        return f'/{"/".join(path_chunks)}'

    def __str__(self) -> str:
        return self.get_fullname()


class Chunk(models.Model):
    id = models.TextField(primary_key=True)
    node: Node = models.ForeignKey(
        "nodes.Node",
        related_name="chunks",
        on_delete=models.CASCADE,
    )
    index = models.IntegerField()
    data = models.TextField(
        null=True,
        blank=True,
    )
    size = models.BigIntegerField(
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [
            ("node", "index"),
        ]

    def representation(self):
        return {
            "id": self.id,
            "name": self.get_name(),
            "fullname": self.get_fullname("id"),
            "size": self.size,
            "data": json.loads(self.data),
            "createdAt": self.created_at.isoformat(),
            "updatedAt": self.updated_at.isoformat(),
        }

    def get_name(self) -> str:
        return f"{self.node.name}:{self.index}"

    def get_fullname(self, property: Literal["name", "id"] = "name") -> str:
        return f"{self.node.get_fullname(property)}:{self.index}"

    def uploaded(self) -> bool:
        return not not self.data

    def __str__(self) -> str:
        return self.get_fullname()
