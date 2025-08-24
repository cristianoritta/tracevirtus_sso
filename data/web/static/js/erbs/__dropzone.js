// ########################
// #
// #  DROPZONE
// #
// ########################
Dropzone.options.fileDropzone = {
    paramName: "file",
    autoProcessQueue: false,
    maxFiles: 5,
    maxFilesize: 5,
    addRemoveLinks: true,
    accept: function (file, done) {
        done();
    },
    init: function () {
        var myDropzone = this;

        this.element.querySelector("button[type=submit]").addEventListener("click", function (e) {
            e.preventDefault();
            e.stopPropagation();

            const form = myDropzone.element;
            const fields = form.querySelectorAll('[required]');
            let allValid = true;

            // Remove error class from all fields
            fields.forEach(field => field.classList.remove('error'));

            // Validate each required field
            fields.forEach(field => {
                if (!field.value.trim()) {
                    allValid = false;
                    field.classList.add('error');
                }
            });

            // If all required fields are valid, process the Dropzone queue
            if (allValid) {
                Toast = Swal.mixin({
                    toast: true,
                    position: "top-end",
                    showConfirmButton: false,
                    timer: 3000
                });
                Toast.fire({
                    icon: "info",
                    title: "Carregando dados..."
                });
                myDropzone.processQueue();
            } else {
                Swal.fire({
                    title: 'Erro!',
                    text: 'Preencha todos os campos corretamente!',
                    icon: 'error',
                });
            }
        });

        this.on("success", function (file, response) {
            addLayerMarkers(response);
        });

        this.on("complete", function (file) {
            this.removeFile(file);
        });
    }
};
