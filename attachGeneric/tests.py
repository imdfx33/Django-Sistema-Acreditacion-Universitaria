import os

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from database.models import File


class ViewsTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Crear usuarios para pruebas
        User = get_user_model()
        cls.superadmin = User.objects.create_superuser(
            cedula='123456789',
            email='admin@gmail.com',
            password='supersecret',
            first_name='Ana',
            last_name='García'
        )
        cls.user = User.objects.create_user(
            cedula='987654321',
            email='user@gmail.com',
            password='password',
            first_name='Pepe',
            last_name='López',
            rol='lector'
        )
        # URL's
        cls.obtener_directores_url = reverse('obtener_directores_programa')
        cls.guardar_archivos_url = reverse('guardar_archivos_adjuntos')

    def setUp(self):
        self.client.force_login(self.superadmin)  # Log in as superadmin for most tests

    def tearDown(self):
        # Limpiar archivos subidos durante las pruebas
        for file in File.objects.all():
            if os.path.exists(file.archivo.path):
                os.remove(file.archivo.path)
            file.archivo.delete(save=False) #delete file field

    def test_obtener_directores_programa(self):
        response = self.client.get(self.obtener_directores_url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['id'], str(self.superadmin.cedula))  # Usa el valor de la instancia
        self.assertEqual(data[0]['nombre'], 'Ana García')

    def test_guardar_archivos_adjuntos_valido(self):
        archivo_prueba = SimpleUploadedFile(
            'archivo_prueba.pdf', b'Contenido del archivo', content_type='application/pdf'
        )
        response = self.client.post(self.guardar_archivos_url, {
            'archivos': archivo_prueba,
            'directorPrograma': self.superadmin.first_name,
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['mensaje'], 'Archivos guardados exitosamente.')
        self.assertEqual(File.objects.count(), 1)
        file_guardado = File.objects.first()
        self.assertEqual(file_guardado.name, 'archivo_prueba')
        self.assertEqual(file_guardado.type, 'pdf')
        # Verificar que el archivo realmente existe
        self.assertTrue(os.path.exists(file_guardado.archivo.path))

    def test_guardar_archivos_adjuntos_tipo_invalido(self):
        archivo_prueba = SimpleUploadedFile(
            'archivo_prueba.txt', b'Contenido del archivo', content_type='text/plain'
        )
        response = self.client.post(self.guardar_archivos_url, {
            'archivos': archivo_prueba,
            'directorPrograma': self.superadmin.first_name,
        })
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], 'Tipo de archivo no permitido: archivo_prueba.txt')

    def test_guardar_archivos_adjuntos_sin_archivo(self):
        response = self.client.post(self.guardar_archivos_url, {
            'directorPrograma': self.superadmin.first_name
        })
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], 'No se recibieron archivos.')