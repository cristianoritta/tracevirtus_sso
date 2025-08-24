/**
 * Inicializa variáveis
 */
var markersMap = {};
var markersItems = [];
var markersColors = [];
var markersColorsInterlocutor = [];

let chamadas_originadas = 0; // Contador para chamadas originadas
let chamadas_recebidas = 0; // Contador para chamadas recebidas

// Ajusta o mapa para ocupar o tamanho horizontal
$('#map').css('height', $(window).height() - 70 + 'px');
// Remove a rolagem do corpo
$('body').css({
    'overflow': 'hidden',
    'margin': 0
});

// Ajuste dinâmico do mapa ao redimensionar a janela
$(window).resize(function () {
    $('#map').css('height', $(window).height() - 70 + 'px');
});


// ########################
// #
// #  M A P
// #
// ########################
var map = L.map('map')
    .setView([-15.77972, -47.92972], 4)
    .on('contextmenu', function () {
        // Obtém todos os marcadores visíveis antes de iterar sobre os semicircles
        var visibleMarkers = getVisibleMarkers();

        map.eachLayer(function (layer) {
            console.log(layer);

            if (layer._mRadius > 0) {
                var markerId = layer.marker_id;
                // Verifica se o marcador associado está visível
                if (markerId && visibleMarkers[markerId]) {
                    layer.setStyle({ 'color': visibleMarkers[markerId]['tipo'] == 'alvo' ? 'blue' : 'green', 'opacity': 0.8, fillOpacity: 0.2 }).setRadius(5000);
                    selectedSemiCircle = null;
                }
            }
        });
    }).on('dblclick', function (e) {
        $('#btn-meuspontos').trigger('click');
        $('#marcador_latitude').val(e.latlng.lat);
        $('#marcador_longitude').val(e.latlng.lng);
    });

// Cria um mapa de marcadores visíveis
function getVisibleMarkers() {
    var visibleMarkers = {};
    map.eachLayer(function (layer) {
        if (layer instanceof L.Marker && layer._icon.style.display !== 'none') {
            visibleMarkers[layer._leaflet_id] = layer;
        }
    });
    return visibleMarkers;
}

// ########################
// #
// #  LAYERS
// #
// ########################
const tiles = L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; STEL <a href="http://www.new.seg.br" target="_blank">by NewSeg</a>'
}).addTo(map);

googleStreets = L.tileLayer('http://{s}.google.com/vt/lyrs=m&x={x}&y={y}&z={z}', {
    maxZoom: 20,
    subdomains: ['mt0', 'mt1', 'mt2', 'mt3']
});

googleSat = L.tileLayer('http://{s}.google.com/vt/lyrs=s&x={x}&y={y}&z={z}', {
    maxZoom: 20,
    subdomains: ['mt0', 'mt1', 'mt2', 'mt3']
});

var stadiaAlidadeSmoothDark = L.tileLayer('https://tiles.stadiamaps.com/tiles/alidade_smooth_dark/{z}/{x}/{y}{r}.{ext}', {
    maxZoom: 20,
    attribution: '&copy; <a href="https://www.stadiamaps.com/" target="_blank">Stadia Maps</a> &copy; <a href="https://openmaptiles.org/" target="_blank">OpenMapTiles</a> &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    ext: 'png'
});
var stadiaStamenToner = L.tileLayer('https://tiles.stadiamaps.com/tiles/stamen_toner/{z}/{x}/{y}{r}.{ext}', {
    maxZoom: 20,
    attribution: '&copy; <a href="https://www.stadiamaps.com/" target="_blank">Stadia Maps</a> &copy; <a href="https://www.stamen.com/" target="_blank">Stamen Design</a> &copy; <a href="https://openmaptiles.org/" target="_blank">OpenMapTiles</a> &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    ext: 'png'
});

const baseLayers = {
    'Padrão': tiles,
    'Google': googleStreets,
    'Satelite': googleSat,
    'Dark': stadiaAlidadeSmoothDark,
    'Desenho': stadiaStamenToner,
};

const meuspontos = L.layerGroup().addTo(map);

const overlays = {
    'Meus pontos': meuspontos
};
const layerControl = L.control.layers(baseLayers, overlays).addTo(map);

