import os
from typing import List, Literal, Optional
import shutil
import json
from django.contrib.auth.models import User
from django.db import models
from django.conf import settings
from django.db.models.manager import BaseManager


class Bucket(models.Model):
    id = models.TextField(primary_key=True)
    name = models.CharField(max_length=256)
    users = models.ManyToManyField("auth.User", related_name="buckets")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.name

    def representation(self):
        return {
            "id": self.id,
            "name": self.name,
            "users": [user.username for user in self.users.all()],
            "createdAt": self.created_at.isoformat(),
            "updatedAt": self.updated_at.isoformat(),
        }

    def tree(
        self,
        parent_node_id=None,
        order_by: Optional[List[Literal["name"]]] = None,
    ):
        if order_by is None:
            order_by = ["name"]

        children = [
            node.representation(order_by=order_by)
            for node in Node.objects.filter(
                parent=parent_node_id,
                bucket_id=self.id,
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


class Node(models.Model):
    chunks: BaseManager["Chunk"]
    children: BaseManager["Node"]

    id = models.TextField(primary_key=True)
    parent = models.ForeignKey(
        "buckets.Node",
        related_name="children",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
    )
    name = models.CharField(max_length=256)
    size = models.BigIntegerField()
    bucket = models.ForeignKey(
        "buckets.Bucket",
        related_name="nodes",
        on_delete=models.CASCADE,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [
            [
                "parent",
                "name",
                "bucket",
            ]
        ]

    def update_bucket(self, bucket_id: str) -> None:
        self.bucket_id = bucket_id
        for child in self.children.all():
            child.update_bucket(bucket_id)
        self.save()

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
        chunks = [chunk.representation() for chunk in self.chunks.all()]
        base_node = {
            "id": self.id,
            "name": self.name,
            "size": self.get_size(),
            "chunks": chunks,
            "uploaded": (
                len([chunk["connector"] for chunk in chunks if chunk["connector"]])
                / (len(chunks) or 1)
                * 100
            ),
            "url": (
                has_chunks
                and os.path.join(
                    "api",
                    "buckets",
                    str(self.bucket.id),
                    "nodes",
                    str(self.id),
                    "download",
                )
            ),
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
        "buckets.Node",
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

        data = self.data and json.loads(self.data)
        url: str = data and data.get("url")
        if url and not url.startswith("http://") and not url.startswith("https://"):
            shutil.rmtree(os.path.join(settings.BASE_DIR, url))

        return result

    def __str__(self) -> str:
        return self.get_filepath()
