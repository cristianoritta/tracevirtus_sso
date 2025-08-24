

jQuery.adjustSelect = function () {
    $("select").each(function () {
        if ($(this).attr('value')) {
            $(this).val($(this).attr('value'));
        }
    });
}
