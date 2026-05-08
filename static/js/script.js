const ociAvaliacao = document.getElementById('oci_avaliacao');
const ociCirurgia = document.getElementById('oci_cirurgia');
const divAvaliacao = document.getElementById('procedimentos_avaliacao');
const divCirurgia = document.getElementById('procedimentos_cirurgia');
const ociPmaeHidden = document.getElementById('oci_pmae');

let pacienteExistente = null;
let modoEdicao = false;

function mostrarErroCampo(id, mensagem) {
    const el = document.getElementById(id);
    if (!el) return;
    el.classList.add('is-invalid');
    let feedback = el.parentNode.querySelector('.invalid-feedback');
    if (!feedback) {
        feedback = document.createElement('div');
        feedback.className = 'invalid-feedback';
        el.parentNode.appendChild(feedback);
    }
    feedback.textContent = mensagem;
}

function limparErrosCampos() {
    document.querySelectorAll('.is-invalid').forEach(function(el) {
        el.classList.remove('is-invalid');
    });
}

// Carregar unidade do usuário logado (fixa - sem seleção)
async function carregarUnidadeUsuario() {
    try {
        const response = await fetch('/api/usuario/unidade_atual');
        const userData = await response.json();
        
        const unidadeInfo = document.getElementById('unidadeInfo');
        
        if (userData.unidade_id && userData.unidade_nome) {
            unidadeInfo.innerHTML = `
                <div class="card border-primary" style="background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);">
                    <div class="card-body py-2">
                        <strong>${userData.unidade_nome}</strong><br>
                        <small class="text-muted">📍 ${userData.unidade_municipio || 'Não informado'}</small><br>
                        <small class="text-muted">📋 CNES: ${userData.unidade_cnes || 'Não informado'}</small>
                    </div>
                </div>
            `;
            localStorage.setItem('unidade_selecionada', JSON.stringify({
                id: userData.unidade_id,
                nome: userData.unidade_nome,
                municipio: userData.unidade_municipio,
                cnes: userData.unidade_cnes
            }));
        } else {
            unidadeInfo.innerHTML = `
                <div class="alert alert-warning mb-0 py-2">
                    ⚠️ Nenhuma unidade definida. 
                    <a href="/configuracoes" class="alert-link">Clique aqui para configurar</a>
                </div>
            `;
        }
    } catch (error) {
        console.error('Erro ao carregar unidade do usuário:', error);
        document.getElementById('unidadeInfo').innerHTML = `
            <div class="alert alert-danger mb-0 py-2">
                ❌ Erro ao carregar unidade
            </div>
        `;
    }
}

