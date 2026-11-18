"""
Cabeçalho do Form40B no cadastro do treinamento: o que o RH preenche no
sistema sai pronto na lista de presença em Excel.
"""
from datetime import date, time
from io import BytesIO

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from openpyxl import load_workbook

from rhcontrol.attendance_sheet import build_attendance_sheet
from rhcontrol.forms import TrainingForm
from rhcontrol.models import Training
from rhcontrol.tests_security import make_user


def base_data(**extra):
    data = {
        'training_name': 'Reciclagem Anual',
        'training_total_hours': '1',
        'training_location_type': 'Interno',
        'requested_by': 'Tauana',
        'approved_by': 'Cássio',
    }
    data.update(extra)
    return data


class Form40BFormTests(TestCase):
    def test_new_form_has_editable_defaults(self):
        form = TrainingForm()

        self.assertEqual(form['requested_by'].value(), 'Tauana')
        self.assertEqual(form['approved_by'].value(), 'Cássio')
        self.assertEqual(form['request_date'].value(), timezone.localdate())
        self.assertEqual(form['formats'].value(), ['training'])

        edited = TrainingForm(data=base_data(requested_by='Maria', approved_by='João'))
        self.assertTrue(edited.is_valid(), edited.errors)
        training = edited.save()
        self.assertEqual((training.requested_by, training.approved_by), ('Maria', 'João'))

    def test_saves_all_fields(self):
        form = TrainingForm(data=base_data(
            request_date='2026-11-01',
            need_reasons=['recycling', 'nonconformity', 'other'],
            nonconformity_number='045/2026',
            need_other='Pedido da diretoria',
            objective='Treinar quanto ao uso das instruções de trabalho.',
            venues=['supplier', 'other'],
            venue_other='Auditório',
            formats=['training', 'meeting'],
            needs_effectiveness_check='no',
            audience='individual',
            uses_equipment='yes',
            equipment_description='Projetor',
            doc_work_instruction='on',
            doc_work_instruction_detail='IT-12, 01/10/2026, rev. 3',
            start_time='07:10',
            end_time='07:30',
            instructor='Tauana Santos',
        ))

        self.assertTrue(form.is_valid(), form.errors)
        training = form.save()
        training.refresh_from_db()
        self.assertEqual(training.need_reasons, ['recycling', 'nonconformity', 'other'])
        self.assertEqual(training.nonconformity_number, '045/2026')
        self.assertEqual(training.venues, ['supplier', 'other'])
        self.assertEqual(training.formats, ['training', 'meeting'])
        self.assertEqual(training.support_documents, {'work_instruction': 'IT-12, 01/10/2026, rev. 3'})
        self.assertEqual((training.start_time, training.end_time), (time(7, 10), time(7, 30)))
        self.assertEqual(training.instructor, 'Tauana Santos')

    def test_text_of_unchecked_option_is_cleared(self):
        form = TrainingForm(data=base_data(
            need_reasons=['recycling'], need_other='sobrou', nonconformity_number='99',
            venues=['supplier'], venue_other='sobrou',
            uses_equipment='no', equipment_description='sobrou',
            doc_quality_manual_detail='sem caixinha marcada',
        ))

        self.assertTrue(form.is_valid(), form.errors)
        training = form.save()
        self.assertEqual(
            (training.need_other, training.nonconformity_number, training.venue_other, training.equipment_description),
            ('', '', '', ''),
        )
        self.assertEqual(training.support_documents, {})

    def test_unknown_option_codes_are_rejected(self):
        form = TrainingForm(data=base_data(need_reasons=['hacker'], venues=['lua'], formats=['x'], audience='todos'))

        self.assertFalse(form.is_valid())
        for field in ('need_reasons', 'venues', 'formats', 'audience'):
            self.assertIn(field, form.errors)

    def test_end_time_before_start_time_is_rejected(self):
        form = TrainingForm(data=base_data(start_time='08:00', end_time='07:00'))

        self.assertFalse(form.is_valid())
        self.assertIn('end_time', form.errors)

    def test_edit_page_shows_section_with_saved_document(self):
        self.client.force_login(make_user('rh', 'rhcontrol.change_training', 'rhcontrol.view_training'))
        training = Training.objects.create(
            training_name='NR-12', training_total_hours=8,
            support_documents={'quality_policy': 'POL-01 rev. 2'},
        )

        response = self.client.get(reverse('rhcontrol:training_update', args=[training.pk]))

        self.assertContains(response, 'Dados da Lista de Presença (Form40B)')
        self.assertContains(response, 'value="POL-01 rev. 2"')
        self.assertContains(response, 'global/js/conditional-fields.js')


