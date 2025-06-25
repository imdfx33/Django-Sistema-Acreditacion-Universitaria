// reports/static/reports/js/informe.js
document.addEventListener('DOMContentLoaded', () => {
    const generateButton = document.getElementById('btn-generate-final-report');
    const spinnerAssembly = document.getElementById('spinner-assembly'); // Cambiado de 'final-report-spinner'
    const messageContainer = document.getElementById('final-report-message'); // [cite: 285] (referencia al uso del id)

    if (!generateButton) {
        // console.log("Botón de generar informe no encontrado en esta página."); // [cite: 286]
        return;
    }

    // MODIFICADO: Verificar spinnerAssembly en lugar de spinner
    if (!spinnerAssembly) {
        console.error("Elemento spinner-assembly (para spinner y texto) no encontrado.");
        return;
    }
    // if (!messageContainer) { // [cite: 287]
    //     console.warn("Contenedor de mensajes 'final-report-message' no encontrado."); // [cite: 288]
    // }

    let csrfToken = null;
    const csrfInput = document.querySelector("input[name='csrfmiddlewaretoken']"); // [cite: 289]
    if (csrfInput) {
        csrfToken = csrfInput.value; // [cite: 290]
    } else {
        const csrfCookie = document.cookie.split('; ').find(row => row.startsWith('csrftoken=')); // [cite: 290]
        if (csrfCookie) {
            csrfToken = csrfCookie.split('=')[1]; // [cite: 291]
        }
    }

    const generateUrl = generateButton.dataset.generateUrl; // [cite: 293]
    if (!generateUrl) {
        console.error("No se encontró data-generate-url en el botón."); // [cite: 293]
        if (messageContainer) {
            messageContainer.innerHTML = `<div class="alert alert-danger" role="alert">Error de configuración: URL para generar informe no encontrada.</div>`; // [cite: 294]
        }
        return; // [cite: 295]
    }

    if (generateUrl.startsWith('{%') || generateUrl.includes('%}')) { // [cite: 297]
        console.error("URL de generación malformada o no resuelta en la plantilla:", generateUrl); // [cite: 298]
        if (messageContainer) {
            messageContainer.innerHTML = `<div class="alert alert-danger" role="alert">Error crítico de configuración: La URL para generar el informe no es válida. Por favor, contacte al administrador. (Detalle: URL no resuelta en plantilla)</div>`; // [cite: 299]
        }
        generateButton.disabled = true; // [cite: 300]
        return; // [cite: 301]
    }

    if (!csrfToken) {
        console.error("CSRF token no encontrado. La petición AJAX fallará."); // [cite: 302]
        if (messageContainer) {
            messageContainer.innerHTML = `<div class="alert alert-danger" role="alert">Error de configuración: Falta token CSRF. Recargue la página.</div>`; // [cite: 303]
        }
        return; // [cite: 305]
    }

    generateButton.addEventListener('click', () => {
        generateButton.disabled = true;
        // MODIFICADO: Mostrar spinnerAssembly (que contiene el spinner y el texto)
        if (spinnerAssembly) spinnerAssembly.style.display = 'flex'; // Usar 'flex' como se definió en el CSS para #spinner-assembly
        if (messageContainer) messageContainer.innerHTML = '';

        fetch(generateUrl, { // [cite: 305]
            method: 'POST', // [cite: 306]
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken,
                'X-Requested-With': 'XMLHttpRequest', // [cite: 306]
            },
            body: JSON.stringify({}), // [cite: 307]
        })
        .then(response => {
            const contentType = response.headers.get("content-type"); // [cite: 308]
            if (contentType && contentType.indexOf("application/json") !== -1) { // [cite: 308]
                return response.json().then(data => ({ ok: response.ok, status: response.status, body: data })); // [cite: 308]
            } else {
                return response.text().then(text => ({ ok: response.ok, status: response.status, body: text })); // [cite: 309]
            }
        })
        .then(result => {
            const { ok, status, body } = result; // [cite: 310]
            let messageText = "";
            let messageType = "danger";

            if (ok && typeof body === 'object' && body.status === 'ok') { // [cite: 311]
                messageText = body.message || "Proceso iniciado correctamente. La página se recargará en breve.";
                messageType = "success";
                setTimeout(() => { // [cite: 312]
                    window.location.reload();
                }, 3000);
            } else {
                if (typeof body === 'object' && body.error) { // [cite: 313]
                    messageText = body.error;
                } else if (typeof body === 'string') { // [cite: 314]
                    messageText = `Error ${status}: ${body.substring(0, 200)}...`; // [cite: 315]
                } else {
                    messageText = `Error ${status} al generar el informe. Respuesta no esperada del servidor.`; // [cite: 316]
                }
                console.error('Error en la respuesta del servidor:', status, body); // [cite: 318]
            }

            if (messageContainer) {
                messageContainer.innerHTML = `<div class="alert alert-${messageType}" role="alert">${messageText}</div>`; // [cite: 319]
            } else {
                alert(messageText); // [cite: 319]
            }
        })
        .catch(error => {
            console.error('Error en la petición fetch:', error); // [cite: 320]
            const userMessage = "Error de red o del servidor al intentar generar el informe. Verifique la consola para más detalles.";
            if (messageContainer) { // [cite: 320]
                messageContainer.innerHTML = `<div class="alert alert-danger" role="alert">${userMessage}</div>`; // [cite: 321]
            } else {
                alert(userMessage);
            }
        })
        .finally(() => { // [cite: 322]
            if (!(messageContainer && messageContainer.querySelector('.alert-success'))) {
                 generateButton.disabled = false;
            }
            // MODIFICADO: Ocultar spinnerAssembly
            if (spinnerAssembly) spinnerAssembly.style.display = 'none'; // [cite: 323] (referencia al ocultamiento del spinner anterior)
        }); // [cite: 324]
    });
});