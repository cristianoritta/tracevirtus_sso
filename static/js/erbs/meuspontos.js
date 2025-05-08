
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