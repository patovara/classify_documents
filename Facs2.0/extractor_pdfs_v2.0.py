"""
=============================================================================
SISTEMA DE EXTRACCIÓN DE CONCEPTOS - VERSIÓN 2.0 REMAA
=============================================================================

PROPÓSITO:
Extrae conceptos de cotización desde PDFs históricos de REMAA con validación
estricta de estructura y calidad de datos.

VERSIÓN: 2.0
EMPRESA: REMAA
AUTOR: Sistema de Automatización Empresarial
FECHA: 2026-02-03

CARACTERÍSTICAS v2.0:
✅ Validación automática de plantilla REMAA
✅ Detección inteligente de claves (patrón: XX-000)
✅ Reconstrucción correcta de conceptos multilínea
✅ 5 niveles de tests de validación automática
✅ Manejo robusto de errores sin detención del proceso
✅ Generación de reportes detallados de validación
✅ Trazabilidad completa del origen de cada concepto

ESTRUCTURA ESPERADA DE COTIZACIONES REMAA:
┌──────────┬─────────────┬──────┬──────┬──────┬─────────┐
│ CLAVE    │ CONCEPTO    │ UNID │ CANT │ P.U. │ IMPORTE │
├──────────┼─────────────┼──────┼──────┼──────┼─────────┤
│ HER-001  │ Descripción │ PZS  │ 10   │ 50.0 │ 500.0   │
│          │ INCLUYE:... │      │      │      │         │
└──────────┴─────────────┴──────┴──────┴──────┴─────────┘

REQUISITOS PREVIOS:
1. Instalar dependencias:
   pip install pdfplumber pandas openpyxl

2. Estructura de carpetas:
   proyecto/
   ├── extractor_pdfs_v2.py
   └── pdfs_cotizaciones/
       ├── cotizacion_001.pdf
       ├── cotizacion_002.pdf
       └── ...

EJECUCIÓN:
   python extractor_pdfs_v2.py

SALIDA GENERADA:
   - conceptos_master.csv      → Base de conceptos validados
   - reporte_validacion.csv    → Detalle de validación por PDF
   - log_extraccion_v2.txt     → Log completo del proceso

TESTS DE VALIDACIÓN IMPLEMENTADOS:
   🧪 TEST 1: Validación de plantilla REMAA
   🧪 TEST 2: Detección de claves válidas
   🧪 TEST 3: Reconstrucción de conceptos multilínea
   🧪 TEST 4: Validación semántica por columna
   🧪 TEST 5: Coherencia numérica

=============================================================================
"""

import pdfplumber
import pandas as pd
import os
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field


# ============================================================================
# CLASES DE DATOS
# ============================================================================

@dataclass
class ConceptoExtraido:
    """Representa un concepto extraído de una cotización."""
    clave: str
    concepto_original: str
    unidad: str
    cantidad: float
    precio_unitario: float
    importe: float
    origen_pdf: str
    numero_linea: int
    errores: List[str] = field(default_factory=list)
    advertencias: List[str] = field(default_factory=list)


@dataclass
class ResultadoValidacionPDF:
    """Resultado de la validación de un PDF."""
    nombre_archivo: str
    es_valido: bool
    es_plantilla_remaa: bool
    conceptos_extraidos: int = 0
    conceptos_validos: int = 0
    errores_criticos: int = 0
    advertencias: int = 0
    tipos_error: List[str] = field(default_factory=list)
    mensaje: str = ""


# ============================================================================
# VALIDADORES
# ============================================================================

