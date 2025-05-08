var markers = JSON.parse($('#markers').val());
let chamadas_recebidas = 0;
let chamadas_originadas = 0;
let horarios = [];
let interlocutores = [];
let cidades = [];
let viagens = [];
let cidade_atual = "";
let ondemora = {};
let erbs = {};
const dddMap = {};

// Itere sobre cada chave no objeto markers
markers.forEach(function (marker) {
    if (marker['Direção'] == 'Recebida') {
        chamadas_recebidas++;
    } else {
        chamadas_originadas++;

    }

    const horario = new Date(marker['data_hora_ordenacao']); // Adicionei 'Z' para garantir que o fuso horário seja UTC
    horarios.push(horario);
    interlocutores.push(marker['Linha do Interlocutor']);

    if (marker['Cidade da ERB do Alvo'] != null) {
        cidade = marker['Cidade da ERB do Alvo'].replace('_', ' ').toUpperCase();
        cidades.push(cidade);

        if (cidade_atual != cidade && cidade != '') {
            cidade_atual = cidade;
            viagens.push([cidade, new Date(marker['Data e Hora']).toLocaleDateString()]);
        }

        // Cria a lista de ERBs de ondemora
        if (horario.getUTCHours() >= 0 && horario.getUTCHours() < 6) {
            const erb = marker['ERB do Alvo'] + '/' + marker['Azimute do Alvo'];
            if (erb != '/') {
                if (!ondemora[erb]) {
                    ondemora[erb] = 0;
                    erbs[erb] = marker;
                }
                ondemora[erb]++;
            }
        }
    }

    // Processar DDD dos interlocutores
    if (marker['Linha do Interlocutor'] != '' && !isNaN(marker['Linha do Interlocutor'])) {
        const telefone = marker['Linha do Interlocutor'] + ' - ' + marker['Operadora do Interlocutor'];
        if (telefone > 0 && telefone.toString().length >= 10 && !telefone.startsWith('303') && !telefone.startsWith('0800') && !telefone.startsWith('800')) {
            const ddd = telefone.substring(2, 4);
            if (!dddMap[ddd]) {
                dddMap[ddd] = new Set();
            }
            dddMap[ddd].add(telefone);
        }
    }

});


// Contadores
$('#chamadas-recebidas').html(chamadas_recebidas);
$('#chamadas-originadas').html(chamadas_originadas);

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
Object.entries(sortedOndeMora).forEach(([index, erbAlvo]) => {
    $('#ondemora-list').append('<li class="d-flex justify-content-between"><div><strong>' + erbs[erbAlvo[0]]['ERB do Alvo'] + ', Az. ' + erbs[erbAlvo[0]]['Azimute do Alvo'] + '</strong><br><small>' + erbs[erbAlvo[0]]['Endereço da ERB do Alvo'] + '</small></div><div>' + erbAlvo[1] + '</div></li>');
});

// Configurando os dados para o gráfico de horários
const ctxHorarios = document.getElementById('horarios');
new Chart(ctxHorarios, {
    type: 'bar',
    data: {
        labels: ['0-4h', '4-8h', '8-12h', '12-16h', '16-20h', '20-24h'],
        datasets: [{
            label: 'Número de Chamadas',
            data: callsPer4Hours,
            borderWidth: 1,
            backgroundColor: [
                'rgba(75, 192, 192, 0.5)',  // 0-4h
                'rgba(54, 162, 235, 0.5)',  // 4-8h
                'rgba(255, 206, 86, 0.5)',  // 8-12h
                'rgba(153, 102, 255, 0.5)', // 12-16h
                'rgba(255, 159, 64, 0.5)',  // 16-20h
                'rgba(255, 99, 132, 0.5)'   // 20-24h
            ]
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

function getRandomColor(opacity = 0.5) {
    const r = Math.floor(Math.random() * 256);
    const g = Math.floor(Math.random() * 256);
    const b = Math.floor(Math.random() * 256);
    return `rgba(${r}, ${g}, ${b}, ${opacity})`;
}
const colors = sortedInterlocutors.map(() => getRandomColor());

// Configurando os dados para o gráfico de interlocutores
const ctxInterlocutores = document.getElementById('interlocutores');
new Chart(ctxInterlocutores, {
    type: 'doughnut',
    data: {
        labels: sortedInterlocutors,
        datasets: [{
            label: 'Número de Chamadas',
            data: sortedCalls,
            borderWidth: 1,
            backgroundColor: colors
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

/* ******************************
 *
 * POSICIONA OS ELEMENTOS NA TELA
 * 
 * ******************************/

function alturaElemento(elemento) {

    // Posição do topo do elemento em relação ao topo da página
    posicaoTop = $(elemento).offset().top;

    // Altura total da janela
    alturaJanela = $(window).height();

    // Calcula a altura restante da tela a partir da posição do elemento até o final da janela
    novaAltura = alturaJanela - posicaoTop - 60;

    return parseInt(novaAltura) + 'px';
}



// Aplica a nova altura ao elemento
$('#viagens-list').css('height', alturaElemento($('#viagens-list')));
$('#ddds-list').css('height', alturaElemento($('#ddds-list')));
$('#ondemora-list').css('height', alturaElemento($('#ondemora-list')));