// ########################
// #
// #  ADICIONAR MARCADORES
// #
// ########################
try {
    // Parse o conteúdo de #markers como um objeto JSON
    var markers = JSON.parse($('#markers').val());
    var heatmappoints = [];

    // Itere sobre cada chave no objeto markers
    Object.values(markers).forEach(function (markerList) {
        // Cada markerList é uma lista de objetos
        markerList.forEach(function (marker) {

            // Cria a ERB do Alvo
            if (marker['Latitude da ERB do Alvo'] != null) {

                // Testa se já existe um marcador nessa posição
                markerCoordinates = marker['Latitude da ERB do Alvo'] + marker['Longitude da ERB do Alvo'] + marker['Azimute do Alvo'];
                if (markersItems[markerCoordinates] != true) {
                    markersItems[markerCoordinates] = true;
                    alvo = createERB(marker);
                    heatmappoints.push([marker['Latitude da ERB do Alvo'], marker['Longitude da ERB do Alvo'], 0.5]);
                }
            }

            // Cria a ERB do Interlocutor
            if (marker['Latitude da ERB do Interlocutor'] != null) {
                // Testa se já existe um marcador nessa posição
                markerCoordinates = marker['Latitude da ERB do Interlocutor'] + marker['Longitude da ERB do Interlocutor'] + marker['Azimute do Interlocutor'];
                if (markersItems[markerCoordinates] != true) {
                    markersItems[markerCoordinates] = true;
                    createErbInterlocutor(marker, alvo);
                }
            }
        });

        const first = Object.values(markersMap)[0];
        const firstMarker = getMarker(first.marker_id);

        map.flyTo(firstMarker.getLatLng(), 12);

        // Adiciona a barra de slider
        //addSlider();
        //atualizarEstatisticas(markers);

    });

    // Adiciona o mapa de calor
    const heatmap = L.heatLayer(heatmappoints, { radius: 100 }).addTo(map);
    layerControl.addOverlay(heatmap, 'Mapa de calor');

} catch (e) {
    console.error("Erro ao parsear JSON:", e);
}

// ########################
// #
// #  ADICIONAR PONTOS PERSONALIZADOS DO CASO
// #
// ########################
var pontos = JSON.parse($('#meuspontos').val());

// Cada markerList é uma lista de objetos
pontos.forEach(function (ponto) {
    const icon = L.divIcon({
        className: "meuspontos",
        iconAnchor: [0, 24],
        labelAnchor: [-6, 0],
        popupAnchor: [0, -36],
        html: `<span class="l-erb" style="background-color: ${ponto.cor};"><i class="fas ${ponto.icone}"></i></span>`
    });

    // Cria um marcador no mapa
    var markerPonto = L.marker([ponto.latitude, ponto.longitude], { draggable: true, icon: icon })
        .addTo(map)
        .bindPopup("<small style='text-transform: capitalize;'>Ponto personalizado</small>")
        .on('dragend', function (e) {
            const newPosition = e.latlng;
            salvarMeusPontos(e);
        });
});