class ValidadorPlantillaREMAA:
    """
    TEST 1: Valida que el PDF tenga la estructura de plantilla REMAA.
    """
    
    PALABRAS_CLAVE_REMAA = ['CLAVE', 'CONCEPTO', 'UNID', 'P.U.', 'IMPORTE']
    
    @classmethod
    def validar(cls, texto_completo: str) -> Tuple[bool, str]:
        """
        Valida si el PDF contiene todas las palabras clave de REMAA.
        
        Args:
            texto_completo: Texto extraído del PDF
            
        Returns:
            Tuple[bool, str]: (es_valido, mensaje)
        """
        texto_upper = texto_completo.upper()
        
        palabras_encontradas = []
        palabras_faltantes = []
        
        for palabra in cls.PALABRAS_CLAVE_REMAA:
            if palabra in texto_upper:
                palabras_encontradas.append(palabra)
            else:
                palabras_faltantes.append(palabra)
        
        if len(palabras_encontradas) == len(cls.PALABRAS_CLAVE_REMAA):
            return True, "✓ Plantilla REMAA válida"
        else:
            return False, f"✗ PLANTILLA_NO_VALIDA - Faltan: {', '.join(palabras_faltantes)}"


class ValidadorClave:
    """
    TEST 2: Valida que las claves sigan el patrón correcto.
    """
    
    # Patrón: 2-4 letras mayúsculas, guion, 3 dígitos
    PATRON_CLAVE = re.compile(r'^[A-Z]{2,4}-\d{3}$')
    PATRON_CLAVE_EN_TEXTO = re.compile(r'\b([A-Z]{2,4}-\d{3})\b')
    
    @classmethod
    def es_clave_valida(cls, texto: str) -> bool:
        """
        Verifica si un texto es una clave válida.
        
        Args:
            texto: Texto a validar
            
        Returns:
            bool: True si es una clave válida
        """
        if not texto or not isinstance(texto, str):
            return False
        
        texto = texto.strip()
        return bool(cls.PATRON_CLAVE.match(texto))
    
    @classmethod
    def extraer_claves(cls, texto: str) -> List[str]:
        """
        Extrae todas las claves válidas de un texto.
        
        Args:
            texto: Texto donde buscar claves
            
        Returns:
            List[str]: Lista de claves encontradas
        """
        if not texto:
            return []
        
        return cls.PATRON_CLAVE_EN_TEXTO.findall(texto)


class ValidadorSemantico:
    """
    TEST 4: Valida la coherencia semántica de cada columna.
    """
    
    @staticmethod
    def validar_clave(clave: str) -> Tuple[bool, Optional[str]]:
        """Valida que la clave tenga formato correcto."""
        if not clave or len(clave.strip()) == 0:
            return False, "CLAVE_VACIA"
        
        if ' ' in clave.strip():
            return False, "CLAVE_CON_ESPACIOS"
        
        if not ValidadorClave.es_clave_valida(clave.strip()):
            return False, "CLAVE_FORMATO_INVALIDO"
        
        return True, None
    
    @staticmethod
    def validar_unidad(unidad: str) -> Tuple[bool, Optional[str]]:
        """Valida que la unidad sea corta y coherente."""
        if not unidad or len(unidad.strip()) == 0:
            return False, "UNIDAD_VACIA"
        
        unidad_limpia = unidad.strip()
        
        # Unidad debe ser corta (máximo 5 caracteres)
        if len(unidad_limpia) > 5:
            return False, "UNIDAD_DEMASIADO_LARGA"
        
        # Unidad no debe contener números (salvo casos como M2, M3)
        if any(c.isdigit() for c in unidad_limpia) and not re.match(r'^[A-Z]+\d{1}$', unidad_limpia):
            return False, "UNIDAD_FORMATO_SOSPECHOSO"
        
        return True, None
    
    @staticmethod
    def validar_concepto(concepto: str) -> Tuple[bool, Optional[str]]:
        """Valida que el concepto tenga longitud razonable."""
        if not concepto or len(concepto.strip()) == 0:
            return False, "CONCEPTO_VACIO"
        
        concepto_limpio = concepto.strip()
        
        # Concepto debe tener longitud mínima razonable
        if len(concepto_limpio) < 10:
            return False, "CONCEPTO_DEMASIADO_CORTO"
        
        return True, None


