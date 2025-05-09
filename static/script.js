let map;
let routeLayer;
let userMarker;
let walkLine;
let taxiLine;
let startMarker, endMarker;
let startWalkLine, startTaxiLine;
let endWalkLine, endTaxiLine;
let selectingStart = true;
let currentRouteDetails = null;
let walkingToStart = null;
let walkingToEnd = null;
let alternativeRoutes = [];



document.getElementById("routeForm").addEventListener("submit", function(event) {
    event.preventDefault();

    // Get route information
    let startSelect = document.getElementById("start");
    let endSelect = document.getElementById("end");
    let startId = startSelect.value;
    let endId = endSelect.value;

    if (!startId || !endId) {
        alert("Lütfen başlangıç ve hedef durağını seçin.");
        return;
    }

    const passengerType = document.getElementById("passenger-type").value;
    const passengerName = document.getElementById("passenger-name").value || "Anonim";
    const passengerAge = parseInt(document.getElementById("passenger-age").value) || 30;

    const paymentMethods = [];
    document.querySelectorAll('input[name="payment-methods"]:checked').forEach(input => {
        paymentMethods.push(input.value);
    });

    const cashAmount = parseFloat(document.getElementById("cash-amount").value) || 0;
    const creditLimit = parseFloat(document.getElementById("credit-limit").value) || 0;
    const kentCardBalance = parseFloat(document.getElementById("kentcard-balance").value) || 0;

    document.getElementById("selected-route-details").innerHTML = '<h3>⏳ Rota hesaplanıyor...</h3>';
    document.getElementById("alt-routes-list").innerHTML = '';

    const requestData = {
        start: startId,
        end: endId,
        passenger_type: passengerType,
        passenger_name: passengerName,
        passenger_age: passengerAge,
        payment_methods: paymentMethods,
        cash_amount: cashAmount,
        credit_limit: creditLimit,
        kent_card_balance: kentCardBalance
    };

    console.log("📝 Yolculuk planı isteği:", requestData);

    fetch("/plan_journey", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(requestData)
    })
    .then(response => response.json())
    .then(data => {
        console.log("🚀 API Yanıtı:", data);

        if (!data.route) {
            console.error("🚨 API'den geçerli rota verisi gelmedi!", data);
            document.getElementById("selected-route-details").innerHTML = `
                <div class="info-block" style="background-color: #ffe5e5; border-left: 4px solid #ff3b30;">
                    ⚠️ Rota bulunamadı! Lütfen farklı duraklar seçin.
                </div>`;
            return;
        }

        currentRouteDetails = data;
        updateMap(data);
        displayRouteDetails(data);

        fetch("/get_alternative_routes", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(requestData)
        })
        .then(res => res.json())
        .then(alternatives => {
            console.log("🔁 Alternatif Rotalar:", alternatives);
            displayAlternativeRoutes(alternatives);
        })
        .catch(error => {
            console.error("⚠️ Alternatif rotalar alınırken hata:", error);
            document.getElementById("alt-routes-list").innerHTML = `
                <div class="info-block" style="background-color: #fff3cd; border-left: 4px solid #ffcc00;">
                    ⚠️ Alternatif rotalar alınamadı.
                </div>`;
        });
    })
    .catch(error => {
        console.error("🚨 Rota verisi alınırken hata oluştu:", error);
        document.getElementById("selected-route-details").innerHTML = `
            <div class="info-block" style="background-color: #ffe5e5; border-left: 4px solid #ff3b30;">
                ⚠️ Rota hesaplanırken bir hata oluştu!
            </div>`;
    });
});

function toggleDetails(id) {
    let details = document.getElementById(id);
    details.style.display = details.style.display === "block" ? "none" : "block";
}

