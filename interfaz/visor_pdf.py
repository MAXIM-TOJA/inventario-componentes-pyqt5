"""Visor de PDF con selección y recorte interactivo."""
import os
import webbrowser

import pymupdf as fitz

from PyQt5.QtCore import QPoint, QRect, Qt
from PyQt5.QtGui import QBrush, QColor, QFont, QImage, QPainter, QPen, QPixmap
from PyQt5.QtWidgets import (
    QAction,
    QApplication,
    QDialog,
    QHBoxLayout,
    QLabel,
    QMenu,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget
)

import almacenamiento
import ocr
from interfaz.editor_imagen import pedir_destino_y_guardar


# -------------------------------------------------------------------
# UTILIDAD: ENLACES CLICABLES EN PDF
# -------------------------------------------------------------------
def hacer_links_clicables_en_pdf(doc_pdf):
    url_pattern = r"(https?://[^\s]+|www\.[^\s]+)"
    for page in doc_pdf:
        links_encontrados = page.search_for(url_pattern)
        for rect in links_encontrados:
            texto_url = page.get_text("text", clip=rect).strip()
            if texto_url:
                uri_final = texto_url if texto_url.startswith("http") else "http://" + texto_url
                try:
                    page.insert_link({
                        "kind": fitz.LINK_URI,
                        "from": rect,
                        "uri": uri_final
                    })
                except Exception:
                    pass


