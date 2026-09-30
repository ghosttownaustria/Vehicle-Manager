document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll("form").forEach((form) => {
        const markupSelect = form.querySelector("select[name='markup']");
        const amountInput = form.querySelector("input[name='amount']");
        const saleAmountInput = form.querySelector("input[name='saleAmount']");
        if (!markupSelect || !amountInput || !saleAmountInput) {
            return;
        }

        const updateSaleAmount = () => {
            const isManual = markupSelect.value === "manual";
            saleAmountInput.readOnly = !isManual;
            if (isManual) {
                return;
            }
            const amount = parseFloat(amountInput.value.replace(",", "."));
            const percentage = markupSelect.value === "ek" ? 0 : parseFloat(markupSelect.value);
            saleAmountInput.value = Number.isNaN(amount)
                ? ""
                : (Math.round(amount * (1 + percentage / 100) * 100) / 100).toFixed(2);
        };

        markupSelect.addEventListener("change", updateSaleAmount);
        amountInput.addEventListener("input", updateSaleAmount);
        updateSaleAmount();
    });
});
