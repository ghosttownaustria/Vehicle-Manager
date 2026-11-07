// Keeps all price fields of a position consistent with each other.
// Stored (gross) values: ekGross, vkGross, discountEur. Everything else is derived.
document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll("[data-cost-calc]").forEach((root) => {
        const vatFactor = 1 + parseFloat(root.dataset.vat) / 100;
        const input = {};
        root.querySelectorAll("[data-field]").forEach((element) => {
            input[element.dataset.field] = element;
        });

        const round2 = (value) => Math.round((value + Number.EPSILON) * 100) / 100;
        const read = (name) => {
            const value = parseFloat(input[name].value.replace(",", "."));
            return Number.isNaN(value) ? 0 : value;
        };
        const show = (name, value) => {
            input[name].value = value.toFixed(2);
        };

        // Percent values keep full precision here so that editing other fields does not drift.
        const state = {markupPct: 0, discountPct: 0};

        const updateMarkupFromPrices = () => {
            const ekNet = read("ekNet");
            const markupEur = round2(read("vkNet") - ekNet);
            show("markupEur", markupEur);
            if (ekNet > 0) {
                state.markupPct = markupEur / ekNet * 100;
            }
            show("markupPct", state.markupPct);
        };
        const setVkNet = (vkNet) => {
            show("vkNet", vkNet);
            show("vkGross", round2(vkNet * vatFactor));
        };
        const updateDiscountFromPercent = () => {
            show("discountEur", round2(read("vkNet") * state.discountPct / 100));
        };
        const updateDiscountFromEuro = () => {
            const vkNet = read("vkNet");
            if (vkNet > 0) {
                state.discountPct = read("discountEur") / vkNet * 100;
            }
            show("discountPct", state.discountPct);
        };
        // The discount applies to the net price; VAT is added last.
        const updatePrice = () => {
            const netUnitPrice = read("vkNet") - read("discountEur");
            show("price", round2(read("quantity") * netUnitPrice * vatFactor));
        };

        // Recalculation starting at each editable field; the edited field itself stays untouched.
        const fromEkNet = () => {
            show("ekGross", round2(read("ekNet") * vatFactor));
            setVkNet(round2(read("ekNet") * (1 + state.markupPct / 100)));
            updateMarkupFromPrices();
            updateDiscountFromPercent();
        };
        const fromEkGross = () => {
            show("ekNet", round2(read("ekGross") / vatFactor));
            fromEkNet();
        };
        const fromMarkupEur = () => {
            setVkNet(round2(read("ekNet") + read("markupEur")));
            if (read("ekNet") > 0) {
                state.markupPct = read("markupEur") / read("ekNet") * 100;
            }
            show("markupPct", state.markupPct);
            updateDiscountFromPercent();
        };
        const fromMarkupPct = () => {
            state.markupPct = read("markupPct");
            const markupEur = round2(read("ekNet") * state.markupPct / 100);
            show("markupEur", markupEur);
            setVkNet(round2(read("ekNet") + markupEur));
            updateDiscountFromPercent();
        };
        const fromVkNet = () => {
            show("vkGross", round2(read("vkNet") * vatFactor));
            updateMarkupFromPrices();
            updateDiscountFromPercent();
        };
        const fromVkGross = () => {
            show("vkNet", round2(read("vkGross") / vatFactor));
            updateMarkupFromPrices();
            updateDiscountFromPercent();
        };
        const fromDiscountEur = () => updateDiscountFromEuro();
        const fromDiscountPct = () => {
            state.discountPct = read("discountPct");
            updateDiscountFromPercent();
        };

        const handlers = {
            ekNet: fromEkNet,
            ekGross: fromEkGross,
            markupEur: fromMarkupEur,
            markupPct: fromMarkupPct,
            vkNet: fromVkNet,
            vkGross: fromVkGross,
            discountEur: fromDiscountEur,
            discountPct: fromDiscountPct,
            quantity: () => {},
        };

        // Select the whole value on focus so typing replaces it instead of appending.
        Object.values(input).forEach((element) => {
            if (!element.readOnly) {
                element.addEventListener("focus", () => element.select());
            }
        });

        Object.entries(handlers).forEach(([name, handler]) => {
            input[name].addEventListener("input", () => {
                // Keep the edited field exactly as typed while all others follow.
                const typedValue = input[name].value;
                handler();
                input[name].value = typedValue;
                updatePrice();
            });
        });

        // Initial state: derive all fields from the stored gross values.
        show("ekNet", round2(read("ekGross") / vatFactor));
        show("vkNet", round2(read("vkGross") / vatFactor));
        updateMarkupFromPrices();
        updateDiscountFromEuro();
        updatePrice();
    });
});