// Buscar paciente por CPF
async function buscarPaciente() {
    const cpf = document.getElementById('cpf').value.replace(/\D/g, '');
    
    if (!cpf || cpf.length !== 11) {
        showToast('Digite um CPF válido com 11 dígitos', 'warning');
        return;
    }
    
    try {
        const response = await fetch('/api/paciente/buscar', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({cpf: cpf})
        });
        
        const result = await response.json();
        
        if (result.encontrado) {
            pacienteExistente = result.paciente;
            modoEdicao = true;
            
            // Preencher dados do paciente
            document.getElementById('nome').value = pacienteExistente.nome_completo;
            document.getElementById('data_nascimento').value = pacienteExistente.data_nascimento;
            document.getElementById('nome_mae').value = pacienteExistente.nome_mae;
            document.getElementById('sexo').value = pacienteExistente.sexo;
            document.getElementById('raca_cor').value = pacienteExistente.raca_cor;
            
            // NOVOS CAMPOS
            if (document.getElementById('endereco')) {
                document.getElementById('endereco').value = pacienteExistente.endereco || '';
                document.getElementById('bairro').value = pacienteExistente.bairro || '';
                document.getElementById('cep').value = pacienteExistente.cep || '';
                document.getElementById('contato').value = pacienteExistente.contato || '';
            }
            
            // Calcular idade
            const nascimento = new Date(pacienteExistente.data_nascimento);
            const hoje = new Date();
            let idade = hoje.getFullYear() - nascimento.getFullYear();
            const mesDiff = hoje.getMonth() - nascimento.getMonth();
            if (mesDiff < 0 || (mesDiff === 0 && hoje.getDate() < nascimento.getDate())) idade--;
            document.getElementById('idade').value = idade;
            
            // Mostrar procedimentos existentes
            const procedimentosExistentes = pacienteExistente.procedimentos || [];
            let procLista = procedimentosExistentes.map(function(p) {
                return typeof p === 'object' && p.nome ? p.nome : p;
            }).join('\n');
            
            showToast('Paciente encontrado: ' + pacienteExistente.nome_completo + ' - Deseja adicionar novo procedimento?', 'info');
            
            if (confirm('✅ Paciente encontrado: ' + pacienteExistente.nome_completo + '\n\nProcedimentos já realizados:\n' + procLista + '\n\nDeseja adicionar um novo procedimento?')) {
                document.getElementById('cpf').disabled = true;
                document.getElementById('nome').disabled = true;
                document.getElementById('data_nascimento').disabled = true;
                document.getElementById('nome_mae').disabled = true;
                document.getElementById('sexo').disabled = true;
                document.getElementById('raca_cor').disabled = true;
                if (document.getElementById('endereco')) {
                    document.getElementById('endereco').disabled = true;
                    document.getElementById('bairro').disabled = true;
                    document.getElementById('cep').disabled = true;
                    document.getElementById('contato').disabled = true;
                }
                
                document.getElementById('mensagem').innerHTML = `
                    <div class="alert alert-info">
                        🔄 Modo de edição: Adicionando procedimento para ${pacienteExistente.nome_completo}
                    </div>
                `;
            } else {
                pacienteExistente = null;
                modoEdicao = false;
                limparFormulario();
            }
        } else {
            modoEdicao = false;
            pacienteExistente = null;
            showToast('Paciente não encontrado. Preencha os dados para novo cadastro.', 'warning');
            document.getElementById('mensagem').innerHTML = `
                <div class="alert alert-warning">
                    ⚠️ Paciente não encontrado. Preencha os dados para novo cadastro.
                </div>
            `;
            setTimeout(() => {
                document.getElementById('mensagem').innerHTML = '';
            }, 3000);
        }
    } catch (error) {
        console.error('Erro:', error);
        showToast('Erro ao buscar paciente', 'error');
    }
}

function limparFormulario() {
    limparErrosCampos();
    document.getElementById('cpf').disabled = false;
    document.getElementById('nome').disabled = false;
    document.getElementById('data_nascimento').disabled = false;
    document.getElementById('nome_mae').disabled = false;
    document.getElementById('sexo').disabled = false;
    document.getElementById('raca_cor').disabled = false;
    if (document.getElementById('endereco')) {
        document.getElementById('endereco').disabled = false;
        document.getElementById('bairro').disabled = false;
        document.getElementById('cep').disabled = false;
        document.getElementById('contato').disabled = false;
    }
    document.getElementById('formPaciente').reset();
    document.getElementById('idade').value = '';
    divAvaliacao.style.display = 'none';
    divCirurgia.style.display = 'none';
    ociAvaliacao.checked = false;
    ociCirurgia.checked = false;
}

// Máscara CPF
document.getElementById('cpf').addEventListener('blur', function() {
    if (this.value.length >= 14) {
        buscarPaciente();
    }
});

document.getElementById('cpf').addEventListener('input', function(e) {
    let value = e.target.value.replace(/\D/g, '');
    if (value.length <= 11) {
        value = value.replace(/(\d{3})(\d)/, '$1.$2');
        value = value.replace(/(\d{3})(\d)/, '$1.$2');
        value = value.replace(/(\d{3})(\d{1,2})$/, '$1-$2');
        e.target.value = value;
    }
});

