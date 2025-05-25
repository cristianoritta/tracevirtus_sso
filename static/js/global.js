$(document).ready(function () {


    /**
     * Exibe / Oculta elementos no DOM
     * 
     * .btn-content-toggle 
     * @params
     * data-hide="class-to-hide" data-show="class-to-show"
     */
    $('.btn-content-toggle').click(function () {
        $('.' + $(this).data('hide')).hide();
        $('.' + $(this).data('show')).show();
    });

    /**
     * Remove o botão direito do mouse
     */
    document.addEventListener('contextmenu', function (event) {
        //event.preventDefault();
    });
    document.addEventListener('keydown', function (event) {
        if (event.key === 'F12' || (event.ctrlKey && (event.key === 'I' || event.key === 'J' || event.key === 'j' || event.key === 'i' || event.key === 'C' || event.key === 'c'))) {
            //event.preventDefault();
            //return false; // Cancela o evento
        }
    });



    /**
     * Popover @bootstrap
     */

    $("a[title]").attr("data-bs-popover", "popover");
    $("a[title]").attr("data-bs-trigger", "hover focus");
    $('[data-bs-toggle="popover"], [data-bs-popover="popover"]').popover();

    /**
     * Tooltip @bootstrap
     */
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });


    /**
     * DataTable
     */
    if ($('.dataTable').length > 0) {
        let table = new DataTable('.dataTable', {
            "order": [0, 'asc'],
            "language": {
                "lengthMenu": "Mostrar _MENU_ registros por página",
                "zeroRecords": "Nenhum registro encontrado",
                "info": "Mostrando página _PAGE_ de _PAGES_",
                "infoEmpty": "Nenhum registro disponível",
                "emptyTable": "Nenhum registro disponível",
                "infoFiltered": "(filtrado de _MAX_ registros no total)",
                "search": "Procurar:",
                "paginate": {
                    "first": "Primeiro",
                    "last": "Último",
                    "next": "Próximo",
                    "previous": "Anterior"
                }
            }
        });
    }


    /**
     * ALERT
     */
    setTimeout(function () {
        $('.alert-card').fadeOut('slow');
    }, 3000);


    /**
     * MODAL
     */
    $('body').on('click', '.show-modal', function (e) {
        e.preventDefault();

        $.ajax({
            url: $(this).attr('href'),
            type: 'GET',
            dataType: 'html',
            beforeSend: function () {
                $("#modal-body").html("<span class='text-white'><i class='fas fa-spinner fa-spin fa-3x fa-fw margin-bottom'></i> carregando...</span>");
                $('#open-modal').trigger('click');
            },
            success: function (html) {
                $("#modal-body").html(html);
            },
            error: function (xhr) {
                $('#modal').modal('hide');
                $("#modal-body").html('');

                Swal.fire({
                    title: 'WTK',
                    text: "Desculpe, não foi possível executar a ação.\n\n" + xhr.responseText,
                    type: 'error',
                    icon: 'info',
                });
            }
        });
        $("#modal-body").html("<span class='text-white'><i class='fas fa-spinner fa-spin fa-fw margin-bottom'></i> carregando...</span>");
    });


    /**
     * 
     * HTMX
     * 
     * Sweet Alert
     */
    document.addEventListener("htmx:confirm", function (e) {
        e.preventDefault();
        if (!e.target.hasAttribute('hx-confirm')) {
            e.detail.issueRequest(true);
            return;
        }

        Swal.fire({
            title: "Atenção",
            text: e.detail.question,
            showCancelButton: true,
            confirmButtonText: "Sim",
            cancelButtonText: "Não",
        }).then(function (result) {
            if (result.value) {
                e.detail.issueRequest(true);
            }
        });
    });


});

/**
 * AdjustSelect: Define o <option> do <select> de acordo com o @value
 */
function adjustSelect() {
    $("select").each(function () {
        if ($(this).attr('value')) {
            $(this).val($(this).attr('value'));
        }
    });
}


/**
 * Capitalizar Nomes
 */
function capitalizarNomes() {
    const inputsNomes = ['nome', 'nome_completo', 'mae', 'pai', 'endereco', 'bairro'];
    inputsNomes.forEach(function (inputId) {
        const inputElem = document.getElementById(inputId);
        if (inputElem) {
            inputElem.value = formatarNome(inputElem.value);
            inputElem.addEventListener("input", function (e) {
                e.target.value = formatarNome(e.target.value);
            });
        }
    });
}
function formatarNome(nome) {
    let value = nome.replace(/[^a-zA-Z\sáéíóúÁÉÍÓÚçÇãõÃÕ]/g, "");
    let palavras = value.split(" ");
    let palavrasFormatadas = [];
    const palavrasMinusculas = ["de", "do", "da", "dos", "das", "e"];

    for (let palavra of palavras) {
        if (palavrasMinusculas.includes(palavra.toLowerCase())) {
            palavrasFormatadas.push(palavra.toLowerCase());
        } else {
            let palavraFormatada = palavra.charAt(0).toUpperCase() + palavra.slice(1).toLowerCase();
            palavrasFormatadas.push(palavraFormatada);
        }
    }

    return palavrasFormatadas.join(" ");
}

/**
 * Copy To Clipboard
 */
function copyToClipboard(el) {
    var range = document.createRange();
    range.selectNode(document.getElementById(el));
    window.getSelection().removeAllRanges();
    window.getSelection().addRange(range);
    document.execCommand("copy");
    window.getSelection().removeAllRanges();
    salert("Copiado para a área de transferência");
}

/**
 * ALERT customizado para o SweetAlert
 */
function salert(message) {
    Swal.fire({
        title: "ALIAS",
        text: message,
    });
}

/**
 * searchData. Pesquisa dentro dos cards
 */

function searchData(o) {
    // Declare variables
    var input, filter;
    input = $(o).val();
    filter = input.toUpperCase();
    cards = $($(o).data('cards'));

    $.each(cards, function (i, obj) {
        sFullText = "";

        $(obj).find("*").each(function () {
            sFullText = sFullText + $(this).text().trim().replace(/\s\s+/g, ' ') + ' ';
        });

        if (sFullText.toUpperCase().search(filter) > -1) {
            $(cards).eq(i).show();
        } else {
            $(cards).eq(i).hide();
        }

    });
}
