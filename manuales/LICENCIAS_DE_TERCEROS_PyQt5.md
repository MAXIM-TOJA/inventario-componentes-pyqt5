# Licencias

## Licencia de esta aplicación

Gestión de Inventario de Componentes Electrónicos
Copyright (c) 2026 Maxim Toja <tojamaxim@gmail.com>

Este programa es software libre: puede redistribuirlo y/o modificarlo bajo los términos de la
**GNU General Public License versión 3** publicada por la Free Software Foundation. Se distribuye
con la esperanza de que sea útil, pero **SIN NINGUNA GARANTÍA**, ni siquiera la garantía implícita
de COMERCIABILIDAD o IDONEIDAD PARA UN PROPÓSITO PARTICULAR. El texto completo está en el archivo
`LICENSE`.

> Nota sobre AGPL: la biblioteca PyMuPDF está bajo AGPL-3.0. La GPL-3.0 (sección 13) permite
> combinar un programa GPL-3.0 con una obra AGPL-3.0; la parte AGPL conserva sus propias
> condiciones. Si prefiere licenciar la aplicación completa bajo AGPL-3.0, reemplace el archivo
> `LICENSE` por el texto oficial (https://www.gnu.org/licenses/agpl-3.0.txt) y cambie el nombre de
> la licencia en este aviso.
>
> Esta es la edición con PyQt5 (GPL v3) y PyMuPDF (AGPL v3). Existe otra edición con PySide6 y
> pypdfium2, sin copyleft fuerte en las bibliotecas.

## Bibliotecas y programas de terceros

La aplicación **no incluye** el código de estas bibliotecas: se instalan aparte con
`python -m pip install -r requirements.txt`. Cada una se rige por su propia licencia.

| Componente | Uso en la aplicación | Licencia | Dónde ver el texto |
|---|---|---|---|
| Python | Lenguaje | PSF License | https://docs.python.org/3/license.html |
| SQLite (módulo sqlite3) | Base de datos | Dominio público | https://www.sqlite.org/copyright.html |
| PyQt5 | Interfaz gráfica | GPL v3 (o licencia comercial de Riverbank Computing) | https://www.riverbankcomputing.com/software/pyqt/ |
| PyMuPDF | Visor de PDF | AGPL v3 (o licencia comercial de Artifex) | https://pymupdf.readthedocs.io |
| ReportLab | PDF de etiquetas | BSD (edición de código abierto) | https://www.reportlab.com/opensource/ |
| qrcode | Código QR | BSD | https://pypi.org/project/qrcode/ |
| Pillow | Imágenes | HPND (tipo MIT) | https://pillow.readthedocs.io |
| openpyxl | Planilla de Excel | MIT | https://openpyxl.readthedocs.io |
| pytesseract | Puente hacia Tesseract | Apache 2.0 | https://pypi.org/project/pytesseract/ |
| Tesseract OCR (opcional, programa aparte) | Reconocimiento de texto | Apache 2.0 | https://github.com/tesseract-ocr/tesseract |

### Dependencias que se instalan automáticamente con las anteriores

| Componente | Lo trae | Licencia (según el conocimiento del autor) |
|---|---|---|
| PyQt5-sip | PyQt5 | SIP (compatible con GPL; también disponible comercialmente) |
| PyQt5-Qt5 (bibliotecas Qt 5.15) | PyQt5 | LGPL v3 |
| MuPDF (motor interno de PyMuPDF) | PyMuPDF | AGPL v3 |
| et_xmlfile | openpyxl | MIT |
| charset-normalizer | ReportLab | MIT |
| packaging | pytesseract | Apache 2.0 / BSD (doble licencia) |
| typing_extensions | qrcode (versiones que lo requieren) | PSF |
| PyInstaller (solo si se genera el .exe) | herramienta de desarrollo | GPL v2 o posterior con excepción: los programas generados pueden distribuirse con cualquier licencia |

La lista exacta depende de las versiones instaladas; se obtiene con `python -m pip list` y
`python -m pip show <paquete>` (campo License).

### Tesseract OCR y tesseract.exe (programa aparte, opcional)

| Elemento | Licencia | Observaciones |
|---|---|---|
| tesseract.exe (Tesseract OCR) | Apache 2.0 | Programa independiente: la aplicación lo ejecuta como un proceso externo y no lo incluye. |
| Instalador de Windows (UB Mannheim) | Apache 2.0 para Tesseract; incluye bibliotecas propias de terceros | El instalador agrega componentes como Leptonica (licencia tipo BSD) y otras bibliotecas con sus propios avisos. |
| Datos de idioma (eng.traineddata, spa.traineddata) | Apache 2.0 | Descargados de tessdata / tessdata_fast. |

Si se distribuye la carpeta `Tesseract-OCR` junto con la aplicación (por ejemplo, en el pendrive),
debe conservarse el texto de la licencia Apache 2.0 y los avisos que trae su instalación (archivo
de licencia dentro de la carpeta o del instalador). Apache 2.0 permite redistribuirlo, incluso con
programas de otra licencia. Esta carpeta está excluida del repositorio por `.gitignore`.

Esta información es orientativa y no constituye asesoramiento legal. Las licencias indicadas son las que conocía el autor al preparar este archivo. **Verifíquelas en la
página de cada proyecto**, porque pueden cambiar con las versiones.

## Si distribuye el ejecutable (.exe)

El ejecutable generado con PyInstaller incluye dentro las bibliotecas anteriores. Al repartirlo:

1. Entregue o enlace el código fuente completo de esta aplicación (por ejemplo, este repositorio).
2. Incluya el archivo `LICENSE` y este archivo.
3. Incluya los avisos de licencia de las bibliotecas empaquetadas (los archivos `LICENSE` de cada
   una, que suelen estar en sus carpetas `*.dist-info` dentro del entorno virtual).
4. No añada restricciones adicionales sobre lo que los receptores pueden hacer con el programa.

## Qué NO está en este repositorio

Los datos del usuario (`Base_Inventario/`, `adjuntos/`, `Etiquetas/`) no forman parte del código y
están excluidos por `.gitignore`. Los datasheets, tutoriales e imágenes que cada usuario adjunta
pertenecen a sus respectivos titulares.