// Máscara para CEP
if (document.getElementById('cep')) {
    document.getElementById('cep').addEventListener('input', function(e) {
        let value = e.target.value.replace(/\D/g, '');
        if (value.length <= 8) {
            if (value.length > 5) {
                value = value.replace(/(\d{5})(\d)/, '$1-$2');
            }
            e.target.value = value;
        }
    });
}

// Máscara para Telefone
if (document.getElementById('contato')) {
    document.getElementById('contato').addEventListener('input', function(e) {
        let value = e.target.value.replace(/\D/g, '');
        if (value.length <= 11) {
            if (value.length > 2) {
                value = value.replace(/(\d{2})(\d)/, '($1) $2');
            }
            if (value.length > 7) {
                if (value.length > 10) {
                    value = value.replace(/(\d{5})(\d{4})$/, '$1-$2');
                } else {
                    value = value.replace(/(\d{4})(\d{4})$/, '$1-$2');
                }
            }
            e.target.value = value;
        }
    });
}

// Calcular idade
document.getElementById('data_nascimento').addEventListener('change', function() {
    if (this.disabled) return;
    const nascimento = new Date(this.value);
    const hoje = new Date();
    let idade = hoje.getFullYear() - nascimento.getFullYear();
    const mesDiff = hoje.getMonth() - nascimento.getMonth();
    if (mesDiff < 0 || (mesDiff === 0 && hoje.getDate() < nascimento.getDate())) idade--;
    document.getElementById('idade').value = idade > 0 ? idade : '';
});

// Maiúsculas
document.getElementById('nome').addEventListener('input', function() { 
    if (!this.disabled) this.value = this.value.toUpperCase(); 
});
document.getElementById('nome_mae').addEventListener('input', function() { 
    if (!this.disabled) this.value = this.value.toUpperCase(); 
});

function atualizarOpcoesOlho() {
    const olhoSelect = document.getElementById('olho');
    const valorAtual = olhoSelect.value;
    const isFaco = ociCirurgia.checked;
    
    olhoSelect.innerHTML = '<option value="">Selecione</option>';
    
    if (isFaco) {
        olhoSelect.innerHTML += '<option value="OD">Olho Direito</option>';
        olhoSelect.innerHTML += '<option value="OE">Olho Esquerdo</option>';
    } else {
        olhoSelect.innerHTML += '<option value="OD">Olho Direito</option>';
        olhoSelect.innerHTML += '<option value="OE">Olho Esquerdo</option>';
        olhoSelect.innerHTML += '<option value="AMBOS">Ambos os Olhos</option>';
        olhoSelect.innerHTML += '<option value="SEM">Sem Indicação Cirúrgica</option>';
    }
    
    if (valorAtual) olhoSelect.value = valorAtual;
}

// Mostrar procedimentos e marcar automaticamente
ociAvaliacao.addEventListener('change', function() {
    if (this.checked) {
        divAvaliacao.style.display = 'block';
        divCirurgia.style.display = 'none';
        ociPmaeHidden.value = this.value;
        
        const procCirurgia = document.getElementById('procedimento_cirurgia');
        if (procCirurgia) procCirurgia.checked = false;
        
        setTimeout(function() {
            const divAvaliacaoEl = document.getElementById('procedimentos_avaliacao');
            if (divAvaliacaoEl) {
                const checkboxes = divAvaliacaoEl.querySelectorAll('input[type="checkbox"]');
                checkboxes.forEach(function(checkbox) {
                    checkbox.checked = true;
                });
            }
        }, 50);
        
        atualizarOpcoesOlho();
    }
});

ociCirurgia.addEventListener('change', function() {
    if (this.checked) {
        divAvaliacao.style.display = 'none';
        divCirurgia.style.display = 'block';
        ociPmaeHidden.value = this.value;
        
        const procCirurgia = document.getElementById('procedimento_cirurgia');
        if (procCirurgia) procCirurgia.checked = true;
        
        const divAvaliacaoEl = document.getElementById('procedimentos_avaliacao');
        if (divAvaliacaoEl) {
            const checkboxes = divAvaliacaoEl.querySelectorAll('input[type="checkbox"]');
            checkboxes.forEach(function(checkbox) {
                checkbox.checked = false;
            });
        }
        
        atualizarOpcoesOlho();
    }
});

