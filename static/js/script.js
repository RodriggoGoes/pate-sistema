const ociAvaliacao = document.getElementById('oci_avaliacao');
const ociCirurgia = document.getElementById('oci_cirurgia');
const divAvaliacao = document.getElementById('procedimentos_avaliacao');
const divCirurgia = document.getElementById('procedimentos_cirurgia');
const ociPmaeHidden = document.getElementById('oci_pmae');

let pacienteExistente = null;
let modoEdicao = false;

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
        alert('⚠️ Digite um CPF válido com 11 dígitos');
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
            let msg = `✅ Paciente encontrado!\n\nNome: ${pacienteExistente.nome_completo}\n`;
            msg += `Procedimentos já realizados:\n`;
            procedimentosExistentes.forEach((p, i) => {
                if (typeof p === 'object' && p.nome) {
                    msg += `${i + 1}. ${p.nome}\n`;
                } else {
                    msg += `${i + 1}. ${p}\n`;
                }
            });
            msg += `\nDeseja adicionar um novo procedimento?`;
            
            if (confirm(msg)) {
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
        alert('❌ Erro ao buscar paciente');
    }
}

function limparFormulario() {
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

// Mostrar procedimentos
ociAvaliacao.addEventListener('change', function() {
    if (this.checked) {
        divAvaliacao.style.display = 'block';
        divCirurgia.style.display = 'none';
        ociPmaeHidden.value = this.value;
        document.getElementById('procedimento_cirurgia').checked = false;
    }
});

ociCirurgia.addEventListener('change', function() {
    if (this.checked) {
        divAvaliacao.style.display = 'none';
        divCirurgia.style.display = 'block';
        ociPmaeHidden.value = this.value;
        document.getElementById('procedimento_cirurgia').checked = true;
    }
});

function getProcedimentos() {
    const procedimentos = [];
    if (ociAvaliacao.checked) {
        document.querySelectorAll('#procedimentos_avaliacao .procedimento-check:checked').forEach(cb => {
            procedimentos.push(cb.getAttribute('data-procedimento'));
        });
    } else if (ociCirurgia.checked && document.getElementById('procedimento_cirurgia').checked) {
        procedimentos.push(document.getElementById('procedimento_cirurgia').getAttribute('data-procedimento'));
    }
    return procedimentos;
}

// Envio do formulário
document.getElementById('formPaciente').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const unidadeSalva = localStorage.getItem('unidade_selecionada');
    if (!unidadeSalva) {
        alert('❌ Configure sua unidade nas Configurações primeiro!');
        window.location.href = '/configuracoes';
        return;
    }
    
    const unidade = JSON.parse(unidadeSalva);
    const procedimentos = getProcedimentos();
    
    if ((ociAvaliacao.checked && procedimentos.length === 0) || (ociCirurgia.checked && procedimentos.length === 0)) {
        alert('❌ Selecione pelo menos um procedimento');
        return;
    }
    
    const cpf = document.getElementById('cpf').value.replace(/\D/g, '');
    const dataRealizacao = document.getElementById('data_realizacao').value;
    
    const btn = document.querySelector('button[type="submit"]');
    btn.disabled = true;
    
    try {
        if (modoEdicao && pacienteExistente) {
            const response = await fetch('/api/paciente/adicionar_procedimento', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    cpf: cpf,
                    procedimento: procedimentos[0],
                    data_realizacao: dataRealizacao
                })
            });
            
            const result = await response.json();
            const msgDiv = document.getElementById('mensagem');
            
            if (response.ok) {
                btn.innerHTML = '✅ Procedimento Adicionado!';
                msgDiv.innerHTML = `<div class="alert alert-success">✅ ${result.mensagem}</div>`;
                
                divAvaliacao.style.display = 'none';
                divCirurgia.style.display = 'none';
                ociAvaliacao.checked = false;
                ociCirurgia.checked = false;
                document.getElementById('data_realizacao').value = '';
                
                setTimeout(() => {
                    msgDiv.innerHTML = '';
                    btn.innerHTML = '💾 Cadastrar Paciente';
                    btn.disabled = false;
                }, 3000);
            } else {
                msgDiv.innerHTML = `<div class="alert alert-danger">❌ ${result.erro}</div>`;
                btn.innerHTML = '💾 Cadastrar Paciente';
                btn.disabled = false;
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
            
            btn.innerHTML = '⏳ Cadastrando...';
            
            const response = await fetch('/api/paciente', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(dados)
            });
            
            const result = await response.json();
            const msgDiv = document.getElementById('mensagem');
            
            if (response.ok) {
                msgDiv.innerHTML = `<div class="alert alert-success">✅ ${result.mensagem}</div>`;
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
                
                setTimeout(() => {
                    msgDiv.innerHTML = '';
                }, 3000);
            } else {
                msgDiv.innerHTML = `<div class="alert alert-danger">❌ ${result.erro}</div>`;
            }
            btn.innerHTML = '💾 Cadastrar Paciente';
            btn.disabled = false;
        }
    } catch (error) {
        console.error('Erro:', error);
        document.getElementById('mensagem').innerHTML = `<div class="alert alert-danger">❌ Erro ao conectar</div>`;
        btn.innerHTML = '💾 Cadastrar Paciente';
        btn.disabled = false;
    }
});

// Carregar unidade do usuário ao iniciar
carregarUnidadeUsuario();