function applyDiscountToFare(baseFare, passengerType) {
    switch(passengerType) {
        case 'student':
            return baseFare * 0.5; // 50% discount
        case 'teacher':
            return baseFare * 0.75; // 25% discount
        case 'senior':
            return 0; // 100% discount (up to usage limit)
        default:
            return baseFare; // No discount
    }
}
function displayRouteDetails(data) {
    const detailsContainer = document.getElementById("selected-route-details");

    if (!data.details) {
        const exampleDetails = {
            totalCost: 6.00,
            totalTime: 20,
            totalDistance: 5.5,
            totalTransfers: 1,
            steps: [
                {
                    from: "bus_otogar",
                    fromName: "Otogar (Bus)",
                    to: "bus_sekapark",
                    toName: "Sekapark (Bus)",
                    transportType: "bus",
                    distance: 3.5,
                    time: 10,
                    cost: 3.00
                },
                {
                    from: "bus_sekapark",
                    fromName: "Sekapark (Bus)",
                    to: "tram_sekapark",
                    toName: "Sekapark (Tram)",
                    transportType: "transfer",
                    distance: 0.1,
                    time: 3,
                    cost: 0.50
                },
                {
                    from: "tram_sekapark",
                    fromName: "Sekapark (Tram)",
                    to: "tram_halkevi",
                    toName: "Halkevi (Tram)",
                    transportType: "tram",
                    distance: 2.0,
                    time: 7,
                    cost: 2.50
                }
            ]
        };

        displayRouteDetailsFromData(exampleDetails, detailsContainer);
    } else {
        displayRouteDetailsFromData(data.details, detailsContainer);
    }
}

function displayRouteDetailsFromData(details, container) {
    let html = `
        <h3>🚏 Rota Detayları</h3>
        <div class="route-steps">
    `;

    if (walkingToStart) {
    const icon = walkingToStart.taxi_required ? '🚖' : '🚶';
    const method = walkingToStart.taxi_required ? 'Taksi' : 'Yürüyerek';
    const costText = walkingToStart.taxi_required ? ` | 💰 Ücret: ${walkingToStart.cost.toFixed(2)} TL` : '';
    const timeText = walkingToStart.taxi_required ? ` | ⏳ Süre: ${walkingToStart.time.toFixed(2)} dk` : '';

    html += `
        <div class="route-stop ${walkingToStart.taxi_required ? 'route-type-taxi' : 'route-type-walk'}">
            <div class="transport-icon">${icon}</div>
            <div>
                <strong>🏠 Başlangıç Konumu → ${walkingToStart.name}</strong>
                <div class="route-step-details">
                    📏 Mesafe: ${(walkingToStart.distance / 1000).toFixed(2)} km (${method})${costText}${timeText}
                </div>
            </div>
        </div>
    `;
}


    details.steps.forEach((step, index) => {
        const icon = getTransportIcon(step.transportType);
        const badge = getTransportBadge(step.transportType);

        html += `
            <div class="route-stop ${getRouteTypeClass(step.transportType)}">
                <div class="transport-icon">${icon}</div>
                <div>
                    <strong>${index + 1}. ${step.fromName} → ${step.toName}</strong> ${badge}
                    <div class="route-step-details">
                        ⏳ Süre: ${step.time} dk | 💰 Ücret: ${step.cost.toFixed(2)} TL | 📏 Mesafe: ${step.distance.toFixed(1)} km
                    </div>
                </div>
            </div>
        `;

        if (index < details.steps.length - 1 && details.steps[index + 1].transportType === "transfer") {
            html += `<div class="transfer-line">Aktarma Noktası</div>`;
        }
    });

    if (walkingToEnd) {
    const icon = walkingToEnd.taxi_required ? '🚖' : '🚶';
    const method = walkingToEnd.taxi_required ? 'Taksi' : 'Yürüyerek';
    const costText = walkingToEnd.taxi_required ? ` | 💰 Ücret: ${walkingToEnd.cost.toFixed(2)} TL` : '';
    const timeText = walkingToEnd.taxi_required ? ` | ⏳ Süre: ${walkingToEnd.time.toFixed(2)} dk` : '';

    html += `
        <div class="route-stop ${walkingToEnd.taxi_required ? 'route-type-taxi' : 'route-type-walk'}">
            <div class="transport-icon">${icon}</div>
            <div>
                <strong>${walkingToEnd.name} → 🏁 Varış Konumu</strong>
                <div class="route-step-details">
                    📏 Mesafe: ${(walkingToEnd.distance / 1000).toFixed(2)} km (${method})${costText}${timeText}
                </div>
            </div>
        </div>
    `;
}


    html += `</div>`;


    html += `
        <div class="route-summary">
            <div>
                <strong>💰 Toplam Ücret</strong>
                <div>${details.totalCost.toFixed(2)} TL</div>
            </div>
            <div>
                <strong>⏳ Toplam Süre</strong>
                <div>${details.totalTime} dk</div>
            </div>
            <div>
                <strong>📏 Toplam Mesafe</strong>
                <div>${details.totalDistance.toFixed(1)} km</div>
            </div>
            <div>
                <strong>🔄 Aktarma Sayısı</strong>
                <div>${details.totalTransfers}</div>
            </div>
        </div>
    `;

    container.innerHTML = html;
}


