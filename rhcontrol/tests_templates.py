"""
Regras de padronização dos templates (Etapa 5).

- Telas do sistema não usam style="..." inline: o visual mora nos arquivos
  CSS de base_static/global/css. Os templates de PDF ficam de fora, porque o
  WeasyPrint monta o layout deles a partir dos próprios estilos.
- Todo arquivo pedido com {% static '...' %} existe em base_static, para o
  collectstatic levá-lo à produção.
"""
import re
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase

TEMPLATE_DIRS = [
    Path(settings.BASE_DIR) / "rhcontrol" / "templates",
    Path(settings.BASE_DIR) / "base_templates",
]
STATIC_DIRS = [Path(d) for d in settings.STATICFILES_DIRS]

# Inline que continua permitido:
#  - display: none -> estado inicial que o JavaScript lê e troca (el.style.display)
#  - border-left-color com variável -> cor que vem do banco, por registro
ALLOWED_INLINE = re.compile(
    r"^\s*(display:\s*none;?|border-left-color:\s*\{\{[^}]+\}\};?)\s*$"
)


def screen_templates():
    for folder in TEMPLATE_DIRS:
        for path in folder.rglob("*.html"):
            if "pdf" in path.parts or path.name == "base_pdf.html":
                continue
            yield path


class InlineStyleTests(SimpleTestCase):
    def test_screens_have_no_inline_style(self):
        found = []
        for path in screen_templates():
            for style in re.findall(r'\sstyle\s*=\s*"([^"]*)"', path.read_text()):
                if not ALLOWED_INLINE.match(style):
                    found.append(f"{path.name}: {style}")
        self.assertEqual(found, [], "Use uma classe do components.css no lugar do style inline.")

    def test_screens_have_no_style_block(self):
        found = [p.name for p in screen_templates() if "<style" in p.read_text()]
        self.assertEqual(found, [], "Mova o bloco <style> para base_static/global/css/pages/.")


class StaticReferencesTests(SimpleTestCase):
    def test_every_static_file_exists(self):
        missing = []
        for folder in TEMPLATE_DIRS:
            for path in folder.rglob("*.html"):
                for ref in re.findall(r"\{%\s*static\s+'([^']+)'\s*%\}", path.read_text()):
                    if not any((d / ref).exists() for d in STATIC_DIRS):
                        missing.append(f"{path.name}: {ref}")
        # A logo da empresa existe só na VM de produção, de propósito.
        missing = [m for m in missing if not m.endswith("LOGO_GDL.png")]
        self.assertEqual(missing, [])