// ########################
// #
// #  CRIAR ERBS
// #
// ########################
function createERB(marker) {
    // Valida Latitude do Marcador
    latitude = marker['Latitude da ERB do Alvo'];
    longitude = marker['Longitude da ERB do Alvo'];
    azimute = marker['Azimute do Alvo'];

    if (typeof (latitude) == 'string') {
        latitude = latitude.replace(',', '.');
        longitude = longitude.replace(',', '.');
    }

    if (latitude == '') {
        return;
    }

    if (isNaN(marker['Linha do Alvo'])) {
        return;
    }

    if (!isNaN(latitude) && !isNaN(longitude)) {
        let popupContent = "";

        // Gera o conteúdo do popup com base nas propriedades do marcador
        for (var tag in marker) {
            if (marker[tag] != null && marker[tag] != '') {
                popupContent += '<br><span class="fw-bolder">' + tag.replace('_', ' ') + '</span>: ' + marker[tag];
            }
        }

        if (markersColors[marker['Linha do Alvo']]) {
            randomColor = markersColors[marker['Linha do Alvo']];
        } else {
            randomColor = getRandomColor();
            markersColors[marker['Linha do Alvo']] = randomColor;
            $('#color-alvo-' + marker['Linha do Alvo']).val(rgbaToHex(randomColor));
        }

        const markerHtmlStyles = `background-color: ${randomColor};`

        const icon = L.divIcon({
            className: "erb",
            iconAnchor: [0, 24],
            labelAnchor: [-6, 0],
            popupAnchor: [0, -36],
            html: `<span class="l-erb" style="${markerHtmlStyles}"><i class="fas"></i></span>`
        });

        // Cria um marcador no mapa
        var m = L.marker([latitude, longitude], { icon: icon })
            .addTo(map)
            .bindPopup("<small style='text-transform: capitalize;'>" + popupContent + "</small><br><a href='/mapa/eventos/" + marker['id'] + "/" + marker['origem'] + "' class='show-modal btn btn-sm btn-primary'>Eventos</a>")
            .on('click', clickMarker);

        // Define propriedades adicionais para o marcador
        m.feature = { properties: { "time": "'" + marker['Data e Hora'] + "'" } };
        m.alvo = marker['Linha do Alvo'];
        m.interlocutor = marker['Linha do Interlocutor'];
        m.iam = marker['Linha do Alvo'];
        m.grupo = marker['Linha do Alvo'];
        m.tipo = 'alvo';
        m.origem = marker['origem'];
        m.erbAlvo = marker['ERB do Alvo'];
        m.dataHora = marker['Data e Hora'];

        if (marker['origem'] == 'Interceptação') {
            m._icon.querySelector("i").classList.add("fa-headset");
        } else if (marker['origem'] == 'Histórico de Chamadas') {
            m._icon.querySelector("i").classList.add("fa-phone-volume");
        } else {
            m._icon.querySelector("i").classList.add("fa-mobile-signal-out");
        }

        // Cria uma semicircunferência do azimute no mapa
        let s = L.semiCircle([latitude, longitude], { radius: 5000, color: 'blue' })
            .setDirection(azimute, 120)
            .on('click', colorSemiCircle)
            .addTo(map);
        s.marker_id = m._leaflet_id; // Associa o semicircle ao marcador

        // Armazena a associação no objeto markersMap
        markersMap[m._leaflet_id] = s;

        return m;
    }
}

function createErbInterlocutor(marker, m) {
    // Valida Latitude do Marcador
    latitude = marker['Latitude da ERB do Interlocutor'];
    longitude = marker['Longitude da ERB do Interlocutor'];
    azimute = marker['Azimute do Interlocutor'];

    if (marker['origem'] == 'Conexões') {
        return;
    }

    if (typeof (latitude) == 'string') {
        latitude = latitude.replace(',', '.');
        longitude = longitude.replace(',', '.');
    }

    if (latitude == '') {
        return;
    }

    if (isNaN(marker['Linha do Interlocutor'])) {
        return;
    }

    if (!isNaN(latitude) && !isNaN(longitude)) {
        let popupContent = '<br><span class="fw-bolder">Alvo:</span>: ' + marker['Linha do Alvo'] +
            '<br><span class="fw-bolder">Interlocutor:</span>: ' + marker['Linha do Interlocutor'] +
            '<br><span class="fw-bolder">Data:</span>: ' + marker['Data e Hora'];

        // Cada alvo tem uma mesma cor para todos os seus interlocutores
        randomColor = markersColors[marker['Linha do Alvo']];
        $('#color-interlocutor-' + marker['Linha do Alvo']).val(rgbaToHex(randomColor));

        const markerHtmlStyles = `background-color: ${randomColor};`

        const icon = L.divIcon({
            className: "erb",
            iconAnchor: [0, 24],
            labelAnchor: [-6, 0],
            popupAnchor: [0, -36],
            html: `<span class="l-erb" style="${markerHtmlStyles}"><i class="fas"></i></span>`
        });

        // Cria um marcador no mapa
        var i = L.marker([latitude, longitude], { icon: icon })
            .addTo(map)
            .bindPopup("<small style='text-transform: capitalize;'>" + popupContent + "</small><br><a href='/mapa/eventos/" + marker['id'] + "/" + marker['origem'] + "' class='show-modal btn btn-sm btn-primary'>Eventos</a>");

        // Define propriedades adicionais para o marcador
        i.feature = { properties: { "time": "'" + marker['Data e Hora'] + "'" } };
        i.alvo = marker['Linha do Alvo'];
        i.interlocutor = marker['Linha do Interlocutor'];
        i.iam = marker['Linha do Alvo'];
        i.grupo = marker['Linha do Alvo'];
        i.tipo = 'interlocutor';
        i.origem = marker['origem'];
        i.erbAlvo = marker['ERB do Alvo'];

        if (marker['origem'] == 'Interceptação') {
            i._icon.querySelector("i").classList.add("fa-headset");
        } else if (marker['origem'] == 'Histórico de Chamadas') {
            i._icon.querySelector("i").classList.add("fa-phone-volume");
        } else {
            i._icon.querySelector("i").classList.add("fa-mobile-signal-out");
        }

        // Cria uma semicircunferência do azimute no mapa
        let si = L.semiCircle([latitude, longitude], { radius: 5000, color: 'green' })
            .setDirection(azimute, 120)
            .on('click', colorSemiCircle)
            .addTo(map);
        si.marker_id = i._leaflet_id;
        si.tipo = 'interlocutor';

        // Armazena a associação no objeto markersMap
        markersMap[i._leaflet_id] = si;

        //if (tipo == 'alvo') {
        //heatmap.addLatLng(m.getLatLng()); // Adiciona a localização do marcador ao heatmap
        //}

        return i;
    }
}

