document.addEventListener('DOMContentLoaded', function () {
    const saveDofaButton = document.getElementById('saveDofaButton');
    const confirmSaveModalElement = document.getElementById('confirmSaveDofaModal');
    if (!confirmSaveModalElement) {
        console.error('Modal with ID "confirmSaveDofaModal" not found.');
        return;
    }
    const confirmSaveModal = new bootstrap.Modal(confirmSaveModalElement);

    const confirmSaveYesButton = document.getElementById('confirmSaveDofaYes');

    // Get CSRF token from the hidden input in the form/page
    const csrfTokenInput = document.querySelector('input[name="csrfmiddlewaretoken"]');
    if (!csrfTokenInput) {
        console.error('CSRF token input not found.');
        return;
    }
    const csrfToken = csrfTokenInput.value;

    if (saveDofaButton) {
        saveDofaButton.addEventListener('click', function () {
            confirmSaveModal.show();
        });
    }

    if (confirmSaveYesButton) {
        confirmSaveYesButton.addEventListener('click', function () {
            const fortalezasData = document.getElementById('fortalezas-json').value;
            const debilidadesData = document.getElementById('debilidades-json').value;
            const oportunidadesData = document.getElementById('oportunidades-json').value;
            const amenazasData = document.getElementById('amenazas-json').value;

            const payload = {
                fortalezas: fortalezasData,
                debilidades: debilidadesData,
                oportunidades: oportunidadesData,
                amenazas: amenazasData,
            };
            const saveUrl = '/home/etapa4/matrixDOFA/saveDOFA';

            fetch(saveUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken, // Crucial for Django POST requests
                },
                body: JSON.stringify(payload),
            })
                .then(response => {
                    if (!response.ok) {
                        // Try to parse error response if it's JSON, otherwise use statusText
                        return response.json().catch(() => {
                            throw new Error(`Error del servidor: ${response.status} ${response.statusText}`);
                        }).then(errData => {
                            throw new Error(errData.message || `Error del servidor: ${response.status}`);
                        });
                    }
                    return response.json();
                })
                .then(data => {
                    confirmSaveModal.hide();
                    if (data.status === 'success') {
                        alert(data.message || '¡DOFA guardado exitosamente!');
                    } else {
                        // Error message is already handled by the !response.ok block mostly
                        alert(data.message || 'Ocurrió un error al guardar.');
                    }
                })
                .catch((error) => {
                    confirmSaveModal.hide();
                    console.error('Error en la solicitud Fetch:', error);
                    alert('Error al guardar: ' + error.message);
                });
        });
    }
});