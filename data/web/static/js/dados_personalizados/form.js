
document.addEventListener("DOMContentLoaded", function () {
    function formatarTelefone(e) {
        let value = e.target.value.replace(/\D/g, "");
        if (value.startsWith("55")) {
            value = value.slice(2);
        }
        if (value.length === 11) {
            e.target.value = `(${value.slice(0, 2)}) ${value.slice(2, 3)} ${value.slice(3, 7)}-${value.slice(7)}`;
        } else if (value.length === 10) {
            e.target.value = `(${value.slice(0, 2)}) ${value.slice(2, 6)}-${value.slice(6)}`;
        }
    }

    const camposTelefone = ["linha"];

    camposTelefone.forEach(function (campo) {
        const input = document.getElementById(campo);
        if (input) {
            input.addEventListener("input", formatarTelefone);
        }
    });

    function formatarNome(e) {
        let value = e.target.value;
        value = value.replace(/[^a-zA-Z\sáéíóúÁÉÍÓÚçÇãõÃÕ]/g, ""); // Remove caracteres não permitidos
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

        let nomeFormatado = palavrasFormatadas.join(" ");
        e.target.value = nomeFormatado;
    }

    const camposParaFormatar = ["utilizador"];

    camposParaFormatar.forEach(function (campo) {
        const input = document.getElementById(campo);
        if (input) {
            input.addEventListener("input", formatarNome);
        }
    });
});