// Destaca as células da ERB selecionada
function clickMarker(e) {
    map.eachLayer(function (layer) {
        if (layer._mRadius > 0) {
            if (layer._latlng.lat == e.latlng.lat && layer._latlng.lng == e.latlng.lng) {
                layer.setStyle({ 'color': '#3388FF', 'opacity': 0.8, 'fillOpacity': 0.2 });
                layer.bringToFront();
            } else {
                layer.setStyle({ 'color': '#F2EFE9', 'opacity': 0, 'fillOpacity': 0 });

            }
        }
    });
}

// LEAFLET SLIDER
function addSlider(layer) {
    var sliderControl = L.control.sliderControl({ position: "bottomleft", layer: layer, range: true });
    map.addControl(sliderControl);
    sliderControl.startSlider();
}


$(document).on('change', '.form-control-color', function () {
    var color = this.value;
    var alvo = $(this).data('alvo');
    var iam = $(this).data('iam');

    map.eachLayer(function (layer) {
        // Troca a cor dos marcadores
        if (layer instanceof L.Marker && layer.tipo == iam && layer.alvo == alvo && layer.grupo == alvo) {
            $(layer._icon).find("span").css("background-color", color);
        }
    });
});


// Função para converter uma cor RGBA em uma cor hexadecimal
function rgbaToHex(rgba) {
    // Obtém a cor RGBA do objeto options.markerColor
    //rgba = rgba.options.markerColor;

    // Remove o prefixo 'rgba(' e o sufixo ')' e divide a string por vírgulas
    var parts = rgba.replace('rgba(', '').replace(')', '').split(',');

    // Remove espaços extras e converte cada componente para um número inteiro
    var r = parseInt(parts[0].trim(), 10);
    var g = parseInt(parts[1].trim(), 10);
    var b = parseInt(parts[2].trim(), 10);
    var a = parts.length > 3 ? parseFloat(parts[3].trim()) : 1; // Valor alfa (opcional)

    // Função auxiliar para converter um componente para hexadecimal
    function componentToHex(c) {
        var hex = c.toString(16);
        return hex.length == 1 ? "0" + hex : hex; // Garante dois dígitos
    }

    // Converte cada componente para hexadecimal e concatena
    var hex = "#" + componentToHex(r) + componentToHex(g) + componentToHex(b);

    // Adiciona o valor alfa em hexadecimal se for diferente de 1 (totalmente opaco)
    if (a < 1) {
        var alphaHex = Math.round(a * 255).toString(16);
        if (alphaHex.length == 1) alphaHex = "0" + alphaHex;
        hex += alphaHex;
    }

    return hex;
}

// Função para obter uma cor aleatória da lista de cores
$('.form-control-color[data-iam="alvo"]').each(function () {
    $(this).value = getRandomColor();
})
// Função para obter uma cor aleatória da lista de cores
function getRandomColor() {

    let cores = [
        'rgba(0, 0, 193)', // LightPink
        'rgba(0, 193, 0)', // PeachPuff
        'rgba(176, 0, 0)', // PowderBlue
        'rgba(0, 239, 0)', // PapayaWhip
        'rgba(0, 0, 255)', // LightCyan
        'rgba(0, 160, 0)', // Plum
        'rgba(205, 0, 0)',  // Peru
        'rgba(0, 228, 0)', // Bisque
        'rgba(176, 0, 0)', // LightSteelBlue
        'rgba(0, 0, 170)', // PaleGoldenrod
        'rgba(175, 0, 0)', // PaleTurquoise
        'rgba(0, 191, 0)', // Thistle
        'rgba(0, 0, 140)', // Khaki
        'rgba(0, 0, 192)', // Silver
        'rgba(0, 0, 173)', // NavajoWhite
        'rgba(0, 192, 0)', // Pink
        'rgba(0, 0, 214)', // Orchid
        'rgba(0, 0, 210)', // LightGoldenrodYellow
        'rgba(0, 0, 225)', // MistyRose
        'rgba(245, 0, 0)', // Beige
        'rgba(0, 0, 181)', // Moccasin
        'rgba(0, 230, 0)', // Lavender
        'rgba(0, 0, 245)', // LavenderBlush
        'rgba(255, 0, 0)', // Bisque
        'rgba(255, 0, 205)', // LemonChiffon
    ];

    const index = Math.floor(Math.random() * cores.length); // Seleciona um índice aleatório
    const selectedColor = cores[index]; // Obtém a cor selecionada
    return selectedColor; // Retorna a cor selecionada
}


