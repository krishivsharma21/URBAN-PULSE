let currentLat = 28.5810;
let currentLon = 77.2451;
let map, routeLayer, startMarker, endMarker;

document.addEventListener("DOMContentLoaded", () => {
    // Initialize Leaflet map with standard OpenStreetMap tile layers & referrer security policy
    map = L.map("map").setView([currentLat, currentLon], 13);

    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 19,
        referrerPolicy: "no-referrer-when-downgrade",
        attribution: '&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(map);

    startMarker = L.marker([currentLat, currentLon]).addTo(map).bindPopup("Ambulance Current Location").openPopup();

    // Load hospital options into the select dropdown on startup
    loadHospitalDropdown();

    document.getElementById("fetch-route-btn").addEventListener("click", fetchRoute);
    document.getElementById("pin-btn").addEventListener("click", updateLiveLocation);
});

async function loadHospitalDropdown() {
    try {
        const response = await fetch("/api/hospitals");
        const data = await response.json();
        if (data.status === "success") {
            const selectEl = document.getElementById("destination-select");
            data.hospitals.forEach(h => {
                const opt = document.createElement("option");
                opt.value = h.name;
                opt.textContent = h.name;
                selectEl.appendChild(opt);
            });
        }
    } catch (e) {
        console.error("Could not fetch hospital registry list:", e);
    }
}

function updateLiveLocation() {
    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(
            (pos) => {
                currentLat = pos.coords.latitude;
                currentLon = pos.coords.longitude;
                document.getElementById("coords-text").innerText = `${currentLat.toFixed(4)}, ${currentLon.toFixed(4)}`;
                startMarker.setLatLng([currentLat, currentLon]);
                map.setView([currentLat, currentLon], 14);
            },
            (err) => {
                alert("GPS Geolocation access denied or unavailable.");
            },
            { enableHighAccuracy: true }
        );
    } else {
        alert("Geolocation is not supported by your browser.");
    }
}

async function fetchRoute() {
    const destinationSelect = document.getElementById("destination-select").value;
    const destination = destinationSelect === "auto" ? "" : destinationSelect;
    
    const fetchBtn = document.getElementById("fetch-route-btn");
    fetchBtn.innerText = "CALCULATING ROUTE...";
    fetchBtn.disabled = true;

    try {
        const response = await fetch("/route", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                lat: currentLat,
                lon: currentLon,
                destination: destination
            })
        });

        const data = await response.json();

        if (!response.ok) {
            alert(data.error || "Route calculation failed.");
            return;
        }

        // Clear previous map layers if they exist
        if (routeLayer) map.removeLayer(routeLayer);
        if (endMarker) map.removeLayer(endMarker);

        // Render optimized route polyline on map
        routeLayer = L.polyline(data.coordinates, { 
            color: "#ef4444", 
            weight: 6,
            opacity: 0.85 
        }).addTo(map);

        map.fitBounds(routeLayer.getBounds(), { padding: [50, 50] });

        // Place destination hospital marker
        const destCoords = data.coordinates[data.coordinates.length - 1];
        endMarker = L.marker(destCoords).addTo(map).bindPopup(`🏥 <b>${data.hospital}</b>`).openPopup();

        // Update dashboard metric cards
        document.getElementById("dist-val").innerText = `${data.distance_km} km`;
        document.getElementById("time-val").innerText = `${data.travel_time_min} min`;

        // --- NEXUS RESPONSE FAMILY NOTIFICATION FEATURE ---
        generateFamilyAlert(data.hospital, data.distance_km, data.travel_time_min);

    } catch (err) {
        console.error("Network error:", err);
        alert("Server connection error. Ensure your local Flask server is running.");
    } finally {
        fetchBtn.innerText = "⚡ FETCH OPTIMISED ROUTE";
        fetchBtn.disabled = false;
    }
}

function generateFamilyAlert(hospitalName, distance, time) {
    // Check if alert container exists, otherwise create it below metrics
    let alertBox = document.getElementById("family-alert-box");
    if (!alertBox) {
        alertBox = document.createElement("div");
        alertBox.id = "family-alert-box";
        alertBox.style.cssText = "margin-top: 15px; padding: 12px; background: #1e293b; border-left: 4px solid #ef4444; border-radius: 4px; color: #f8fafc; font-size: 13px;";
        
        // Append it right under the destination selector or control panel
        const controlPanel = document.querySelector(".dispatch-controller") || document.body;
        controlPanel.appendChild(alertBox);
    }

    const message = `🚨 [NEXUS RESPONSE ALERT] Emergency dispatch active! Patient is being transported to ${hospitalName}. Distance: ${distance} km | Est. Arrival: ${time} mins.`;
    
    alertBox.innerHTML = `
        <b>FAMILY NOTIFICATION BROADCAST</b><br>
        <span style="color: #94a3b8; font-size: 11px;">Auto-generated status message for emergency contacts:</span><br>
        <div style="margin-top: 6px; padding: 8px; background: #0f172a; border-radius: 3px; font-family: monospace; color: #38bdf8;">
            "${message}"
        </div>
    `;
}