class Form40BSheetTests(TestCase):
    def sheet(self, **fields):
        data = {'training_name': 'Reciclagem Anual', 'training_total_hours': 1}
        data.update(fields)
        return load_workbook(BytesIO(build_attendance_sheet(Training.objects.create(**data))))['FRENTE']

    def test_header_texts(self):
        sheet = self.sheet(
            requested_by='Tauana', approved_by='Cássio', request_date=date(2026, 11, 1),
            start_date=date(2026, 11, 16), start_time=time(7, 10), end_time=time(7, 30),
            instructor='Tauana Santos', training_provider='Fornecedor X',
        )

        self.assertEqual(sheet['B6'].value.strip(), 'Área Solicitante: Treinamento')
        self.assertTrue(sheet['G6'].value.endswith('Tauana'))
        self.assertTrue(sheet['B7'].value.endswith('Cássio'))
        self.assertTrue(sheet['J6'].value.endswith('01/11/2026'))
        self.assertTrue(sheet['I7'].value.endswith('01/11/2026'))
        self.assertTrue(sheet['H37'].value.endswith('07:10h - 07:30h'))
        self.assertTrue(sheet['B38'].value.endswith('Tauana Santos'))

    def test_instructor_falls_back_to_provider_and_goal_to_description(self):
        sheet = self.sheet(training_provider='Fornecedor X', training_description='Descrição longa')

        self.assertTrue(sheet['B38'].value.endswith('Fornecedor X'))
        self.assertTrue(sheet['B15'].value.endswith('Descrição longa'))

        sheet = self.sheet(training_description='Descrição longa', objective='Objetivo curto')
        self.assertTrue(sheet['B15'].value.endswith('Objetivo curto'))
        self.assertNotIn('Descrição longa', sheet['B15'].value)

    def test_need_reasons_are_marked(self):
        sheet = self.sheet(
            need_reasons=['recycling', 'nonconformity', 'other'],
            nonconformity_number='045/2026', need_other='Diretoria', is_integration=True,
        )

        self.assertTrue(sheet['J10'].value.startswith('( X ) Reciclagem'))
        self.assertTrue(sheet['B11'].value.startswith('( X ) Não Conformidade'))
        self.assertTrue(sheet['B11'].value.endswith('045/2026'))
        self.assertTrue(sheet['B13'].value.startswith('( X ) Outros'))
        self.assertTrue(sheet['B13'].value.endswith('Diretoria'))
        self.assertEqual(sheet['J12'].value, '( X )Integração')
        self.assertTrue(sheet['B10'].value.startswith('(    ) Descrição'))

    def test_boxes_are_ticked(self):
        sheet = self.sheet(
            venues=['supplier', 'other'], venue_other='Auditório',
            formats=['training'], needs_effectiveness_check='no', audience='individual',
            uses_equipment='yes', equipment_description='Projetor',
            support_documents={'work_instruction': 'IT-12 rev. 3', 'other': 'Fluxograma'},
        )

        self.assertIn('☒ Fornecedor', sheet['B18'].value)
        self.assertIn('☐ Sala de Treinamento', sheet['B18'].value)
        self.assertTrue(sheet['B18'].value.endswith('Auditório'))
        self.assertEqual([sheet[c].value for c in ('B22', 'E22', 'H22', 'K22')], ['☐', '☐', '☐', '☒'])
        self.assertIn('☒ Não', sheet['F25'].value)
        self.assertEqual((sheet['J25'].value, sheet['L25'].value), ('☒', '☐'))
        self.assertIn('☒ Sim', sheet['B28'].value)
        self.assertTrue(sheet['B28'].value.endswith('Projetor'))
        self.assertIn('☒ Instrução de Trabalho', sheet['B32'].value)
        self.assertTrue(sheet['B32'].value.rstrip().endswith('IT-12 rev. 3'))
        self.assertTrue(sheet['B35'].value.endswith('Revisão: Fluxograma'))
        self.assertIn('☐ Manual da Qualidade', sheet['B34'].value)

    def test_empty_fields_leave_template_blank(self):
        sheet = self.sheet(requested_by='', approved_by='')

        self.assertEqual(sheet['G6'].value.strip(), 'Resp.:')
        self.assertEqual(sheet['H37'].value.strip(), 'Horário:')
        self.assertIn('☐ Não', sheet['B28'].value)
        self.assertIn('☐ Sim', sheet['F25'].value)
