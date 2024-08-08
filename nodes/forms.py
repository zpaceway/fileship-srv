import json
from django import forms
from nodes import connectors
from nodes.models import Node


AVAILABLE_CONNECTORS = {
    "telegram": {"name": "Telegram Connector", "cls": connectors.TelegramConnector},
    "local": {"name": "Local Connector", "cls": connectors.LocalConnector},
}


class NodeForm(forms.ModelForm):
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
    name = forms.CharField(required=False)

    class Meta:
        model = Node
        fields = [
            "parent",
            "name",
            "file",
        ]

    def save(self, commit: bool):
        instance = super().save(commit)
        file = self.cleaned_data["file"]
        connector_cls = AVAILABLE_CONNECTORS.get(
            self.cleaned_data["connector"], {}
        ).get("cls")
        connector = connector_cls()

        if file:
            instance.size = file.size
            chunks, compressed = connector.upload(file)
            if not instance.name:
                instance.name = file.name
            instance.data = json.dumps(
                {
                    "chunks": chunks,
                    "compressed": compressed,
                }
            )

        return instance