function displayAlternativeRoutes(data) {
    const altRoutesContainer = document.getElementById("alt-routes-list");
    alternativeRoutes = data.alternatives;

    if (!alternativeRoutes || alternativeRoutes.length === 0) {
        altRoutesContainer.innerHTML = '<div class="info-block">Alternatif rota bulunamadı.</div>';
        return;
    }

    let html = '';

    alternativeRoutes.forEach((route, index) => {
        html += `
            <div class="alt-route route-type-${route.type}" data-index="${index}">
                <div class="alt-route-icon">🛤</div>
                <div class="alt-route-details">
                    <strong>${route.name}</strong>
                    <div class="alt-route-metrics">
                        <span>💰 ${route.cost.toFixed(2)} TL</span>
                        <span>⏳ ${route.time} dk</span>
                        <span>📏 ${route.distance.toFixed(1)} km</span>
                    </div>
                </div>
            </div>
        `;
    });

    altRoutesContainer.innerHTML = html;

    document.querySelectorAll('.alt-route').forEach(routeEl => {
        routeEl.addEventListener('click', function () {
            document.querySelectorAll('.alt-route').forEach(r => r.classList.remove('active'));
            this.classList.add('active');

            const index = parseInt(this.dataset.index);
            const selected = alternativeRoutes[index];

            updateMap({ route: selected.route });

            let html = `
                <h3>🚏 Alternatif Rota Detayları (${selected.name})</h3>
                <div class="route-steps">
            `;

            if (walkingToStart) {
                const icon = walkingToStart.taxi_required ? '🚖' : '🚶';
                const method = walkingToStart.taxi_required ? 'Taksi' : 'Yürüyerek';
                const costText = walkingToStart.taxi_required ? ` | 💰 Ücret: ${walkingToStart.cost.toFixed(2)} TL` : '';
                const timeText = walkingToStart.taxi_required ? ` | ⏳ Süre: ${walkingToStart.time.toFixed(2)} dk` : '';
                html += `
                    <div class="route-stop ${walkingToStart.taxi_required ? 'route-type-taxi' : 'route-type-walk'}">
                        <div class="transport-icon">${icon}</div>
                        <div>
                            <strong>🏠 Başlangıç Konumu → ${walkingToStart.name}</strong>
                            <div class="route-step-details">
                                📏 Mesafe: ${(walkingToStart.distance / 1000).toFixed(2)} km (${method})${costText}${timeText}
                            </div>
                        </div>
                    </div>
                `;
            }

            selected.steps.forEach((step, index) => {
                const icon = getTransportIcon(step.transportType);
                const badge = getTransportBadge(step.transportType);

                html += `
                    <div class="route-stop ${getRouteTypeClass(step.transportType)}">
                        <div class="transport-icon">${icon}</div>
                        <div>
                            <strong>${index + 1}. ${step.fromName} → ${step.toName}</strong> ${badge}
                            <div class="route-step-details">
                                ⏳ Süre: ${step.time} dk | 💰 Ücret: ${step.cost.toFixed(2)} TL | 📏 Mesafe: ${step.distance.toFixed(1)} km
                            </div>
                        </div>
                    </div>
                `;
            });

            if (walkingToEnd) {
                const icon = walkingToEnd.taxi_required ? '🚖' : '🚶';
                const method = walkingToEnd.taxi_required ? 'Taksi' : 'Yürüyerek';
                const costText = walkingToEnd.taxi_required ? ` | 💰 Ücret: ${walkingToEnd.cost.toFixed(2)} TL` : '';
                const timeText = walkingToEnd.taxi_required ? ` | ⏳ Süre: ${walkingToEnd.time.toFixed(2)} dk` : '';
                html += `
                    <div class="route-stop ${walkingToEnd.taxi_required ? 'route-type-taxi' : 'route-type-walk'}">
                        <div class="transport-icon">${icon}</div>
                        <div>
                            <strong>${walkingToEnd.name} → 🏁 Varış Konumu</strong>
                            <div class="route-step-details">
                                📏 Mesafe: ${(walkingToEnd.distance / 1000).toFixed(2)} km (${method})${costText}${timeText}
                            </div>
                        </div>
                    </div>
                `;
            }

            html += `</div>
            <div class="route-summary">
                <div><strong>💰 Toplam Ücret</strong><div>${selected.cost.toFixed(2)} TL</div></div>
                <div><strong>⏳ Toplam Süre</strong><div>${selected.time} dk</div></div>
                <div><strong>📏 Toplam Mesafe</strong><div>${selected.distance.toFixed(1)} km</div></div>
                <div><strong>🔄 Aktarma Sayısı</strong><div>${selected.transfers}</div></div>
            </div>`;

            document.getElementById("selected-route-details").innerHTML = html;
        });
    });
}