// Função para destacar a semicircunferência em vermelho
function colorSemiCircle(e) {

    // Obtém todos os marcadores visíveis antes de iterar sobre os semicircles
    var visibleMarkers = getVisibleMarkers();
    var markerId = e.target.marker_id;

    // Verifica se o marcador associado está visível
    try {
        if (e.originalEvent.shiftKey == false) {
            map.eachLayer(function (layer) {
                if (layer._mRadius > 0) {
                    layer.setStyle({ color: '#F2EFE9', opacity: 0, fillOpacity: 0 }); // Redefine o estilo dos outros layers
                }
            });
        }
    } catch (e) { console.log(e); }


    visibleMarkers.each(function (l) {

        if (l.marker_id == this.marker_id) {
            this.setStyle({ color: 'red', opacity: 0.8, fillOpacity: 0.2 });
            selectedSemiCircle = this;
        }
        console.log(l);
        // Define o layer selecionado como o semicircle atual

    });

}


// Recupera um marcador a partir do id
function getMarker(id) {
    marker_by_id = null;

    map.eachLayer(function (layer) {
        if (layer instanceof L.Marker) {
            if (layer._leaflet_id == id) {
                marker_by_id = layer;
            }
        }
    });

    return marker_by_id;
}


// Mapeia as teclas do teclado
$(document).keypress(function (e) {

    // Move o mapa para o primeiro marcador
    if (e.keyCode == 49) { // Tecla '1'
        const first = Object.values(markersMap)[0];
        const firstMarker = getMarker(first.marker_id);
        firstMarker.openPopup();
        map.flyTo(firstMarker.getLatLng(), 12);

        // Mapeia os botões 8 e 2 do teclado numérico para ajustar o raio da pizza em +/- 1000m
    } else if (e.keyCode == 50) { // Tecla '2'
        if (selectedSemiCircle._mRadius > 1000) {
            selectedSemiCircle.setRadius(selectedSemiCircle._mRadius - 1000);
        }
    } else if (e.keyCode == 56) { // Tecla '8'
        selectedSemiCircle.setRadius(selectedSemiCircle._mRadius + 1000);

    }
})


// Exibe/Oculta marcadores
$(document).on('change', '.checkbox-camadas', function () {
    var alvo = $(this).data('alvo');
    var iam = $(this).data('iam');
    var display_camada = $(this).is(':checked');

    map.eachLayer(function (layer) {

        if (layer.grupo == alvo) {
            if (display_camada) {
                if (layer instanceof L.Marker && layer.tipo == iam) {
                    layer._icon.style.display = '';

                    // Exibe o semicircle correspondente, se existir
                    if (markersMap[layer._leaflet_id]) {
                        let s = markersMap[layer._leaflet_id];
                        s.setStyle({ color: layer.tipo === 'alvo' ? 'blue' : 'green', opacity: 0.8, fillOpacity: 0.2 }).setRadius(5000);
                    }
                }
            } else {
                if (layer instanceof L.Marker && layer.tipo == iam) {
                    layer._icon.style.display = 'none';

                    // Oculta o semicircle correspondente, se existir
                    if (markersMap[layer._leaflet_id]) {
                        let s = markersMap[layer._leaflet_id];
                        s.setStyle({ opacity: 0, fillOpacity: 0 });
                    }
                }
            }
        }
    });
});
// Oculta as camadas no início do carregamento
$('.checkbox-camadas').each(function () {
    $(this).trigger('click');
});
// Exibe um alerta para o usuário mostrar manualmente as camadas
Swal.fire({
    title: "STEL",
    text: "Controle a visualização dos alvos no menu de Camadas.",
    confirmButtonText: "Ok",
});