// reports/static/reports/js/informe.js
document.addEventListener('DOMContentLoaded', () => {
    const generateButton = document.getElementById('btn-generate-final-report');
    const spinner = document.getElementById('final-report-spinner');
    const messageContainer = document.getElementById('final-report-message'); // Para mostrar errores o feedback

    if (!generateButton) {
        // console.log("Botón de generar informe no encontrado en esta página.");
        return;
    }
    if (!spinner) {
        console.error("Elemento spinner no encontrado.");
        return;
    }
    if (!messageContainer) {
        console.warn("Contenedor de mensajes 'final-report-message' no encontrado.");
    }

    // Obtener el token CSRF
    let csrfToken = null;
    const csrfInput = document.querySelector("input[name='csrfmiddlewaretoken']");
    if (csrfInput) {
        csrfToken = csrfInput.value;
    } else {
        // Intentar obtener de las cookies si no está en un input (menos común para AJAX POST puro)
        const csrfCookie = document.cookie.split('; ').find(row => row.startsWith('csrftoken='));
        if (csrfCookie) {
            csrfToken = csrfCookie.split('=')[1];
        }
    }

    if (!csrfToken) {
        console.error("CSRF token no encontrado. La petición AJAX fallará.");
        if (messageContainer) messageContainer.innerHTML = `<div class="alert alert-danger">Error de configuración: Falta token CSRF.</div>`;
        return;
    }

    generateButton.addEventListener('click', () => {
        generateButton.disabled = true;
        spinner.style.display = 'inline-block';
        if (messageContainer) messageContainer.innerHTML = ''; // Limpiar mensajes previos

        fetch("{% url 'reports:generate_final_report' %}", { // Usar la URL nombrada de Django
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken,
                'X-Requested-With': 'XMLHttpRequest', // Para que request.is_ajax() funcione si se usa
            },
            body: JSON.stringify({}), // Cuerpo vacío si no se envían datos adicionales
        })
        .then(response => {
            // Verificar si la respuesta es JSON antes de intentar parsearla
            const contentType = response.headers.get("content-type");
            if (contentType && contentType.indexOf("application/json") !== -1) {
                return response.json().then(data => ({ status: response.status, body: data }));
            } else {
                return response.text().then(text => ({ status: response.status, body: text }));
            }
        })
        .then(result => {
            const { status, body } = result;
            if (status === 200 && typeof body === 'object' && body.status === 'ok') {
                if (messageContainer) {
                     messageContainer.innerHTML = `<div class="alert alert-success">${body.message || "Proceso iniciado. La página se recargará."}</div>`;
                } else {
                    alert(body.message || "Proceso iniciado. La página se recargará.");
                }
                // Recargar la página para ver el nuevo enlace al informe
                setTimeout(() => {
                    window.location.reload();
                }, 3000); // Esperar 3 segundos para que el usuario lea el mensaje
            } else {
                let errorMessage = "Error desconocido al generar el informe.";
                if (typeof body === 'object' && body.error) {
                    errorMessage = body.error;
                } else if (typeof body === 'string') {
                    errorMessage = body; // Si la respuesta no fue JSON pero hubo texto
                }
                console.error('Error en la respuesta:', status, body);
                if (messageContainer) {
                    messageContainer.innerHTML = `<div class="alert alert-danger">${errorMessage}</div>`;
                } else {
                    alert(errorMessage);
                }
            }
        })
        .catch(error => {
            console.error('Error en la petición fetch:', error);
            const userMessage = "Error de red o del servidor al intentar generar el informe.";
            if (messageContainer) {
                messageContainer.innerHTML = `<div class="alert alert-danger">${userMessage}</div>`;
            } else {
                alert(userMessage);
            }
        })
        .finally(() => {
            generateButton.disabled = false;
            spinner.style.display = 'none';
        });
    });
});
