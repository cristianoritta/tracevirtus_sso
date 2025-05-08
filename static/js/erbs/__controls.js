// ########################
// #
// #  Meus Pontos Personalizados
// #
// ########################
const customButtonMeusPontos = L.control({ position: 'topleft' });
const meusPontosList = []; // Lista para armazenar todos os markers

customButtonMeusPontos.onAdd = () => {
    const buttonDiv = L.DomUtil.create('div', 'leaflet-bar leaflet-control');
    const buttonA = L.DomUtil.create('a', 'leaflet-control-button', buttonDiv);
    const icon = L.divIcon({
        className: "erb",
        iconAnchor: [0, 24],
        labelAnchor: [-6, 0],
        popupAnchor: [0, -36],
        html: `<span class="l-erb" style="background-color: rgba(176, 0, 0)"><i class="fas fa-home"></i></span>`
    })

    buttonA.innerHTML = "<i class='fas fa-home' title='Adicionar marcador'></i>";
    buttonDiv.addEventListener('click', () => {
        const initialPosition = map.getCenter();
        const markerPonto = L.marker(initialPosition, { draggable: true, icon: icon })
            .addTo(map);

        markerPonto.on('move', (e) => {
            const newPosition = e.latlng;
            salvarMeusPontos(e);
        });
    });
    return buttonDiv;
};
customButtonMeusPontos.addTo(map);


function salvarMeusPontos(e) {
    const newPosition = e.latlng;

    // Preparar dados para enviar ao backend
    const data = {
        latitude: newPosition.lat,
        longitude: newPosition.lng,
        nome: 'Ponto Personalizado', // Você pode adicionar um input para isso
        icone: 'fa-home',
        cor: 'rgba(176, 0, 0)'
    };

    // Enviar dados para o backend
    fetch('/erbs/meuspontos/salvar', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(data)
    })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Adicionar marcador ao mapa
                const markerErbsRegion = L.marker(newPosition, { draggable: true, icon: icon })
                    .addTo(map);

                markerErbsRegion.on('dragend', (e) => {
                    const newPosition = e.latlng;
                });

                meusPontosList.push(markerErbsRegion);
            }
        })
        .catch(error => {
            console.error('Erro:', error);
        });
}


// ########################
// #
// #  Localizar Alvos em Múltiplos Pontos
// #
// ########################
const customButtonMultiTargets = L.control({ position: 'topleft' });
const semiCircleAreaList = []; // Lista para armazenar todos os semi-círculos
const markerAreaList = []; // Lista para armazenar todos os markers

customButtonMultiTargets.onAdd = () => {
    const buttonDiv = L.DomUtil.create('div', 'leaflet-bar leaflet-control');
    const buttonA = L.DomUtil.create('a', 'leaflet-control-button', buttonDiv);

    buttonA.innerHTML = "<i class='fas fa-route' title='Localizar alvos em múltiplos pontos.'></i>";
    buttonDiv.addEventListener('click', () => {
        const initialPosition = map.getCenter();
        const marker = L.marker(initialPosition, { draggable: true }).addTo(map);
        const semiCircle = L.circle(initialPosition, { radius: 10000, color: 'orange' }).addTo(map);

        semiCircleAreaList.push(semiCircle); // Adiciona o novo semi-círculo à lista
        markerAreaList.push(marker); // Adiciona o novo marcador à lista

        marker.on('move', (e) => {
            const newPosition = e.latlng;
            semiCircle.setLatLng(newPosition);
            semiCircle.setStyle({ color: 'orange', opacity: 0.8, fillOpacity: 0.2 });
        }).on('dragend', () => {
            updateMarkersInsideMultiTargets();
        });

        // Adiciona a seleção ao marcador
        marker.on('click', () => {
            marker._icon.parentNode.appendChild(marker._icon); // Traz o ícone do marcador para frente
            marker.properties = { selected: true }; // Adiciona a seleção ao marcador atual
        });
    });
    return buttonDiv;
};
customButtonMultiTargets.addTo(map);

document.addEventListener('keydown', (e) => {
    if (e.key === 'Delete' || e.key === 'Del' || e.keyCode === 46) {
        // Remove o marcador e o semi-círculo selecionados dos multiplos pontos
        const selectedMarker = markerAreaList.find(marker => marker.properties && marker.properties.selected === true);
        if (selectedMarker) {
            const index = markerAreaList.indexOf(selectedMarker);
            if (index > -1) {
                map.removeLayer(selectedMarker);
                map.removeLayer(semiCircleAreaList[index]);
                markerAreaList.splice(index, 1);
                semiCircleAreaList.splice(index, 1);
                updateMarkersInsideMultiTargets();
            }
        }
    }
});