class ValidadorNumerico:
    """
    TEST 5: Valida coherencia numérica entre cantidad, precio e importe.
    """
    
    TOLERANCIA_REDONDEO = 0.02  # 2% de tolerancia
    
    @classmethod
    def validar_coherencia(cls, cantidad: float, precio_unitario: float, 
                          importe: float) -> Tuple[bool, Optional[str]]:
        """
        Valida que IMPORTE ≈ CANT × P.U.
        
        Args:
            cantidad: Cantidad del concepto
            precio_unitario: Precio unitario
            importe: Importe total
            
        Returns:
            Tuple[bool, Optional[str]]: (es_valido, mensaje_error)
        """
        # Validar que sean valores positivos
        if cantidad <= 0:
            return False, "CANTIDAD_INVALIDA"
        
        if precio_unitario <= 0:
            return False, "PRECIO_INVALIDO"
        
        if importe <= 0:
            return False, "IMPORTE_INVALIDO"
        
        # Calcular importe esperado
        importe_calculado = cantidad * precio_unitario
        
        # Verificar coherencia con tolerancia
        diferencia = abs(importe - importe_calculado)
        tolerancia = importe_calculado * cls.TOLERANCIA_REDONDEO
        
        if diferencia > tolerancia:
            return False, f"INCOHERENCIA_NUMERICA (Esperado: {importe_calculado:.2f}, Real: {importe:.2f})"
        
        return True, None


# ============================================================================
# EXTRACTOR PRINCIPAL
# ============================================================================