function displayNearestStopInfo(data) {
    const container = document.getElementById("nearest-stop-info");

    if (!data || !data.name) {
        container.innerHTML = '';
        return;
    }

    let accessMethod = '';
    if (data.taxi_required) {
        accessMethod = `
            <div>🚕 Taksi Gerekli!</div>
            <div>💰 Taksi Ücreti: ${data.taxi_cost.toFixed(2)} TL</div>
            <div>⏳ Taksi Süresi: ${data.taxi_time.toFixed(2)} dk</div>
        `;
    } else {
        accessMethod = `<div>🚶 Yürüyerek ulaşılabilir (${(data.distance / 1000).toFixed(2)} km)</div>`;
    }

    container.innerHTML = `
        <h3>📍 En Yakın Durak Bilgisi</h3>
        <div class="info-block nearest-stop-info">
            <strong>${data.name}</strong>
            <div>📏 Mesafe: ${(data.distance/1000).toFixed(2)} km</div>
            ${accessMethod}
        </div>
    `;
}

function getTransportIcon(type) {
    switch(type) {
        case 'bus': return '🚌';
        case 'tram': return '🚋';
        case 'taxi': return '🚕';
        case 'transfer': return '🔄';
        default: return '🚶';
    }
}

function getTransportBadge(type) {
    switch(type) {
        case 'bus': return '<span class="badge badge-bus">Otobüs</span>';
        case 'tram': return '<span class="badge badge-tram">Tramvay</span>';
        case 'taxi': return '<span class="badge badge-taxi">Taksi</span>';
        case 'transfer': return '<span class="badge badge-transfer">Aktarma</span>';
        default: return '';
    }
}

function getRouteTypeClass(type) {
    return `route-type-${type}`;
}

