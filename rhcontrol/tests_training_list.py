"""Lista de treinamentos: a linha inteira leva à edição do treinamento."""
from django.test import TestCase
from django.urls import reverse

from rhcontrol.models import Training
from rhcontrol.tests_security import make_user


class ClickableRowTests(TestCase):
    def test_each_training_row_links_to_its_edit_page(self):
        self.client.force_login(make_user('rh', 'rhcontrol.view_training'))
        training = Training.objects.create(training_name='NR-12', training_total_hours=8)
        url = reverse('rhcontrol:training_update', args=[training.pk])

        response = self.client.get(reverse('rhcontrol:training_list'))

        self.assertContains(response, f'<tr class="clickable-row" data-href="{url}">')
        # O link do nome continua lá (Ctrl+clique, leitor de tela).
        self.assertContains(response, f'<a href="{url}">NR-12</a>')
        self.assertContains(response, 'global/js/clickable-rows.js')
