"""
Testes de regressão das correções de segurança (Etapa 1 da auditoria).
"""
import importlib

from django.test import TestCase, override_settings
from django.urls import Resolver404
from django.urls.resolvers import RegexPattern, URLResolver

import rh.urls


class ProjectFilesExposureTests(TestCase):
    """Com DEBUG=1 nenhuma URL pode servir arquivos da raiz do projeto."""

    def tearDown(self):
        importlib.reload(rh.urls)

    @override_settings(DEBUG=True)
    def test_project_files_are_not_routable_in_debug(self):
        resolver = URLResolver(RegexPattern(r'^/'), importlib.reload(rh.urls))
        for path in ['/.env', '/db.sqlite3', '/rh/settings.py', '/manage.py']:
            with self.subTest(path=path), self.assertRaises(Resolver404):
                resolver.resolve(path)