document.addEventListener("DOMContentLoaded", function () {
    fetch("/get_stops")
        .then(response => response.json())
        .then(data => {
            let startSelect = document.getElementById("start");
            let endSelect = document.getElementById("end");

            data.forEach(stop => {
                let option1 = document.createElement("option");
                option1.value = stop.id;
                option1.textContent = stop.name;

                let option2 = option1.cloneNode(true);

                startSelect.appendChild(option1);
                endSelect.appendChild(option2);
            });
        })
        .catch(error => console.error("Durakları yüklerken hata oluştu:", error));

    if (!map) {
        map = L.map('map').setView([40.7652, 29.9619], 12);
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; OpenStreetMap contributors'
        }).addTo(map);

        map.on("click", function (event) {
    let userLat = event.latlng.lat;
    let userLon = event.latlng.lng;

    if (selectingStart) {
        alert("📌 Başlangıç konumunu belirliyorsunuz.");
    } else {
        alert("📍 Varış konumunu belirliyorsunuz.");
    }

    fetch(selectingStart ? "/find_nearest_stop" : "/find_nearest_stop_for_destination", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ lat: userLat, lon: userLon })
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            alert("En yakın durak bulunamadı.");
            return;
        }

        if (selectingStart) {
            if (startMarker) map.removeLayer(startMarker);
            if (startWalkLine) map.removeLayer(startWalkLine);
            if (startTaxiLine) map.removeLayer(startTaxiLine);
        } else {
            if (endMarker) map.removeLayer(endMarker);
            if (endWalkLine) map.removeLayer(endWalkLine);
            if (endTaxiLine) map.removeLayer(endTaxiLine);
        }

        if (selectingStart) {
            startMarker = L.marker([userLat, userLon]).addTo(map)
                .bindPopup(`📍 Başlangıç Konumu`);

            let startSelect = document.getElementById("start");
            startSelect.value = data.id;

            walkingToStart = {
    name: data.name,
    distance: data.distance,
    taxi_required: data.taxi_required,
    cost: data.taxi_cost,
    time: data.taxi_time
};

            if (data.taxi_required && data.taxi_route) {
                alert(`🚕 Başlangıç için taksi gerekli!\n📏 Mesafe: ${(data.distance / 1000).toFixed(2)} km\n💰 Ücret: ${data.taxi_cost.toFixed(2)} TL\n⏳ Süre: ${data.taxi_time.toFixed(2)} dk`);
                startTaxiLine = L.polyline(data.taxi_route, {
                    color: "yellow",
                    weight: 4,
                    dashArray: "10, 10"
                }).addTo(map);
            } else if (data.walking_route) {
                startWalkLine = L.polyline(data.walking_route, {
                    color: "red",
                    weight: 3,
                    dashArray: "5, 5"
                }).addTo(map);
            }

            displayNearestStopInfo(data);
        } else {
            endMarker = L.marker([userLat, userLon], { color: "blue" }).addTo(map)
                .bindPopup(`🏁 Varış Konumu`);

            let endSelect = document.getElementById("end");
            endSelect.value = data.id;

            walkingToEnd = {
    name: data.name,
    distance: data.distance,
    taxi_required: data.taxi_required,
    cost: data.taxi_cost,
    time: data.taxi_time
};


            if (data.taxi_required && data.taxi_route) {
                alert(`🚕 Varış için taksi gerekli!\n📏 Mesafe: ${(data.distance / 1000).toFixed(2)} km\n💰 Ücret: ${data.taxi_cost.toFixed(2)} TL\n⏳ Süre: ${data.taxi_time.toFixed(2)} dk`);
                endTaxiLine = L.polyline(data.taxi_route, {
                    color: "yellow",
                    weight: 4,
                    dashArray: "10, 10"
                }).addTo(map);
            } else if (data.walking_route) {
                endWalkLine = L.polyline(data.walking_route, {
                    color: "red",
                    weight: 3,
                    dashArray: "5, 5"
                }).addTo(map);
            }

            displayNearestStopInfo(data);
        }

        selectingStart = !selectingStart;
    })
    .catch(error => console.error("🚨 En yakın durak bulunurken hata oluştu:", error));
});

    }
});

function updateMap(routes) {
    if (!map) return;

    if (routeLayer) {
        map.removeLayer(routeLayer);
    }

    routeLayer = L.layerGroup().addTo(map);

    let latlngs = routes.route;

    if (latlngs.length > 1) {
        let polyline = L.polyline(latlngs, { color: 'blue', weight: 5 }).addTo(routeLayer);
        map.fitBounds(polyline.getBounds());

        let startMarker = L.marker(latlngs[0]).addTo(routeLayer)
            .bindPopup("📍 Başlangıç Noktası")
            .openPopup();

        let endMarker = L.marker(latlngs[latlngs.length - 1]).addTo(routeLayer)
            .bindPopup("🏁 Bitiş Noktası")
            .openPopup();


        if (!routes.details) {

            displayRouteDetails(routes);
        }
    }
}

document.getElementById("resetSelection").addEventListener("click", function () {
    if (startMarker) map.removeLayer(startMarker);
    if (endMarker) map.removeLayer(endMarker);
    if (startWalkLine) map.removeLayer(startWalkLine);
    if (startTaxiLine) map.removeLayer(startTaxiLine);
    if (endWalkLine) map.removeLayer(endWalkLine);
    if (endTaxiLine) map.removeLayer(endTaxiLine);

    startMarker = endMarker = null;
    startWalkLine = startTaxiLine = endWalkLine = endTaxiLine = null;
    selectingStart = true;

    document.getElementById("start").value = "";
    document.getElementById("end").value = "";

    document.getElementById("nearest-stop-info").innerHTML = '';
    document.getElementById("selected-route-details").innerHTML = '';
    document.getElementById("alt-routes-list").innerHTML = '';
});