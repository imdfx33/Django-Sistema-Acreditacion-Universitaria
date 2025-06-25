// main.js

document.addEventListener('DOMContentLoaded', () => {
// 1) Tablas responsivas: añade data-label a cada celda
document.querySelectorAll('.table-responsive table').forEach(table => {
    const headers = Array.from(table.querySelectorAll('thead th')).map(th => th.textContent.trim());
    table.querySelectorAll('tbody tr').forEach(row => {
    Array.from(row.cells).forEach((cell, i) => {
        cell.setAttribute('data-label', headers[i] || '');
    });
    });
});

// 2) Progress bars: asigna ancho según data-value o inline style
document.querySelectorAll('.progress-bar[data-value]').forEach(bar => {
    bar.style.width = `${bar.dataset.value}%`;
});

// 3) Confirmaciones genéricas
document.querySelectorAll('[data-confirm]').forEach(el => {
    el.addEventListener('click', e => {
    if (!confirm(el.dataset.confirm || '¿Seguro?')) e.preventDefault();
    });
});

// 4) Auto-ocultar alertas tras 5s
document.querySelectorAll('.alert').forEach(alert => {
    setTimeout(() => alert.classList.add('fade'), 5000);
});

// 5) Ordenación de tablas
document.querySelectorAll('table.table-sortable thead th').forEach((th, idx) => {
    th.style.cursor = 'pointer';
    th.addEventListener('click', () => sortTable(th.closest('table'), idx));
});

// 6) Smooth scroll para enlaces internos
document.addEventListener('click', e => {
    const a = e.target.closest('a[href^="#"]');
    if (a) {
    e.preventDefault();
    document.querySelector(a.getAttribute('href')).scrollIntoView({ behavior: 'smooth' });
    }
});

// 7) Pop-up de responsables en listas
document.querySelectorAll('.responsibles-cell').forEach(cell => {
    const popup = cell.querySelector('.responsibles-popup');
    cell.addEventListener('mouseenter', () => popup && (popup.style.display = 'block'));
    cell.addEventListener('mouseleave', () => popup && (popup.style.display = 'none'));
});
});

// Función para ordenar
function sortTable(table, colIndex) {
const tbody = table.tBodies[0];
const rows = Array.from(tbody.rows);
const asc = table.dataset.sortDir !== 'asc';
rows.sort((a,b) => {
    const aText = a.cells[colIndex].textContent.trim();
    const bText = b.cells[colIndex].textContent.trim();
    const aNum = parseFloat(aText.replace(/[^0-9.-]/g,'')),
        bNum = parseFloat(bText.replace(/[^0-9.-]/g,''));
    if (!isNaN(aNum) && !isNaN(bNum)) return asc ? aNum - bNum : bNum - aNum;
    return asc ? aText.localeCompare(bText) : bText.localeCompare(aText);
});
rows.forEach(r=>tbody.appendChild(r));
table.dataset.sortDir = asc ? 'asc' : 'desc';
}