# -------------------------------------------------------------------
# VISOR DE PDF INTERACTIVO PROFESIONAL CON DOBLE MODO (TEXTO / RECORTE)
# -------------------------------------------------------------------
class WidgetVisorPDFInteractivo(QWidget):
    def __init__(self, page, zoom_level, parent_dialog=None):
        super().__init__()
        self.page = page
        self.zoom_level = zoom_level
        self.parent_dialog = parent_dialog
        self.modo = "texto"  # "texto" o "recorte"
        self.actualizar_renderizado()
        self.dragging = False
        self.start_pos = QPoint()
        self.end_pos = QPoint()
        self.selection_rect = QRect()
        self.texto_seleccionado_actual = ""
        self.texto_por_ocr = False      # True si el texto seleccionado salió del OCR y no del texto del PDF
        self.aviso_ocr = ""             # motivo por el que el OCR no pudo usarse (para mostrarlo en el menú)
        self.setMouseTracking(True)

    def set_modo(self, modo):
        self.modo = modo
        self.selection_rect = QRect()
        self.update()
        if modo == "recorte":
            self.setCursor(Qt.CrossCursor)
        else:
            self.setCursor(Qt.IBeamCursor)

    def actualizar_renderizado(self):
        matrix = fitz.Matrix(self.zoom_level, self.zoom_level)
        pix = self.page.get_pixmap(matrix=matrix, colorspace=fitz.csRGB, alpha=False)
        qimage = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888)
        self.pixmap = QPixmap.fromImage(qimage)
        self.setFixedSize(self.pixmap.size())
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), Qt.white)
        painter.drawPixmap(0, 0, self.pixmap)
        
        if not self.selection_rect.isNull():
            if self.modo == "texto":
                painter.setPen(QPen(QColor(0, 120, 215), 1, Qt.SolidLine))
                painter.setBrush(QBrush(QColor(0, 120, 215, 60)))
            else:  # Modo recorte: Marco rojo solicitado
                painter.setPen(QPen(Qt.red, 2, Qt.DashLine))
                painter.setBrush(QBrush(QColor(255, 0, 0, 30)))
            painter.drawRect(self.selection_rect)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self.modo == "texto":
                point_pdf = fitz.Point(event.pos().x() / self.zoom_level, event.pos().y() / self.zoom_level)
                link_encontrado = None
                for link in self.page.get_links():
                    if "from" in link and link["from"].contains(point_pdf):
                        link_encontrado = link
                        break

                if link_encontrado:
                    if link_encontrado.get("kind") == fitz.LINK_URI:
                        uri = link_encontrado.get("uri")
                        if uri:
                            webbrowser.open(uri)
                            return

            self.dragging = True
            self.start_pos = event.pos()
            self.end_pos = self.start_pos
            self.selection_rect = QRect()
            self.texto_seleccionado_actual = ""
            self.texto_por_ocr = False
            self.aviso_ocr = ""
            self.update()

    def mouseMoveEvent(self, event):
        if self.dragging:
            self.end_pos = event.pos()
            self.selection_rect = QRect(self.start_pos, self.end_pos).normalized()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.dragging:
            self.dragging = False
            self.selection_rect = QRect(self.start_pos, self.end_pos).normalized()
            self.update()
            
            if self.modo == "texto":
                self.extraer_texto_seleccionado()
            # En modo recorte la región solo queda marcada: se guarda con el botón "Guardar Recorte".

    def extraer_texto_seleccionado(self):
        if self.selection_rect.width() < 3 or self.selection_rect.height() < 3:
            return
        x1 = self.selection_rect.left() / self.zoom_level
        y1 = self.selection_rect.top() / self.zoom_level
        x2 = self.selection_rect.right() / self.zoom_level
        y2 = self.selection_rect.bottom() / self.zoom_level
        pdf_rect = fitz.Rect(x1, y1, x2, y2)
        self.aviso_ocr = ""
        texto = self._texto_en_region(pdf_rect)
        self.texto_por_ocr = False
        if not texto:                       # la página no tiene texto en esa zona (es una imagen): se prueba con OCR
            texto = self._texto_por_ocr(pdf_rect)
            self.texto_por_ocr = bool(texto)
        self.texto_seleccionado_actual = texto
        if self.texto_seleccionado_actual:
            QApplication.clipboard().setText(self.texto_seleccionado_actual)

    def _texto_por_ocr(self, rect_pdf):
        """Reconoce con Tesseract el texto de una región que es imagen. Cadena vacía si no hay o no hay OCR
        (en ese caso `aviso_ocr` explica por qué)."""
        region = fitz.Rect(rect_pdf).intersect(self.page.rect)
        if region.is_empty:
            return ""
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            imagen = self._renderizar(region, escala=3.0)        # más resolución: el OCR acierta mucho más
            ruta = almacenamiento.guardar_temporal(imagen, "ocr_temp.png", "PNG")
            return ocr.reconocer_texto(ruta)
        except ocr.OcrError as e:
            self.aviso_ocr = str(e)
            return ""
        finally:
            QApplication.restoreOverrideCursor()

    def _texto_en_region(self, rect_pdf):
        """Texto de la región. Primero el texto contenido en el marco; si no hay, las palabras que el marco toca
        (un marco que corta una letra no debe dejar la selección vacía)."""
        texto = self.page.get_text("text", clip=rect_pdf).strip()
        if texto:
            return texto
        palabras = [w for w in self.page.get_text("words") if fitz.Rect(w[:4]).intersects(rect_pdf)]
        palabras.sort(key=lambda w: (w[5], w[6], w[7]))          # bloque, línea, palabra
        lineas, actual = [], None
        for w in palabras:
            if (w[5], w[6]) != actual:
                lineas.append([])
                actual = (w[5], w[6])
            lineas[-1].append(w[4])
        return "\n".join(" ".join(linea) for linea in lineas).strip()

    def _renderizar(self, clip=None, escala=2.0):
        """Imagen de la página (o de una región de ella), por defecto a doble resolución. Copia propia: no depende del buffer de PyMuPDF."""
        pix = self.page.get_pixmap(matrix=fitz.Matrix(escala, escala), clip=clip, colorspace=fitz.csRGB, alpha=False)
        return QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888).copy()

    def imagen_recorte(self):
        """Imagen de la región marcada en modo recorte, o None si no hay una región válida."""
        if self.modo != "recorte" or self.selection_rect.width() <= 5 or self.selection_rect.height() <= 5:
            return None
        clip = fitz.Rect(self.selection_rect.left() / self.zoom_level, self.selection_rect.top() / self.zoom_level,
                         self.selection_rect.right() / self.zoom_level, self.selection_rect.bottom() / self.zoom_level)
        clip.intersect(self.page.rect)          # la región no puede salirse de la página
        if clip.is_empty:
            return None
        return self._renderizar(clip)

    def imagen_pagina(self):
        """Imagen de toda la página que muestra el visor."""
        return self._renderizar()

    def contextMenuEvent(self, event):
        if self.modo != "texto":
            return
        menu = QMenu(self)
        if not self.texto_seleccionado_actual:
            # Siempre se muestra un menú: así se ve que el clic derecho funciona y por qué no hay nada que copiar.
            if self.selection_rect.isNull():
                aviso = "Arrastre el mouse sobre el texto para seleccionarlo"
            elif self.aviso_ocr:
                aviso = self.aviso_ocr
            else:
                aviso = "No se encontró texto en la zona marcada (ni con OCR)"
            accion_aviso = QAction(aviso, self)
            accion_aviso.setEnabled(False)
            menu.addAction(accion_aviso)
            menu.exec_(event.globalPos())
            return
        accion_copiar = QAction("📋 Copiar texto seleccionado" + (" (reconocido por OCR)" if self.texto_por_ocr else ""), self)
        accion_copiar.triggered.connect(lambda: QApplication.clipboard().setText(self.texto_seleccionado_actual))
        menu.addAction(accion_copiar)

        if self.parent_dialog and hasattr(self.parent_dialog, 'parent_dialogo_componente') and self.parent_dialog.parent_dialogo_componente:
            padre = self.parent_dialog.parent_dialogo_componente

            menu.addSeparator()
            accion_chip = QAction("⚡ Usar como '7. Chip Principal'", self)
            accion_chip.triggered.connect(lambda: padre.txt_chip.setText(self.texto_seleccionado_actual))
            menu.addAction(accion_chip)

            accion_desc = QAction("📝 Usar como '5. Descripción'", self)
            accion_desc.triggered.connect(lambda: padre.txt_descripcion.setPlainText(self.texto_seleccionado_actual))
            menu.addAction(accion_desc)

            accion_ubic = QAction("📍 Usar como '11. Ubicación Física'", self)
            accion_ubic.triggered.connect(lambda: padre.txt_ubicacion.setText(self.texto_seleccionado_actual))
            menu.addAction(accion_ubic)

        menu.exec_(event.globalPos())


