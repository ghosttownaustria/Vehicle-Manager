(() => {
    "use strict";

    const container = document.querySelector("[data-vehicle-tabs]");
    if (!container) return;
    const tabBar = container.querySelector(".vehicle-tab-bar");
    const buttons = [...container.querySelectorAll("[data-tab-button]")];
    const panels = [...container.querySelectorAll("[data-tab-panel]")];
    if (!tabBar || !buttons.length || !panels.length) return;

    function panelFor(name) {
        return panels.find(panel => panel.dataset.tabPanel === name);
    }

    function activate(name, {scrollToHash = false, scrollTabIntoView = false} = {}) {
        const panel = panelFor(name) || panels[0];
        const activeName = panel.dataset.tabPanel;
        for (const button of buttons) {
            const isActive = button.dataset.tabButton === activeName;
            button.classList.toggle("active", isActive);
            button.setAttribute("aria-selected", String(isActive));
            button.tabIndex = isActive ? 0 : -1;
            if (isActive && scrollTabIntoView) button.scrollIntoView({block: "nearest", inline: "nearest"});
        }
        for (const item of panels) item.hidden = item.dataset.tabPanel !== activeName;
        if (scrollToHash && window.location.hash) {
            const target = document.getElementById(decodeURIComponent(window.location.hash.slice(1)));
            if (target && panel.contains(target)) {
                requestAnimationFrame(() => target.scrollIntoView({block: "start"}));
            }
        }
    }

    function tabForHashTarget() {
        if (!window.location.hash) return null;
        let target;
        try {
            target = document.getElementById(decodeURIComponent(window.location.hash.slice(1)));
        } catch {
            return null;
        }
        if (!target) return null;
        const panel = panels.find(item => item.contains(target));
        return panel ? panel.dataset.tabPanel : null;
    }

    function initialTab() {
        return tabForHashTarget()
            || (new URLSearchParams(window.location.search).has("tab") ? "orders" : null)
            || buttons[0].dataset.tabButton;
    }

    for (const button of buttons) {
        button.addEventListener("click", () => activate(button.dataset.tabButton));
    }

    for (const link of container.querySelectorAll("[data-tab-goto]")) {
        link.addEventListener("click", () => {
            activate(link.dataset.tabGoto, {scrollTabIntoView: true});
            tabBar.scrollIntoView({block: "start", behavior: "smooth"});
        });
    }

    tabBar.addEventListener("keydown", event => {
        const index = buttons.indexOf(document.activeElement);
        if (index === -1) return;
        let nextIndex = null;
        if (event.key === "ArrowRight") nextIndex = (index + 1) % buttons.length;
        else if (event.key === "ArrowLeft") nextIndex = (index - 1 + buttons.length) % buttons.length;
        else if (event.key === "Home") nextIndex = 0;
        else if (event.key === "End") nextIndex = buttons.length - 1;
        if (nextIndex === null) return;
        event.preventDefault();
        buttons[nextIndex].focus();
        activate(buttons[nextIndex].dataset.tabButton);
    });

    window.addEventListener("hashchange", () => {
        const tab = tabForHashTarget();
        if (tab) activate(tab, {scrollToHash: true});
    });

    activate(initialTab(), {scrollToHash: true});
})();
