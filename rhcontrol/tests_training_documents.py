"""
Documentos escaneados nos treinamentos (lista de presença etc.): envio de
vários arquivos, validação do tipo real, download protegido e limpeza do
arquivo físico quando o documento ou o treinamento é excluído.
"""
import re
import shutil
import tempfile
from datetime import date
from pathlib import Path

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from rhcontrol.models import Department, Employee, JobTitle, Training, TrainingDocument
from rhcontrol.tests_security import make_user

PDF = b"%PDF-1.4\n% lista de presenca\n%%EOF\n"
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
STORED_NAME = re.compile(r"^trainings/\d{4}/\d{2}/[0-9a-f]{32}\.(pdf|png)$")


def upload(name, content):
    return SimpleUploadedFile(name, content)


class TrainingDocumentTestCase(TestCase):
    def setUp(self):
        self.media_root = tempfile.mkdtemp()
        media = override_settings(MEDIA_ROOT=self.media_root)
        media.enable()
        self.addCleanup(media.disable)

        self.user = make_user(
            'rh', 'rhcontrol.add_training', 'rhcontrol.change_training',
            'rhcontrol.view_training', 'rhcontrol.delete_training',
        )
        self.client.force_login(self.user)

    def tearDown(self):
        shutil.rmtree(self.media_root, ignore_errors=True)

    def _data(self, **extra):
        data = {
            'training_name': 'NR-12',
            'training_total_hours': '8',
            'training_location_type': 'Interno',
            'start_date': '2026-10-01',
        }
        data.update(extra)
        return data

    def _create(self, *files):
        return self.client.post(
            reverse('rhcontrol:training_create'), self._data(documents=list(files))
        )

    def _update(self, training, **extra):
        return self.client.post(
            reverse('rhcontrol:training_update', args=[training.pk]), self._data(**extra)
        )

    def _path(self, document):
        return Path(self.media_root) / document.file.name

    def _make_document(self, training, name='lista.pdf', content=PDF):
        return TrainingDocument.objects.create(
            training=training, file=upload(name, content), original_name=name,
        )


class UploadTests(TrainingDocumentTestCase):
    def test_create_with_two_valid_files(self):
        response = self._create(upload('Lista Presença.pdf', PDF), upload('foto.PNG', PNG))

        self.assertRedirects(response, reverse('rhcontrol:training_list'), fetch_redirect_response=False)
        training = Training.objects.get()
        documents = list(training.documents.all())
        self.assertEqual(len(documents), 2)
        self.assertEqual(
            sorted(d.original_name for d in documents), ['Lista Presença.pdf', 'foto.PNG']
        )
        for document in documents:
            self.assertRegex(document.file.name, STORED_NAME)
            self.assertTrue(self._path(document).exists())
            self.assertEqual(document.uploaded_by, self.user)

    def test_create_without_files_still_works(self):
        response = self.client.post(reverse('rhcontrol:training_create'), self._data())

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Training.objects.get().documents.count(), 0)

    def test_edit_adds_more_documents(self):
        training = Training.objects.create(training_name='NR-12', training_total_hours=8)
        self._make_document(training)

        response = self._update(training, documents=[upload('segunda.pdf', PDF)])

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            list(training.documents.values_list('original_name', flat=True)),
            ['lista.pdf', 'segunda.pdf'],
        )

    def test_invalid_extension_is_rejected(self):
        response = self._create(upload('planilha.docx', PDF))

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Training.objects.exists())
        self.assertContains(response, 'planilha.docx')
        self.assertContains(response, 'tipo de arquivo não permitido')

    def test_renamed_file_with_wrong_signature_is_rejected(self):
        response = self._create(upload('lista.pdf', PDF), upload('virus.pdf', b'MZ\x90\x00binario'))

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Training.objects.exists())
        self.assertFalse(TrainingDocument.objects.exists())
        self.assertContains(response, 'virus.pdf')
        self.assertContains(response, 'não é um PDF válido')

    @override_settings(TRAINING_DOCUMENT_MAX_SIZE=16)
    def test_file_over_size_limit_is_rejected(self):
        response = self._create(upload('grande.pdf', PDF))

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Training.objects.exists())
        self.assertContains(response, 'grande.pdf')
        self.assertContains(response, 'passa do limite')

    def test_form_is_multipart(self):
        response = self.client.get(reverse('rhcontrol:training_create'))

        self.assertContains(response, 'enctype="multipart/form-data"')
        self.assertContains(response, 'multiple')
        # Lista dos arquivos escolhidos e o script que os acumula até salvar.
        self.assertContains(response, 'id="pending-documents"')
        self.assertContains(response, 'global/js/training-documents.js')