class DialogoVisorPDF(QDialog):
    def __init__(self, pdf_path, parent_dialogo_componente=None, parent=None, es_modo_etiquetas=False, titulo=None):
        super().__init__(parent)
        self.parent_dialogo_componente = parent_dialogo_componente
        self.es_modo_etiquetas = es_modo_etiquetas
        
        titulo_ventana = "🖨️ Previsualización de Etiquetas" if self.es_modo_etiquetas else f"📖 Visor de Documento PDF - {titulo or os.path.basename(pdf_path)}"
        self.setWindowTitle(titulo_ventana)
        self.setWindowFlags(Qt.Window | Qt.WindowMaximizeButtonHint | Qt.WindowMinimizeButtonHint | Qt.WindowCloseButtonHint)
        self.setWindowState(Qt.WindowMaximized)   # siempre abre maximizada
        
        self.pdf_path = pdf_path
        self.doc = fitz.open(self.pdf_path)
        
        hacer_links_clicables_en_pdf(self.doc)

        self.current_page = 0
        self.total_pages = len(self.doc)
        self.zoom_level = 1.5  
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        controls_layout = QHBoxLayout()
        self.btn_zoom_menos = QPushButton("🔍➖ Reducir")
        self.btn_zoom_menos.setAutoDefault(False); self.btn_zoom_menos.setDefault(False)
        self.btn_zoom_menos.clicked.connect(self.zoom_menos)

        self.btn_zoom_mas = QPushButton("🔍➕ Ampliar")
        self.btn_zoom_mas.setAutoDefault(False); self.btn_zoom_mas.setDefault(False)
        self.btn_zoom_mas.clicked.connect(self.zoom_mas)

        self.btn_anterior = QPushButton("◀ Anterior")
        self.btn_anterior.setAutoDefault(False); self.btn_anterior.setDefault(False)
        self.btn_anterior.clicked.connect(self.pagina_anterior)
        
        self.lbl_paginacion = QLabel()
        self.lbl_paginacion.setAlignment(Qt.AlignCenter)
        self.lbl_paginacion.setFont(QFont("Arial", 10, QFont.Bold))

        self.btn_siguiente = QPushButton("Siguiente ▶")
        self.btn_siguiente.setAutoDefault(False); self.btn_siguiente.setDefault(False)
        self.btn_siguiente.clicked.connect(self.pagina_siguiente)

        controls_layout.addWidget(self.btn_zoom_menos)
        controls_layout.addWidget(self.btn_zoom_mas)
        controls_layout.addSpacing(15)
        controls_layout.addWidget(self.btn_anterior)
        controls_layout.addWidget(self.lbl_paginacion)
        controls_layout.addWidget(self.btn_siguiente)
        controls_layout.addSpacing(15)

        if not self.es_modo_etiquetas:
            # Botones para alternar modo conmutador (Texto vs Marco Rojo Recorte)
            self.btn_modo_texto = QPushButton("🖊️ Modo Texto")
            self.btn_modo_texto.setCheckable(True)
            self.btn_modo_texto.setChecked(True)
            self.btn_modo_texto.setStyleSheet("background-color: #007bff; color: white; font-weight: bold; padding: 5px 10px;")
            self.btn_modo_texto.clicked.connect(lambda: self.cambiar_modo_visor("texto"))

            self.btn_modo_recorte = QPushButton("✂️ Modo Recorte (Marco Rojo)")
            self.btn_modo_recorte.setCheckable(True)
            self.btn_modo_recorte.setChecked(False)
            self.btn_modo_recorte.setStyleSheet("background-color: #6c757d; color: white; font-weight: bold; padding: 5px 10px;")
            self.btn_modo_recorte.clicked.connect(lambda: self.cambiar_modo_visor("recorte"))

            controls_layout.addWidget(self.btn_modo_texto)
            controls_layout.addWidget(self.btn_modo_recorte)
        
        layout.addLayout(controls_layout)

        if not self.es_modo_etiquetas:
            # Guardado de imágenes: se activa solo en modo recorte. Guarda en la carpeta que elija el usuario.
            estilo = ("QPushButton { color: white; font-weight: bold; padding: 5px 10px; background-color: %s; }"
                      "QPushButton:disabled { background-color: #ced4da; color: #868e96; }")
            recorte_layout = QHBoxLayout()
            self.btn_guardar_recorte = QPushButton("✅ Guardar Recorte")
            self.btn_guardar_recorte.setAutoDefault(False); self.btn_guardar_recorte.setDefault(False)
            self.btn_guardar_recorte.setStyleSheet(estilo % "#28a745")
            self.btn_guardar_recorte.clicked.connect(self.guardar_recorte)
            self.btn_guardar_entera = QPushButton("💾 Guardar Imagen Entera")
            self.btn_guardar_entera.setAutoDefault(False); self.btn_guardar_entera.setDefault(False)
            self.btn_guardar_entera.setStyleSheet(estilo % "#17a2b8")
            self.btn_guardar_entera.clicked.connect(self.guardar_imagen_entera)
            self.btn_guardar_recorte.setEnabled(False)
            self.btn_guardar_entera.setEnabled(False)
            recorte_layout.addWidget(self.btn_guardar_recorte)
            recorte_layout.addWidget(self.btn_guardar_entera)
            recorte_layout.addStretch()
            layout.addLayout(recorte_layout)

        lbl_hint = QLabel("💡 Modo Texto: seleccione texto y use clic derecho (si la página es una imagen se reconoce con OCR). Modo Recorte: arrastre el mouse para marcar una región y pulse «Guardar Recorte»; «Guardar Imagen Entera» guarda la página completa.")
        lbl_hint.setWordWrap(True)
        lbl_hint.setStyleSheet("background-color: #e9ecef; color: #333; padding: 6px; border-radius: 4px;")
        layout.addWidget(lbl_hint)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("background-color: #e0e0e0;")
        self.actualizar_visor_pagina()
        layout.addWidget(self.scroll_area)

    def cambiar_modo_visor(self, modo):
        if modo == "texto":
            self.btn_modo_texto.setChecked(True)
            self.btn_modo_texto.setStyleSheet("background-color: #007bff; color: white; font-weight: bold; padding: 5px 10px;")
            self.btn_modo_recorte.setChecked(False)
            self.btn_modo_recorte.setStyleSheet("background-color: #6c757d; color: white; font-weight: bold; padding: 5px 10px;")
        else:
            self.btn_modo_recorte.setChecked(True)
            self.btn_modo_recorte.setStyleSheet("background-color: #dc3545; color: white; font-weight: bold; padding: 5px 10px;")
            self.btn_modo_texto.setChecked(False)
            self.btn_modo_texto.setStyleSheet("background-color: #6c757d; color: white; font-weight: bold; padding: 5px 10px;")

        en_recorte = (modo == "recorte")
        self.btn_guardar_recorte.setEnabled(en_recorte)
        self.btn_guardar_entera.setEnabled(en_recorte)

        if hasattr(self, 'pdf_widget') and self.pdf_widget:
            self.pdf_widget.set_modo(modo)

    def _chip_actual(self):
        comp = self.parent_dialogo_componente
        return (comp.txt_chip.text().strip() if comp is not None else "") or "componente"

    def guardar_recorte(self):
        imagen = self.pdf_widget.imagen_recorte()
        if imagen is None:
            QMessageBox.information(self, "Sin región", "Marque primero una región con el mouse (arrastrando sobre la página).")
            return
        pedir_destino_y_guardar(self, imagen, "recorte.png", "Guardar Recorte Como...", self._chip_actual())

    def guardar_imagen_entera(self):
        pedir_destino_y_guardar(self, self.pdf_widget.imagen_pagina(), f"pagina_{self.current_page + 1}.png",
                                "Guardar Imagen Entera Como...", self._chip_actual())

    def actualizar_visor_pagina(self):
        if 0 <= self.current_page < self.total_pages:
            page = self.doc[self.current_page]
            modo_actual = "recorte" if (not self.es_modo_etiquetas and hasattr(self, 'btn_modo_recorte') and self.btn_modo_recorte.isChecked()) else "texto"
            
            self.pdf_widget = WidgetVisorPDFInteractivo(page, self.zoom_level, self)
            self.pdf_widget.set_modo(modo_actual)
            
            self.scroll_area.setWidget(self.pdf_widget)
            self.lbl_paginacion.setText(f"Página {self.current_page + 1} de {self.total_pages} (Zoom: {int(self.zoom_level * 100)}%)")
            self.btn_anterior.setEnabled(self.current_page > 0)
            self.btn_siguiente.setEnabled(self.current_page < self.total_pages - 1)

    def zoom_mas(self):
        if self.zoom_level < 3.0:
            self.zoom_level += 0.25
            self.actualizar_visor_pagina()

    def zoom_menos(self):
        if self.zoom_level > 1.0:
            self.zoom_level -= 0.25
            self.actualizar_visor_pagina()

    def pagina_anterior(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.actualizar_visor_pagina()

    def pagina_siguiente(self):
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self.actualizar_visor_pagina()
