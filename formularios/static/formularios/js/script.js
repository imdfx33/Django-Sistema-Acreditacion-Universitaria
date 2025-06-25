document.addEventListener('DOMContentLoaded', function() {
    const botonAgregarFormulario = document.getElementById('boton-agregar-formulario');
    const archivoFormularioInput = document.getElementById('archivo-formulario');
    const tablaFormularios = document.querySelector('.table-container table');
    const tablaFormulariosBody = tablaFormularios ? tablaFormularios.querySelector('tbody') : null;
    const header = document.querySelector('.navbar');
    const gestionFormulariosH2 = document.querySelector('h2');
    const container = document.querySelector('.container');
    const botonBottomOffset = 80;
    const espacioEntreTablaYBoton = 40;
    let containerPaddingTop = 0;
    let containerPaddingBottom = 0;

    if (container) {
        const computedStyle = getComputedStyle(container);
        containerPaddingTop = parseFloat(computedStyle.paddingTop) || 0;
        containerPaddingBottom = parseFloat(computedStyle.paddingBottom) || 0;
    }

    function ajustarMaxHeightTabla() {
        const headerHeight = header ? header.offsetHeight : 0;
        const h2Height = gestionFormulariosH2 ? gestionFormulariosH2.offsetHeight : 0;
        const botonHeight = botonAgregarFormulario ? botonAgregarFormulario.offsetHeight : 0;

        const alturaDisponible = window.innerHeight - headerHeight - h2Height - containerPaddingTop - containerPaddingBottom - botonHeight - botonBottomOffset - espacioEntreTablaYBoton - 20;

        if (tablaFormularios) {
            tablaFormularios.style.maxHeight = Math.max(100, alturaDisponible) + 'px';
        }
    }

    ajustarMaxHeightTabla();
    window.addEventListener('resize', ajustarMaxHeightTabla);

    if (botonAgregarFormulario && archivoFormularioInput) {
        botonAgregarFormulario.addEventListener('click', function() {
            archivoFormularioInput.click();
        });

        archivoFormularioInput.addEventListener('change', function() {
            this.form.submit();
        });
    }

    function crearElemento(tipo, clase, texto) {
        const elemento = document.createElement(tipo);
        if (clase) elemento.className = clase;
        if (texto) elemento.textContent = texto;
        return elemento;
    }

    function crearOpcionesEstado() {
        const opcionesDiv = crearElemento('div', 'estado-opciones');
        const estadosPosibles = ["Pendiente", "Finalizado", "En-curso"];
        estadosPosibles.forEach((opcion) => {
            const botonEstado = crearElemento('button', 'cambiar-estado', opcion);
            botonEstado.dataset.estado = opcion.toLowerCase().replace(' ', '-'); // Guarda el estado en minúsculas para la clase
            botonEstado.textContent = opcion; // Muestra el estado con la primera letra en mayúscula
            opcionesDiv.appendChild(botonEstado);
        });
        return opcionesDiv;
    }

    function inicializarEventListenersEstado() {
        document.querySelectorAll('.estado-celda > span').forEach(estadoSpan => {
            estadoSpan.addEventListener('click', function(event) {
                event.stopPropagation();
                document.querySelectorAll('.estado-opciones.show').forEach(otherOpciones => {
                    if (otherOpciones.parentNode !== this.parentNode) {
                        otherOpciones.classList.remove('show');
                    }
                });
                const opcionesCelda = this.parentNode.querySelector('.estado-opciones');
                if (opcionesCelda) {
                    opcionesCelda.classList.toggle('show');
                }
            });
        });

        document.querySelectorAll('.estado-opciones button').forEach(button => { // Selector más específico
            button.addEventListener('click', function(event) {
                event.stopPropagation();
                const nuevoEstadoTexto = this.textContent; // Obtiene el texto visible del botón
                const nuevoEstadoClase = this.dataset.estado; // Obtiene el estado en minúsculas para la clase
                const estadoTextoSpan = this.closest('.estado-celda').querySelector('span');
                const opcionesCelda = this.closest('.estado-opciones');

                estadoTextoSpan.textContent = nuevoEstadoTexto;
                estadoTextoSpan.className = nuevoEstadoClase;
                opcionesCelda.classList.remove('show');

                const rowIdElement = this.closest('tr').querySelector('.info-formulario > .id_formulario');
                const rowId = rowIdElement ? rowIdElement.textContent : null;
                if (rowId) {
                    console.log(`Actualizar formulario con ID: ${rowId} a estado: ${nuevoEstadoClase}`);

                }
            });
        });
    }

    document.querySelectorAll('.estado-celda').forEach(celdaEstado => {
        const opcionesEstadoDiv = crearOpcionesEstado();
        celdaEstado.appendChild(opcionesEstadoDiv);
    });

    inicializarEventListenersEstado();
    document.addEventListener('click', function(event) {
        if (!event.target.closest('.estado-celda')) {
            document.querySelectorAll('.estado-opciones.show').forEach(opciones => {
                opciones.classList.remove('show');
            });
        }
    });
});