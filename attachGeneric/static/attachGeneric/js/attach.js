document.addEventListener('DOMContentLoaded', () => {
    const dropArea = document.getElementById('dropArea');
    const dropMessage = document.getElementById('dropMessage');
    const fileList = document.getElementById('fileList');
    const fileInput = document.getElementById('fileInput');
    
    const errorMessageModalEl = document.getElementById('errorMessageModal');
    const errorMessageModal = errorMessageModalEl ? new bootstrap.Modal(errorMessageModalEl) : null;
    const errorMessageText = document.getElementById('errorMessageText');

    const discardConfirmModalEl = document.getElementById('discardConfirmationModal');
    const discardConfirmationModal = discardConfirmModalEl ? new bootstrap.Modal(discardConfirmModalEl) : null;
    
    const saveConfirmModalEl = document.getElementById('confirmConfirmationModal');
    const confirmConfirmationModal = saveConfirmModalEl ? new bootstrap.Modal(saveConfirmModalEl) : null;

    const successModalEl = document.getElementById('successMessageModal');
    const successMessageModal = successModalEl ? new bootstrap.Modal(successModalEl) : null;

    const discardButton = document.querySelector('.btn-outline-danger'); 
    const confirmButton = document.getElementById("confirmSaveBtn"); 
    const directorProgramaSelect = document.getElementById('directorPrograma');
    const confirmDiscardBtn = document.getElementById('confirmDiscardBtn');
    const confirmSaveBtnElement = document.getElementById('confirmSaveBtnModal');

    let selectedFiles = []; 

    if (directorProgramaSelect) {
        fetch('/attachGeneric/obtener-directores/') 
            .then(response => {
                if (!response.ok) {
                    return response.text().then(text => { 
                        throw new Error(`HTTP ${response.status} en obtener-directores: ${text.substring(0,100)}`); 
                    });
                }
                return response.json();
            })
            .then(data => {
                console.log('JS: Directores recibidos:', data);
                const optionsToRemove = directorProgramaSelect.querySelectorAll('option:not(:first-child)');
                optionsToRemove.forEach(option => option.remove());

                if (data && data.length > 0) {
                    data.forEach(director => {
                        if (director.id && director.nombre) {
                            const option = document.createElement('option');
                            option.value = director.id; 
                            option.textContent = director.nombre;
                            directorProgramaSelect.appendChild(option);
                        }
                    });
                } else {
                     if(directorProgramaSelect.options[0]) {
                        directorProgramaSelect.options[0].textContent = 'No hay directores';
                        directorProgramaSelect.options[0].disabled = true;
                     }
                }
            })
            .catch(error => {
                console.error('JS: Error al cargar los directores de programa:', error);
                if (errorMessageText && errorMessageModal) {
                    errorMessageText.textContent = `Error cargando directores: ${error.message}.`;
                    errorMessageModal.show();
                }
                 if (directorProgramaSelect && directorProgramaSelect.options[0]) {
                    directorProgramaSelect.options[0].textContent = 'Error al cargar';
                    directorProgramaSelect.options[0].disabled = true;
                }
            });
    } else {
        console.error("JS: Elemento select 'directorPrograma' no encontrado.");
    }

    function updateFileListDisplay() {
        if (!fileList || !dropMessage) { console.error("JS: fileList o dropMessage no encontrados."); return; }
        fileList.innerHTML = ''; 
        if (selectedFiles.length > 0) {
            dropMessage.style.display = 'none';
            fileList.style.display = 'flex';
            fileList.style.flexWrap = 'wrap';
            fileList.style.gap = '10px';
            selectedFiles.forEach(file => {
                const fileBlock = document.createElement('div');
                fileBlock.classList.add('file-block');
                fileBlock.style.cssText = 'display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; padding: 10px; border: 1px solid #ccc; border-radius: 5px; width: auto; margin-bottom: 0; max-width: 120px;';
                let fileIcon = document.createElement('i');
                fileIcon.classList.add('fas', 'fa-3x');
                fileIcon.style.marginBottom = '5px';
                if (file.type === 'application/pdf') {
                    fileIcon.classList.add('fa-file-pdf'); fileIcon.style.color = '#dc3545';
                } else if (file.type === 'application/zip' || file.type === 'application/x-zip-compressed') {
                    fileIcon.classList.add('fa-file-archive'); fileIcon.style.color = '#007bff';
                } else { fileIcon.classList.add('fa-file'); }
                const fileName = document.createElement('p');
                let truncatedName = file.name;
                const maxLength = 12; 
                if (truncatedName.length > maxLength) { truncatedName = truncatedName.substring(0, maxLength) + '...'; }
                fileName.textContent = truncatedName;
                fileName.classList.add('file-name');
                fileName.style.cssText = 'font-size: 0.7em; word-break: break-all; text-align: center; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; margin-bottom: 0;';
                fileBlock.appendChild(fileIcon); fileBlock.appendChild(fileName); fileList.appendChild(fileBlock);
            });
        } else {
            dropMessage.style.display = 'block';
            fileList.style.display = 'none';
        }
    }

    function handleFiles(files) {
        const newFiles = Array.from(files);
        for (const file of newFiles) {
            const isPdf = file.type === 'application/pdf';
            const isZip = file.type === 'application/zip' || file.type === 'application/x-zip-compressed';
            const currentPdfCount = selectedFiles.filter(f => f.type === 'application/pdf').length;
            const currentZipCount = selectedFiles.filter(f => f.type === 'application/zip' || f.type === 'application/x-zip-compressed').length;
            console.log('JS: File Type procesado:', file.type);
            if (isPdf && currentPdfCount < 4 && currentZipCount === 0) {
                selectedFiles.push(file);
            } else if (isZip && currentZipCount < 1 && currentPdfCount === 0 && selectedFiles.length === 0) {
                selectedFiles.push(file);
            } else {
                if(errorMessageText && errorMessageModal){
                    errorMessageText.textContent = 'Solo se permiten hasta 4 archivos PDF o 1 archivo ZIP.';
                    errorMessageModal.show();
                }
            }
        }
        updateFileListDisplay();
    }

    if(dropArea) {
        dropArea.addEventListener('dragover', (event) => { event.preventDefault(); dropArea.classList.add('dragover'); });
        dropArea.addEventListener('dragleave', () => { dropArea.classList.remove('dragover'); });
        dropArea.addEventListener('drop', (event) => {
            event.preventDefault(); dropArea.classList.remove('dragover');
            if(event.dataTransfer && event.dataTransfer.files) handleFiles(event.dataTransfer.files);
        });
        dropArea.addEventListener('click', () => { if(fileInput) fileInput.click(); });
    }
    const selectZipFolderBtn = document.getElementById('selectZipFolder');
    if(selectZipFolderBtn && fileInput) {
        selectZipFolderBtn.addEventListener('click', () => { fileInput.accept = '.zip'; fileInput.multiple = false; fileInput.click(); });
    }
    const selectPdfFilesBtn = document.getElementById('selectPdfFiles');
    if(selectPdfFilesBtn && fileInput) {
        selectPdfFilesBtn.addEventListener('click', () => { fileInput.accept = '.pdf'; fileInput.multiple = true; fileInput.click(); });
    }
    if(fileInput) {
        fileInput.addEventListener('change', () => { if(fileInput.files) handleFiles(fileInput.files); fileInput.value = ''; });
    }
    if(discardButton && discardConfirmationModal) {
        discardButton.addEventListener('click', () => {
            if (selectedFiles.length > 0 && directorProgramaSelect && directorProgramaSelect.value !== 'Seleccionar...') {
                discardConfirmationModal.show();
            } else if (directorProgramaSelect && directorProgramaSelect.value === 'Seleccionar...') {
                 if(errorMessageText && errorMessageModal){ errorMessageText.textContent = 'Por favor, seleccione un director de programa.'; errorMessageModal.show(); }
            }
        });
    }
    if(confirmButton && confirmConfirmationModal) {
        confirmButton.addEventListener('click', () => {
            if (selectedFiles.length > 0 && directorProgramaSelect && directorProgramaSelect.value !== 'Seleccionar...') {
                confirmConfirmationModal.show();
            } else if (directorProgramaSelect && directorProgramaSelect.value === 'Seleccionar...') {
                if(errorMessageText && errorMessageModal){ errorMessageText.textContent = 'Por favor, seleccione un director de programa.'; errorMessageModal.show(); }
            } else if (selectedFiles.length === 0) {
                 if(errorMessageText && errorMessageModal){ errorMessageText.textContent = 'Por favor, seleccione al menos un archivo.'; errorMessageModal.show(); }
            }
        });
    }
    if(confirmDiscardBtn && discardConfirmationModal) {
        confirmDiscardBtn.addEventListener('click', () => {
            selectedFiles = []; updateFileListDisplay(); 
            if(directorProgramaSelect) directorProgramaSelect.value = 'Seleccionar...';
            discardConfirmationModal.hide(); 
        });
    }

    if (confirmSaveBtnElement && confirmConfirmationModal) {
        confirmSaveBtnElement.addEventListener('click', (e) => {
            e.preventDefault();  
            if (selectedFiles.length === 0) {
                if(errorMessageText && errorMessageModal){ errorMessageText.textContent = 'Por favor, seleccione al menos un archivo.'; errorMessageModal.show(); }
                return;
            }
            if (!directorProgramaSelect || directorProgramaSelect.value === 'Seleccionar...') {
                 if(errorMessageText && errorMessageModal){ errorMessageText.textContent = 'Por favor, seleccione un director de programa.'; errorMessageModal.show(); }
                return;
            }
            confirmConfirmationModal.hide();
    
            const formData = new FormData();
            formData.append('directorPrograma', directorProgramaSelect.value);
            selectedFiles.forEach(file => { formData.append('archivos', file, file.name); });
            const idEventoEl = document.getElementById('id_evento');
            formData.append('id_evento', idEventoEl ? idEventoEl.value : '');

            // *** CORRECCIÓN IMPORTANTE PARA CSRF TOKEN ***
            const elFormularioDeSubidaParaToken = document.getElementById('formSubidaArchivos'); // ID de tu formulario
            const csrfTokenEl = elFormularioDeSubidaParaToken ? elFormularioDeSubidaParaToken.querySelector('[name=csrfmiddlewaretoken]') : null;
            
            if (csrfTokenEl) {
                formData.append('csrfmiddlewaretoken', csrfTokenEl.value);
            } else {
                console.error("JS: CSRF token no encontrado dentro de #formSubidaArchivos."); // Actualizado el ID
                if (errorMessageText && errorMessageModal) { errorMessageText.textContent = 'Error de seguridad (token CSRF). Recargue.'; errorMessageModal.show(); }
                return;
            }
            
            // *** CORRECCIÓN CRÍTICA AQUÍ PARA LA URL DE ENVÍO ***
            const elFormularioDeSubida = document.getElementById('formSubidaArchivos'); // Usa el ID de tu form en HTML
            if (!elFormularioDeSubida) {
                console.error("JS: ¡Error Crítico! No se encontró el formulario con ID 'formSubidaArchivos'. Verifica tu HTML.");
                if (errorMessageText && errorMessageModal) { errorMessageText.textContent = 'Error interno: Formulario no encontrado.'; errorMessageModal.show(); }
                return; 
            }
            const urlCorrecta = elFormularioDeSubida.action; 
            
            console.log('JS: --- FormData Entries ---');
            for (let [k,v] of formData.entries()) console.log(`JS: ${k}`, v);
            console.log('JS: Enviando a:', urlCorrecta); // Verificar que esta sea la URL de 'guardar_archivos_adjuntos'

            fetch(urlCorrecta, { 
                method: 'POST',
                body: formData,
            })
            .then(response => { 
                if (!response.ok) {
                    return response.text().then(text => {
                        console.error("JS: Respuesta no OK del servidor:", response.status, text.substring(0, 500));
                        try {
                            const errData = JSON.parse(text); 
                            throw { status: response.status, data: errData, isJson: true};
                        } catch (e) { 
                            throw new Error(`Error del servidor: ${response.status}. Respuesta no fue JSON.`);
                        }
                    });
                }
                return response.json(); 
            })
            .then(data => {
                console.log('JS: Respuesta del servidor (JSON):', data);
                if (data.error) {
                    if(errorMessageText && errorMessageModal){ errorMessageText.textContent = data.error; errorMessageModal.show(); }
                } else if (data.mensaje) { 
                    if(successMessageModal) successMessageModal.show();
                    const successModalElement = document.getElementById('successMessageModal');
                    if (successModalElement && successModalElement.dataset.redirecting !== 'true') {
                         setTimeout(() => {
                            if(successMessageModal) successMessageModal.hide();
                            selectedFiles = []; updateFileListDisplay();
                            if(directorProgramaSelect) directorProgramaSelect.value = 'Seleccionar...';
                        }, 3000);
                    }
                } else {
                     if(errorMessageText && errorMessageModal){ errorMessageText.textContent = "Respuesta inesperada del servidor."; errorMessageModal.show(); }
                }
            })
            .catch(error => { 
                console.error('JS: Error en fetch o procesando la respuesta:', error);
                let msg = 'Ocurrió un error al enviar los archivos.';
                if (error && error.data && error.data.error) { 
                    msg = error.data.error;
                } else if (error && error.message) { 
                    msg = error.message;
                }
                if(errorMessageText && errorMessageModal){ errorMessageText.textContent = msg; errorMessageModal.show(); }
            });
        });
    }
    updateFileListDisplay();
});
