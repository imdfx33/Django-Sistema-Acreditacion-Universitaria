# reports/management/commands/generar_informe.py
import io
import logging
from datetime import datetime

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils.html import strip_tags
from django.utils.text import slugify
# MODIFICADO: Asegurar que timezone de django.utils esté disponible
from django.utils import timezone # Anteriormente podrías haber tenido 'from django.utils.timezone import now'
import locale # Importar el módulo locale

from projects.models import Project
from factorManager.models import Factor
from traitManager.models import Trait
from aspectManager.models import Aspect
from reports.models import FinalReport
from reports.google_utils import (
    get_drive_service, get_docs_service, download_google_doc_content,
    create_google_doc, batch_update_google_doc, export_doc_as_pdf,
    upload_file_to_drive, set_file_public_readable, list_files_in_folder
)

logger = logging.getLogger(__name__)
User = get_user_model()

class Command(BaseCommand):
    help = "Genera el Informe Final consolidado de proyectos, lo sube a Google Drive y guarda el enlace."

    def add_arguments(self, parser):
        parser.add_argument(
            "--user-id",
            type=int,
            help="ID del usuario que dispara la generación, para registrar autoría.",
        )
        parser.add_argument(
            "--project-ids",
            nargs='+',
            type=str,
            help="(Opcional) IDs específicos de proyectos a incluir. Si no se provee, incluye todos los finalizados.",
        )

    # _add_text_request (sin cambios)
    def _add_text_request(self, text, heading_level=None, bold=False, italic=False, underline=False, bullet=False):
        requests = []
        if not text:
            return requests
        if not text.endswith('\n'):
            text += '\n'
        insert_text_request = {"insertText": {"location": {"index": 1}, "text": text}}
        requests.append(insert_text_request)
        text_len = len(text)
        style_requests = []
        if heading_level:
            style_requests.append({
                "updateParagraphStyle": {
                    "range": {"startIndex": 1, "endIndex": text_len},
                    "paragraphStyle": {"namedStyleType": f"HEADING_{heading_level}"},
                    "fields": "namedStyleType, Varia",
                }
            })
        text_style = {}
        if bold: text_style['bold'] = True
        if italic: text_style['italic'] = True
        if underline: text_style['underline'] = True
        if text_style:
            style_requests.append({
                "updateTextStyle": {
                    "range": {"startIndex": 1, "endIndex": text_len -1},
                    "textStyle": text_style,
                    "fields": ",".join(text_style.keys())
                }
            })
        if bullet:
            style_requests.append({
                "createParagraphBullets": {
                    "range": {"startIndex": 1, "endIndex": text_len -1 },
                    "bulletPreset": "BULLET_DISC_CIRCLE_SQUARE"
                }
            })
        return requests

    def handle(self, *args, **opts):
        self.stdout.write(self.style.NOTICE("Iniciando la generación del informe final..."))

        requesting_user = None
        if user_id := opts.get("user_id"):
            try:
                requesting_user = User.objects.get(pk=user_id)
            except User.DoesNotExist:
                raise CommandError(f"Usuario con ID {user_id} no encontrado.")

        drive_service = get_drive_service()
        docs_service = get_docs_service()

        if not drive_service or not docs_service:
            raise CommandError("No se pudieron inicializar los servicios de Google. Verifica las credenciales y scopes.")

        # --- INICIO DE MODIFICACIONES PARA FECHA Y HORA LOCAL ---
        
        # 1. Configurar el locale para nombres de meses en español
        # Intentamos con varias configuraciones comunes para español Colombia y español genérico.
        spanish_locales_to_try = ['es_CO.UTF-8', 'Spanish_Colombia', 'es_ES.UTF-8', 'es_ES', 'Spanish_Spain', 'es']
        locale_set_successfully = False
        original_locale = locale.getlocale(locale.LC_TIME) # Guardar locale original

        for loc_name in spanish_locales_to_try:
            try:
                locale.setlocale(locale.LC_TIME, loc_name)
                # self.stdout.write(self.style.SUCCESS(f"Locale para LC_TIME configurado a: {loc_name}"))
                locale_set_successfully = True
                break
            except locale.Error:
                # self.stdout.write(self.style.WARNING(f"No se pudo configurar locale a: {loc_name}"))
                pass
        
        if not locale_set_successfully:
            self.stdout.write(self.style.WARNING(
                "No se pudo establecer la configuración regional a español para los nombres de los meses. "
                "Los meses podrían aparecer en inglés."
            ))

        # 2. Obtener la hora actual convertida a la zona horaria de Django (configurada en settings.TIME_ZONE)
        # Asegúrate que settings.TIME_ZONE = 'America/Bogota' en tu archivo settings.py
        # timezone.now() devuelve la hora en UTC si USE_TZ=True
        # timezone.localtime() la convierte a la zona horaria definida en settings.TIME_ZONE
        current_local_time = timezone.localtime(timezone.now())

        # Formatear la fecha/hora para el título del informe
        report_title_timestamp_str = current_local_time.strftime('%Y-%m-%d %H:%M')
        report_title = f"Informe Final Consolidado - {report_title_timestamp_str}" # [cite: 243]

        # Formatear la fecha/hora para la portada (con nombre del mes)
        # %B usará el locale configurado previamente para el nombre del mes en español
        cover_page_timestamp_str = current_local_time.strftime('%d de %B de %Y a las %H:%M')
        # --- FIN DE MODIFICACIONES PARA FECHA Y HORA LOCAL ---


        if project_ids_str := opts.get("project_ids"):
            projects_qs = Project.objects.filter(id_project__in=project_ids_str, progress=100)
            if not projects_qs.exists() or projects_qs.count() != len(project_ids_str):
                # Restaurar locale antes de salir por error
                if locale_set_successfully: locale.setlocale(locale.LC_TIME, original_locale)
                raise CommandError("Alguno de los IDs de proyecto provistos no existe o no está finalizado.")
        else:
            projects_qs = Project.objects.filter(progress=100) # [cite: 241]
        
        if not projects_qs.exists():
            self.stdout.write(self.style.WARNING("No hay proyectos finalizados para incluir en el informe."))
            # Restaurar locale antes de salir
            if locale_set_successfully: locale.setlocale(locale.LC_TIME, original_locale)
            return

        projects_list = list(projects_qs.order_by('name').prefetch_related(
            'factors', 
            'factors__traits', 
            'factors__traits__aspects'
        )) # [cite: 242]
        num_projects = len(projects_list)

        new_doc_details = create_google_doc(docs_service, report_title) # [cite: 243]
        if not new_doc_details:
            # Restaurar locale antes de salir por error
            if locale_set_successfully: locale.setlocale(locale.LC_TIME, original_locale)
            raise CommandError("No se pudo crear el Google Doc base para el informe.")
        new_doc_id = new_doc_details['documentId']
        self.stdout.write(self.style.SUCCESS(f"Documento base de Google Docs creado con ID: {new_doc_id}"))

        doc_requests = []
        current_index = 1 

        # --- Portada ---
        cover_text = f"{report_title}\n"
        cover_text += f"Universidad Icesi\n"
        # Usar la cadena de fecha/hora ya formateada y localizada
        cover_text += f"Generado el: {cover_page_timestamp_str}\n" #
        if requesting_user:
            try:
                # CORRECCIÓN AQUÍ: Quitar los paréntesis
                user_full_name = requesting_user.get_full_name 
            except AttributeError: 
                user_full_name = requesting_user.username 
            cover_text += f"Generado por: {user_full_name}\n"
        cover_text += f"Número total de proyectos incluidos: {num_projects}\n\n"
        
        doc_requests.append({"insertText": {"location": {"index": current_index}, "text": cover_text}})
        doc_requests.append({
            "updateParagraphStyle": {
                "range": {"startIndex": current_index, "endIndex": current_index + len(report_title)},
                "paragraphStyle": {"namedStyleType": "TITLE"}, "fields": "namedStyleType"
            }
        })
        current_index += len(cover_text)

        # --- Contenido de Proyectos ---
        for project in projects_list:
            project_header_text = f"Proyecto: {project.name}\n"
            doc_requests.append({"insertText": {"location": {"index": current_index}, "text": project_header_text}})
            doc_requests.append({
                "updateParagraphStyle": {
                    "range": {"startIndex": current_index, "endIndex": current_index + len(project_header_text) -1 },
                    "paragraphStyle": {"namedStyleType": "HEADING_1"}, "fields": "namedStyleType"
                }
            })
            current_index += len(project_header_text)

            # Las fechas de inicio y fin del proyecto son DateField, no tienen hora, por lo que no necesitan conversión de zona horaria.
            project_details = f"  Fechas: {project.start_date.strftime('%Y-%m-%d')} - {project.end_date.strftime('%Y-%m-%d')}\n" # [cite: 253]
            project_details += f"  Descripción: {strip_tags(project.description) if project.description else 'N/A'}\n\n"
            doc_requests.append({"insertText": {"location": {"index": current_index}, "text": project_details}})
            current_index += len(project_details)

            for factor in project.factors.all().order_by('name'): # [cite: 254]
                factor_header_text = f"  Factor: {factor.name}\n"
                doc_requests.append({"insertText": {"location": {"index": current_index}, "text": factor_header_text}})
                doc_requests.append({
                    "updateParagraphStyle": {
                        "range": {"startIndex": current_index, "endIndex": current_index + len(factor_header_text) -1},
                        "paragraphStyle": {"namedStyleType": "HEADING_2"}, "fields": "namedStyleType"
                    }
                })
                current_index += len(factor_header_text)

                factor_details_text = f"    Ponderación: {factor.ponderation}%\n"
                if factor.document_id: # [cite: 256]
                    factor_doc_content = download_google_doc_content(docs_service, factor.document_id) # [cite: 257]
                    if factor_doc_content:
                        factor_details_text += f"    Contenido del Documento del Factor:\n{factor_doc_content}\n\n"
                    else:
                        factor_details_text += f"    (No se pudo cargar el contenido del documento del factor: {factor.document_link})\n\n" # [cite: 258]
                else:
                    factor_details_text += f"    (Sin documento de Drive asociado al factor)\n\n" # [cite: 258]
                
                doc_requests.append({"insertText": {"location": {"index": current_index}, "text": factor_details_text}})
                current_index += len(factor_details_text)

                for trait in factor.traits.all().order_by('name'): # [cite: 259]
                    trait_header_text = f"    Característica: {trait.name}\n"
                    doc_requests.append({"insertText": {"location": {"index": current_index}, "text": trait_header_text}})
                    doc_requests.append({
                        "updateParagraphStyle": {
                            "range": {"startIndex": current_index, "endIndex": current_index + len(trait_header_text) -1},
                            "paragraphStyle": {"namedStyleType": "HEADING_3"}, "fields": "namedStyleType"
                        }
                    })
                    current_index += len(trait_header_text)
                    
                    trait_weight_value = getattr(trait, 'weight', 'N/A') # [cite: 263]
                    trait_details_text = f"      Peso: {trait_weight_value}%\n" # [cite: 263]
                    trait_details_text += f"      Descripción: {strip_tags(trait.description) if trait.description else 'N/A'}\n\n" # [cite: 263]
                    doc_requests.append({"insertText": {"location": {"index": current_index}, "text": trait_details_text}})
                    current_index += len(trait_details_text)

                    for aspect in trait.aspects.all().order_by('name'):
                        aspect_status = "Aprobado" if aspect.approved else "Pendiente" # [cite: 264, 265]
                        aspect_weight_value = getattr(aspect, 'weight', 'N/A') # [cite: 265]
                        aspect_text = f"      - Aspecto: {aspect.name} (Peso: {aspect_weight_value}%, Estado: {aspect_status})\n" # [cite: 265]
                        aspect_text += f"        Descripción: {strip_tags(aspect.description) if aspect.description else 'N/A'}\n\n" # [cite: 266]
                        doc_requests.append({"insertText": {"location": {"index": current_index}, "text": aspect_text}})
                        current_index += len(aspect_text)
            
            doc_requests.append({"insertText": {"location": {"index": current_index}, "text": "\n"}}) 
            current_index +=1

        if not batch_update_google_doc(docs_service, new_doc_id, doc_requests):
            logger.error(f"Falló batchUpdate. Requests enviadas: {doc_requests}") # [cite: 267, 268]
            # Restaurar locale antes de salir por error
            if locale_set_successfully: locale.setlocale(locale.LC_TIME, original_locale)
            raise CommandError(f"No se pudo escribir el contenido en el Google Doc ID: {new_doc_id}")
        self.stdout.write(self.style.SUCCESS(f"Contenido consolidado en Google Doc: {new_doc_id}"))

        pdf_bytes = export_doc_as_pdf(drive_service, new_doc_id) # [cite: 268]
        if not pdf_bytes:
            # Restaurar locale antes de salir por error
            if locale_set_successfully: locale.setlocale(locale.LC_TIME, original_locale)
            raise CommandError(f"No se pudo exportar el Google Doc ID {new_doc_id} a PDF.")
        self.stdout.write(self.style.SUCCESS("Documento exportado a PDF."))

        pdf_file_name = f"{slugify(report_title)}.pdf"
        uploaded_pdf_details = upload_file_to_drive(
            drive_service,
            pdf_file_name,
            'application/pdf',
            pdf_bytes,
            settings.GOOGLE_DRIVE_REPORTS_FOLDER_ID
        ) # [cite: 270]
        if not uploaded_pdf_details:
            # Restaurar locale antes de salir por error
            if locale_set_successfully: locale.setlocale(locale.LC_TIME, original_locale)
            raise CommandError(f"No se pudo subir el PDF '{pdf_file_name}' a Google Drive.")
        
        pdf_drive_id = uploaded_pdf_details.get('id') # [cite: 271]
        pdf_webview_link = uploaded_pdf_details.get('webViewLink')  # [cite: 271]
        
        if not set_file_public_readable(drive_service, pdf_drive_id): # [cite: 271]
            self.stdout.write(self.style.WARNING(f"No se pudieron establecer permisos públicos para el PDF ID {pdf_drive_id}. El enlace podría no ser accesible.")) # [cite: 271]
        
        self.stdout.write(self.style.SUCCESS(f"PDF subido a Google Drive: {pdf_webview_link}"))

        FinalReport.objects.create(
            pdf_url=pdf_webview_link, 
            generated_by=requesting_user,
            generated_at=timezone.now() # Se guarda en UTC, lo cual es correcto para la BD
        ) # [cite: 272, 273]
        self.stdout.write(self.style.SUCCESS(f"Enlace al informe guardado en la base de datos."))
        
        # Restaurar el locale original al final de la ejecución exitosa
        if locale_set_successfully:
            try:
                locale.setlocale(locale.LC_TIME, original_locale)
                # self.stdout.write(self.style.NOTICE(f"Locale para LC_TIME restaurado a: {original_locale}"))
            except locale.Error:
                self.stdout.write(self.style.WARNING("No se pudo restaurar la configuración regional original."))

        self.stdout.write(self.style.SUCCESS("¡Informe Final generado y guardado exitosamente!"))