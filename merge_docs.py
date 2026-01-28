import os
import sys
import logging
import argparse
from pathlib import Path
from typing import List, Dict, Optional
import json
import pdfplumber
import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.units import inch
from reportlab.lib import colors
from openai import OpenAI  # ✅ Nueva sintaxis

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DocumentProcessor:
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)  # ✅ Nuevo cliente
        self.extracted_data = []

    def extract_pdf_text(self, pdf_path: Path) -> Optional[str]:
        """Extract text from PDF file"""
        try:
            text = ""
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            logger.info(f"✓ Extracted text from {pdf_path.name}")
            return text.strip()
        except Exception as e:
            logger.error(f"✗ Error reading {pdf_path.name}: {e}")
            return None

    def classify_document(self, text: str, filename: str) -> Optional[str]:
        """Classify document using ChatGPT API"""
        try:
            response = self.client.chat.completions.create(  # ✅ Nueva sintaxis
                model="gpt-3.5-turbo",
                messages=[{
                    "role": "user",
                    "content": f"""Clasifica este documento en UNA de estas categorías:
- Cotización
- Estimación
- Requisición
- Otro

Responde SOLO con la categoría, sin explicación.

Documento ({filename}):
{text[:1500]}"""
                }],
                temperature=0.3,
                max_tokens=10
            )
            classification = response.choices[0].message.content.strip()  # ✅ Nueva sintaxis
            logger.info(f"  Clasificación: {classification}")
            return classification if classification != "Otro" else None
        except Exception as e:
            logger.error(f"  Error en clasificación: {e}")
            return None

    def extract_items(self, text: str, filename: str) -> List[Dict]:
        """Extract items from relevant documents"""
        try:
            response = self.client.chat.completions.create(  # ✅ Nueva sintaxis
                model="gpt-3.5-turbo",
                messages=[{
                    "role": "user",
                    "content": f"""Extrae TODOS los productos/servicios del documento.
Para cada uno, devuelve JSON con esta estructura:
[{{"clave": "XXX", "concepto": "descripción", "categoria": "Materiales|Mano de Obra|Equipo|Herramienta|Subcontrato", "unidad": "pza/m²/m³/lt/kg/hr/día/etc", "precio_unitario": 0.00}}]

Si falta información, usa null. Devuelve SOLO el JSON, sin texto adicional.

Documento:
{text[:3000]}"""
                }],
                temperature=0.3,
                max_tokens=2000
            )
            
            json_str = response.choices[0].message.content.strip()  # ✅ Nueva sintaxis
            
            # Limpiar respuesta si viene con markdown
            if json_str.startswith("```"):
                json_str = json_str.split("```")[1]
                if json_str.startswith("json"):
                    json_str = json_str[4:]
            
            items = json.loads(json_str)
            logger.info(f"  ✓ Extraídos {len(items)} items")
            return items
        except json.JSONDecodeError as e:
            logger.warning(f"  ✗ Error parsing JSON: {e}")
            logger.debug(f"  Respuesta recibida: {json_str[:200]}")
            return []
        except Exception as e:
            logger.error(f"  ✗ Error en extracción: {e}")
            return []

    def process_pdfs(self, ruta: str) -> pd.DataFrame:
        """Process all PDFs in directory"""
        pdf_path = Path(ruta)
        if not pdf_path.exists():
            logger.error(f"❌ Ruta no existe: {ruta}")
            return pd.DataFrame()

        pdf_files = list(pdf_path.glob("*.pdf"))
        logger.info(f"\n🔍 Encontrados {len(pdf_files)} archivos PDF\n")

        stats = {"Cotización": 0, "Estimación": 0, "Requisición": 0, "Otros": 0}

        for idx, pdf_file in enumerate(pdf_files, 1):
            logger.info(f"[{idx}/{len(pdf_files)}] Procesando: {pdf_file.name}")
            
            # Extract text
            text = self.extract_pdf_text(pdf_file)
            if not text:
                stats["Otros"] += 1
                continue

            # Classify
            classification = self.classify_document(text, pdf_file.name)
            if not classification:
                logger.info(f"  → Descartado (clasificado como 'Otro')")
                stats["Otros"] += 1
                continue

            stats[classification] = stats.get(classification, 0) + 1

            # Extract items
            items = self.extract_items(text, pdf_file.name)
            for item in items:
                item['documento'] = pdf_file.name
                item['clasificacion'] = classification
                self.extracted_data.append(item)

        # Print statistics
        logger.info(f"\n📊 ESTADÍSTICAS DE CLASIFICACIÓN:")
        logger.info(f"   ├─ Cotizaciones: {stats.get('Cotización', 0)}")
        logger.info(f"   ├─ Estimaciones: {stats.get('Estimación', 0)}")
        logger.info(f"   ├─ Requisiciones: {stats.get('Requisición', 0)}")
        logger.info(f"   └─ Otros: {stats['Otros']}\n")

        return pd.DataFrame(self.extracted_data)

    def generate_pdf(self, df: pd.DataFrame, output_path: str):
        """Generate PDF catalog"""
        if df.empty:
            logger.warning("⚠️  No hay datos para generar PDF")
            return

        # Sort by category
        df_sorted = df.sort_values('categoria', na_position='last')
        
        # Prepare table data
        headers = ["Clave", "Concepto", "Categoría", "Unidad", "P.U."]
        data = [headers]
        
        for _, row in df_sorted.iterrows():
            data.append([
                str(row.get('clave') or '-'),
                str(row.get('concepto') or '-')[:40],  # Limitar a 40 caracteres
                str(row.get('categoria') or '-'),
                str(row.get('unidad') or '-'),
                f"${float(row.get('precio_unitario') or 0):.2f}"
            ])

        # Create PDF
        doc = SimpleDocTemplate(output_path, pagesize=letter)
        elements = []

        # Title
        styles = getSampleStyleSheet()
        title = Paragraph("<b>Catálogo de Productos</b>", styles['Title'])
        elements.append(title)
        elements.append(Spacer(1, 0.3 * inch))

        # Table with adjusted column widths
        col_widths = [0.8*inch, 2.5*inch, 1.2*inch, 0.8*inch, 1*inch]
        table = Table(data, colWidths=col_widths)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
        ]))
        elements.append(table)

        doc.build(elements)
        logger.info(f"✅ PDF generado: {output_path}")

        # Also save as Excel for easier editing
        excel_path = output_path.replace('.pdf', '.xlsx')
        df_sorted.to_excel(excel_path, index=False)
        logger.info(f"✅ Excel generado: {excel_path}")


