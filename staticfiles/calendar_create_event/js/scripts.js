document.addEventListener("DOMContentLoaded", function () {
    const eventForm = document.getElementById("event-form");

    // Handle form submission
    eventForm.addEventListener("submit", function (e) {
        e.preventDefault(); 
    
        
        const title = document.getElementById("event-title").value.trim();
        const description = document.getElementById("event-description").value.trim();
        const date = document.getElementById("event-date").value;
        const time = document.getElementById("event-time").value;
        const location = document.getElementById("event-location").value.trim();
        const link = document.getElementById("event-link").value.trim(); // <- No será validado
        const meetingType = document.getElementById("event-type").value;
    
        // Validar solo campos obligatorios 
        if (!title || !description || !date || !time || !location || !meetingType) {
            alert("Por favor, completa todos los campos obligatorios (excepto el link).");
            return;
        }
    
        // Obtener participantes
        let participants = [];
        document.querySelectorAll(".participants-container input[type='checkbox']:checked").forEach(checkbox => {
            participants.push(checkbox.value);
        });
    
        // Confirmar creación del evento
        if (!confirm("Confirm event creation?")) {
            return;
        }
    
        // Enviar datos al backend
        fetch("/guardar_evento/", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": getCookie("csrftoken")
            },
            body: JSON.stringify({
                title,
                description,
                date,
                time,
                location,
                link, 
                meetingType,
                participants
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert("Event created successfully");
                window.location.href = "/calendar/";
            } else {
                alert("Failed to create event");
            }
        })
    });    

    // Helper function to get CSRF token from cookies
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.startsWith(name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
});