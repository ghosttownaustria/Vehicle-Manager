(() => {
    "use strict";

    const section = document.getElementById("service-history");
    const chart = section?.querySelector("[data-history-chart]");
    const dialog = section?.querySelector("#history-entry-dialog");
    if (!chart || !dialog || typeof dialog.showModal !== "function") return;

    const plot = chart.querySelector("[data-history-plot]");
    const svg = plot.querySelector("[data-history-svg]");
    const pointLayer = plot.querySelector("[data-history-points]");
    const tooltip = plot.querySelector("[data-history-tooltip]");
    const fallback = section.querySelector("[data-history-fallback]");
    const detailContent = dialog.querySelector("[data-history-dialog-content]");
    const categories = JSON.parse(section.querySelector("[data-history-categories]").textContent);
    const categoryColors = {
        service: "#155eef", repair: "#d95619", tires: "#8752cc",
        inspection: "#16845b", other: "#667085",
    };
    const number = new Intl.NumberFormat("de-DE");
    const compactNumber = new Intl.NumberFormat("de-DE", {
        notation: "compact", maximumFractionDigits: 1,
    });
    const dateLabel = new Intl.DateTimeFormat("de-DE", {
        day: "2-digit", month: "2-digit", year: "numeric", timeZone: "UTC",
    });
    const entries = [...fallback.querySelectorAll("[data-history-entry]")].map(node => ({
        id: node.dataset.id,
        time: Date.parse(`${node.dataset.date}T00:00:00Z`),
        mileage: Number(node.dataset.mileage),
        categories: JSON.parse(node.dataset.categories),
        node,
        article: node.querySelector(".history-entry"),
    })).sort((a, b) => a.time - b.time || Number(a.id) - Number(b.id));
    const curveEntries = JSON.parse(section.querySelector("[data-history-curve]").textContent).map(item => ({
        id: String(item.id),
        time: Date.parse(`${item.date}T00:00:00Z`),
        mileage: item.mileage,
    })).sort((a, b) => a.time - b.time || Number(a.id) - Number(b.id));
    if (!curveEntries.length) return;
    const projectionData = JSON.parse(section.querySelector("[data-history-projection]").textContent);
    const projection = projectionData ? {
        time: Date.parse(`${projectionData.date}T00:00:00Z`),
        mileage: projectionData.mileage,
    } : null;

    let openedEntries = [];
    let activeButton = null;
    let tooltipButton = null;
    let lastWidth = 0;
    let resizeFrame = 0;

    function element(tag, className, text) {
        const node = document.createElement(tag);
        if (className) node.className = className;
        if (text !== undefined) node.textContent = text;
        return node;
    }

    function svgElement(tag, attributes, text) {
        const node = document.createElementNS("http://www.w3.org/2000/svg", tag);
        for (const [name, value] of Object.entries(attributes)) node.setAttribute(name, value);
        if (text !== undefined) node.textContent = text;
        return node;
    }

    function selectedCategories(items) {
        return categories.filter(category => items.some(item => item.categories.includes(category.value)));
    }

    function dateRange(items) {
        const first = dateLabel.format(items[0].time);
        const last = dateLabel.format(items[items.length - 1].time);
        return first === last ? first : `${first} – ${last}`;
    }

    function mileageRange(items) {
        const values = items.map(item => item.mileage);
        const low = Math.min(...values);
        const high = Math.max(...values);
        return `${number.format(low)}${low === high ? "" : ` – ${number.format(high)}`} km`;
    }

    function hideTooltip() {
        tooltip.hidden = true;
        tooltipButton?.removeAttribute("aria-describedby");
        tooltipButton = null;
    }

    function showTooltip(button, items) {
        if (dialog.open) return;
        hideTooltip();
        const single = items.length === 1;
        tooltip.replaceChildren(
            element("strong", "history-chart-tooltip-title", single ? dateRange(items) : `${items.length} Einträge · ${dateRange(items)}`),
            element("p", "history-chart-tooltip-meta", mileageRange(items)),
            element("p", "history-chart-tooltip-description", selectedCategories(items).map(item => item.label).join(" · ")),
        );
        if (single) {
            const description = items[0].article.querySelector(".history-description")?.textContent.trim();
            if (description) tooltip.append(element("p", "history-chart-tooltip-description",
                description.length > 110 ? `${description.slice(0, 107)}…` : description));
        }
        tooltip.append(element("p", "history-chart-tooltip-hint", "Anklicken für alle Details"));
        tooltip.hidden = false;
        const x = parseFloat(button.style.left);
        const y = parseFloat(button.style.top);
        const left = Math.max(8, Math.min(x - tooltip.offsetWidth / 2, plot.clientWidth - tooltip.offsetWidth - 8));
        const top = y - tooltip.offsetHeight - 20;
        tooltip.style.left = `${left}px`;
        tooltip.style.top = `${top >= 8 ? top : Math.min(y + 22, plot.clientHeight - tooltip.offsetHeight - 8)}px`;
        tooltipButton = button;
        button.setAttribute("aria-describedby", tooltip.id);
    }

    function openDetails(button, items) {
        hideTooltip();
        activeButton = button;
        openedEntries = items;
        for (const item of items) detailContent.append(item.article);
        dialog.querySelector(".history-dialog-toolbar strong").textContent =
            items.length === 1 ? "Historieneintrag" : `${items.length} Historieneinträge`;
        button.classList.add("history-chart-selected");
        dialog.showModal();
        dialog.scrollTop = 0;
        dialog.querySelector("[data-history-close]").focus();
    }

    dialog.querySelector("[data-history-close]").addEventListener("click", () => dialog.close());
    dialog.addEventListener("close", () => {
        for (const item of openedEntries) item.node.append(item.article);
        openedEntries = [];
        activeButton?.classList.remove("history-chart-selected");
        activeButton?.focus({preventScroll: true});
    });
    dialog.addEventListener("click", event => {
        if (event.target !== dialog) return;
        const rect = dialog.getBoundingClientRect();
        if (event.clientX < rect.left || event.clientX > rect.right ||
            event.clientY < rect.top || event.clientY > rect.bottom) dialog.close();
    });
    section.addEventListener("keydown", event => {
        if (event.key === "Escape") hideTooltip();
    });

    function tickStep(value) {
        const power = 10 ** Math.floor(Math.log10(value));
        const fraction = value / power;
        return (fraction <= 1 ? 1 : fraction <= 2 ? 2 : fraction <= 5 ? 5 : 10) * power;
    }

    function draw() {
        const width = plot.clientWidth;
        const height = plot.clientHeight;
        if (!width || !height || width === lastWidth) return;
        lastWidth = width;
        const focusedIds = pointLayer.contains(document.activeElement) ? document.activeElement.dataset.entryIds : null;
        hideTooltip();
        svg.replaceChildren();
        pointLayer.replaceChildren();
        svg.setAttribute("viewBox", `0 0 ${width} ${height}`);

        const left = 26, right = width - 82, top = 24, bottom = height - 48;
        const values = curveEntries.map(item => item.mileage);
        if (projection) values.push(projection.mileage);
        const minimum = Math.min(...values), maximum = Math.max(...values);
        const span = Math.max(maximum - minimum, maximum * 0.08, 100);
        const step = Math.max(1, tickStep(span / 4));
        const lower = Math.max(0, Math.floor((minimum - span * 0.1) / step) * step);
        const upper = Math.ceil((maximum + span * 0.1) / step) * step;
        const firstTime = curveEntries[0].time;
        const lastTime = projection?.time ?? curveEntries[curveEntries.length - 1].time;
        const xPosition = time => firstTime === lastTime ? (left + right) / 2 : left + (time - firstTime) / (lastTime - firstTime) * (right - left);
        const yPosition = mileage => bottom - (mileage - lower) / (upper - lower) * (bottom - top);

        for (let value = lower; value <= upper; value += step) {
            const y = yPosition(value);
            svg.append(svgElement("line", {x1: left, x2: right + 12, y1: y, y2: y, class: "history-chart-grid"}));
            svg.append(svgElement("text", {x: width - 5, y: y + 4, "text-anchor": "end", class: "history-chart-axis-label"},
                value >= 1000000 ? compactNumber.format(value) : number.format(value)));
        }
        svg.append(svgElement("text", {x: width - 5, y: 12, "text-anchor": "end", class: "history-chart-axis-label"}, "km"));

        const tickCount = firstTime === lastTime ? 1 : width < 600 ? 2 : 4;
        const usedDates = new Set();
        for (let i = 0; i < tickCount; i++) {
            const time = tickCount === 1 ? firstTime : firstTime + (lastTime - firstTime) * i / (tickCount - 1);
            const label = dateLabel.format(time);
            if (usedDates.has(label)) continue;
            usedDates.add(label);
            svg.append(svgElement("text", {
                x: xPosition(time), y: height - 12, class: "history-chart-axis-label",
                "text-anchor": tickCount === 1 ? "middle" : i === 0 ? "start" : i === tickCount - 1 ? "end" : "middle",
            }, projection && i === tickCount - 1 ? "Heute" : label));
        }

        const points = curveEntries.map(item => ({item, x: xPosition(item.time), y: yPosition(item.mileage)}));
        let path = `M ${points[0].x} ${points[0].y}`;
        for (let i = 1; i < points.length; i++) {
            const previous = points[i - 1], point = points[i];
            const middle = (previous.x + point.x) / 2;
            // Horizontal controls keep the curve within each pair's measured mileage values.
            path += ` C ${middle} ${previous.y}, ${middle} ${point.y}, ${point.x} ${point.y}`;
        }
        if (points.length > 1) {
            svg.append(svgElement("path", {d: `${path} L ${points[points.length - 1].x} ${bottom} L ${points[0].x} ${bottom} Z`, class: "history-chart-area"}));
            svg.append(svgElement("path", {d: path, class: "history-chart-line"}));
        }
        if (projection) {
            const lastPoint = points[points.length - 1];
            const endX = xPosition(projection.time), endY = yPosition(projection.mileage);
            svg.append(svgElement("path", {
                d: `M ${lastPoint.x} ${lastPoint.y} L ${endX} ${endY}`,
                class: "history-chart-projection",
            }));
            const endpoint = svgElement("circle", {
                cx: endX, cy: endY, r: 4, class: "history-chart-projection-end",
            });
            endpoint.append(svgElement("title", {},
                `Schätzung für ${dateLabel.format(projection.time)}: ca. ${number.format(projection.mileage)} km`));
            svg.append(endpoint);
        }

        // Count close points together so overlapping dates/mileages remain clickable.
        const groups = [];
        const visibleEntries = new Map(entries.map(item => [item.id, item]));
        for (const point of points) {
            const group = groups.find(item => Math.hypot(item.x - point.x, item.y - point.y) < 38);
            if (group) group.curveItems.push(point.item);
            else groups.push({x: point.x, y: point.y, curveItems: [point.item]});
        }
        for (const group of groups) {
            // Keep group positions stable too: filtering only changes their visible entries.
            group.items = group.curveItems.map(item => visibleEntries.get(item.id)).filter(Boolean);
            if (!group.items.length) continue;
            const button = element("button", "history-chart-point");
            button.type = "button";
            button.style.left = `${group.x}px`;
            button.style.top = `${group.y}px`;
            button.dataset.entryIds = group.items.map(item => item.id).join(",");
            button.setAttribute("aria-haspopup", "dialog");
            button.setAttribute("aria-controls", dialog.id);
            const types = selectedCategories(group.items);
            button.setAttribute("aria-label", `${group.items.length > 1 ? `${group.items.length} Einträge, ` : ""}${dateRange(group.items)}, ${mileageRange(group.items)}, ${types.map(item => item.label).join(", ")}. Details öffnen.`);
            const colors = types.map(item => categoryColors[item.value] || categoryColors.other);
            const segments = colors.map((color, index) => `${color} ${index * 100 / colors.length}% ${(index + 1) * 100 / colors.length}%`);
            const dot = element("span", "history-chart-point-dot");
            dot.style.setProperty("--point-fill", `conic-gradient(${segments.join(",")})`);
            dot.setAttribute("aria-hidden", "true");
            dot.append(element("span", "history-chart-point-symbol", group.items.length > 1 ? String(group.items.length) : types[0]?.symbol || "•"));
            button.append(dot);
            button.addEventListener("pointerenter", () => showTooltip(button, group.items));
            button.addEventListener("pointerleave", hideTooltip);
            button.addEventListener("focus", () => showTooltip(button, group.items));
            button.addEventListener("blur", hideTooltip);
            button.addEventListener("click", () => openDetails(button, group.items));
            pointLayer.append(button);
            if (openedEntries.some(item => group.items.includes(item))) {
                activeButton = button;
                button.classList.add("history-chart-selected");
            }
            if (focusedIds && group.items.some(item => focusedIds.split(",").includes(item.id))) button.focus({preventScroll: true});
        }
    }

    const latest = curveEntries[curveEntries.length - 1];
    const latestLabel = chart.querySelector("[data-history-latest]");
    latestLabel.replaceChildren(
        element("span", null, "Letzter erfasster Stand"),
        element("strong", null, `${number.format(latest.mileage)} km`),
    );
    chart.hidden = false;
    draw();
    fallback.hidden = true;
    const resize = () => {
        cancelAnimationFrame(resizeFrame);
        resizeFrame = requestAnimationFrame(draw);
    };
    if (typeof ResizeObserver === "function") new ResizeObserver(resize).observe(plot);
    else window.addEventListener("resize", resize);
})();
