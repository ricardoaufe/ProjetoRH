"""
Sinais do app rhcontrol.

O Django apaga só a linha do banco: o arquivo físico de um TrainingDocument
ficaria esquecido no disco. post_delete roda também no CASCADE (ao excluir o
treinamento) e o on_commit garante que o arquivo só sai depois que a exclusão
foi gravada de fato (se a transação falhar, o arquivo continua lá).
"""
from django.db import transaction
from django.db.models.signals import post_delete
from django.dispatch import receiver

from rhcontrol.models import TrainingDocument


@receiver(post_delete, sender=TrainingDocument)
def delete_training_document_file(sender, instance, **kwargs):
    if not instance.file:
        return
    storage, name = instance.file.storage, instance.file.name
    transaction.on_commit(lambda: storage.delete(name))
