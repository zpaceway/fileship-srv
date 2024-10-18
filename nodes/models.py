import os
from typing import List, Literal, Optional
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
    unique_key = models.CharField(max_length=128)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def get_size(self):
        if self.chunks.exists():
            return self.size

        size = self.children.aggregate(total_size=models.Sum("size"))["total_size"] or 0

        if size != self.size:
            self.size = size
            self.save()

        return self.size

    def representation(self, order_by: Optional[List[Literal["name"]]] = None):
        self.children: BaseManager[Node]

        if order_by is None:
            order_by = ["name"]

        has_chunks = self.chunks.exists()
        base_node = {
            "id": self.id,
            "name": self.name,
            "size": self.get_size(),
            "chunks": [chunk.representation() for chunk in self.chunks.all()],
            "url": has_chunks and os.path.join("nodes", str(self.id), "download"),
            "children": [],
            "createdAt": self.created_at.isoformat(),
            "updatedAt": self.updated_at.isoformat(),
        }

        if has_chunks:
            del base_node["children"]
        else:
            del base_node["url"]
            del base_node["chunks"]

        return base_node

    @staticmethod
    def tree(
        unique_key: str,
        parent_node_id=None,
        order_by: Optional[List[Literal["name"]]] = None,
    ):
        if order_by is None:
            order_by = ["name"]

        children = [
            node.representation(order_by=order_by)
            for node in Node.objects.filter(
                parent=parent_node_id,
                unique_key=unique_key,
            )
            .prefetch_related("chunks")
            .order_by(*order_by)
        ]

        pathname = (
            Node.objects.get(id=parent_node_id).get_filepath()
            if parent_node_id
            else "/"
        )

        return {
            "pathname": pathname,
            "children": children,
        }

    def get_filepath(self, property: Literal["name", "id"] = "name") -> str:
        path_chunks: List[str] = [self.name if property == "name" else self.id]
        parent_node: Node = self.parent

        while parent_node:
            path_chunks.append(
                parent_node.name if property == "name" else parent_node.id
            )
            parent_node = parent_node.parent

        path_chunks.reverse()

        fullname = "/".join(path_chunks)

        if not fullname:
            fullname = "/"

        return f"/{fullname}/"

    def __str__(self) -> str:
        return self.get_filepath()


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
        connector = (
            None
            if not self.data
            else (
                "telegram"
                if "telegram" in self.data
                else "discord" if "https://" in self.data else "local"
            )
        )
        return {
            "id": self.id,
            "connector": connector,
        }

    def get_name(self) -> str:
        return f"{self.node.name}:{self.index}"

    def get_filepath(self, property: Literal["name", "id"] = "name") -> str:
        return f"{self.node.get_filepath(property)}:{self.index}"

    def delete(self, using=None, keep_parents=False):
        result = super().delete(using, keep_parents)

        url: str = self.data and self.data.get("url")
        if url and not url.startswith("http://") and not url.startswith("https://"):
            shutil.rmtree(os.path.join(settings.BASE_DIR, url))

        return result

    def __str__(self) -> str:
        return self.get_filepath()
