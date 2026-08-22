document.addEventListener("DOMContentLoaded", () => {
    const button = document.getElementById("enterprise-gps-button");
    const status = document.getElementById("enterprise-gps-status");
    const latitude = document.getElementById("id_latitude");
    const longitude = document.getElementById("id_longitude");
    const commune = document.getElementById("id_commune");
    const address = document.getElementById("id_adresse");
    if (!button || !latitude || !longitude) return;

    const mapStyles = document.createElement("link");
    mapStyles.rel = "stylesheet";
    mapStyles.href = "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css";
    document.head.appendChild(mapStyles);
    const customStyles = document.createElement("link");
    customStyles.rel = "stylesheet";
    customStyles.href = "/static/authentication/enterprise-map.css?v=1";
    document.head.appendChild(customStyles);

    const mapTools = document.createElement("div");
    mapTools.className = "enterprise-map-tools";
    mapTools.innerHTML = '<div class="enterprise-map-search"><input type="search" placeholder="Rechercher une commune, un quartier ou une adresse"><button type="button">Rechercher</button></div><div id="enterprise-location-map" aria-label="Carte de localisation de l’entreprise"></div><p>Cliquez sur la carte ou déplacez le marqueur pour préciser l’emplacement exact.</p>';
    status.insertAdjacentElement("afterend", mapTools);
    const searchInput = mapTools.querySelector("input");
    const searchButton = mapTools.querySelector("button");
    let locationMap = null;
    let locationMarker = null;

    const setCoordinates = (lat, lng, center = true) => {
        latitude.value = Number(lat).toFixed(6);
        longitude.value = Number(lng).toFixed(6);
        if (!locationMap) return;
        if (!locationMarker) {
            locationMarker = L.marker([lat, lng], {draggable: true}).addTo(locationMap);
            locationMarker.on("dragend", () => {
                const point = locationMarker.getLatLng();
                setCoordinates(point.lat, point.lng, false);
                showStatus("Position ajustée. Cliquez sur Enregistrer pour sauvegarder.");
            });
        } else locationMarker.setLatLng([lat, lng]);
        if (center) locationMap.setView([lat, lng], 17);
    };

    const initializeMap = () => {
        const initialLat = Number.parseFloat(latitude.value) || 5.36;
        const initialLng = Number.parseFloat(longitude.value) || -4.0083;
        locationMap = L.map("enterprise-location-map").setView([initialLat, initialLng], latitude.value && longitude.value ? 16 : 11);
        L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {maxZoom: 19, attribution: "&copy; OpenStreetMap"}).addTo(locationMap);
        if (latitude.value && longitude.value) setCoordinates(initialLat, initialLng, false);
        locationMap.on("click", ({latlng}) => {
            setCoordinates(latlng.lat, latlng.lng, false);
            showStatus("Position choisie sur la carte. Cliquez sur Enregistrer pour sauvegarder.");
        });
    };
    if (window.L) initializeMap();
    else {
        const leafletScript = document.createElement("script");
        leafletScript.src = "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js";
        leafletScript.onload = initializeMap;
        document.head.appendChild(leafletScript);
    }

    const showStatus = (message, error = false) => {
        status.hidden = false;
        status.classList.toggle("error", error);
        status.textContent = message;
    };
    button.addEventListener("click", () => {
        if (!window.isSecureContext && !["localhost", "127.0.0.1"].includes(window.location.hostname)) {
            showStatus("Le GPS est bloqué sur une adresse HTTP. Utilisez HTTPS ou ouvrez http://127.0.0.1:8000 sur cet ordinateur.", true);
            return;
        }
        if (!navigator.geolocation) {
            showStatus("La géolocalisation n’est pas disponible sur cet appareil.", true);
            return;
        }
        button.disabled = true;
        button.textContent = "Localisation en cours…";
        showStatus("Recherche de la position GPS de l’entreprise…");
        navigator.geolocation.getCurrentPosition(async ({coords}) => {
            setCoordinates(coords.latitude, coords.longitude);
            let locationName = "";
            try {
                const url = `https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat=${encodeURIComponent(coords.latitude)}&lon=${encodeURIComponent(coords.longitude)}&accept-language=fr`;
                const response = await fetch(url, {headers: {"Accept": "application/json"}});
                if (!response.ok) throw new Error("reverse-geocoding-failed");
                const payload = await response.json();
                const data = payload.address || {};
                const communeValue = data.municipality || data.city || data.town || data.village || data.county || data.suburb || "";
                const addressValue = [data.suburb || data.neighbourhood, data.road, data.house_number].filter(Boolean).join(" · ") || payload.display_name || "";
                if (commune && communeValue) commune.value = communeValue;
                if (address && addressValue) address.value = addressValue;
                locationName = communeValue ? ` · ${communeValue}` : "";
            } catch (error) {
                locationName = " · commune non récupérée";
            }
            showStatus(`Position récupérée${locationName}. Latitude ${latitude.value}, longitude ${longitude.value}, précision ${Math.round(coords.accuracy)} m. Cliquez sur « Enregistrer l’entreprise » pour sauvegarder.`);
            button.disabled = false;
            button.textContent = "↻ Actualiser ma position GPS";
        }, (error) => {
            const errors = {1: "Accès à la position refusé.", 2: "Position GPS indisponible.", 3: "La recherche GPS a expiré."};
            showStatus(errors[error.code] || "Impossible de récupérer la position.", true);
            button.disabled = false;
            button.textContent = "⌖ Réessayer";
        }, {enableHighAccuracy: true, timeout: 30000, maximumAge: 30000});
    });

    const searchAddress = async () => {
        const query = searchInput.value.trim();
        if (!query) { showStatus("Saisissez une commune, un quartier ou une adresse.", true); return; }
        searchButton.disabled = true;
        showStatus("Recherche de l’adresse en cours…");
        try {
            const response = await fetch(`https://nominatim.openstreetmap.org/search?format=jsonv2&limit=1&countrycodes=ci&accept-language=fr&q=${encodeURIComponent(query)}`);
            if (!response.ok) throw new Error("search-failed");
            const results = await response.json();
            if (!results.length) { showStatus("Adresse introuvable. Essayez avec la commune et le quartier.", true); return; }
            const result = results[0];
            setCoordinates(result.lat, result.lon);
            if (address && !address.value) address.value = result.display_name;
            showStatus(`Position trouvée : ${result.display_name}. Ajustez le marqueur si nécessaire, puis enregistrez.`);
        } catch (error) {
            showStatus("La recherche d’adresse est temporairement indisponible.", true);
        } finally { searchButton.disabled = false; }
    };
    searchButton.addEventListener("click", searchAddress);
    searchInput.addEventListener("keydown", (event) => {
        if (event.key === "Enter") { event.preventDefault(); searchAddress(); }
    });
});
