// static/global/assignments.js
document.addEventListener('DOMContentLoaded', () => {
    console.log('> assignments.js cargado y DOM listo');

    function getCsrfToken() {
        const match = document.cookie.split('; ').find(row => row.startsWith('csrftoken='));
        return match ? match.split('=')[1] : '';
    }
    const csrftoken = getCsrfToken();

    const urls = {
        api_projects_for_assignment: '/assignments/api/projects-for-assignment/', // SuperAdmin asignando Proyectos
        api_projects_for_miniadmin_factor_assignment: '/assignments/api/projects-for-miniadmin-factor-assignment/', // MiniAdmin seleccionando proyecto para asignar factores
        api_mini_admin_users: '/assignments/api/mini-admin-users/',
        api_assignable_users_for_factor: '/assignments/api/assignable-users-for-factor/',
        api_factors_for_assignment: (projectId) => `/assignments/api/factors-for-assignment/${projectId}/`,
        api_project_assignments: (projectId) => `/assignments/api/project-assignments/${projectId}/`,
        api_factor_assignments: (factorId) => `/assignments/api/factor-assignments/${factorId}/`,
        assign_project_to_miniadmin: '/assignments/assign/project-to-miniadmin/',
        assign_factor_to_user: '/assignments/assign/factor-to-user/',
    };

    // --- Pestaña: Asignar Proyectos a MiniAdmin (Visible para SuperAdmin/Akadi) ---
    const projectSelectForMiniAdmin = document.getElementById('projectSelectForMiniAdmin');
    const miniAdminUsersContainer = document.getElementById('miniAdminUsersContainer');
    const saveProjectToMiniAdminBtn = document.getElementById('saveProjectToMiniAdminBtn');

    async function loadProjectsForMiniAdminAssignment() {
        if (!projectSelectForMiniAdmin) return;
        try {
            const response = await fetch(urls.api_projects_for_assignment);
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            const projects = await response.json();
            projectSelectForMiniAdmin.innerHTML = '<option value="">— Seleccione un proyecto —</option>';
            projects.forEach(p => projectSelectForMiniAdmin.add(new Option(p.name, p.id)));
        } catch (error) {
            console.error('Error cargando proyectos para asignar a MiniAdmin:', error);
            projectSelectForMiniAdmin.innerHTML = '<option value="">Error al cargar proyectos</option>';
        }
    }

    async function loadMiniAdminUsersAndAssignments() {
        if (!projectSelectForMiniAdmin || !miniAdminUsersContainer) return;
        const projectId = projectSelectForMiniAdmin.value;
        miniAdminUsersContainer.innerHTML = '';
        if (!projectId) {
            miniAdminUsersContainer.innerHTML = '<p class="text-muted">Seleccione un proyecto.</p>';
            return;
        }

        try {
            miniAdminUsersContainer.innerHTML = '<p>Cargando MiniAdmins...</p>';
            const [usersResponse, assignmentsResponse] = await Promise.all([
                fetch(urls.api_mini_admin_users),
                fetch(urls.api_project_assignments(projectId))
            ]);

            if (!usersResponse.ok) throw new Error(`Error cargando MiniAdmins: ${usersResponse.status}`);
            const users = await usersResponse.json();

            if (!assignmentsResponse.ok) throw new Error(`Error cargando asignaciones: ${assignmentsResponse.status}`);
            const assignments = await assignmentsResponse.json();
            
            renderUserTable(miniAdminUsersContainer, users, assignments, 'miniAdminRoleSelect');
        } catch (error) {
            console.error('Error cargando MiniAdmins o asignaciones:', error);
            miniAdminUsersContainer.innerHTML = `<p class="text-danger">Error: ${error.message}</p>`;
        }
    }

    if (projectSelectForMiniAdmin) {
        loadProjectsForMiniAdminAssignment();
        projectSelectForMiniAdmin.addEventListener('change', loadMiniAdminUsersAndAssignments);
    }

    if (saveProjectToMiniAdminBtn) {
        saveProjectToMiniAdminBtn.addEventListener('click', async () => {
            const projectId = projectSelectForMiniAdmin.value;
            if (!projectId) {
                alert('Por favor, seleccione un proyecto.');
                return;
            }
            const assignments = collectAssignments(miniAdminUsersContainer, 'miniAdminRoleSelect');
            try {
                const response = await fetch(urls.assign_project_to_miniadmin, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrftoken },
                    body: JSON.stringify({ project_id: projectId, assignments: assignments })
                });
                if (!response.ok) {
                     const errorData = await response.json();
                     throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
                }
                const result = await response.json();
                applyAssignments(miniAdminUsersContainer, result.assignments, 'miniAdminRoleSelect');
                alert('Asignaciones de proyecto a MiniAdmin actualizadas.');
            } catch (error) {
                console.error('Error guardando asignaciones de proyecto a MiniAdmin:', error);
                alert(`Error: ${error.message}`);
            }
        });
    }

    // --- Pestaña: Asignar Factores a Usuarios (Visible para SuperAdmin/Akadi y MiniAdmin) ---
    const projectSelectForFactor = document.getElementById('projectSelectForFactor');
    const factorSelectForUser = document.getElementById('factorSelectForUser');
    const factorUsersContainer = document.getElementById('factorUsersContainer');
    const saveFactorToUserBtn = document.getElementById('saveFactorToUserBtn');

    async function loadProjectsForFactorAssignment() {
        if (!projectSelectForFactor) return;
        try {
            // MiniAdmins usan una URL diferente que filtra proyectos donde son editores
            const url = urls.api_projects_for_miniadmin_factor_assignment; // Ajustar si SuperAdmin usa otra URL
            const response = await fetch(url);
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            const projects = await response.json();
            projectSelectForFactor.innerHTML = '<option value="">— Seleccione un proyecto —</option>';
            projects.forEach(p => projectSelectForFactor.add(new Option(p.name, p.id)));
            factorSelectForUser.disabled = true;
            factorSelectForUser.innerHTML = '<option value="">— Seleccione un proyecto primero —</option>';
        } catch (error) {
            console.error('Error cargando proyectos para asignación de factor:', error);
            projectSelectForFactor.innerHTML = '<option value="">Error al cargar proyectos</option>';
        }
    }

    async function loadFactorsForAssignment() {
        if (!projectSelectForFactor || !factorSelectForUser) return;
        const projectId = projectSelectForFactor.value;
        factorSelectForUser.innerHTML = '<option value="">— Cargando factores... —</option>';
        factorUsersContainer.innerHTML = '';
        factorSelectForUser.disabled = true;

        if (!projectId) {
            factorSelectForUser.innerHTML = '<option value="">— Seleccione un proyecto primero —</option>';
            factorUsersContainer.innerHTML = '<p class="text-muted">Seleccione un proyecto.</p>';
            return;
        }

        try {
            const response = await fetch(urls.api_factors_for_assignment(projectId));
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            const factors = await response.json();
            factorSelectForUser.innerHTML = '<option value="">— Seleccione un factor —</option>';
            factors.forEach(f => factorSelectForUser.add(new Option(f.name, f.id)));
            factorSelectForUser.disabled = false;
            if (factors.length === 0) {
                 factorSelectForUser.innerHTML = '<option value="">— No hay factores en este proyecto —</option>';
                 factorUsersContainer.innerHTML = '<p class="text-muted">No hay factores en el proyecto seleccionado.</p>';
            } else {
                 factorUsersContainer.innerHTML = '<p class="text-muted">Seleccione un factor.</p>';
            }
        } catch (error) {
            console.error('Error cargando factores:', error);
            factorSelectForUser.innerHTML = '<option value="">Error al cargar factores</option>';
            factorSelectForUser.disabled = true;
        }
    }

    async function loadFactorUsersAndAssignments() {
        if (!factorSelectForUser || !factorUsersContainer) return;
        const factorId = factorSelectForUser.value;
        factorUsersContainer.innerHTML = '';
        if (!factorId) {
            factorUsersContainer.innerHTML = '<p class="text-muted">Seleccione un factor.</p>';
            return;
        }

        try {
            factorUsersContainer.innerHTML = '<p>Cargando usuarios...</p>';
            const [usersResponse, assignmentsResponse] = await Promise.all([
                fetch(urls.api_assignable_users_for_factor),
                fetch(urls.api_factor_assignments(factorId))
            ]);

            if (!usersResponse.ok) throw new Error(`Error cargando usuarios: ${usersResponse.status}`);
            const users = await usersResponse.json();
            
            if (!assignmentsResponse.ok) throw new Error(`Error cargando asignaciones de factor: ${assignmentsResponse.status}`);
            const assignments = await assignmentsResponse.json();

            renderUserTable(factorUsersContainer, users, assignments, 'factorUserRoleSelect');
        } catch (error) {
            console.error('Error cargando usuarios o asignaciones de factor:', error);
            factorUsersContainer.innerHTML = `<p class="text-danger">Error: ${error.message}</p>`;
        }
    }

    if (projectSelectForFactor) {
        loadProjectsForFactorAssignment();
        projectSelectForFactor.addEventListener('change', loadFactorsForAssignment);
    }
    if (factorSelectForUser) {
        factorSelectForUser.addEventListener('change', loadFactorUsersAndAssignments);
    }

    if (saveFactorToUserBtn) {
        saveFactorToUserBtn.addEventListener('click', async () => {
            const factorId = factorSelectForUser.value;
            if (!factorId) {
                alert('Por favor, seleccione un factor.');
                return;
            }
            const assignments = collectAssignments(factorUsersContainer, 'factorUserRoleSelect');
            try {
                const response = await fetch(urls.assign_factor_to_user, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrftoken },
                    body: JSON.stringify({ factor_id: factorId, assignments: assignments })
                });
                 if (!response.ok) {
                     const errorData = await response.json();
                     throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
                }
                const result = await response.json();
                applyAssignments(factorUsersContainer, result.assignments, 'factorUserRoleSelect');
                alert('Asignaciones de factor actualizadas.');
            } catch (error) {
                console.error('Error guardando asignaciones de factor:', error);
                alert(`Error: ${error.message}`);
            }
        });
    }

    // --- Funciones Helper Comunes ---
    function renderUserTable(container, users, existingAssignments = [], selectClass) {
        if (users.length === 0) {
            container.innerHTML = '<p class="text-muted">No hay usuarios disponibles para asignar.</p>';
            return;
        }
        let html = `
          <table class="table table-striped table-sm">
            <thead class="table-light">
              <tr>
                <th>Usuario</th>
                <th style="width: 200px;">Rol Asignado</th>
              </tr>
            </thead>
            <tbody>
        `;
        users.forEach(user => {
            const currentAssignment = existingAssignments.find(a => a.user_id === user.id);
            const currentRole = currentAssignment ? currentAssignment.role : "";
            html += `
              <tr>
                <td>${user.name} (${user.id})</td>
                <td>
                  <select class="form-select form-select-sm ${selectClass}" data-user-id="${user.id}">
                    <option value="" ${currentRole === "" ? "selected" : ""}>Sin Permisos</option>
                    <option value="lector" ${currentRole === "lector" ? "selected" : ""}>Lector</option>
                    <option value="comentador" ${currentRole === "comentador" ? "selected" : ""}>Comentador</option>
                    <option value="editor" ${currentRole === "editor" ? "selected" : ""}>Editor</option>
                  </select>
                </td>
              </tr>
            `;
        });
        html += `</tbody></table>`;
        container.innerHTML = html;
    }

    function applyAssignments(container, assignments, selectClass) {
        assignments.forEach(a => {
            const sel = container.querySelector(`select.${selectClass}[data-user-id="${a.user_id}"]`);
            if (sel) sel.value = a.role;
        });
    }

    function collectAssignments(container, selectClass) {
        return Array.from(container.querySelectorAll(`select.${selectClass}`))
            .map(s => ({
                user_id: s.dataset.userId,
                role: s.value // Incluir incluso si el rol es "" (Sin Permisos) para poder desasignar
            }));
    }
});