def main():
    parser = argparse.ArgumentParser(
        description='Clasificar y extraer datos de PDFs de cotizaciones/estimaciones/requisiciones'
    )
    
    # ✅ CORREGIDO: Solo el nombre del argumento
    parser.add_argument(
        '--ruta', 
        required=True, 
        help='Ruta de la carpeta que contiene los archivos PDF a procesar'
    )
    
    parser.add_argument(
        '--output', 
        default='Catalogo_de_Productos.pdf',
        help='Ruta completa del archivo PDF de salida (catálogo)'
    )
    
    args = parser.parse_args()

    # ✅ CORREGIDO: Nombre de la variable de entorno
    api_key = os.getenv('OPENAI_API_KEY')
    
    if not api_key:
        logger.error("❌ Error: Variable OPENAI_API_KEY no configurada")
        logger.error("\nConfigúrala así:")
        logger.error("  PowerShell: $env:OPENAI_API_KEY='tu-api-key-aqui'")
        logger.error("  CMD:        set OPENAI_API_KEY=tu-api-key-aqui")
        logger.error("  Linux/Mac:  export OPENAI_API_KEY='tu-api-key-aqui'")
        sys.exit(1)

    logger.info("🚀 Iniciando procesamiento...\n")
    
    processor = DocumentProcessor(api_key)
    df = processor.process_pdfs(args.ruta)

    if not df.empty:
        logger.info(f"\n📋 Resumen por categoría:")
        category_counts = df['categoria'].value_counts()
        for categoria, count in category_counts.items():
            logger.info(f"   ├─ {categoria}: {count} conceptos")
        
        processor.generate_pdf(df, args.output)
        logger.info(f"\n✅ Proceso completado. {len(df)} items extraídos en total.")
    else:
        logger.warning("\n⚠️  No se extrajeron datos de ningún documento.")


if __name__ == "__main__":
    main()