function getProcedimentos() {
    const procedimentos = [];
    
    if (ociAvaliacao.checked) {
        procedimentos.push('09.05.01.003-5 - OCI DE AVALIAÇÃO INICIAL EM OFTALMOLOGIA');
        
        document.querySelectorAll('#procedimentos_avaliacao .procedimento-check:checked').forEach(cb => {
            procedimentos.push(cb.getAttribute('data-procedimento'));
        });
    } else if (ociCirurgia.checked && document.getElementById('procedimento_cirurgia').checked) {
        const procCirurgia = document.getElementById('procedimento_cirurgia');
        if (procCirurgia) {
            procedimentos.push(procCirurgia.getAttribute('data-procedimento'));
        }
    }
    
    return procedimentos;
}

function validarFormulario() {
    limparErrosCampos();
    let valido = true;
    
    if (!document.getElementById('nome').value.trim()) {
        mostrarErroCampo('nome', 'Nome do paciente é obrigatório');
        valido = false;
    }
    if (!document.getElementById('cpf').value.replace(/\D/g, '')) {
        mostrarErroCampo('cpf', 'CPF é obrigatório');
        valido = false;
    }
    if (!document.getElementById('data_nascimento').value) {
        mostrarErroCampo('data_nascimento', 'Data de nascimento é obrigatória');
        valido = false;
    }
    if (!document.getElementById('nome_mae').value.trim()) {
        mostrarErroCampo('nome_mae', 'Nome da mãe é obrigatório');
        valido = false;
    }
    if (!document.getElementById('sexo').value) {
        mostrarErroCampo('sexo', 'Selecione o sexo');
        valido = false;
    }
    if (!document.getElementById('raca_cor').value) {
        mostrarErroCampo('raca_cor', 'Selecione a raça/cor');
        valido = false;
    }
    if (!document.getElementById('data_realizacao').value) {
        mostrarErroCampo('data_realizacao', 'Data da realização é obrigatória');
        valido = false;
    }
    if (!ociAvaliacao.checked && !ociCirurgia.checked) {
        showToast('Selecione o tipo de OCI/PMAE', 'warning');
        valido = false;
    }
    if (!document.getElementById('olho').value) {
        mostrarErroCampo('olho', 'Selecione o olho');
        valido = false;
    }
    
    if (ociCirurgia.checked) {
        const temProcedimentoAvaliacao = Array.from(document.querySelectorAll('#procedimentos_avaliacao .procedimento-check:checked')).length > 0;
        if (temProcedimentoAvaliacao) {
            showToast('Para CIRURGIA, não é permitido selecionar procedimentos de AVALIAÇÃO!', 'error');
            valido = false;
        }
    }
    
    const procedimentos = getProcedimentos();
    if ((ociAvaliacao.checked && procedimentos.length === 0) || (ociCirurgia.checked && procedimentos.length === 0)) {
        showToast('Selecione pelo menos um procedimento', 'warning');
        valido = false;
    }
    
    return valido;
}