class ExtractorConceptosREMAA:
    """
    Extractor principal de conceptos desde PDFs de cotizaciones REMAA.
    Implementa todos los tests de validación.
    """
    
    def __init__(self, carpeta_pdfs: str = "pdfs_cotizaciones"):
        """
        Inicializa el extractor.
        
        Args:
            carpeta_pdfs: Ruta de la carpeta con los PDFs
        """
        self.carpeta_pdfs = carpeta_pdfs
        self.conceptos_extraidos: List[ConceptoExtraido] = []
        self.resultados_validacion: List[ResultadoValidacionPDF] = []
        
        # Estadísticas
        self.total_pdfs = 0
        self.pdfs_procesados = 0
        self.pdfs_validos = 0
        self.pdfs_ignorados = 0
        self.total_conceptos = 0
        self.conceptos_validos = 0
        self.conceptos_con_errores = 0
    
    
    def validar_entorno(self) -> bool:
        """Valida que exista la carpeta de PDFs y contenga archivos."""
        if not os.path.exists(self.carpeta_pdfs):
            print(f"❌ ERROR: No existe la carpeta '{self.carpeta_pdfs}'")
            print(f"   Cree la carpeta y coloque los PDFs de cotizaciones REMAA.")
            return False
        
        pdfs = list(Path(self.carpeta_pdfs).glob("*.pdf"))
        if not pdfs:
            print(f"❌ ERROR: No se encontraron archivos PDF en '{self.carpeta_pdfs}'")
            return False
        
        self.total_pdfs = len(pdfs)
        print(f"✅ Carpeta encontrada: {self.total_pdfs} PDFs detectados")
        return True
    
    
    def extraer_texto_completo_pdf(self, ruta_pdf: str) -> Optional[str]:
        """
        Extrae todo el texto de un PDF.
        
        Args:
            ruta_pdf: Ruta del archivo PDF
            
        Returns:
            Optional[str]: Texto completo o None si hay error
        """
        try:
            texto_completo = []
            with pdfplumber.open(ruta_pdf) as pdf:
                for pagina in pdf.pages:
                    texto = pagina.extract_text()
                    if texto:
                        texto_completo.append(texto)
            
            return "\n".join(texto_completo)
        except Exception as e:
            print(f"     ⚠️  Error al extraer texto: {str(e)}")
            return None
    
    
    def extraer_tabla_con_contexto(self, pagina) -> List[List[str]]:
        """
        Extrae tabla preservando filas multilínea.
        
        Args:
            pagina: Objeto de página de pdfplumber
            
        Returns:
            List[List[str]]: Filas de la tabla
        """
        try:
            # Extraer tabla con configuración específica
            tabla = pagina.extract_table({
                "vertical_strategy": "lines",
                "horizontal_strategy": "lines",
                "intersection_tolerance": 15
            })
            
            if not tabla:
                # Intentar extracción alternativa
                tabla = pagina.extract_table()
            
            return tabla if tabla else []
            
        except Exception as e:
            print(f"     ⚠️  Error al extraer tabla: {str(e)}")
            return []
    
    
    def reconstruir_concepto_multilinea(self, filas: List[List[str]], 
                                       inicio: int) -> Tuple[str, int]:
        """
        TEST 3: Reconstruye un concepto que puede ocupar múltiples líneas.
        
        Args:
            filas: Lista de filas de la tabla
            inicio: Índice de la fila inicial (con la clave)
            
        Returns:
            Tuple[str, int]: (concepto_completo, índice_última_fila)
        """
        concepto_partes = []
        fila_actual = inicio
        
        # La primera fila contiene la clave y el inicio del concepto
        # Columna 1 suele ser el concepto (después de CLAVE)
        if len(filas[inicio]) > 1 and filas[inicio][1]:
            concepto_partes.append(filas[inicio][1].strip())
        
        # Buscar líneas adicionales del concepto
        fila_actual += 1
        while fila_actual < len(filas):
            fila = filas[fila_actual]
            
            # Si la primera columna tiene una nueva clave, terminamos
            if fila[0] and ValidadorClave.es_clave_valida(str(fila[0]).strip()):
                break
            
            # Si la primera columna está vacía pero hay texto en la segunda, es continuación
            if (not fila[0] or str(fila[0]).strip() == '') and len(fila) > 1 and fila[1]:
                texto_adicional = str(fila[1]).strip()
                if texto_adicional:
                    concepto_partes.append(texto_adicional)
                    fila_actual += 1
                else:
                    break
            else:
                break
        
        concepto_completo = " ".join(concepto_partes)
        return concepto_completo, fila_actual - 1
    
    
    def limpiar_valor_numerico(self, texto: str) -> Optional[float]:
        """
        Extrae valor numérico de un texto.
        
        Args:
            texto: Texto con el número
            
        Returns:
            Optional[float]: Valor numérico o None
        """
        if not texto:
            return None
        
        try:
            # Limpiar el texto
            texto = str(texto).strip()
            texto = texto.replace('$', '').replace(',', '').replace(' ', '')
            
            # Extraer número
            match = re.search(r'-?\d+\.?\d*', texto)
            if match:
                return float(match.group())
        except:
            pass
        
        return None
    
    
    def procesar_tabla_pdf(self, tabla: List[List[str]], 
                          nombre_archivo: str) -> List[ConceptoExtraido]:
        """
        Procesa una tabla extraída de un PDF y genera conceptos validados.
        
        Args:
            tabla: Tabla extraída del PDF
            nombre_archivo: Nombre del archivo PDF
            
        Returns:
            List[ConceptoExtraido]: Lista de conceptos extraídos
        """
        if not tabla or len(tabla) < 2:
            return []
        
        conceptos = []
        i = 0
        
        # Saltar encabezados (buscar primera fila con clave válida)
        while i < len(tabla):
            if tabla[i][0] and ValidadorClave.es_clave_valida(str(tabla[i][0]).strip()):
                break
            i += 1
        
        # Procesar filas con conceptos
        while i < len(tabla):
            fila = tabla[i]
            
            # Verificar si la fila tiene una clave válida
            if not fila[0] or not ValidadorClave.es_clave_valida(str(fila[0]).strip()):
                i += 1
                continue
            
            # Extraer datos básicos
            clave = str(fila[0]).strip()
            
            # Reconstruir concepto multilínea (TEST 3)
            concepto, ultima_fila = self.reconstruir_concepto_multilinea(tabla, i)
            
            # Extraer otros campos (ajustar índices según estructura)
            # Estructura esperada: CLAVE | CONCEPTO | UNID | CANT | P.U. | IMPORTE
            unidad = str(fila[2]).strip() if len(fila) > 2 and fila[2] else ""
            cantidad = self.limpiar_valor_numerico(fila[3]) if len(fila) > 3 else None
            precio_unitario = self.limpiar_valor_numerico(fila[4]) if len(fila) > 4 else None
            importe = self.limpiar_valor_numerico(fila[5]) if len(fila) > 5 else None
            
            # Crear concepto
            concepto_obj = ConceptoExtraido(
                clave=clave,
                concepto_original=concepto,
                unidad=unidad,
                cantidad=cantidad or 0,
                precio_unitario=precio_unitario or 0,
                importe=importe or 0,
                origen_pdf=nombre_archivo,
                numero_linea=i + 1
            )
            
            # Aplicar validaciones (TEST 4 y TEST 5)
            self.aplicar_validaciones(concepto_obj)
            
            conceptos.append(concepto_obj)
            
            # Avanzar al siguiente concepto
            i = ultima_fila + 1
        
        return conceptos
    
    
    def aplicar_validaciones(self, concepto: ConceptoExtraido):
        """
        Aplica todas las validaciones a un concepto.
        
        Args:
            concepto: Concepto a validar
        """
        # TEST 4: Validación semántica
        es_valida, error = ValidadorSemantico.validar_clave(concepto.clave)
        if not es_valida:
            concepto.errores.append(error)
        
        es_valida, error = ValidadorSemantico.validar_unidad(concepto.unidad)
        if not es_valida:
            concepto.errores.append(error)
        
        es_valida, error = ValidadorSemantico.validar_concepto(concepto.concepto_original)
        if not es_valida:
            concepto.advertencias.append(error)
        
        # TEST 5: Validación numérica
        es_valida, error = ValidadorNumerico.validar_coherencia(
            concepto.cantidad,
            concepto.precio_unitario,
            concepto.importe
        )
        if not es_valida:
            concepto.errores.append(error)
    
    
    def procesar_pdf(self, ruta_pdf: str) -> ResultadoValidacionPDF:
        """
        Procesa un PDF completo con todos los tests de validación.
        
        Args:
            ruta_pdf: Ruta del archivo PDF
            
        Returns:
            ResultadoValidacionPDF: Resultado de la validación
        """
        nombre_archivo = os.path.basename(ruta_pdf)
        resultado = ResultadoValidacionPDF(
            nombre_archivo=nombre_archivo,
            es_valido=False,
            es_plantilla_remaa=False
        )
        
        try:
            # TEST 1: Validar plantilla REMAA
            texto_completo = self.extraer_texto_completo_pdf(ruta_pdf)
            if not texto_completo:
                resultado.mensaje = "No se pudo extraer texto del PDF"
                return resultado
            
            es_remaa, mensaje = ValidadorPlantillaREMAA.validar(texto_completo)
            resultado.es_plantilla_remaa = es_remaa
            
            if not es_remaa:
                resultado.mensaje = mensaje
                resultado.tipos_error.append("PLANTILLA_NO_VALIDA")
                return resultado
            
            # TEST 2: Verificar que hay claves válidas en el documento
            claves_encontradas = ValidadorClave.extraer_claves(texto_completo)
            if not claves_encontradas:
                resultado.mensaje = "No se encontraron claves válidas en el PDF"
                resultado.tipos_error.append("SIN_CLAVES_VALIDAS")
                return resultado
            
            # Extraer tablas y conceptos
            conceptos_pdf = []
            with pdfplumber.open(ruta_pdf) as pdf:
                for num_pagina, pagina in enumerate(pdf.pages, 1):
                    tabla = self.extraer_tabla_con_contexto(pagina)
                    if tabla:
                        conceptos = self.procesar_tabla_pdf(tabla, nombre_archivo)
                        conceptos_pdf.extend(conceptos)
            
            # Validar que se extrajeron conceptos
            if not conceptos_pdf:
                resultado.mensaje = "No se pudieron extraer conceptos válidos"
                resultado.tipos_error.append("SIN_CONCEPTOS")
                return resultado
            
            # Contar errores y advertencias
            conceptos_validos = 0
            errores_criticos = 0
            advertencias_total = 0
            tipos_error_set = set()
            
            for concepto in conceptos_pdf:
                if not concepto.errores:
                    conceptos_validos += 1
                else:
                    errores_criticos += 1
                    tipos_error_set.update(concepto.errores)
                
                advertencias_total += len(concepto.advertencias)
            
            # Actualizar resultado
            resultado.es_valido = True
            resultado.conceptos_extraidos = len(conceptos_pdf)
            resultado.conceptos_validos = conceptos_validos
            resultado.errores_criticos = errores_criticos
            resultado.advertencias = advertencias_total
            resultado.tipos_error = list(tipos_error_set)
            resultado.mensaje = f"✓ Procesado correctamente: {conceptos_validos}/{len(conceptos_pdf)} conceptos válidos"
            
            # Agregar conceptos a la lista global
            self.conceptos_extraidos.extend(conceptos_pdf)
            
        except Exception as e:
            resultado.mensaje = f"Error al procesar: {str(e)}"
            resultado.tipos_error.append("ERROR_PROCESAMIENTO")
        
        return resultado
    
    
    def procesar_todos_los_pdfs(self):
        """Procesa todos los PDFs de la carpeta."""
        print("\n" + "="*80)
        print("🚀 INICIANDO EXTRACCIÓN DE CONCEPTOS REMAA v2.0")
        print("="*80 + "\n")
        
        if not self.validar_entorno():
            return
        
        pdfs = sorted(Path(self.carpeta_pdfs).glob("*.pdf"))
        
        print(f"📊 Total de PDFs a procesar: {len(pdfs)}\n")
        print("="*80)
        
        for idx, pdf_path in enumerate(pdfs, 1):
            print(f"\n[{idx}/{len(pdfs)}] 📄 {pdf_path.name}")
            print("-" * 80)
            
            resultado = self.procesar_pdf(str(pdf_path))
            self.resultados_validacion.append(resultado)
            
            # Mostrar resultado
            if resultado.es_plantilla_remaa and resultado.es_valido:
                print(f"   ✅ {resultado.mensaje}")
                if resultado.advertencias > 0:
                    print(f"   ⚠️  Advertencias: {resultado.advertencias}")
                self.pdfs_validos += 1
            else:
                print(f"   ❌ {resultado.mensaje}")
                if resultado.tipos_error:
                    print(f"   📋 Errores: {', '.join(resultado.tipos_error[:3])}")
                self.pdfs_ignorados += 1
            
            self.pdfs_procesados += 1
        
        # Calcular estadísticas finales
        self.total_conceptos = len(self.conceptos_extraidos)
        self.conceptos_validos = sum(1 for c in self.conceptos_extraidos if not c.errores)
        self.conceptos_con_errores = self.total_conceptos - self.conceptos_validos
        
        print("\n" + "="*80)
        print("✅ EXTRACCIÓN COMPLETADA")
        print("="*80)
        print(f"📊 Estadísticas:")
        print(f"   PDFs procesados:        {self.pdfs_procesados}/{self.total_pdfs}")
        print(f"   PDFs válidos (REMAA):   {self.pdfs_validos}")
        print(f"   PDFs ignorados:         {self.pdfs_ignorados}")
        print(f"   Conceptos extraídos:    {self.total_conceptos}")
        print(f"   Conceptos válidos:      {self.conceptos_validos}")
        print(f"   Requieren revisión:     {self.conceptos_con_errores}")
        print("="*80 + "\n")
    
    
    def generar_csv_master(self, nombre_archivo: str = "conceptos_master.csv"):
        """
        Genera el CSV maestro con los conceptos validados.
        
        Args:
            nombre_archivo: Nombre del archivo de salida
        """
        if not self.conceptos_extraidos:
            print("❌ No hay conceptos para exportar")
            return
        
        # Convertir a DataFrame
        datos = []
        for concepto in self.conceptos_extraidos:
            # Solo incluir conceptos sin errores críticos
            if not concepto.errores:
                datos.append({
                    'clave': concepto.clave,
                    'concepto_original': concepto.concepto_original,
                    'unidad': concepto.unidad,
                    'precio_unitario': concepto.precio_unitario,
                    'origen_pdf': concepto.origen_pdf
                })
        
        if not datos:
            print("❌ No hay conceptos válidos para exportar")
            return
        
        df = pd.DataFrame(datos)
        
        # Eliminar duplicados por clave (mantener el primero)
        df_unico = df.drop_duplicates(subset=['clave'], keep='first')
        
        # Guardar
        df_unico.to_csv(nombre_archivo, index=False, encoding='utf-8-sig')
        
        print(f"✅ Archivo generado: {nombre_archivo}")
        print(f"   Conceptos únicos: {len(df_unico)}")
        print(f"   Conceptos duplicados eliminados: {len(df) - len(df_unico)}")
    
    
    def generar_reporte_validacion(self, nombre_archivo: str = "reporte_validacion.csv"):
        """
        Genera el reporte detallado de validación.
        
        Args:
            nombre_archivo: Nombre del archivo de reporte
        """
        if not self.resultados_validacion:
            print("�� No hay resultados para reportar")
            return
        
        datos_reporte = []
        for resultado in self.resultados_validacion:
            datos_reporte.append({
                'archivo': resultado.nombre_archivo,
                'es_plantilla_remaa': 'SÍ' if resultado.es_plantilla_remaa else 'NO',
                'es_valido': 'SÍ' if resultado.es_valido else 'NO',
                'conceptos_extraidos': resultado.conceptos_extraidos,
                'conceptos_validos': resultado.conceptos_validos,
                'errores_criticos': resultado.errores_criticos,
                'advertencias': resultado.advertencias,
                'tipos_error': '; '.join(resultado.tipos_error) if resultado.tipos_error else '',
                'mensaje': resultado.mensaje
            })
        
        df_reporte = pd.DataFrame(datos_reporte)
        df_reporte.to_csv(nombre_archivo, index=False, encoding='utf-8-sig')
        
        print(f"✅ Reporte generado: {nombre_archivo}")
    
    
    def generar_log_detallado(self, nombre_archivo: str = "log_extraccion_v2.txt"):
        """
        Genera un log detallado de toda la operación.
        
        Args:
            nombre_archivo: Nombre del archivo de log
        """
        with open(nombre_archivo, 'w', encoding='utf-8') as f:
            f.write("="*80 + "\n")
            f.write("LOG DE EXTRACCIÓN DE CONCEPTOS REMAA v2.0\n")
            f.write("="*80 + "\n\n")
            f.write(f"Fecha de ejecución: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Carpeta procesada: {self.carpeta_pdfs}\n\n")
            
            f.write("ESTADÍSTICAS GENERALES:\n")
            f.write("-"*80 + "\n")
            f.write(f"PDFs encontrados:       {self.total_pdfs}\n")
            f.write(f"PDFs procesados:        {self.pdfs_procesados}\n")
            f.write(f"PDFs válidos (REMAA):   {self.pdfs_validos}\n")
            f.write(f"PDFs ignorados:         {self.pdfs_ignorados}\n")
            f.write(f"Conceptos extraídos:    {self.total_conceptos}\n")
            f.write(f"Conceptos válidos:      {self.conceptos_validos}\n")
            f.write(f"Requieren revisión:     {self.conceptos_con_errores}\n\n")
            
            f.write("DETALLE POR ARCHIVO:\n")
            f.write("="*80 + "\n\n")
            
            for resultado in self.resultados_validacion:
                f.write(f"📄 {resultado.nombre_archivo}\n")
                f.write(f"   Plantilla REMAA: {resultado.es_plantilla_remaa}\n")
                f.write(f"   Válido: {resultado.es_valido}\n")
                f.write(f"   Conceptos extraídos: {resultado.conceptos_extraidos}\n")
                f.write(f"   Conceptos válidos: {resultado.conceptos_validos}\n")
                f.write(f"   Errores críticos: {resultado.errores_criticos}\n")
                f.write(f"   Advertencias: {resultado.advertencias}\n")
                if resultado.tipos_error:
                    f.write(f"   Tipos de error: {', '.join(resultado.tipos_error)}\n")
                f.write(f"   Mensaje: {resultado.mensaje}\n")
                f.write("-"*80 + "\n\n")
            
            f.write("\nCONCEPTOS CON ERRORES/ADVERTENCIAS:\n")
            f.write("="*80 + "\n\n")
            
            for concepto in self.conceptos_extraidos:
                if concepto.errores or concepto.advertencias:
                    f.write(f"Clave: {concepto.clave}\n")
                    f.write(f"Archivo: {concepto.origen_pdf}\n")
                    f.write(f"Línea: {concepto.numero_linea}\n")
                    if concepto.errores:
                        f.write(f"Errores: {', '.join(concepto.errores)}\n")
                    if concepto.advertencias:
                        f.write(f"Advertencias: {', '.join(concepto.advertencias)}\n")
                    f.write("-"*80 + "\n\n")
        
        print(f"✅ Log detallado generado: {nombre_archivo}")
    
    
    def ejecutar_extraccion_completa(self):
        """Ejecuta el proceso completo de extracción y generación de reportes."""
        # Procesar PDFs
        self.procesar_todos_los_pdfs()
        
        if not self.conceptos_extraidos:
            print("\n❌ No se extrajeron conceptos válidos.")
            print("   Verifique que los PDFs tengan la estructura REMAA correcta.")
            return
        
        # Generar archivos de salida
        print("\n" + "="*80)
        print("📁 GENERANDO ARCHIVOS DE SALIDA")
        print("="*80 + "\n")
        
        self.generar_csv_master()
        self.generar_reporte_validacion()
        self.generar_log_detallado()
        
        print("\n" + "="*80)
        print("🎉 PROCESO COMPLETADO EXITOSAMENTE")
        print("="*80)
        print("\n📁 ARCHIVOS GENERADOS:")
        print("   1. conceptos_master.csv      → Base de conceptos validados (USAR EN MÓDULO 2)")
        print("   2. reporte_validacion.csv    → Detalle de validación por PDF")
        print("   3. log_extraccion_v2.txt     → Log completo del proceso")
        print("\n💡 SIGUIENTE PASO:")
        print("   Revisar reporte_validacion.csv para identificar PDFs con problemas.")
        print("   Usar conceptos_master.csv en el MÓDULO 2 (Sistema de Cotización).")
        print("\n")


# ============================================================================
# PUNTO DE ENTRADA
# ============================================================================

def main():
    """Función principal que ejecuta el extractor."""
    print("\n")
    print("╔" + "="*78 + "╗")
    print("║" + " "*78 + "║")
    print("║" + "  EXTRACTOR DE CONCEPTOS REMAA - VERSIÓN 2.0  ".center(78) + "║")
    print("║" + " "*78 + "║")
    print("╚" + "="*78 + "╝")
    print("\n")
    
    # Crear instancia del extractor
    extractor = ExtractorConceptosREMAA(carpeta_pdfs=r"C:\Users\melok\OneDrive\Documentos\REMAA\H1 _ HPIC - HOTEL PRESIDENTE INTER. CANCUN\pdf\archivos_PPTO")
    
    # Ejecutar proceso completo
    extractor.ejecutar_extraccion_completa()


if __name__ == "__main__":
    main()