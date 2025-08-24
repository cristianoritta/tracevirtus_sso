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
//const heatmap = L.heatLayer([], { radius: 100 }).addTo(map);

const overlays = {
    'Meus pontos': meuspontos,
  //  'Mapa de calor': heatmap,
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

let chamadas_originadas = 0; // Contador para chamadas originadas
let chamadas_recebidas = 0; // Contador para chamadas recebidas

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

// Função para destacar a semicircunferência em vermelho
function colorSemiCircle(e) {
    try {
        if (e.originalEvent.shiftKey == false) {
            map.eachLayer(function (layer) {
                if (layer._mRadius > 0) {
                    layer.setStyle({ color: '#F2EFE9', opacity: 0, fillOpacity: 0 }); // Redefine o estilo dos outros layers
                }
            });
        }
    } catch (e) { console.log(e); }

    console.log(this);
    console.log(e);

    this.setStyle({ color: 'red', 'opacity': 0.8, fillOpacity: 0.5 }); // Define o estilo do layer selecionado
    selectedSemiCircle = this; // Define o layer selecionado como o semicircle atual
}

// Mapeia as teclas do teclado
$(document).keypress(function (e) {

    // Move o mapa para o primeiro marcador
    if (e.keyCode == 49) { // Tecla '1'
        const first = Object.values(markerMap)[0];
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

// Função para criar uma Estação Rádio Base (ERB)
var markerMap = {}; // Objeto para armazenar a associação entre marcadores e semicircles
function createERB(tipo, latitude, longitude, marker, icon, iam, azimute, grupo, addto) {

    if (typeof (latitude) == 'string') {
        latitude = latitude.replace(',', '.');
        longitude = longitude.replace(',', '.');
    }

    if (latitude == '') {
        return;
    }

    if (!isNaN(latitude) && !isNaN(longitude)) {
        let popupContent = "";

        if (typeof icon == 'string') {
            icon = icon.split(":");
            icon = L.IconMaterial.icon({ markerColor: icon[0], iconSize: [31, 42], icon: icon[1] });
        }

        // Gera o conteúdo do popup com base nas propriedades do marcador
        for (var tag in marker) {
            popupContent += '<br><strong>' + tag.replace('_', ' ') + '</strong>: ' + marker[tag];
        }

        // Cria um marcador no mapa
        var m = L.marker([latitude, longitude], { icon: icon })
            .addTo(addto)
            .bindPopup("<small style='text-transform: capitalize;'>" + popupContent + "</small>")
            .on('click', clickMarker);

        // Define propriedades adicionais para o marcador
        m.feature = { properties: { "time": "" + marker.DATA_FORMATADA + " " + marker.HORA_FORMATADA + "" } };
        m.alvo = marker.ALVO;
        m.interlocutor = marker.INTERLOCUTOR;
        m.iam = iam;
        m.grupo = grupo;
        m.tipo = tipo;
        m.erbAlvo = marker.ERB_ALVO;

        // Cria uma semicircunferência no mapa
        let s = L.semiCircle([latitude, longitude], { radius: 5000, color: 'blue' })
            .setDirection(azimute, 120)
            .on('click', colorSemiCircle)
            .addTo(addto);
        s.marker_id = m._leaflet_id; // Associa o semicircle ao marcador

        // Armazena a associação no objeto markerMap
        markerMap[m._leaflet_id] = s;

        if (tipo == 'alvo') {
            heatmap.addLatLng(m.getLatLng()); // Adiciona a localização do marcador ao heatmap
        }

        return m;
    }
}


$(document).on('change', '.form-control-color', function () {
    var color = this.value;
    var alvo = $(this).data('alvo');
    var iam = $(this).data('iam');

    markers_layer_alvo.eachLayer(function (layer) {
        if (iam == 'alvo') {
            // Troca a cor dos marcadores de chamada do alvo
            if (layer instanceof L.Marker && layer.iam == layer.alvo && layer.alvo == alvo && layer.grupo == alvo) {
                layer.setIcon(new L.IconMaterial.icon({ markerColor: color, icon: layer.options.icon.options.icon }));
            }
        } else {
            if (layer instanceof L.Marker && layer.iam != layer.alvo && layer.alvo == alvo && layer.grupo == alvo) {
                layer.setIcon(new L.IconMaterial.icon({ markerColor: color, icon: layer.options.icon.options.icon }));
            }
        }
    });
});

// Exibe/Oculta marcadores
$(document).on('change', '.checkbox-camadas', function () {
    var alvo = $(this).data('alvo');
    var iam = $(this).data('iam');
    var display_camada = $(this).is(':checked');

    Toast.fire({
        icon: "info",
        title: "Atualizando mapa..."
    });

    markers_layer_alvo.eachLayer(function (layer) {
        if (layer.grupo == alvo) {
            if (display_camada) {
                if (layer instanceof L.Marker && layer.tipo == iam) {
                    layer._icon.style.display = '';

                    // Exibe o semicircle correspondente, se existir
                    if (markerMap[layer._leaflet_id]) {
                        let s = markerMap[layer._leaflet_id];
                        s.setStyle({ color: 'blue', opacity: 0.8, fillOpacity: 0.2 }).setRadius(5000);
                    }
                }
            } else {
                if (layer instanceof L.Marker && layer.tipo == iam) {
                    layer._icon.style.display = 'none';

                    // Oculta o semicircle correspondente, se existir
                    if (markerMap[layer._leaflet_id]) {
                        let s = markerMap[layer._leaflet_id];
                        s.setStyle({ opacity: 0, fillOpacity: 0 });
                    }
                }
            }
        }
    });
});

function getMarker(id) {
    fm = null;

    map.eachLayer(function (layer) {
        if (layer instanceof L.Marker) {
            if (layer._leaflet_id == id) {
                fm = layer;
            }
        }
    });

    return fm;
}

function addLayerMarkers(data) {
    var random_color_icon = L.IconMaterial.icon({ markerColor: getRandomColor(), iconSize: [31, 42], icon: 'tower' });
    var random_color_icon_voz = L.IconMaterial.icon({ markerColor: getRandomColor(), iconSize: [31, 42], icon: 'phone_forwarded' });
    var random_color_icon_dados = L.IconMaterial.icon({ markerColor: getRandomColor(), iconSize: [31, 42], icon: 'wifi' });
    var random_color_icon_deslocamento = L.IconMaterial.icon({ markerColor: getRandomColor(), iconSize: [31, 42], icon: 'phone_in_talk' });
    var icon_interlocutor = L.IconMaterial.icon({ markerColor: 'green', iconSize: [31, 42], icon: 'phone_callback' });

    if ($('#layout').val() == 'Voz') {
        icon = random_color_icon_voz;
    } else {
        icon = random_color_icon_dados;
    }

    layer_alvo = $('#alvo').val();

    $('#camadas-container').append(
        `<div class="row" style="width: 300px;">
            <div class="col"><small class="text-muted"><strong>Operadora:</strong> ` + $('#operadora').val() + `</small></div>
            <div class="col"><small class="text-muted"><strong>Layout:</strong> ` + $('#layout').val() + `</small></div>
        </div>
        <div class="mb-2 d-flex justify-content-between border-bottom" style="width: 300px;">
            <div>
                <h6>
                    <input type="checkbox" class="form-checkbox checkbox-camadas" data-alvo="` + layer_alvo + `" data-iam="alvo" checked>
                    <strong>` + $('#alvo').val() + `</strong>
                </h6>
                <input type="checkbox" class="form-checkbox checkbox-camadas" data-alvo="` + layer_alvo + `" data-iam="interlocutor" checked>
                <small>Interlocutor</small>
            </div>
            <div class="form-group">
                <small class="form-label">Alvo</small>
                <input type="color" data-alvo="` + layer_alvo + `" data-iam="alvo" value="` + rgbaToHex(icon) + `" class="border-0 form-control form-control-sm form-control-color">
            </div>
            <div class="form-group">
                <small class="form-label">Interlocutor</small>
                <input type="color" data-alvo="` + layer_alvo + `" data-iam="interlocutor" value="#008000" class="border-0 form-control form-control-sm form-control-color">
            </div>
        </div>`);


    var markers = data.trim().split('\n');
    var markers_items = [];

    try {
        tableEventos.destroy();
    } catch (e) { console.log(e); }

    try {
        markers.forEach(function (marker) {
            marker = JSON.parse(marker);

            ma = {};
            mi = {};

            if (marker.ERB_ALVO_LATITUDE !== null) {
                if (markers_items[marker.ERB_ALVO_LATITUDE + marker.ERB_ALVO_LONGITUDE + marker.ERB_ALVO_AZIMUTE] != true) {
                    markers_items[marker.ERB_ALVO_LATITUDE + marker.ERB_ALVO_LONGITUDE + marker.ERB_ALVO_AZIMUTE] = true;

                    ma = createERB('alvo', marker.ERB_ALVO_LATITUDE, marker.ERB_ALVO_LONGITUDE, marker, icon, marker.ALVO, parseInt(marker.ERB_ALVO_AZIMUTE || 0), layer_alvo, markers_layer_alvo);
                }
            }

            // Marcador de deslocamento
            if (typeof marker === 'object' && marker !== null && 'ERB_FINAL_ALVO_LATITUDE' in marker && marker.ERB_FINAL_ALVO_LATITUDE !== null) {
                if (markers_items[marker.ERB_FINAL_ALVO_LATITUDE + marker.ERB_FINAL_ALVO_LONGITUDE + marker.ERB_FINAL_ALVO_AZIMUTE] != true) {
                    markers_items[marker.ERB_FINAL_ALVO_LATITUDE + marker.ERB_FINAL_ALVO_LONGITUDE + marker.ERB_FINAL_ALVO_AZIMUTE] = true;

                    createERB('alvo', marker.ERB_FINAL_ALVO_LATITUDE, marker.ERB_FINAL_ALVO_LONGITUDE, marker, icon, marker.ALVO, parseInt(marker.ERB_FINAL_ALVO_AZIMUTE || 0), layer_alvo, markers_layer_alvo);
                }
            }

            // Interlocutor
            if (typeof (marker.ERB_INTERLOCUTOR_LATITUDE) !== undefined) {
                if (marker.ERB_INTERLOCUTOR_LATITUDE !== null && marker.ERB_INTERLOCUTOR_LATITUDE !== '') {
                    if (markers_items[marker.ERB_INTERLOCUTOR_LATITUDE + marker.ERB_INTERLOCUTOR_LONGITUDE + marker.ERB_INTERLOCUTOR_AZIMUTE] != true) {
                        markers_items[marker.ERB_INTERLOCUTOR_LATITUDE + marker.ERB_INTERLOCUTOR_LONGITUDE + marker.ERB_INTERLOCUTOR_AZIMUTE] = true;

                        mi = createERB('interlocutor', marker.ERB_INTERLOCUTOR_LATITUDE, marker.ERB_INTERLOCUTOR_LONGITUDE, marker, icon_interlocutor, marker.INTERLOCUTOR, parseInt(marker.ERB_INTERLOCUTOR_AZIMUTE || 0), layer_alvo, markers_layer_alvo);

                        // TODO: Ver pq em alguns processamentos não tá rodando a linha que liga alvo no interlocutor
                        if (typeof mi === 'object' && mi !== null && '_leaflet_id' in ma && ma != undefined) {
                            ma.destino_id = mi._leaflet_id;
                            mi.destino_id = ma._leaflet_id;
                        }
                    }
                }
            }

            if (marker.TIPO == 'ORIGINADA') {
                chamadas_originadas++;
            } else {
                chamadas_recebidas++;
            }

            // Cria a tabela de eventos
            if (marker.ERB_ALVO_LATITUDE != null) {
                marker.ERB_ALVO_LATITUDE = marker.ERB_ALVO_LATITUDE.toString().replace(',', '.')
                marker.ERB_ALVO_LONGITUDE = marker.ERB_ALVO_LONGITUDE.toString().replace(',', '.')
                $('#eventos-container').append(`<tr>
                    <td>${marker.NUMERO_A}</td>
                    <td>${marker.NUMERO_B}</td>
                    <td>${marker.TIPO}</td>
                    <td>${marker.DATA_FORMATADA}</td>
                    <td>${marker.HORA_FORMATADA}</td>
                    <td>${marker.DURACAO}</td>
                    <td>${(marker.ERB_ALVO != '' ? marker.ERB_ALVO + '<br><span class="text-muted">Az. ' + marker.ERB_ALVO_AZIMUTE + ', Cidade: ' + marker.ERB_ALVO_CIDADE : '')}</span></td>
                    <td>${marker.ERB_INTERLOCUTOR}</td>
                    <td>
                        ${(marker.ERB_ALVO != '' ?
                        "<a href='#' class='btn btn-gray' onclick='map.flyTo([" + marker.ERB_ALVO_LATITUDE + "," + marker.ERB_ALVO_LONGITUDE + "], 12); colorSemiCircle(markerMap[" + ma._leaflet_id + "]);'><i class='fas fa-eye'></i></a>" :
                        ""
                    )}
                    </td>
                </tr>`.replace('null', '').replace('undefined', ''));
            }
        });


        // Atualiza o DataTable
        tableEventos = $('#eventos').DataTable({
            language: {
                url: 'https://cdn.datatables.net/plug-ins/1.13.6/i18n/pt-BR.json',
            },
            order: [[3, 'asc']],
            columnDefs: [
                {
                    targets: [3],
                    orderData: [3, 4],
                    //render: $.fn.dataTable.render.moment('YYYY-MM-DD', 'DD/MM/YYYY')
                }
            ]
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

    // Add Slider
    addSlider(markers_layer_alvo);
    // Estatisticas
    atualizarEstatisticas(markers);
}

function clickMarker(e) {
    map.eachLayer(function (layer) {

        if (layer._leaflet_id == e.sourceTarget.destino_id) {
            var polyline = L.polyline([layer.getLatLng(), e.latlng], { color: 'red', weight: 0.8 }).addTo(map);
        }

        if (layer instanceof L.Polyline) {
            layer.remove();
        }

        if (layer._mRadius > 0) {
            if (layer._latlng.lat == e.latlng.lat && layer._latlng.lng == e.latlng.lng) {

                if (e.sourceTarget.feature.properties.alvo != 'base') {
                    layer.setStyle({ color: '#3388FF', opacity: 0.8, fillOpacity: 0.2 });
                } else {
                    layer.setStyle({ color: '#FFCC00', opacity: 0.8, fillOpacity: 0.2 });
                }

                layer.bringToFront();
            } else {
                layer.setStyle({ color: '#F2EFE9', opacity: 0, fillOpacity: 0 });
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

// ########################
// #
// # NOVA CAMADA
// #
// ########################
$('#nova-camada').click(function () {
    if ($(this).html() == 'Nova camada') {
        $('#col-formulario').show();
        $('#col-mapa').removeClass('col-9').addClass('col-10');
        $('#col-statisticas').hide();
        $(this).html("Estatísticas");
    } else {
        $('#col-formulario').hide();
        $('#col-mapa').removeClass('col-10').addClass('col-9');
        $('#col-statisticas').show();
        $(this).html("Nova camada");
    }
});

// ########################
// #
// # ESTATISTICA
// #
// ########################
function atualizarEstatisticas(markers) {
    $('#accordion-camadas').show();
    $('#col-formulario').hide();
    $('#col-mapa').removeClass('col-10').addClass('col-9');
    $('#col-statisticas').show();
    $('#nova-camada').html("Nova camada");

    // Contadores
    $('#chamadas-recebidas').html(chamadas_recebidas);
    $('#chamadas-originadas').html(chamadas_originadas);

    // Extraindo os horários das chamadas e interlocutores
    let horarios = [];
    let interlocutores = [];
    let cidades = [];
    let viagens = [];
    let cidade_atual = "";
    let ondemora = {};
    const ondemoraLayers = L.layerGroup().addTo(map);
    const dddMap = {};

    markers.forEach(function (marker) {
        marker = JSON.parse(marker);
        const horario = new Date('1970-01-01T' + marker.HORA_FORMATADA + 'Z'); // Adicionei 'Z' para garantir que o fuso horário seja UTC
        horarios.push(horario);
        interlocutores.push(marker.INTERLOCUTOR);

        if (marker.ERB_ALVO_CIDADE != null) {
            cidade = marker.ERB_ALVO_CIDADE.replace('_', ' ').toUpperCase();
            cidades.push(cidade);

            if (cidade_atual != cidade && cidade != '') {
                cidade_atual = cidade;
                viagens.push([cidade, new Date(marker.DATA_FORMATADA).toLocaleDateString()]);
            }

            // Cria a lista de ERBs de ondemora
            if (horario.getUTCHours() >= 0 && horario.getUTCHours() < 6) {
                const erb = marker.ERB_ALVO + '/' + marker.ERB_ALVO_AZIMUTE;
                if (erb != '/') {
                    if (!ondemora[erb]) {
                        ondemora[erb] = 0;

                        if (marker.ERB_ALVO_LATITUDE) {
                            createERB('ondemora', marker.ERB_ALVO_LATITUDE, marker.ERB_ALVO_LONGITUDE, marker, 'orange:home', marker.INTERLOCUTOR, parseInt(marker.ERB_ALVO_AZIMUTE || 0), 'ondemora', ondemoraLayers);
                        }
                    }
                    ondemora[erb]++;
                }
            }
        }

        // Processar DDD dos interlocutores
        if (marker.INTERLOCUTOR != '' && !isNaN(marker.interlocutor)) {
            const telefone = marker.INTERLOCUTOR.toString();
            if (telefone > 0 && telefone.toString().length >= 10 && !telefone.startsWith('303') && !telefone.startsWith('0800') && !telefone.startsWith('800')) {
                const ddd = telefone.substring(0, 2);
                if (!dddMap[ddd]) {
                    dddMap[ddd] = new Set();
                }
                dddMap[ddd].add(telefone);
            }
        }

    });

    // Atualizar lista de DDDs
    $('#ddds-list').html('');
    Object.keys(dddMap).forEach(ddd => {
        const numeros = Array.from(dddMap[ddd]);
        $('#ddds-list').append('<li><strong>DDD ' + ddd + '</strong><ul>' + numeros.map(num => '<li>' + num + '</li>').join('') + '</ul></li>');
    });

    // Contando o número de chamadas a cada 4 horas
    const callsPer4Hours = Array(6).fill(0);
    horarios.forEach(horario => {
        const hour = horario.getUTCHours();
        const group = Math.floor(hour / 4);
        callsPer4Hours[group]++;
    });

    // Contando o número de chamadas por interlocutor
    const callsPerInterlocutor = {};
    interlocutores.forEach(interlocutor => {
        if (!callsPerInterlocutor[interlocutor]) {
            callsPerInterlocutor[interlocutor] = 0;
        }
        callsPerInterlocutor[interlocutor]++;
    });

    // Contando o número de registros por cidade
    const callsPerCity = {};
    cidades.forEach(cidade => {
        if (!callsPerCity[cidade]) {
            callsPerCity[cidade] = 0;
        }
        callsPerCity[cidade]++;
    });
    const sortedCallsPerCity = Object.entries(callsPerCity).sort((a, b) => b[1] - a[1]);

    // Ordenando os interlocutores por número de chamadas em ordem decrescente
    const sortedEntries = Object.entries(callsPerInterlocutor).sort((a, b) => b[1] - a[1]);

    // Filtrando os registros que sejam maiores do que 5% do valor do primeiro registro
    const firstRecordValue = sortedEntries[0][1];
    const threshold = firstRecordValue * 0.05;

    const callsPerInterlocutorTop5Percent = sortedEntries.filter(entry => entry[1] > threshold);
    const sortedInterlocutors = callsPerInterlocutorTop5Percent.map(entry => entry[0]);
    const sortedCalls = callsPerInterlocutorTop5Percent.map(entry => entry[1]);

    // Ordenando as ERBs ondemora
    const sortedOndeMora = Object.entries(ondemora).sort((a, b) => b[1] - a[1]);

    // Configurando os dados para o gráfico de horários
    const ctxHorarios = document.getElementById('horarios');
    new Chart(ctxHorarios, {
        type: 'bar',
        data: {
            labels: ['0-4h', '4-8h', '8-12h', '12-16h', '16-20h', '20-24h'],
            datasets: [{
                label: 'Número de Chamadas',
                data: callsPer4Hours,
                borderWidth: 1
            }]
        },
        options: {
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });

    // Configurando os dados para o gráfico de interlocutores
    const ctxInterlocutores = document.getElementById('interlocutores');
    new Chart(ctxInterlocutores, {
        type: 'doughnut',
        data: {
            labels: sortedInterlocutors,
            datasets: [{
                label: 'Número de Chamadas',
                data: sortedCalls,
                borderWidth: 1
            }]
        },
        options: {
            plugins: {
                legend: {
                    display: false
                }
            }
        }
    });
    Object.entries(sortedEntries).forEach(([index, interlocutor]) => {
        $('#interlocutores-list').append('<li class="d-flex justify-content-between"><span>' + interlocutor[0] + '</span><span>' + interlocutor[1] + '</span></li>');
    });
    $('#interlocutores-list').hide();
    $('#btn-interlocutores-list').click(function (e) {
        $('#interlocutores-list').toggle();
        $('#interlocutores').toggle();
    });

    // Cidades
    Object.entries(sortedCallsPerCity).forEach(([index, cidade]) => {
        if (cidade[0] == 'null') {
            return;
        }
        $('#cidades-list').append('<li class="d-flex justify-content-between"><span>' + cidade[0] + '</span><span>' + cidade[1] + '</span></li>');
    });

    // Viagens
    Object.entries(viagens).forEach(([index, cidade]) => {
        $('#viagens-list').append('<li class="d-flex justify-content-between"><span>' + cidade[0] + '</span><span>' + cidade[1] + '</span></li>');
    });

    // Adicionando os elementos ao #ondemora-list
    layerControl.addOverlay(ondemoraLayers, "Onde Mora?");
    Object.entries(sortedOndeMora).forEach(([index, erbAlvo]) => {
        $('#ondemora-list').append('<li class="d-flex justify-content-between"><span><a href="#" class="destaqueErbOndemora" data-erb="' + erbAlvo[0] + '">' + erbAlvo[0] + '</a></span><span>' + erbAlvo[1] + '</span></li>');
    });
}




$(document).on('click', '.destaqueErbOndemora', function (e) {
    e.preventDefault();
    var erbAlvo = $(this).data('erb').split('/')[0];

    map.eachLayer(function (layer) {
        if (layer instanceof L.Marker) {
            if (layer.erbAlvo == erbAlvo) {
                layer.openPopup();
                map.flyTo(layer.getLatLng(), 12);
            }
        }
    });
});




// ########################
// #
// #  PROCURAR
// #
// ########################
$('#btn-procurar').click(function (e) {

    var interlocutor = $('#interlocutor').val();

    map.eachLayer(function (layer) {
        if (layer instanceof L.Marker) {
            if (parseInt(layer.interlocutor) != parseInt(interlocutor)) {
                if (layer._icon) {
                    layer._icon.style.display = 'none'; // Oculta o marcador
                }
                if (layer._shadow) {
                    layer._shadow.style.display = 'none'; // Oculta a sombra do marcador
                }
            }
        }
    });

});

// ########################
// #
// #  MARCADORES CUSTOMIZADOS
// #
// ########################
$('#novo-meuspontos').click(function () {
    var icon = L.IconMaterial.icon({ markerColor: $('#marcador_cor').val(), iconSize: [31, 42], icon: $('#marcador_icone').val() });

    m = L.marker([$('#marcador_latitude').val(), $('#marcador_longitude').val()], { draggable: 'true', icon: icon })
        .addTo(meuspontos)
        .bindTooltip($('#marcador_titulo').val(), { permanent: true })
    m.on('dragend', function (event) {
        var marker = event.target;
        var position = marker.getLatLng();
        marker.setLatLng(new L.LatLng(position.lat, position.lng));
    });

    var timestamp = new Date().getTime();
    m._id = timestamp;
    $('#close-modal-meuspontos').trigger('click');

    $('#camadas-container').append(
        `<div class="row mb-2 border-bottom" style="width: 300px;">
            <div class="d-flex justify-content-between">
                <h6>
                    <input type="checkbox" class="form-checkbox checkbox-camadas" data-iam="alvo" checked>
                    <strong>` + $('#marcador_titulo').val() + `</strong>
                </h6>
                <input type="color" data-iam="` + $('#marcador_titulo').val() + `" value="` + $('#marcador_cor').val() + `" class="border-0 form-control form-control-sm form-control-color">
            </div>
        </div>`);
    $("#accordion-camadas").show();
});


$('#btn-meuspontos, #btn-camadas-meuspontos').click(function () {
    map_center = map.getCenter();
    $('#marcador_latitude').val(map_center.lat);
    $('#marcador_longitude').val(map_center.lng);
});