// Envio do formulário
document.getElementById('formPaciente').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    if (!validarFormulario()) return;
    
    const unidadeSalva = localStorage.getItem('unidade_selecionada');
    if (!unidadeSalva) {
        showToast('Configure sua unidade nas Configurações primeiro!', 'error');
        window.location.href = '/configuracoes';
        return;
    }
    
    const unidade = JSON.parse(unidadeSalva);
    
    const procedimentos = getProcedimentos();
    const cpf = document.getElementById('cpf').value.replace(/\D/g, '');
    const dataRealizacao = document.getElementById('data_realizacao').value;
    
    const btn = document.querySelector('button[type="submit"]');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> Salvando...';
    
    try {
        if (modoEdicao && pacienteExistente) {
            const olhoEdit = document.getElementById('olho').value;
            
            const response = await fetch('/api/paciente/adicionar_procedimento', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    cpf: cpf,
                    procedimento: procedimentos[0],
                    data_realizacao: dataRealizacao,
                    olho: olhoEdit
                })
            });
            
            const result = await response.json();
            
            if (response.ok) {
                showToast(result.mensagem || 'Procedimento adicionado com sucesso!', 'success');
                
                divAvaliacao.style.display = 'none';
                divCirurgia.style.display = 'none';
                ociAvaliacao.checked = false;
                ociCirurgia.checked = false;
                document.getElementById('data_realizacao').value = '';
                document.getElementById('olho').value = '';
                
                document.getElementById('mensagem').innerHTML = `<div class="alert alert-success">✅ ${result.mensagem}</div>`;
                setTimeout(() => { document.getElementById('mensagem').innerHTML = ''; }, 3000);
            } else {
                showToast(result.erro || 'Erro ao adicionar procedimento', 'error');
                document.getElementById('mensagem').innerHTML = `<div class="alert alert-danger">❌ ${result.erro}</div>`;
            }
        } else {
            const dados = {
                nome: document.getElementById('nome').value,
                data_nascimento: document.getElementById('data_nascimento').value,
                cpf: cpf,
                nome_mae: document.getElementById('nome_mae').value,
                sexo: document.getElementById('sexo').value,
                raca_cor: document.getElementById('raca_cor').value,
                procedimentos: procedimentos,
                olho: document.getElementById('olho').value,
                data_realizacao: dataRealizacao,
                oci_pmae: ociPmaeHidden.value,
                unidade_executora: unidade,
                endereco: document.getElementById('endereco') ? document.getElementById('endereco').value : '',
                bairro: document.getElementById('bairro') ? document.getElementById('bairro').value : '',
                cep: document.getElementById('cep') ? document.getElementById('cep').value : '',
                contato: document.getElementById('contato') ? document.getElementById('contato').value : ''
            };
            
            const response = await fetch('/api/paciente', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(dados)
            });
            
            const result = await response.json();
            
            if (response.ok) {
                showToast(result.mensagem || 'Paciente cadastrado com sucesso!', 'success');
                document.getElementById('formPaciente').reset();
                divAvaliacao.style.display = 'none';
                divCirurgia.style.display = 'none';
                ociAvaliacao.checked = false;
                ociCirurgia.checked = false;
                document.getElementById('idade').value = '';
                document.getElementById('cpf').disabled = false;
                if (document.getElementById('endereco')) {
                    document.getElementById('endereco').disabled = false;
                    document.getElementById('bairro').disabled = false;
                    document.getElementById('cep').disabled = false;
                    document.getElementById('contato').disabled = false;
                }
                document.getElementById('mensagem').innerHTML = `<div class="alert alert-success">✅ ${result.mensagem}</div>`;
                setTimeout(() => { document.getElementById('mensagem').innerHTML = ''; }, 3000);
            } else {
                showToast(result.erro || 'Erro ao cadastrar', 'error');
                document.getElementById('mensagem').innerHTML = `<div class="alert alert-danger">❌ ${result.erro}</div>`;
            }
        }
    } catch (error) {
        console.error('Erro:', error);
        showToast('Erro ao conectar com o servidor', 'error');
        document.getElementById('mensagem').innerHTML = `<div class="alert alert-danger">❌ Erro ao conectar</div>`;
    }
    
    btn.innerHTML = '💾 Cadastrar Paciente';
    btn.disabled = false;
});

// Carregar unidades ao iniciar (se o elemento existir)
if (document.getElementById('unidadeExportar')) {
    carregarUnidadesParaExportar();
}

// Carregar unidade do usuário ao iniciar
carregarUnidadeUsuario();