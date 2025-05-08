$('#col-statisticas').hide();
$('#accordion-camadas').hide();

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
            if (layer._mRadius > 0) {
                var markerId = layer.marker_id;
                // Verifica se o marcador associado está visível
                if (markerId && visibleMarkers[markerId]) {
                    layer.setStyle({ 'color': 'blue', 'opacity': 0.8, fillOpacity: 0.2 }).setRadius(5000);
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

const tiles = L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a> desenvolvido por <a href="https://www.cristianoritta.com.br" target="_blank">Cristiano Ritta</a>'
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

const alvo = L.layerGroup().addTo(map);
const interlocutor = L.layerGroup().addTo(map);
const meuspontos = L.layerGroup().addTo(map);
const markers_layer_alvo = L.layerGroup().addTo(map);
const heatmap = L.heatLayer([], { radius: 100 }).addTo(map);

const overlays = {
    'Meus pontos': meuspontos,
    'Mapa de calor': heatmap,
};

const layerControl = L.control.layers(baseLayers, overlays).addTo(map);

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

// Função para converter uma cor RGBA em uma cor hexadecimal
function rgbaToHex(rgba) {
    // Obtém a cor RGBA do objeto options.markerColor
    rgba = rgba.options.markerColor;

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
function getRandomColor() {
    if (cores.length === 0) {
        return 'rgba(0,0,0)'; // Retorna preto se não houver mais cores
    }
    const index = Math.floor(Math.random() * cores.length); // Seleciona um índice aleatório
    const selectedColor = cores[index]; // Obtém a cor selecionada
    cores.splice(index, 1); // Remove a cor da lista
    return selectedColor; // Retorna a cor selecionada
}





function addLayerMarkers(data) {
    var random_color_icon = L.IconMaterial.icon({ markerColor: getRandomColor(), iconSize: [31, 42], icon: 'tower' });

    layer_alvo = 'Uber Takeout'

    $('#camadas-container').append(
        `<div class="row" style="width: 300px;">
            <div class="col"><small class="text-muted"><strong>Operadora:</strong> ` + $('#servico').val() + `</small></div>
        </div>
        <div class="mb-2 d-flex justify-content-between border-bottom" style="width: 300px;">
            <div>
                <h6>
                    <input type="checkbox" class="form-checkbox checkbox-camadas" data-alvo="` + layer_alvo + `" data-iam="alvo" checked>
                    <strong>` + $('#alvo').val() + `</strong>
                </h6>
            </div>
        </div>`);

    var markers = data.trim().split('\n');
    var markers_items = [];

    try {
        tableEventos.destroy();
    } catch (e) { console.log(e); }

    try {
        icon = L.IconMaterial.icon({ markerColor: getRandomColor(), iconSize: [31, 42], icon: 'tower' });

        markers.forEach(function (marker) {
            marker = JSON.parse(marker);
            popupContent = "";

            ma = {};

            if (marker.Latitude !== null) {
                // Gera o conteúdo do popup com base nas propriedades do marcador
                for (var tag in marker) {
                    popupContent += '<br><strong>' + tag.replace('_', ' ') + '</strong>: ' + marker[tag];
                }


                // Cria um marcador no mapa
                if (markers_items[marker.Latitude + marker.Longitude] != true) {
                    markers_items[marker.Latitude + marker.Longitude] = true;

                    var m = L.marker([marker.Latitude, marker.Longitude], { icon: icon })
                        .addTo(map)
                        .bindPopup("<small style='text-transform: capitalize;'>" + popupContent + "</small>");
                }
            }
        });


        // Atualiza o DataTable
        tableEventos = $('#eventos').DataTable({
            language: {
                url: 'https://cdn.datatables.net/plug-ins/1.13.6/i18n/pt-BR.json',
            },
        });

        Swal.fire({
            title: 'Sucesso!',
            text: 'Alvo adicionado com sucesso: ' + layer_alvo,
            icon: 'success',
        });
    } catch (e) {
        Swal.fire({
            title: 'Error!',
            text: e.stack + ': Não foi possível adicionar o conteúdo do arquivo. ' + e,
            icon: 'error',
        });
    }


}