function updateMarkersInsideMultiTargets() {
    const markerCountMap = new Map(); // Map para contar quantos círculos contêm cada marcador
    $('#multiPontos').removeClass('d-none');

    map.eachLayer(function (layer) {
        if (layer instanceof L.Marker) {
            let isInsideAnySemiCircle = false;

            for (const semiCircle of semiCircleAreaList) {
                const semiCircleCenter = semiCircle.getLatLng();
                const semiCircleRadius = semiCircle.getRadius();
                const markerPosition = layer.getLatLng();
                const distance = map.distance(semiCircleCenter, markerPosition);

                if (distance <= semiCircleRadius) {
                    isInsideAnySemiCircle = true;
                    const key = `${layer.iam}`;
                    if (key !== 'undefined') {
                        if (!markerCountMap.has(key)) {
                            markerCountMap.set(key, new Set());
                        }
                        markerCountMap.get(key).add(semiCircle._leaflet_id);
                    }
                }
            }

            if (isInsideAnySemiCircle) {
                if (layer._icon) {
                    layer._icon.style.display = ''; // Exibe o marcador
                }
                if (layer._shadow) {
                    layer._shadow.style.display = ''; // Exibe a sombra do marcador
                }
            } else {
                if (layer._icon) {
                    layer._icon.style.display = 'none'; // Oculta o marcador
                }
                if (layer._shadow) {
                    layer._shadow.style.display = 'none'; // Oculta a sombra do marcador
                }
            }
        } else if (layer instanceof L.Circle || layer instanceof L.SemiCircle) {
            let isInsideAnySemiCircle = false;

            for (const semiCircle of semiCircleAreaList) {
                const semiCircleCenter = semiCircle.getLatLng();
                const semiCircleRadius = semiCircle.getRadius();
                const circleCenter = layer.getLatLng();
                const distance = map.distance(semiCircleCenter, circleCenter);

                if (distance <= semiCircleRadius) {
                    isInsideAnySemiCircle = true;
                    break;
                }
            }

            if (isInsideAnySemiCircle) {
                layer.setStyle({ opacity: 1, fillOpacity: 0.2 }); // Exibe o círculo/semi-círculo
            } else {
                layer.setStyle({ opacity: 0, fillOpacity: 0 }); // Oculta o círculo/semi-círculo
            }
        }
    });

    // Filtra e lista os marcadores que estão em mais de um círculo
    const repeatedMarkers = [];
    markerCountMap.forEach((semiCircles, key) => {
        if (key !== undefined) {
            repeatedMarkers.push({ key: key, count: semiCircles.size });
        }
    });

    // Ordena a lista repeatedMarkers pela chave
    repeatedMarkers.sort((a, b) => a.key.localeCompare(b.key));

    $('#area-list').html('');
    repeatedMarkers.forEach((element) => {
        const listItemClass = element.count > 1 ? 'list-group-item text-danger' : 'list-group-item';
        $('#area-list').append('<li class="' + listItemClass + ' d-flex justify-content-between"><span>' + element.key + '</span><span>' + element.count + '</span></li>');
    });
}



// ########################
// #
// #  Download Filtrado
// #
// ########################

// Transforma a lista de marcadores visiveis em csv
function getVisibleMarkersToCsv() {
    var visibleMarkers = getVisibleMarkers();

    // Define o cabeçalho do CSV
    var csvContent = "ID,Origem,Data,Alvo,ERB Alvo,Latitude,Longitude,Interlocutor\n";

    // Preenche o conteúdo do CSV com os dados dos marcadores visíveis
    for (var id in visibleMarkers) {
        var marker = visibleMarkers[id];
        csvContent += `${id},${marker.origem},${marker.dataHora},${marker.alvo},${marker.erbAlvo},${marker.getLatLng().lat},${marker.getLatLng().lng},${marker.interlocutor},\n`;
    }

    return csvContent;
}

const customButtonDownload = L.control({ position: 'topleft' });

customButtonDownload.onAdd = () => {
    const buttonDiv = L.DomUtil.create('div', 'leaflet-bar leaflet-control');
    const buttonA = L.DomUtil.create('a', 'leaflet-control-button', buttonDiv);

    buttonA.innerHTML = "<i class='fas fa-download' title='Download filtrado'></i>";
    buttonDiv.addEventListener('click', () => {
        csvContent = getVisibleMarkersToCsv();

        // Codifica o conteúdo do CSV em UTF-8 usando TextEncoder
        const utf8Content = new TextEncoder().encode(csvContent);

        // Cria um Blob com o conteúdo codificado em UTF-8
        var blob = new Blob([utf8Content], { type: 'text/csv;charset=utf-8;' });
        var url = URL.createObjectURL(blob);

        // Cria um link de download temporário e clica nele para iniciar o download
        var link = document.createElement("a");
        link.href = url;
        link.setAttribute("download", "visible_markers.csv");
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    });
    return buttonDiv;
};
customButtonDownload.addTo(map);



// ########################
// #
// #  IA
// #
// ########################
const customButtonRelatorioIA = L.control({ position: 'topleft' });

customButtonRelatorioIA.onAdd = () => {
    const buttonDiv = L.DomUtil.create('div', 'leaflet-bar leaflet-control');
    const buttonA = L.DomUtil.create('a', 'leaflet-control-button', buttonDiv);

    buttonA.innerHTML = "<i class='fas fa-microchip-ai' title='Análise com IA'></i>";
    buttonDiv.addEventListener('click', () => {

        Swal.fire({
            title: "STEL",
            text: "Aguarde enquanto o relatório de análise é gerado. O resultado é mais eficiente se for feito com um alvo por vez.",
            confirmButtonText: "Ok",
        });

        var visibleMarkers = getVisibleMarkersToCsv();

        $.ajax({
            url: '/ia/relatorio/visiblemarkers',
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({ 'dados': visibleMarkers }),
            success: function (data) {
                navigator.clipboard.writeText(data).then(function () {
                    Swal.fire({
                        title: "STEL",
                        text: "Relatório copiado para área de transferência.",
                        confirmButtonText: "Ok",
                    });
                }).catch(function (error) {
                    alert("Erro ao copiar para a área de transferência: " + error);
                });
            }
        });

    });
    return buttonDiv;
};
customButtonRelatorioIA.addTo(map);