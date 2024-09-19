import os
import json
from typing import List, Literal
import shutil
from django.db import models
from django.conf import settings
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

        # TODO: Save size in the database
        return 0

        return sum(
            [
                child.get_size()
                for child in self.children.all()
                .prefetch_related("children")
                .prefetch_related("chunks")
            ]
        )

    def uploaded(self):
        if self.chunks.count() > 0:
            return all([chunk.uploaded() for chunk in self.chunks.all()])

        # TODO: Save uploaded in the database
        return True

        return all(
            [
                child.uploaded()
                for child in self.children.all()
                .prefetch_related("children")
                .prefetch_related("chunks")
            ]
        )

    def representation(self, depth=0, order_by=List[Literal["name"]]):
        self.children: BaseManager[Node]

        base_node = {
            "id": self.id,
            "name": self.name,
            "size": self.get_size(),
            "chunks": [chunk.representation() for chunk in self.chunks.all()],
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
            del base_node["chunks"]

            base_node["children"] = (
                [
                    child.representation(depth=depth - 1, order_by=order_by)
                    for child in self.children.all()
                    .prefetch_related("children")
                    .prefetch_related("chunks")
                    .order_by(*order_by)
                ]
                if depth - 1 >= 0
                else []
            )

        return base_node

    @staticmethod
    def tree(node_id=None, order_by=List[Literal["name"]]):
        return [
            node.representation(order_by=order_by)
            for node in Node.objects.filter(parent=node_id)
            .prefetch_related("children")
            .prefetch_related("chunks")
            .order_by(*order_by)
        ]

    def get_fullname(self, property: Literal["name", "id"] = "name") -> str:
        path_chunks: List[str] = [self.name if property == "name" else self.id]
        parent_node: Node = self.parent

        while parent_node:
            path_chunks.append(
                parent_node.name if property == "name" else parent_node.id
            )
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
        constraints = [
            models.UniqueConstraint(fields=["node", "index"], name="unique_node_chunk")
        ]

    def representation(self):
        return {
            "id": self.id,
            "name": self.get_name(),
            "size": self.size,
            "data": self.data and json.loads(self.data),
            "createdAt": self.created_at.isoformat(),
            "updatedAt": self.updated_at.isoformat(),
        }

    def get_name(self) -> str:
        return f"{self.node.name}:{self.index}"

    def get_fullname(self, property: Literal["name", "id"] = "name") -> str:
        return f"{self.node.get_fullname(property)}:{self.index}"

    def uploaded(self) -> bool:
        return not not self.data

    def delete(self, using=None, keep_parents=False):
        result = super().delete(using, keep_parents)

        url: str = self.data and self.data.get("url")
        if url and not url.startswith("http://") and not url.startswith("https://"):
            shutil.rmtree(os.path.join(settings.BASE_DIR, url))

        return result

    def __str__(self) -> str:
        return self.get_fullname()
