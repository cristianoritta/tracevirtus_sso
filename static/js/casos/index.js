function activateButton(clickedButton) {
    // Seleciona todos os botões com a classe 'caso-btn' e altera para 'btn-outline-primary'
    document.querySelectorAll('.caso-btn').forEach(button => {
        button.classList.remove('btn-outline-warning');
        button.classList.add('btn-outline-primary');
    });
    // Altera o botão clicado para 'btn-outline-warning'
    clickedButton.classList.remove('btn-outline-primary');
    clickedButton.classList.add('btn-outline-warning');
}