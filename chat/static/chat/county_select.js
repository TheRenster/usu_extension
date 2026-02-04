// County dropdown: store selection in localStorage and redirect to chat
document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('countyForm');
    const countySelect = document.getElementById('countySelect');
    const continueBtn = document.getElementById('continueBtn');

    // Restore previous selection if returning to page
    const previousCounty = localStorage.getItem('selected_county');
    if (previousCounty) {
        const option = Array.from(countySelect.options).find(o => o.value === previousCounty);
        if (option) {
            countySelect.value = previousCounty;
        }
    }

    // Enable Continue when a county is selected
    countySelect.addEventListener('change', function() {
        continueBtn.disabled = !this.value;
    });

    // If a county is already selected on load, enable the button
    if (countySelect.value) {
        continueBtn.disabled = false;
    }

    form.addEventListener('submit', function(e) {
        e.preventDefault();
        const county = countySelect.value;
        if (!county) return;

        localStorage.setItem('selected_county', county);
        window.location.href = '/chat/';
    });
});
