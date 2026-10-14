document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("invoice-form");
    if (!form) {
        return;
    }
    const workerRows = form.querySelectorAll(".worker-row");
    const totalOutput = document.getElementById("invoice-total");
    const costBoxes = form.querySelectorAll("input[name='cost_id']");
    const incomeBoxes = form.querySelectorAll("input[name='income_id']");

    const parse = (input) => {
        const value = parseFloat(input.value.replace(",", "."));
        return Number.isNaN(value) ? 0 : value;
    };
    const round2 = (value) => Math.round(value * 100) / 100;

    const discountRows = document.getElementById("discount-rows");
    const roundingLine = document.getElementById("rounding-line");
    const formatEuro = (cents) => (cents / 100).toLocaleString("de-DE", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
    }) + " \u20ac";

    const updateTotal = () => {
        let subtotal = 0;
        workerRows.forEach((row) => {
            subtotal += parse(row.querySelector("[name='workerTotal']"));
        });
        costBoxes.forEach((box) => {
            if (box.checked) {
                subtotal += parseFloat(box.dataset.price);
            }
        });
        const subtotalCents = Math.round(subtotal * 100);
        let totalCents = subtotalCents;
        incomeBoxes.forEach((box) => {
            if (box.checked && parseFloat(box.dataset.amount) > 0) {
                totalCents -= Math.round(parseFloat(box.dataset.amount) * 100);
            }
        });
        discountRows.querySelectorAll(".discount-row").forEach((row) => {
            const value = parse(row.querySelector("[name='discountValue']"));
            const isPercent = row.querySelector("[name='discountType']").value === "percent";
            totalCents -= isPercent ? Math.round(subtotalCents * value / 100) : Math.round(value * 100);
        });
        const roundingCents = ((totalCents % 10) + 10) % 10;
        roundingLine.textContent = roundingCents ? "Centausgleich: -" + formatEuro(roundingCents) : "";
        totalOutput.textContent = formatEuro(totalCents - roundingCents);
    };

    document.getElementById("add-discount").addEventListener("click", () => {
        discountRows.appendChild(document.getElementById("discount-template").content.cloneNode(true));
    });
    discountRows.addEventListener("input", updateTotal);
    discountRows.addEventListener("change", updateTotal);
    discountRows.addEventListener("click", (event) => {
        const button = event.target.closest(".remove-discount");
        if (button) {
            button.closest(".discount-row").remove();
            updateTotal();
        }
    });

    workerRows.forEach((row) => {
        const hoursInput = row.querySelector("[name='workerHours']");
        const rateInput = row.querySelector("[name='workerRate']");
        const totalInput = row.querySelector("[name='workerTotal']");

        const updateTotalFromRate = () => {
            totalInput.value = round2(parse(rateInput) * parse(hoursInput)).toFixed(2);
            updateTotal();
        };
        const updateRateFromTotal = () => {
            const hours = parse(hoursInput);
            rateInput.value = hours > 0 ? round2(parse(totalInput) / hours).toFixed(2) : "0.00";
            updateTotal();
        };

        hoursInput.addEventListener("input", updateTotalFromRate);
        rateInput.addEventListener("input", updateTotalFromRate);
        totalInput.addEventListener("input", updateRateFromTotal);
    });
    costBoxes.forEach((box) => box.addEventListener("change", updateTotal));
    incomeBoxes.forEach((box) => box.addEventListener("change", updateTotal));
    updateTotal();
});
