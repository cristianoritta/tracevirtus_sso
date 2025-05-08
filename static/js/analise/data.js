// static/js/analise/data.js

var $table = $('#table');
var selections = [];

function getIdSelections() {
    return $.map($table.bootstrapTable('getSelections'), function (row) {
        return row.id;
    });
}

function responseHandler(res) {
    var columns = res.columns.map(function (col) {
        if (col == "origem" || col == "Operadora") {
            filter = "select";
            classControl = "form-select";
        } else {
            filter = "input";
            classControl = "form-control";
        }

        return {
            field: col,
            title: col.charAt(0).toUpperCase() + col.slice(1),
            sortable: true,
            align: 'center',
            visible: !['id', 'id_caso', 'id_arquivo', 'created_by'].includes(col.toLowerCase()),
            switchable: !['id', 'id_caso', 'id_arquivo', 'created_by'].includes(col.toLowerCase()),
            filterControl: filter,
        };
    });

    $table.bootstrapTable('destroy').bootstrapTable({
        height: $table.parent().height(),
        width: $table.parent().width(),
        locale: 'pt-BR',
        columns: columns,
        data: res.rows,
        classes: 'table table-bordered table-sm small'
    });

    return res;
}

function detailFormatter(index, row) {
    var html = [];
    $.each(row, function (key, value) {
        html.push('<p class="small"><b>' + key + ':</b> ' + value + '</p>');
    });
    return html.join('');
}

function initTable() {
    var url = $table.data('url');

    $table.bootstrapTable('destroy').bootstrapTable({
        height: $table.parent().height(),
        width: $table.parent().width(),
        locale: 'pt-BR',
        columns: [],
        data: [],
        classes: 'table table-bordered table-sm small'
    });

    $.get(url, function (res) {
        responseHandler(res);
    });

    $table.on('check.bs.table uncheck.bs.table check-all.bs.table uncheck-all.bs.table', function () {
        selections = getIdSelections();
    });

    $table.on('all.bs.table', function (e, name, args) {
        console.log(name, args);
    });
}

$(function () {
    initTable();

    $(window).resize(function () {
        $table.bootstrapTable('resetView', {
            height: $table.parent().height(),
            width: $table.parent().width()
        });
    });
});