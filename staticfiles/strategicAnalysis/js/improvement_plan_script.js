document.addEventListener('DOMContentLoaded', function() {
    console.log("Plan SIN Notas Script: DOMContentLoaded.");

    // --- Obtener URLs ---
    let SAVE_PLAN_AJAX_URL = '';
    let ETAPA4_URL = '';
    const jsUrlsElement = document.getElementById('jsUrls');
    console.log("Plan SIN Notas Script: jsUrlsElement:", jsUrlsElement);
    if (jsUrlsElement && jsUrlsElement.textContent) {
        try {
            const urls = JSON.parse(jsUrlsElement.textContent);
            SAVE_PLAN_AJAX_URL = urls.savePlanAjaxUrl;
            ETAPA4_URL = urls.etapa4Url;
            console.log("Plan SIN Notas Script: URLs:", { save: SAVE_PLAN_AJAX_URL, etapa4: ETAPA4_URL });
            if (!SAVE_PLAN_AJAX_URL || !ETAPA4_URL) {
                console.warn("Plan SIN Notas Script: URLs vacías. Verifica 'save_plan' y 'etapa_4' en la plantilla.");
            }
        } catch (e) {
            console.error("Plan SIN Notas Script: Error parseando URLs. Contenido:", jsUrlsElement.textContent, "Error:", e);
        }
    } else {
        console.error("Plan SIN Notas Script: 'jsUrls' no encontrado o vacío.");
    }

    // --- Elementos del DOM ---
    const planIdInput = document.getElementById('planMejoramientoId');
    console.log("Plan SIN Notas Script: planIdInput:", planIdInput);
    if (!planIdInput) {
        console.error("Plan SIN Notas Script: 'planMejoramientoId' no encontrado.");
        return;
    }
    const planId = planIdInput.value;
    console.log("Plan SIN Notas Script: planId:", planId);

    const planTextoElem = document.getElementById('planMejoramientoTexto');
    const statusMessageElem = document.getElementById('statusMessage');
    console.log("Plan SIN Notas Script: planTextoElem:", planTextoElem);
    console.log("Plan SIN Notas Script: statusMessageElem:", statusMessageElem);

    const cancelarPlanBtnOriginal = document.getElementById('cancelarPlanBtnOriginal');
    const enviarPlanBtnOriginal = document.getElementById('enviarPlanBtnOriginal'); // Botón de Guardar
    console.log("Plan SIN Notas Script: cancelarPlanBtnOriginal:", cancelarPlanBtnOriginal);
    console.log("Plan SIN Notas Script: enviarPlanBtnOriginal:", enviarPlanBtnOriginal);

    let confirmCancelModalInstance, confirmSaveModalInstance;
    const confirmCancelModalEl = document.getElementById('confirmCancelModal');
    const confirmSaveModalEl = document.getElementById('confirmSaveModal');
    console.log("Plan SIN Notas Script: confirmCancelModalEl:", confirmCancelModalEl);
    console.log("Plan SIN Notas Script: confirmSaveModalEl:", confirmSaveModalEl);

    if (typeof bootstrap === 'undefined' || typeof bootstrap.Modal === 'undefined') {
        console.error("Plan SIN Notas Script: Bootstrap.Modal no definido.");
    } else {
        if (confirmCancelModalEl) {
            try {
                confirmCancelModalInstance = new bootstrap.Modal(confirmCancelModalEl);
                console.log("Plan SIN Notas Script: Instancia confirmCancelModal creada.");
            } catch(e) { console.error("Plan SIN Notas Script: Error creando instancia de confirmCancelModal:", e); }
        } else { console.warn("Plan SIN Notas Script: confirmCancelModalEl no encontrado."); }

        if (confirmSaveModalEl) {
            try {
                confirmSaveModalInstance = new bootstrap.Modal(confirmSaveModalEl);
                console.log("Plan SIN Notas Script: Instancia confirmSaveModal creada.");
            } catch(e) { console.error("Plan SIN Notas Script: Error creando instancia de confirmSaveModal:", e); }
        } else { console.warn("Plan SIN Notas Script: confirmSaveModalEl no encontrado."); }
    }

    const confirmCancelYesBtn = document.getElementById('confirmCancelYesBtn');
    const confirmSaveYesBtn = document.getElementById('confirmSaveYesBtn');
    console.log("Plan SIN Notas Script: confirmCancelYesBtn:", confirmCancelYesBtn);
    console.log("Plan SIN Notas Script: confirmSaveYesBtn:", confirmSaveYesBtn);

    // --- Verificaciones de elementos ---
    if (!planTextoElem || !statusMessageElem ||
        !cancelarPlanBtnOriginal || !enviarPlanBtnOriginal ||
        !confirmCancelModalInstance || !confirmSaveModalInstance ||
        !confirmCancelYesBtn || !confirmSaveYesBtn) {
        console.error("Plan SIN Notas Script: Uno o más elementos/instancias requeridos no fueron encontrados. El script se detendrá.");
        return;
    }
    console.log("Plan SIN Notas Script: Todos los elementos e instancias listos.");

    // --- Lógica para habilitar/deshabilitar el botón Guardar ---
    function toggleSaveButtonState() {
        if (planTextoElem && enviarPlanBtnOriginal) {
            const planText = planTextoElem.value.trim();
            if (planText.length > 0) {
                enviarPlanBtnOriginal.disabled = false;
            } else {
                enviarPlanBtnOriginal.disabled = true;
            }
        }
    }

    toggleSaveButtonState();

    if (planTextoElem) {
        planTextoElem.addEventListener('input', toggleSaveButtonState);
        console.log("Plan SIN Notas Script: Event listener 'input' añadido a planTextoElem.");
    }

    function performSave() {
        console.log("Plan SIN Notas Script: performSave() llamado.");
        statusMessageElem.textContent = 'Guardando...';
        statusMessageElem.className = 'status-message float-start';

        const dataToSend = {
            plan_id: planId,
            plan_texto: planTextoElem.value,
            notas_texto: ""
        };
        console.log("Plan SIN Notas Script: Datos a enviar:", dataToSend);

        if (!SAVE_PLAN_AJAX_URL) {
            console.error("Plan SIN Notas Script: SAVE_PLAN_AJAX_URL no definida.");
            statusMessageElem.textContent = 'Error: URL de guardado no encontrada.';
            statusMessageElem.classList.add('status-error');
            return;
        }
        console.log("Plan SIN Notas Script: Enviando fetch a:", SAVE_PLAN_AJAX_URL);

        fetch(SAVE_PLAN_AJAX_URL, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') },
            body: JSON.stringify(dataToSend)
        })
            .then(response => { /* ... manejo de respuesta ... */
                console.log("Plan SIN Notas Script: Respuesta fetch, status:", response.status);
                if (!response.ok) {
                    return response.json().then(errData => { throw { status: response.status, data: errData }; })
                        .catch(() => { throw { status: response.status, data: { message: `Error HTTP ${response.status}` }}; });
                }
                return response.json();
            })
            .then(data => { /* ... manejo de datos ... */
                console.log("Plan SIN Notas Script: Datos JSON de respuesta:", data);
                if (data.status === 'success') {
                    statusMessageElem.textContent = data.message || 'Guardado exitosamente.';
                    statusMessageElem.classList.add('status-success');
                } else {
                    statusMessageElem.textContent = data.message || 'Error al guardar.';
                    statusMessageElem.classList.add('status-error');
                }
                setTimeout(() => { statusMessageElem.textContent = ''; statusMessageElem.className = 'status-message float-start'; }, 5000);
            })
            .catch(error => {
                console.error('Plan SIN Notas Script: Error en fetch (guardado):', error);
                const errorMessage = (error.data && error.data.message) ? error.data.message : 'Error de conexión.';
                statusMessageElem.textContent = errorMessage;
                statusMessageElem.classList.add('status-error');
                setTimeout(() => { statusMessageElem.textContent = ''; statusMessageElem.className = 'status-message float-start'; }, 7000);
            });
    }

    cancelarPlanBtnOriginal.addEventListener('click', function() {
        console.log("Plan SIN Notas Script: Cancelar Original clickeado.");
        if (confirmCancelModalInstance) confirmCancelModalInstance.show();
        else console.error("Plan SIN Notas Script: confirmCancelModalInstance no definida.");
    });

    confirmCancelYesBtn.addEventListener('click', function() {
        console.log("Plan SIN Notas Script: Sí (Cancelar Modal) clickeado.");
        if (!ETAPA4_URL) {
            console.error("Plan SIN Notas Script: ETAPA4_URL no definida.");
            alert("Error: No se puede redirigir.");
            if(confirmCancelModalInstance) confirmCancelModalInstance.hide();
            return;
        }
        console.log("Plan SIN Notas Script: Redirigiendo a ETAPA4_URL:", ETAPA4_URL);
        window.location.href = ETAPA4_URL;
    });

    enviarPlanBtnOriginal.addEventListener('click', function() {
        console.log("Plan SIN Notas Script: Enviar Original clickeado.");
        if (confirmSaveModalInstance) confirmSaveModalInstance.show();
        else console.error("Plan SIN Notas Script: confirmSaveModalInstance no definida.");
    });

    confirmSaveYesBtn.addEventListener('click', function() {
        console.log("Plan SIN Notas Script: Sí (Guardar Modal) clickeado.");
        performSave();
        if(confirmSaveModalInstance) confirmSaveModalInstance.hide();
    });

    console.log("Plan SIN Notas Script: Event listeners principales adjuntados.");

    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
});