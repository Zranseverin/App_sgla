(function () {
    const svg = document.querySelector("#wash-evolution-chart");
    const dailySource = document.querySelector("#dashboard-daily-data");
    const donut = document.querySelector("#wash-status-chart");
    const statusSource = document.querySelector("#dashboard-status-data");
    const svgNamespace = "http://www.w3.org/2000/svg";

    function createSvg(name, attributes, text) {
        const element = document.createElementNS(svgNamespace, name);
        Object.entries(attributes || {}).forEach(([key, value]) => element.setAttribute(key, value));
        if (text !== undefined) element.textContent = text;
        return element;
    }

    for (const [chart, metric] of [[svg, "count"], [document.querySelector("#revenue-evolution-chart"), "revenue"]]) {
        if (!chart || !dailySource) continue;
        const data = JSON.parse(dailySource.textContent);
        const left = 46, right = 672, top = 22, bottom = 194;
        const maximum = Math.max(1, ...data.map((item) => Number(item[metric])));
        const stepX = data.length > 1 ? (right - left) / (data.length - 1) : 0;
        for (let line = 0; line <= 4; line += 1) {
            const y = top + ((bottom - top) * line / 4);
            const value = Math.round(maximum * (4 - line) / 4);
            chart.appendChild(createSvg("line", { x1: left, y1: y, x2: right, y2: y, class: "chart-grid-line" }));
            chart.appendChild(createSvg("text", { x: left - 12, y: y + 4, class: "chart-axis-label", "text-anchor": "end" }, value));
        }
        const points = data.map((item, index) => ({
            x: left + (stepX * index),
            y: bottom - (Number(item[metric]) / maximum * (bottom - top)),
            item,
        }));
        const linePoints = points.map((point) => `${point.x},${point.y}`).join(" ");
        chart.appendChild(createSvg("polygon", { points: `${left},${bottom} ${linePoints} ${right},${bottom}`, class: "chart-area" }));
        chart.appendChild(createSvg("polyline", { points: linePoints, class: "chart-line" }));
        points.forEach(({ x, y, item }) => {
            chart.appendChild(createSvg("circle", { cx: x, cy: y, r: 5, class: "chart-point" }));
            chart.appendChild(createSvg("text", { x, y: y - 12, class: "chart-value", "text-anchor": "middle" }, Number(item[metric]).toLocaleString("fr-FR")));
            chart.appendChild(createSvg("text", { x, y: bottom + 27, class: "chart-day", "text-anchor": "middle" }, item.label));
        });
    }

    if (donut && statusSource) {
        const statuses = JSON.parse(statusSource.textContent);
        const colors = { orange: "#efa73b", blue: "#2780d4", green: "#28a765", red: "#dc5353" };
        const total = statuses.reduce((sum, item) => sum + Number(item.count), 0);
        let cursor = 0;
        const segments = statuses.map((item) => {
            const start = cursor;
            cursor += total ? Number(item.count) * 100 / total : 0;
            return `${colors[item.color] || "#ccd4dd"} ${start}% ${cursor}%`;
        });
        donut.style.background = total ? `conic-gradient(${segments.join(",")})` : "#e7ecf1";
    }
})();
