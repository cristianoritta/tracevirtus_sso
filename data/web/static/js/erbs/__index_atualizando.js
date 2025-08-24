$('#col-statisticas').hide();
$('#accordion-camadas').hide();







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