class RemoveTests(TrainingDocumentTestCase):
    def test_remove_deletes_row_and_file(self):
        training = Training.objects.create(training_name='NR-12', training_total_hours=8)
        keep = self._make_document(training, 'fica.pdf')
        gone = self._make_document(training, 'sai.pdf')
        gone_path = self._path(gone)

        with self.captureOnCommitCallbacks(execute=True):
            response = self._update(training, remove_documents=[gone.pk])

        self.assertEqual(response.status_code, 302)
        self.assertEqual(list(training.documents.all()), [keep])
        self.assertFalse(gone_path.exists())
        self.assertTrue(self._path(keep).exists())

    def test_cannot_remove_document_from_another_training(self):
        training = Training.objects.create(training_name='NR-12', training_total_hours=8)
        other = Training.objects.create(training_name='NR-35', training_total_hours=8)
        foreign = self._make_document(other)

        with self.captureOnCommitCallbacks(execute=True):
            response = self._update(training, remove_documents=[foreign.pk])

        self.assertEqual(response.status_code, 200)
        self.assertTrue(TrainingDocument.objects.filter(pk=foreign.pk).exists())
        self.assertTrue(self._path(foreign).exists())

    def test_deleting_training_deletes_files(self):
        training = Training.objects.create(training_name='NR-12', training_total_hours=8)
        paths = [self._path(self._make_document(training, n)) for n in ('a.pdf', 'b.pdf')]

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(reverse('rhcontrol:training_delete', args=[training.pk]))

        self.assertEqual(response.status_code, 302)
        self.assertFalse(TrainingDocument.objects.exists())
        for path in paths:
            self.assertFalse(path.exists())


class DownloadTests(TrainingDocumentTestCase):
    def setUp(self):
        super().setUp()
        training = Training.objects.create(training_name='NR-12', training_total_hours=8)
        self.document = self._make_document(training, 'Lista Presença.pdf')
        self.url = reverse('rhcontrol:training_document', args=[self.document.pk])

    def test_requires_login(self):
        self.client.logout()

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('rhcontrol:login'), response['Location'])

    def test_requires_permission(self):
        self.client.force_login(make_user('sem_acesso'))

        self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_authorized_user_gets_file(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(b''.join(response.streaming_content), PDF)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertTrue(response['Content-Disposition'].startswith('inline'))
        self.assertIn('Lista', response['Content-Disposition'])
        response.close()

    def test_missing_file_returns_404(self):
        self._path(self.document).unlink()

        self.assertEqual(self.client.get(self.url).status_code, 404)

    def test_edit_page_lists_documents(self):
        response = self.client.get(
            reverse('rhcontrol:training_update', args=[self.document.training_id])
        )

        self.assertContains(response, 'Lista Presença.pdf')
        self.assertContains(response, self.url)
        self.assertContains(response, f'value="{self.document.pk}"')
        self.assertContains(response, 'id="documentos"')


class ListCountTests(TrainingDocumentTestCase):
    def test_list_shows_document_count_without_inflating_attended(self):
        department = Department.objects.create(name='Produção')
        job = JobTitle.objects.create(name='Operador', department=department, base_salary=2500)
        employees = [
            Employee.objects.create(
                name=name, cpf=cpf, birth_date=date(1990, 1, 1), department=department,
                job_title=job, current_salary=2500, hire_date=date(2020, 1, 6),
            )
            for name, cpf in (('Ana', '67134509206'), ('Bruno', '52998224725'), ('Carla', '11144477735'))
        ]
        training = Training.objects.create(
            training_name='NR-12', training_total_hours=8, start_date=date(2026, 1, 10)
        )
        training.scheduled_employees.set(employees)
        training.attended_employees.set(employees)
        self._make_document(training, 'a.pdf')
        self._make_document(training, 'b.pdf')
        Training.objects.create(training_name='Sem documentos', training_total_hours=2)

        response = self.client.get(reverse('rhcontrol:training_list'))

        rows = {t.training_name: t for t in response.context['object_list']}
        self.assertEqual(rows['NR-12'].num_documents, 2)
        self.assertEqual(rows['NR-12'].num_attended, 3)
        self.assertEqual(rows['Sem documentos'].num_documents, 0)
        self.assertContains(response, 'training-docs-badge', count=1)
        self.assertContains(response, '2 documentos escaneados')
        # O clipe leva direto à seção de documentos da edição.
        edit_url = reverse('rhcontrol:training_update', args=[training.pk])
        self.assertContains(response, f'href="{edit_url}#documentos"')
