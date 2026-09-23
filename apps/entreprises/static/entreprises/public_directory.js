document.addEventListener("DOMContentLoaded", () => {
    const dataNode = document.getElementById("map-companies");
    const companies = dataNode ? JSON.parse(dataNode.textContent) : [];
    const mappedCompanies = companies.filter((company) => company.lat !== null && company.lng !== null);
    let visitorId = localStorage.getItem("cleango_visitor_id");
    if (!visitorId) {
        visitorId = (window.crypto?.randomUUID?.() || `${Date.now()}-${Math.random().toString(36).slice(2)}`);
        localStorage.setItem("cleango_visitor_id", visitorId);
    }
    const deviceLabel = [navigator.userAgentData?.platform || navigator.platform, navigator.userAgentData?.mobile ? "Mobile" : "Navigateur web"].filter(Boolean).join(" · ");
    const trackEvent = (eventType, details = {}) => fetch("/api/entreprises/track/", {
        method: "POST", headers: {"Content-Type": "application/json"}, credentials: "same-origin", keepalive: true,
        body: JSON.stringify({event_type: eventType, visitor_id: visitorId, device_label: deviceLabel, page_path: location.pathname + location.search, referrer: document.referrer, ...details}),
    }).catch(() => {});
    trackEvent("page_view");
    const initialSearch = new URLSearchParams(location.search).get("q");
    if (initialSearch) trackEvent("search", {search_query: initialSearch});
    const map = L.map("finder-map", {center: [5.36, -4.0083], zoom: 12, zoomControl: true});
    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 19,
        referrerPolicy: "strict-origin-when-cross-origin",
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    }).addTo(map);

    const markers = new Map();
    let userMarker = null;
    let userPosition = null;
    let routeLayer = null;
    let routeBadge = null;
    let pendingRouteCompany = null;

    const routeStyles = document.createElement("link");
    routeStyles.rel = "stylesheet";
    routeStyles.href = "/static/entreprises/route.css?v=1";
    document.head.appendChild(routeStyles);
    const catalogStyles = document.createElement("link");
    catalogStyles.rel = "stylesheet";
    catalogStyles.href = "/static/entreprises/catalog.css?v=1";
    document.head.appendChild(catalogStyles);
    const catalogPanel = document.createElement("section");
    catalogPanel.className = "catalog-panel";
    catalogPanel.hidden = true;
    catalogPanel.innerHTML = '<div class="catalog-dialog"><header><div><small>CATALOGUE & TARIFS</small><h2 data-catalog-company></h2></div><button type="button" data-catalog-close aria-label="Fermer">×</button></header><div class="catalog-services" data-catalog-services></div></div>';
    document.body.appendChild(catalogPanel);
    const formatPrice = (value, currency) => `${Math.round(value).toLocaleString("fr-FR")} ${currency}`;
    const openCatalog = (company) => {
        if (!company) return;
        trackEvent("catalog_view", {company_id: company.id});
        catalogPanel.querySelector("[data-catalog-company]").textContent = company.name;
        const servicesNode = catalogPanel.querySelector("[data-catalog-services]");
        servicesNode.innerHTML = "";
        if (!company.catalog.length) {
            servicesNode.innerHTML = '<div class="catalog-empty"><strong>Catalogue indisponible</strong><span>Cette entreprise n’a pas encore publié de prestation active.</span></div>';
        } else {
            const groups = company.catalog.reduce((result, service) => result.set(service.vehicle, [...(result.get(service.vehicle) || []), service]), new Map());
            groups.forEach((services, vehicle) => {
                const group = document.createElement("section");
                const title = document.createElement("h3");
                title.textContent = vehicle;
                group.appendChild(title);
                services.forEach((service) => {
                    const item = document.createElement("article");
                    item.innerHTML = `<div><strong></strong><small></small></div><p><b>${formatPrice(service.price, company.currency)}</b>${service.duration ? `<span>${service.duration} min</span>` : ""}</p>`;
                    item.querySelector("strong").textContent = service.name;
                    item.querySelector("small").textContent = service.description || "Prestation de lavage";
                    group.appendChild(item);
                });
                servicesNode.appendChild(group);
            });
        }
        catalogPanel.hidden = false;
        document.body.classList.add("catalog-open");
    };
    const closeCatalog = () => { catalogPanel.hidden = true; document.body.classList.remove("catalog-open"); };
    catalogPanel.querySelector("[data-catalog-close]").addEventListener("click", closeCatalog);
    catalogPanel.addEventListener("click", (event) => { if (event.target === catalogPanel) closeCatalog(); });

    const routePanel = document.createElement("section");
    routePanel.className = "route-panel";
    routePanel.hidden = true;
    routePanel.innerHTML = '<button class="route-close" type="button" aria-label="Fermer">×</button><small>ITINÉRAIRE</small><h2 data-route-name>Station sélectionnée</h2><div class="route-metrics"><strong data-route-distance>—</strong><span data-route-duration>Calcul en cours…</span></div><p data-route-message>Recherche du meilleur trajet.</p><a data-route-start href="#" target="_blank" rel="noopener">Démarrer la navigation</a>';
    document.querySelector(".finder-map-wrap").appendChild(routePanel);
    routePanel.querySelector(".route-close").addEventListener("click", () => {
        routePanel.hidden = true;
        if (routeLayer) { map.removeLayer(routeLayer); routeLayer = null; }
        if (routeBadge) { map.removeLayer(routeBadge); routeBadge = null; }
    });

    const haversine = (lat1, lon1, lat2, lon2) => {
        const radius = 6371;
        const toRad = (value) => value * Math.PI / 180;
        const dLat = toRad(lat2 - lat1);
        const dLon = toRad(lon2 - lon1);
        const a = Math.sin(dLat / 2) ** 2 + Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLon / 2) ** 2;
        return radius * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    };
    const formatDistance = (km) => km < 1 ? `${Math.round(km * 1000)} m` : `${km.toFixed(1)} km`;
    const stationIcon = (company, color) => L.divIcon({
        className: "", iconSize: [48, 48], iconAnchor: [24, 45], popupAnchor: [0, -48],
        html: `<div class="station-marker" style="--marker-color:${color}"><span>${company.logo ? `<img src="${company.logo}" alt="">` : company.initials}</span></div>`,
    });
    const userIcon = L.divIcon({className: "", iconSize: [20, 20], iconAnchor: [10, 10], html: '<div class="user-marker"></div>'});

    const showRoute = async (company) => {
        if (!company || !company.location_configured) {
            alert("Cette entreprise n’a pas encore configuré sa position GPS.");
            return;
        }
        trackEvent("route_request", {company_id: company.id});
        if (!userPosition) {
            pendingRouteCompany = company;
            document.getElementById("gps-button").click();
            return;
        }
        activateCard(company.id);
        routePanel.hidden = false;
        routePanel.querySelector("[data-route-name]").textContent = company.name;
        routePanel.querySelector("[data-route-distance]").textContent = "—";
        routePanel.querySelector("[data-route-duration]").textContent = "Calcul en cours…";
        routePanel.querySelector("[data-route-message]").textContent = "Recherche du meilleur trajet routier.";
        routePanel.querySelector("[data-route-start]").href = `https://www.google.com/maps/dir/?api=1&origin=${userPosition.lat},${userPosition.lng}&destination=${company.lat},${company.lng}&travelmode=driving`;
        if (routeLayer) map.removeLayer(routeLayer);
        if (routeBadge) { map.removeLayer(routeBadge); routeBadge = null; }
        try {
            const endpoint = `https://router.project-osrm.org/route/v1/driving/${userPosition.lng},${userPosition.lat};${company.lng},${company.lat}?overview=full&geometries=geojson`;
            const response = await fetch(endpoint);
            if (!response.ok) throw new Error("route unavailable");
            const payload = await response.json();
            const route = payload.routes && payload.routes[0];
            if (!route) throw new Error("route unavailable");
            routeLayer = L.geoJSON(route.geometry, {style: {color: "#168a55", weight: 7, opacity: 0.9, lineCap: "round", lineJoin: "round"}}).addTo(map);
            routeLayer.bringToFront();
            map.fitBounds(routeLayer.getBounds(), {padding: [55, 55]});
            const distanceLabel = formatDistance(route.distance / 1000);
            const durationLabel = `${Math.max(1, Math.round(route.duration / 60))} min`;
            routePanel.querySelector("[data-route-distance]").textContent = distanceLabel;
            routePanel.querySelector("[data-route-duration]").textContent = `${durationLabel} en voiture`;
            routePanel.querySelector("[data-route-message]").textContent = "Itinéraire calculé à partir du réseau routier disponible.";
            const coordinates = route.geometry.coordinates;
            const midpoint = coordinates[Math.floor(coordinates.length / 2)];
            const badgeIcon = L.divIcon({className: "", iconSize: [92, 58], iconAnchor: [46, 29], html: `<div class="route-map-badge"><strong>🚗 ${durationLabel}</strong><span>${distanceLabel}</span></div>`});
            routeBadge = L.marker([midpoint[1], midpoint[0]], {icon: badgeIcon, interactive: false, zIndexOffset: 900}).addTo(map);
        } catch (error) {
            const distance = haversine(userPosition.lat, userPosition.lng, company.lat, company.lng);
            routeLayer = L.polyline([[userPosition.lat, userPosition.lng], [company.lat, company.lng]], {color: "#168a55", weight: 5, dashArray: "9 9"}).addTo(map);
            map.fitBounds(routeLayer.getBounds(), {padding: [55, 55]});
            routePanel.querySelector("[data-route-distance]").textContent = formatDistance(distance);
            routePanel.querySelector("[data-route-duration]").textContent = "Ouvrir la navigation";
            routePanel.querySelector("[data-route-message]").textContent = "Le détail routier est indisponible. Démarrez la navigation pour continuer.";
        }
        document.getElementById("finder-sidebar").classList.remove("open");
    };

    mappedCompanies.forEach((company) => {
        const markerColor = company.location_configured ? company.color : "#7b8798";
        const marker = L.marker([company.lat, company.lng], {icon: stationIcon(company, markerColor), opacity: company.location_configured ? 1 : 0.8}).addTo(map);
        const locationText = company.location_configured ? ([company.commune, company.address].filter(Boolean).join(" · ") || company.slogan) : "Position provisoire · GPS à configurer par l’entreprise";
        marker.bindPopup(`<div class="map-popup"><strong>${company.name}</strong><span>${locationText}</span>${company.phone ? `<a href="tel:${company.phone}">☎ ${company.phone}</a>` : ""}<button type="button" data-popup-catalog="${company.id}">Catalogue & tarifs (${company.catalog.length})</button></div>`);
        marker.on("click", () => { trackEvent("company_view", {company_id: company.id, metadata: {source: "map_marker"}}); showRoute(company); });
        markers.set(String(company.id), marker);
    });
    if (mappedCompanies.length) {
        map.fitBounds(L.latLngBounds(mappedCompanies.map((company) => [company.lat, company.lng])), {padding: [45, 45], maxZoom: 14});
    }

    const activateCard = (id) => {
        document.querySelectorAll(".finder-card").forEach((card) => card.classList.remove("active"));
        const card = document.querySelector(`[data-company-id="${id}"]`);
        if (card) { card.classList.add("active"); card.scrollIntoView({behavior: "smooth", block: "nearest"}); }
    };
    document.querySelectorAll("[data-show-map]").forEach((button) => button.addEventListener("click", (event) => {
        event.stopPropagation();
        const card = button.closest("[data-company-id]");
        const marker = markers.get(card.dataset.companyId);
        if (!marker) { alert("Cette entreprise n’a pas encore configuré sa position GPS."); return; }
        map.setView(marker.getLatLng(), 16, {animate: true}); marker.openPopup(); activateCard(card.dataset.companyId);
        showRoute(mappedCompanies.find((company) => String(company.id) === card.dataset.companyId));
    }));
    document.querySelectorAll(".finder-card").forEach((card) => card.addEventListener("click", () => {
        const marker = markers.get(card.dataset.companyId);
        if (marker) {
            trackEvent("company_view", {company_id: card.dataset.companyId, metadata: {source: "company_card"}});
            map.setView(marker.getLatLng(), 15, {animate: true});
            marker.openPopup();
            showRoute(mappedCompanies.find((company) => String(company.id) === card.dataset.companyId));
        }
    }));
    document.querySelectorAll(".finder-card").forEach((card) => {
        const actions = card.querySelector(".finder-actions");
        if (!actions) return;
        const button = document.createElement("button");
        button.type = "button";
        button.className = "route-button";
        button.textContent = "Itinéraire";
        button.addEventListener("click", (event) => {
            event.stopPropagation();
            showRoute(mappedCompanies.find((company) => String(company.id) === card.dataset.companyId));
        });
        actions.appendChild(button);
        const catalogButton = document.createElement("button");
        catalogButton.type = "button";
        catalogButton.className = "catalog-button";
        catalogButton.textContent = "Catalogue & tarifs";
        catalogButton.addEventListener("click", (event) => {
            event.stopPropagation();
            openCatalog(mappedCompanies.find((company) => String(company.id) === card.dataset.companyId));
        });
        actions.appendChild(catalogButton);
    });
    document.addEventListener("click", (event) => {
        const button = event.target.closest("[data-popup-catalog]");
        if (!button) return;
        openCatalog(mappedCompanies.find((company) => String(company.id) === button.dataset.popupCatalog));
    });

    const gpsButton = document.getElementById("gps-button");
    const gpsStatus = document.getElementById("gps-status");
    const setStatus = (type, message) => { gpsStatus.className = `finder-status ${type || ""}`; gpsStatus.querySelector("p").textContent = message; };
    gpsButton.addEventListener("click", () => {
        trackEvent("geolocation_request");
        if (!window.isSecureContext && !["localhost", "127.0.0.1"].includes(window.location.hostname)) {
            setStatus("error", "Le GPS est bloqué sur une adresse HTTP. Ouvrez le site en HTTPS ou utilisez http://127.0.0.1:8000 sur cet ordinateur.");
            return;
        }
        if (!navigator.geolocation) { setStatus("error", "Géolocalisation non prise en charge."); return; }
        gpsButton.disabled = true; setStatus("", "Détection de votre position en cours…");
        navigator.geolocation.getCurrentPosition(async ({coords}) => {
            userPosition = {lat: coords.latitude, lng: coords.longitude};
            if (userMarker) map.removeLayer(userMarker);
            userMarker = L.marker([userPosition.lat, userPosition.lng], {icon: userIcon}).addTo(map).bindPopup("Votre position").openPopup();
            const sorted = mappedCompanies.filter((company) => company.location_configured).map((company) => ({...company, distance: haversine(userPosition.lat, userPosition.lng, company.lat, company.lng)})).sort((a, b) => a.distance - b.distance);
            document.querySelectorAll("[data-distance]").forEach((node) => { node.textContent = ""; });
            sorted.forEach((company) => { const node = document.querySelector(`[data-company-id="${company.id}"] [data-distance]`); if (node) node.textContent = formatDistance(company.distance); });
            if (sorted.length) {
                const nearest = sorted[0];
                activateCard(nearest.id);
                const nearestMarker = markers.get(String(nearest.id));
                map.fitBounds(L.latLngBounds([[userPosition.lat, userPosition.lng], [nearest.lat, nearest.lng]]), {padding: [60, 60]});
                nearestMarker.openPopup();
                const requestedCompany = pendingRouteCompany || nearest;
                pendingRouteCompany = null;
                showRoute(requestedCompany);
            } else { map.setView([userPosition.lat, userPosition.lng], 15); }
            let place = "Position détectée";
            try {
                const response = await fetch(`https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat=${coords.latitude}&lon=${coords.longitude}&accept-language=fr`);
                const payload = await response.json();
                const address = payload.address || {};
                place = address.municipality || address.city || address.town || address.village || address.suburb || place;
            } catch (error) { /* Les coordonnées restent utilisables sans géocodage. */ }
            setStatus("found", `${place} · ${sorted.length} entreprise${sorted.length > 1 ? "s" : ""} localisée${sorted.length > 1 ? "s" : ""}`);
            trackEvent("geolocation_success", {latitude: userPosition.lat, longitude: userPosition.lng, locality: place, metadata: {accuracy_m: Math.round(coords.accuracy)}});
            gpsButton.disabled = false; gpsButton.textContent = "↻ Actualiser ma position";
        }, (error) => {
            const messages = {
                1: "Localisation refusée. Autorisez la position dans les paramètres du navigateur, puis réessayez.",
                2: "Position indisponible. Activez le GPS ou la localisation de l’appareil, puis réessayez.",
                3: "La détection GPS a expiré. Placez-vous près d’une fenêtre ou activez le Wi-Fi, puis réessayez.",
            };
            setStatus("error", messages[error.code] || `Impossible d’obtenir votre position (erreur ${error.code || "inconnue"}).`);
            gpsButton.disabled = false;
        }, {enableHighAccuracy: true, timeout: 30000, maximumAge: 60000});
    });

    const mobileToggle = document.getElementById("finder-mobile-toggle");
    const sidebar = document.getElementById("finder-sidebar");
    mobileToggle.addEventListener("click", () => { sidebar.classList.toggle("open"); mobileToggle.textContent = sidebar.classList.contains("open") ? "⌖ Voir la carte" : "☷ Voir la liste"; });
});
