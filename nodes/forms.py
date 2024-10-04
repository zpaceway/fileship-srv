import uuid
import json
from django import forms
from nodes import connectors
from nodes.models import Chunk, Node
from django.core.files.uploadedfile import InMemoryUploadedFile


AVAILABLE_CONNECTORS = {
    "telegram": {
        "name": connectors.TelegramConnector.name,
        "cls": connectors.TelegramConnector,
    },
    "local": {
        "name": connectors.LocalConnector.name,
        "cls": connectors.LocalConnector,
    },
    "discord": {
        "name": connectors.DiscordConnector.name,
        "cls": connectors.DiscordConnector,
    },
}


class NodeForm(forms.ModelForm):

    class Meta:
        model = Node
        fields = [
            "id",
            "name",
            "parent",
            "size",
            "unique_key",
        ]


class ChunkForm(forms.ModelForm):
    connector = forms.ChoiceField(
        choices=list(
            map(
                lambda connector: (
                    connector[0],
                    connector[1]["name"],
                ),
                AVAILABLE_CONNECTORS.items(),
            )
        ),
        required=True,
    )
    file = forms.FileField(required=False)

    class Meta:
        model = Chunk
        fields = [
            "connector",
            "file",
        ]

    def save(self, commit: bool):
        instance: Chunk = super().save(commit)

        file: InMemoryUploadedFile = self.cleaned_data["file"]
        connector: connectors.AbstractConnector = AVAILABLE_CONNECTORS.get(
            self.cleaned_data["connector"], {}
        ).get("cls")

        if file:
            instance.size = file.size
            chunk = connector.upload(file)
            instance.data = json.dumps(chunk)

        return instance
