document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll("[data-toggle-group]").forEach((button) => {
        button.addEventListener("click", () => {
            const boxes = document.querySelectorAll(
                `input[data-group='${button.dataset.toggleGroup}']`
            );
            const allChecked = Array.from(boxes).every((box) => box.checked);
            boxes.forEach((box) => {
                box.checked = !allChecked;
            });
        });
    });
});
