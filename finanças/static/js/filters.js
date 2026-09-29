/* Comportamento dos filtros compartilhados (_tx_filters.html). */
document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('[data-filter-form]').forEach(function (form) {
        const period = form.querySelector('input[name=period]');
        const dates = form.querySelector('.custom-dates');

        // "Personalizado" mostra as datas em vez de enviar direto.
        form.querySelectorAll('[data-preset]').forEach(function (btn) {
            btn.addEventListener('click', function (e) {
                if (btn.dataset.preset === 'custom') {
                    e.preventDefault();
                    period.value = 'custom';
                    dates && dates.classList.remove('d-none');
                    form.querySelectorAll('[data-preset]').forEach(b => b.classList.toggle('active', b === btn));
                    const first = dates && dates.querySelector('input');
                    first && first.focus();
                }
            });
        });

        // Preencher datas vira período personalizado.
        form.querySelectorAll('.custom-dates input').forEach(function (inp) {
            inp.addEventListener('change', function () { period.value = 'custom'; });
        });

        // Selects simples aplicam na hora.
        form.querySelectorAll('select[name=type], select[name=account], select[name=status]').forEach(function (sel) {
            sel.addEventListener('change', function () { form.requestSubmit ? form.requestSubmit() : form.submit(); });
        });
        form.querySelectorAll('input[name=loans][type=checkbox], input[name=investments][type=checkbox]').forEach(function (cb) {
            cb.addEventListener('change', function () { form.requestSubmit ? form.requestSubmit() : form.submit(); });
        });

        const clear = form.querySelector('[data-clear-categories]');
        clear && clear.addEventListener('click', function () {
            form.querySelectorAll('input[name=category]').forEach(cb => { cb.checked = false; });
        });

        // Não mandar campos vazios (URL limpa e compartilhável).
        form.addEventListener('submit', function () {
            form.querySelectorAll('input, select').forEach(function (el) {
                if (!el.name || el.type === 'checkbox' || el.type === 'hidden') return;
                if (el.value === '') el.disabled = true;
            });
        });
    });
});
