from flask import Flask, request, jsonify, send_file, render_template, session, redirect, url_for, Response
from flask_cors import CORS
from datetime import datetime, timedelta
from database import mongo_db
from models.usuario import Usuario
from models.unidade import UnidadeExecutor
import re
import pandas as pd
from io import BytesIO
from bson import json_util
import json
import os
from functools import wraps
import traceback

# ========== CRIAÇÃO DO APP PRIMEIRO ==========
app = Flask(__name__)
CORS(app, supports_credentials=True, origins=[])  # Mesma origem apenas

# ========== CONFIGURAÇÕES DE PRODUÇÃO ==========
# Desativar modo debug
DEBUG = False

# Chave secreta - usar variável de ambiente em produção
SECRET_KEY = os.environ.get('SECRET_KEY')
if not SECRET_KEY:
    SECRET_KEY = 'pate_semsa_2024_chave_fixa_para_dev'

# Configurações do Flask
app.config['SECRET_KEY'] = SECRET_KEY
app.config['JSON_AS_ASCII'] = False
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_COOKIE_SECURE'] = False  # True se usar HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=8)

# Configurações adicionais de segurança
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# ========== FUNÇÕES AUXILIARES ==========
def sanitizar_cpf(cpf):
    if not isinstance(cpf, str):
        return ''
    return re.sub(r'[^0-9]', '', cpf)

def validar_cpf(cpf):
    """Validação completa de CPF"""
    try:
        cpf = sanitizar_cpf(cpf)
        
        if len(cpf) != 11:
            return False
        
        if cpf == cpf[0] * 11:
            return False
        
        soma = sum(int(cpf[i]) * (10 - i) for i in range(9))
        digito1 = 11 - (soma % 11)
        if digito1 >= 10:
            digito1 = 0
        
        soma = sum(int(cpf[i]) * (11 - i) for i in range(10))
        digito2 = 11 - (soma % 11)
        if digito2 >= 10:
            digito2 = 0
        
        return digito1 == int(cpf[9]) and digito2 == int(cpf[10])
    except:
        return False

def calcular_idade(data_nascimento_str):
    """Calcula idade a partir da data de nascimento"""
    try:
        nascimento = datetime.strptime(data_nascimento_str, '%Y-%m-%d')
        hoje = datetime.now()
        idade = hoje.year - nascimento.year
        if (hoje.month, hoje.day) < (nascimento.month, nascimento.day):
            idade -= 1
        return idade
    except:
        return None

def get_oci_descricao(codigo):
    """Retorna a descrição completa do OCI/PMAE"""
    mapa = {
        '09.05.01.003-5': 'OCI DE AVALIAÇÃO INICIAL EM OFTALMOLOGIA A PARTIR DE 09 ANOS',
        '04.05.05.037-2': 'FACOEMULSIFICAÇÃO COM IMPLANTE DE LENTE INTRA-OCULAR DOBRAVEL'
    }
    return mapa.get(codigo, codigo)
def gerar_relatorio_formatado():
    """Gera relatório EXATAMENTE no formato solicitado - INCLUI TODOS OS PACIENTES"""
    
    try:
        pacientes = list(mongo_db.pacientes.find({}, {'_id': 0}))
        print("[DADOS] {len(pacientes)} pacientes encontrados para relatório")
    except Exception as e:
        print(f"Erro ao buscar pacientes: {e}")
        return pd.DataFrame()
    
    dados_relatorio = []
    
    mapa_raca = {
        '01': 'BRANCA', 
        '02': 'PRETA', 
        '03': 'PARDA',
        '04': 'INDÍGENA'
    }
    
    for paciente in pacientes:
        # Garantir que o nome não tem espaços extras
        nome_paciente = paciente.get('nome_completo', '').strip()
        
        procedimentos = paciente.get('procedimentos', [])
        
        if not procedimentos:
            procedimentos = ['Nenhum procedimento']
        
        for procedimento in procedimentos:
            try:
                # Extrair nome do procedimento
                if isinstance(procedimento, dict):
                    nome_proc_completo = procedimento.get('nome', '')
                    data_realizacao_proc = procedimento.get('data_realizacao', '')
                else:
                    nome_proc_completo = procedimento
                    data_realizacao_proc = paciente.get('data_realizacao', '')
                
                # Se for um dicionário aninhado, extrair corretamente
                if isinstance(nome_proc_completo, dict):
                    nome_proc_completo = nome_proc_completo.get('nome', '')
                
                if ' - ' in nome_proc_completo:
                    codigo_proc = nome_proc_completo.split(' - ')[0]
                    nome_proc = nome_proc_completo.split(' - ')[1]
                else:
                    codigo_proc = nome_proc_completo[:20]
                    nome_proc = nome_proc_completo
                
                # Formatar data da realização
                if data_realizacao_proc:
                    try:
                        data_formatada = datetime.strptime(data_realizacao_proc, '%Y-%m-%d').strftime('%d/%m/%Y')
                    except:
                        data_formatada = data_realizacao_proc
                else:
                    data_formatada = ''
                
                data_nasc = paciente.get('data_nascimento', '')
                if data_nasc:
                    try:
                        data_nasc_formatada = datetime.strptime(data_nasc, '%Y-%m-%d').strftime('%d/%m/%Y')
                    except:
                        data_nasc_formatada = data_nasc
                else:
                    data_nasc_formatada = ''
                
                cpf = paciente.get('cpf', '')
                if len(cpf) == 11 and cpf.isdigit():
                    cpf_formatado = f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"
                else:
                    cpf_formatado = cpf
                
                codigo_raca = paciente.get('raca_cor', '')
                descricao_raca = mapa_raca.get(codigo_raca, '')
                
                if codigo_raca and descricao_raca:
                    raca_formatada = f"{codigo_raca} {descricao_raca}"
                else:
                    raca_formatada = ''
                
                proc_unidade = procedimento.get('nome_estabelecimento', '') if isinstance(procedimento, dict) else ''
                proc_cnes = procedimento.get('cnes', '') if isinstance(procedimento, dict) else ''
                proc_cnpj = procedimento.get('cnpj', '') if isinstance(procedimento, dict) else ''
                proc_municipio = procedimento.get('municipio', '') if isinstance(procedimento, dict) else ''
                proc_olho = procedimento.get('olho', '') if isinstance(procedimento, dict) else ''

                linha = {
                    'DATA DA REALIZAÇÃO': data_formatada,
                    'NOME': nome_paciente,
                    'CPF': cpf_formatado,
                    'DATA DE NASCIMENTO': data_nasc_formatada,
                    'NOME DA MÃE': paciente.get('nome_mae', '').strip(),
                    'SEXO': paciente.get('sexo', ''),
                    'RAÇA': raca_formatada,
                    'ENDEREÇO': paciente.get('endereco', '').strip(),
                    'BAIRRO': paciente.get('bairro', '').strip(),
                    'CEP': paciente.get('cep', '').strip(),
                    'CONTATO': paciente.get('contato', '').strip(),
                    'CODIGO': codigo_proc,
                    'NOME_PROC': nome_proc,
                    'OLHO': proc_olho or paciente.get('olho', ''),
                    'CBO': paciente.get('cbo', '225265'),
                    'QTD': '0000001',
                    'NOME DO ESTABELECIMENTO': proc_unidade or paciente.get('nome_estabelecimento', '').strip(),
                    'CNES': proc_cnes or paciente.get('cnes', ''),
                    'CNPJ': proc_cnpj or paciente.get('cnpj', ''),
                    'MUNICIPIO': proc_municipio or paciente.get('municipio', '').strip()
                }
                dados_relatorio.append(linha)
            except Exception as e:
                print(f"Erro ao processar procedimento para {paciente.get('nome_completo')}: {e}")
                continue
    
    print("[DADOS] Total de linhas geradas no relatório: {len(dados_relatorio)}")
    return pd.DataFrame(dados_relatorio)

# ========== DECORADORES DE AUTENTICAÇÃO ==========
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario_id' not in session:
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario_id' not in session:
            return redirect(url_for('login_page'))
        if session.get('usuario_tipo') != 'admin':
            return jsonify({'erro': 'Acesso negado. Permissão de administrador necessária.'}), 403
        return f(*args, **kwargs)
    return decorated_function

def operador_redirect(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario_id' not in session:
            return redirect(url_for('login_page'))
        if session.get('usuario_tipo') == 'operador':
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated_function

# ========== ROTAS DAS PÁGINAS ==========
@app.route('/login')
def login_page():
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login_page'))

@app.route('/')
@login_required
def home():
    return render_template('index.html')

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

@app.route('/sobre')
@login_required
def sobre():
    return render_template('sobre.html')

@app.route('/gerenciar-pacientes')
@login_required
@admin_required
def gerenciar_pacientes_page():
    return render_template('gerenciar_pacientes.html')

@app.route('/unidades')
@login_required
@operador_redirect
def unidades_page():
    return render_template('unidades.html')

@app.route('/usuarios')
@login_required
@operador_redirect
def usuarios_page():
    return render_template('usuarios.html')

@app.route('/configuracoes')
@login_required
def configuracoes_page():
    return render_template('configuracoes.html')

# ========== ROTAS DE AUTENTICAÇÃO ==========
@app.route('/api/recuperar_senha', methods=['POST'])
def recuperar_senha():
    dados = request.json
    email = dados.get('email')
    
    if not isinstance(email, str):
        return jsonify({'erro': 'Email inválido'}), 400
    
    usuario = Usuario.colecao.find_one({'email': email.strip()})
    
    if not usuario:
        return jsonify({'erro': 'Email não encontrado'}), 404
    
    return jsonify({
        'mensagem': 'Instruções de recuperação enviadas. Verifique sua caixa de entrada.'
    }), 200

@app.route('/api/registro', methods=['POST'])
def registrar_usuario():
    dados = request.json
    
    if not isinstance(dados.get('nome'), str) or not dados['nome'].strip():
        return jsonify({'erro': 'Nome é obrigatório'}), 400
    if not isinstance(dados.get('email'), str) or not dados['email'].strip():
        return jsonify({'erro': 'Email é obrigatório'}), 400
    if not isinstance(dados.get('senha'), str) or not dados['senha']:
        return jsonify({'erro': 'Senha é obrigatória'}), 400
    
    from models.usuario import Usuario as UsuarioModel
    if UsuarioModel.colecao.find_one({'email': dados['email'].strip()}):
        return jsonify({'erro': 'Email já cadastrado'}), 400
    
    # Força tipo como 'operador' — nunca permite auto-registro como admin
    usuario = {
        'nome': dados['nome'].strip(),
        'email': dados['email'].strip(),
        'senha': dados['senha'],
        'tipo': 'operador',
        'unidade_id': '',
        'ativo': True
    }
    
    result = UsuarioModel.criar(usuario)
    
    return jsonify({
        'mensagem': 'Usuário registrado com sucesso! Faça login para continuar.',
        'id': str(result.inserted_id)
    }), 201

@app.route('/api/login', methods=['POST'])
def api_login():
    dados = request.json
    if not isinstance(dados.get('email'), str) or not isinstance(dados.get('senha'), str):
        return jsonify({'erro': 'Email e senha devem ser texto'}), 400
    email = dados['email'].strip()
    senha = dados['senha']
    
    usuario = Usuario.autenticar(email, senha)
    
    if usuario:
        # Regenerar sessão para prevenir fixation
        session.clear()
        session['usuario_id'] = str(usuario['_id'])
        session['usuario_nome'] = usuario['nome']
        session['usuario_email'] = usuario['email']
        session['usuario_tipo'] = usuario['tipo']
        session['unidade_id'] = usuario.get('unidade_id', '')
        
        if session['unidade_id']:
            unidade_data = UnidadeExecutor.buscar_por_id(session['unidade_id'])
            if unidade_data:
                session['unidade_nome'] = unidade_data.get('nome', '')
                session['unidade_municipio'] = unidade_data.get('municipio', '')
                session['unidade_cnes'] = unidade_data.get('cnes', '')
        
        return jsonify({
            'mensagem': 'Login realizado com sucesso',
            'usuario': {
                'nome': usuario['nome'],
                'email': usuario['email'],
                'tipo': usuario['tipo'],
                'unidade_id': session['unidade_id']
            }
        })
    else:
        return jsonify({'erro': 'Email ou senha inválidos'}), 401

@app.route('/api/usuario/senha', methods=['PUT'])
@login_required
def alterar_senha():
    dados = request.json
    senha_atual = dados.get('senha_atual')
    nova_senha = dados.get('nova_senha')
    
    usuario = Usuario.autenticar(session['usuario_email'], senha_atual)
    
    if not usuario:
        return jsonify({'erro': 'Senha atual incorreta'}), 401
    
    from models.usuario import Usuario as UsuarioModel
    from bson import ObjectId
    import bcrypt
    
    salt = bcrypt.gensalt()
    nova_senha_hash = bcrypt.hashpw(nova_senha.encode('utf-8'), salt)
    
    UsuarioModel.colecao.update_one(
        {'_id': ObjectId(session['usuario_id'])},
        {'$set': {'senha_hash': nova_senha_hash}}
    )
    
    return jsonify({'mensagem': 'Senha alterada com sucesso'})

@app.route('/api/usuario/unidade', methods=['PUT'])
@login_required
def alterar_unidade():
    unidade_id = request.json.get('unidade_id')
    
    from models.usuario import Usuario as UsuarioModel
    from bson import ObjectId
    
    UsuarioModel.colecao.update_one(
        {'_id': ObjectId(session['usuario_id'])},
        {'$set': {'unidade_id': unidade_id}}
    )
    
    session['unidade_id'] = unidade_id
    
    if unidade_id:
        unidade_data = UnidadeExecutor.buscar_por_id(unidade_id)
        if unidade_data:
            session['unidade_nome'] = unidade_data.get('nome', '')
            session['unidade_municipio'] = unidade_data.get('municipio', '')
            session['unidade_cnes'] = unidade_data.get('cnes', '')
    
    return jsonify({'mensagem': 'Unidade alterada com sucesso'})

@app.route('/api/usuario/unidade_atual', methods=['GET'])
@login_required
def get_unidade_atual():
    return jsonify({
        'unidade_id': session.get('unidade_id', ''),
        'unidade_nome': session.get('unidade_nome', ''),
        'unidade_municipio': session.get('unidade_municipio', ''),
        'unidade_cnes': session.get('unidade_cnes', '')
    })

@app.route('/api/usuario/unidade_padrao', methods=['PUT'])
@login_required
def salvar_unidade_padrao():
    unidade_id = request.json.get('unidade_id')
    
    from models.usuario import Usuario as UsuarioModel
    from bson import ObjectId
    
    UsuarioModel.colecao.update_one(
        {'_id': ObjectId(session['usuario_id'])},
        {'$set': {'unidade_id': unidade_id}}
    )
    
    session['unidade_id'] = unidade_id
    
    unidade_data = None
    if unidade_id:
        unidade_data = UnidadeExecutor.buscar_por_id(unidade_id)
        if unidade_data:
            session['unidade_nome'] = unidade_data.get('nome', '')
            session['unidade_municipio'] = unidade_data.get('municipio', '')
            session['unidade_cnes'] = unidade_data.get('cnes', '')
    
    return jsonify({
        'mensagem': 'Unidade padrão salva com sucesso',
        'unidade': {
            'id': unidade_id,
            'nome': session.get('unidade_nome', ''),
            'municipio': session.get('unidade_municipio', ''),
            'cnes': session.get('unidade_cnes', '')
        } if unidade_data else None
    })

# ========== ROTAS PARA USUÁRIOS (ADMIN) ==========
# ========== ROTAS PARA GERENCIAMENTO DE PACIENTES (ADMIN) ==========
@app.route('/api/pacientes/todos', methods=['GET'])
@admin_required
def listar_todos_pacientes():
    """Lista todos os pacientes para o admin gerenciar"""
    pacientes = list(mongo_db.pacientes.find().sort('data_cadastro', -1))
    for p in pacientes:
        p['_id'] = str(p['_id'])
    return json.loads(json_util.dumps(pacientes))

@app.route('/api/paciente/<paciente_id>', methods=['PUT'])
@admin_required
def atualizar_paciente(paciente_id):
    """Atualiza todos os dados do paciente"""
    from bson import ObjectId
    import traceback
    
    try:
        dados = request.json
        print("[DADOS] Dados recebidos: {dados}")
        
        # Buscar paciente existente
        paciente_existente = mongo_db.pacientes.find_one({'_id': ObjectId(paciente_id)})
        if not paciente_existente:
            return jsonify({'erro': 'Paciente não encontrado'}), 404
        
        # Verificar se CPF já existe em outro paciente
        cpf_limpo = re.sub(r'[^0-9]', '', dados.get('cpf', ''))
        if cpf_limpo and cpf_limpo != paciente_existente.get('cpf'):
            outro_paciente = mongo_db.pacientes.find_one({
                'cpf': cpf_limpo, 
                '_id': {'$ne': ObjectId(paciente_id)}
            })
            if outro_paciente:
                return jsonify({'erro': 'CPF já cadastrado para outro paciente'}), 400
        
        # Validar unidade_id (evitar 'undefined', 'null', etc.)
        unidade_id_input = dados.get('unidade_id')
        unidade = None
        unidade_valida = False

        if unidade_id_input and unidade_id_input != '' and unidade_id_input != 'undefined' and unidade_id_input != 'null':
            try:
                unidade = UnidadeExecutor.buscar_por_id(unidade_id_input)
                if unidade:
                    unidade_valida = True
                else:
                    print("[AVISO] Unidade não encontrada para ID: {unidade_id_input}")
            except Exception as e:
                print("[AVISO] Erro ao buscar unidade {unidade_id_input}: {e}")
        else:
            print("[AVISO] unidade_id inválido: {unidade_id_input}")

        if unidade_valida:
            unidade_id_final = unidade_id_input
        else:
            # Manter a unidade existente se a nova for inválida
            unidade_id_final = paciente_existente.get('unidade_id', '')
            # Se o paciente não tem unidade, tentar recuperar do primeiro procedimento
            if not unidade_id_final:
                for proc in paciente_existente.get('procedimentos', []):
                    if isinstance(proc, dict) and proc.get('unidade_id'):
                        unidade_id_final = proc['unidade_id']
                        if isinstance(unidade_id_final, ObjectId):
                            unidade_id_final = str(unidade_id_final)
                        break
            if unidade_id_final:
                try:
                    unidade = UnidadeExecutor.buscar_por_id(unidade_id_final)
                except:
                    unidade = None

        # Mesclar procedimentos: preservar os existentes, adicionar os novos
        data_realizacao = dados.get('data_realizacao')
        procedimentos_existentes = paciente_existente.get('procedimentos', [])
        novos_procedimentos = dados.get('procedimentos', [])

        for proc in novos_procedimentos:
            if not proc:
                continue
            # Verificar se já existe procedimento igual
            ja_existe = False
            for existente in procedimentos_existentes:
                nome_existente = existente.get('nome') if isinstance(existente, dict) else existente
                if nome_existente == proc:
                    ja_existe = True
                    break
            if not ja_existe:
                proc_obj = {
                    'nome': proc,
                    'data_realizacao': data_realizacao,
                    'data_registro': datetime.now().isoformat(),
                    'unidade_id': unidade_id_final or '',
                    'nome_estabelecimento': unidade.get('nome', '') if unidade else '',
                    'municipio': unidade.get('municipio', '') if unidade else '',
                    'cnes': unidade.get('cnes', '') if unidade else '',
                    'cnpj': unidade.get('cnpj', '') if unidade else ''
                }
                if 'FACOEMULSIFICAÇÃO' in proc.upper():
                    proc_obj['olho'] = dados.get('olho', '')
                procedimentos_existentes.append(proc_obj)

        # Calcular idade
        idade = None
        if dados.get('data_nascimento'):
            idade = calcular_idade(dados.get('data_nascimento'))
        
        # Preparar dados atualizados
        paciente_atualizado = {
            'nome_completo': dados.get('nome_completo', '').upper().strip() if dados.get('nome_completo') else '',
            'cpf': cpf_limpo,
            'data_nascimento': dados.get('data_nascimento'),
            'idade': idade,
            'nome_mae': dados.get('nome_mae', '').upper().strip() if dados.get('nome_mae') else '',
            'sexo': dados.get('sexo'),
            'raca_cor': dados.get('raca_cor'),
            'olho': dados.get('olho'),
            'endereco': dados.get('endereco', '').strip(),
            'bairro': dados.get('bairro', '').strip(),
            'cep': dados.get('cep', '').strip(),
            'contato': dados.get('contato', '').strip(),
            'cns': dados.get('cns', '').strip(),
            'data_realizacao': data_realizacao,
            'procedimentos': procedimentos_existentes,
            'unidade_id': unidade_id_final or '',
            'nome_estabelecimento': unidade.get('nome', '') if unidade else (paciente_existente.get('nome_estabelecimento', '')),
            'municipio': unidade.get('municipio', '') if unidade else (paciente_existente.get('municipio', '')),
            'cnes': unidade.get('cnes', '') if unidade else (paciente_existente.get('cnes', '')),
            'cnpj': unidade.get('cnpj', '') if unidade else (paciente_existente.get('cnpj', '')),
            'data_atualizacao': datetime.now(),
            'usuario_atualizou': session.get('usuario_nome', '')
        }
        
        # Remover campos com None
        paciente_atualizado = {k: v for k, v in paciente_atualizado.items() if v is not None}
        
        print("[DADOS] Paciente atualizado: {paciente_atualizado}")
        
        result = mongo_db.pacientes.update_one(
            {'_id': ObjectId(paciente_id)},
            {'$set': paciente_atualizado}
        )
        
        if result.modified_count > 0:
            return jsonify({'mensagem': 'Paciente atualizado com sucesso'}), 200
        else:
            return jsonify({'mensagem': 'Nenhuma alteração realizada'}), 200
            
    except Exception as e:
        print("[ERRO] ERRO ao atualizar paciente: {str(e)}")
        traceback.print_exc()
        return jsonify({'erro': 'Erro interno ao atualizar paciente'}), 500
    
@app.route('/api/paciente/<paciente_id>', methods=['DELETE'])
@admin_required
def deletar_paciente(paciente_id):
    """Exclui um paciente do sistema"""
    from bson import ObjectId
    
    try:
        result = mongo_db.pacientes.delete_one({'_id': ObjectId(paciente_id)})
        
        if result.deleted_count > 0:
            return jsonify({'mensagem': 'Paciente excluído com sucesso'}), 200
        else:
            return jsonify({'erro': 'Paciente não encontrado'}), 404
    except Exception as e:
        return jsonify({'erro': 'Erro interno ao excluir paciente'}), 500
    
@app.route('/api/usuarios/<usuario_id>/resetar_senha', methods=['PUT'])
@admin_required
def resetar_senha_usuario(usuario_id):
    from models.usuario import Usuario as UsuarioModel
    from bson import ObjectId
    import bcrypt
    
    dados = request.json
    nova_senha = dados.get('nova_senha')
    
    if not nova_senha:
        return jsonify({'erro': 'Nova senha é obrigatória'}), 400
    
    if len(nova_senha) < 6:
        return jsonify({'erro': 'A senha deve ter pelo menos 6 caracteres'}), 400
    
    salt = bcrypt.gensalt()
    nova_senha_hash = bcrypt.hashpw(nova_senha.encode('utf-8'), salt)
    
    result = UsuarioModel.colecao.update_one(
        {'_id': ObjectId(usuario_id)},
        {'$set': {'senha_hash': nova_senha_hash}}
    )
    
    if result.modified_count > 0:
        return jsonify({'mensagem': 'Senha alterada com sucesso'}), 200
    else:
        return jsonify({'erro': 'Usuário não encontrado'}), 404

@app.route('/api/usuarios', methods=['GET'])
@admin_required
def listar_usuarios_api():
    from models.usuario import Usuario as UsuarioModel
    usuarios = list(UsuarioModel.colecao.find({}, {'senha_hash': 0}))
    
    for usuario in usuarios:
        usuario['_id'] = str(usuario['_id'])
        if usuario.get('unidade_id'):
            unidade = UnidadeExecutor.buscar_por_id(usuario['unidade_id'])
            usuario['unidade_nome'] = unidade.get('nome', '') if unidade else ''
    
    return jsonify(usuarios)

@app.route('/api/usuarios', methods=['POST'])
@admin_required
def criar_usuario_api():
    dados = request.json
    
    if not dados.get('nome'):
        return jsonify({'erro': 'Nome é obrigatório'}), 400
    if not dados.get('email'):
        return jsonify({'erro': 'Email é obrigatório'}), 400
    if not dados.get('senha'):
        return jsonify({'erro': 'Senha é obrigatória'}), 400
    if not dados.get('tipo'):
        return jsonify({'erro': 'Tipo de usuário é obrigatório'}), 400
    
    from models.usuario import Usuario as UsuarioModel
    if UsuarioModel.colecao.find_one({'email': dados['email']}):
        return jsonify({'erro': 'Email já cadastrado'}), 400
    
    usuario = {
        'nome': dados['nome'],
        'email': dados['email'],
        'senha': dados['senha'],
        'tipo': dados['tipo'],
        'unidade_id': dados.get('unidade_id', ''),
        'ativo': True
    }
    
    result = UsuarioModel.criar(usuario)
    
    return jsonify({
        'mensagem': 'Usuário criado com sucesso',
        'id': str(result.inserted_id)
    }), 201

@app.route('/api/usuarios/<usuario_id>', methods=['DELETE'])
@admin_required
def deletar_usuario_api(usuario_id):
    from models.usuario import Usuario as UsuarioModel
    from bson import ObjectId
    
    UsuarioModel.colecao.update_one(
        {'_id': ObjectId(usuario_id)},
        {'$set': {'ativo': False}}
    )
    
    return jsonify({'mensagem': 'Usuário desativado com sucesso'})
@app.route('/api/exportar/relatorio_cadastros', methods=['GET'])
@admin_required
def exportar_relatorio_cadastros():
    """Exporta relatório de cadastros por operador/dia (formato texto)"""
    
    # Pipeline para agrupar por data e operador
    pipeline = [
        {
            '$group': {
                '_id': {
                    'data': {'$dateToString': {'format': '%d/%m/%Y', 'date': '$data_cadastro'}},
                    'operador': '$usuario_cadastrou'
                },
                'total': {'$sum': 1}
            }
        },
        {
            '$sort': {'_id.data': -1, '_id.operador': 1}
        }
    ]
    
    resultados = list(mongo_db.pacientes.aggregate(pipeline))
    
    # Totais por operador
    pipeline_operador = [
        {
            '$group': {
                '_id': '$usuario_cadastrou',
                'total': {'$sum': 1}
            }
        },
        {
            '$sort': {'total': -1}
        }
    ]
    totais_operador = list(mongo_db.pacientes.aggregate(pipeline_operador))
    
    # Total geral
    total_geral = mongo_db.pacientes.count_documents({})
    
    # Criar conteúdo do relatório
    from io import StringIO
    output = StringIO()
    
    output.write("="*80 + "\n")
    output.write("📊 RELATÓRIO DE CADASTROS - PATE\n")
    output.write("="*80 + "\n")
    output.write(f"Data de geração: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
    output.write("="*80 + "\n\n")
    
    output.write(f"📌 TOTAL GERAL DE CADASTROS: {total_geral}\n\n")
    
    output.write("📅 REGISTROS POR DIA E OPERADOR:\n")
    output.write("-"*80 + "\n")
    
    dados_por_data = {}
    for item in resultados:
        data = item['_id']['data']
        operador = item['_id']['operador'] if item['_id']['operador'] else 'NÃO IDENTIFICADO'
        total = item['total']
        
        if data not in dados_por_data:
            dados_por_data[data] = []
        dados_por_data[data].append({'operador': operador, 'total': total})
    
    for data in sorted(dados_por_data.keys(), reverse=True):
        output.write(f"\n📆 {data}:\n")
        for item in dados_por_data[data]:
            output.write(f"   👤 {item['operador']}: {item['total']} cadastro(s)\n")
    
    output.write("\n" + "="*80 + "\n")
    output.write("👤 TOTAIS GERAIS POR OPERADOR:\n")
    output.write("-"*80 + "\n")
    
    for item in totais_operador:
        operador = item['_id'] if item['_id'] else 'NÃO IDENTIFICADO'
        total = item['total']
        output.write(f"   👤 {operador}: {total} cadastro(s)\n")
    
    output.write("\n" + "="*80 + "\n")
    output.write("📊 RESUMO:\n")
    output.write("-"*80 + "\n")
    output.write(f"Total de dias com registros: {len(dados_por_data)}\n")
    output.write(f"Total de operadores ativos: {len(totais_operador)}\n")
    
    # Calcular média por dia
    if len(dados_por_data) > 0:
        media = total_geral / len(dados_por_data)
        output.write(f"Média de cadastros por dia: {media:.1f}\n")
    
    output.write("\n" + "="*80 + "\n")
    output.write("Fim do relatório\n")
    output.write("="*80 + "\n")
    
    # Criar resposta
    output_text = output.getvalue()
    output.close()
    
    return Response(
        output_text,
        mimetype='text/plain',
        headers={'Content-Disposition': f'attachment; filename=relatorio_cadastros_{datetime.now().strftime("%Y%m%d_%H%M")}.txt'}
    )

# ========== ROTAS PARA UNIDADES EXECUTORAS ==========
@app.route('/api/unidades', methods=['GET'])
@login_required
def listar_unidades():
    unidades = UnidadeExecutor.listar_com_id()
    return jsonify(unidades)

@app.route('/api/unidades/todas', methods=['GET'])
@admin_required
def listar_todas_unidades():
    unidades = list(UnidadeExecutor.colecao.find({}))
    for unidade in unidades:
        unidade['_id'] = str(unidade['_id'])
    return jsonify(unidades)

@app.route('/api/unidades', methods=['POST'])
@admin_required
def criar_unidade():
    dados = request.json
    
    if not dados.get('nome'):
        return jsonify({'erro': 'Nome da unidade é obrigatório'}), 400
    if not dados.get('municipio'):
        return jsonify({'erro': 'Município é obrigatório'}), 400
    
    existente = UnidadeExecutor.buscar_por_nome(dados['nome'])
    if existente:
        return jsonify({'erro': 'Unidade já cadastrada'}), 400
    
    unidade = {
        'nome': dados['nome'],
        'municipio': dados['municipio'],
        'cnes': dados.get('cnes', ''),
        'cnpj': dados.get('cnpj', ''),
        'endereco': dados.get('endereco', ''),
        'telefone': dados.get('telefone', ''),
        'responsavel': dados.get('responsavel', ''),
        'ativa': True,
        'data_cadastro': datetime.now()
    }
    
    result = UnidadeExecutor.criar(unidade)
    
    return jsonify({
        'mensagem': 'Unidade criada com sucesso',
        'id': str(result.inserted_id)
    }), 201

@app.route('/api/unidades/<unidade_id>', methods=['GET'])
@admin_required
def buscar_unidade(unidade_id):
    """Busca uma unidade por ID"""
    unidade = UnidadeExecutor.buscar_por_id(unidade_id)
    if unidade:
        unidade['_id'] = str(unidade['_id'])
        return jsonify(unidade)
    return jsonify({'erro': 'Unidade não encontrada'}), 404

@app.route('/api/unidades/<unidade_id>/reativar', methods=['PUT'])
@admin_required
def reativar_unidade(unidade_id):
    """Reativa uma unidade executora"""
    result = UnidadeExecutor.reativar(unidade_id)
    
    if result.modified_count > 0:
        return jsonify({'mensagem': 'Unidade reativada com sucesso'}), 200
    else:
        return jsonify({'erro': 'Unidade não encontrada'}), 404

@app.route('/api/unidades/<unidade_id>', methods=['PUT'])
@admin_required
def editar_unidade(unidade_id):
    """Edita uma unidade executora"""
    dados = request.json
    
    if not dados.get('nome'):
        return jsonify({'erro': 'Nome da unidade é obrigatório'}), 400
    if not dados.get('municipio'):
        return jsonify({'erro': 'Município é obrigatório'}), 400
    
    existente = UnidadeExecutor.buscar_por_nome(dados['nome'])
    if existente and str(existente['_id']) != unidade_id:
        return jsonify({'erro': 'Unidade já cadastrada com este nome'}), 400
    
    unidade = {
        'nome': dados['nome'],
        'municipio': dados['municipio'],
        'cnes': dados.get('cnes', ''),
        'cnpj': dados.get('cnpj', ''),
        'endereco': dados.get('endereco', ''),
        'telefone': dados.get('telefone', ''),
        'responsavel': dados.get('responsavel', ''),
        'data_atualizacao': datetime.now()
    }
    
    result = UnidadeExecutor.atualizar(unidade_id, unidade)
    
    if result.modified_count > 0:
        return jsonify({'mensagem': 'Unidade atualizada com sucesso'}), 200
    else:
        return jsonify({'erro': 'Unidade não encontrada'}), 404

@app.route('/api/unidades/<unidade_id>/desativar', methods=['DELETE'])
@admin_required
def desativar_unidade(unidade_id):
    result = UnidadeExecutor.desativar(unidade_id)
    
    if result.modified_count > 0:
        return jsonify({'mensagem': 'Unidade desativada com sucesso'})
    else:
        return jsonify({'erro': 'Unidade não encontrada'}), 404

# ========== ROTAS DE BUSCA E EDIÇÃO DE PACIENTES ==========
@app.route('/api/paciente/buscar', methods=['POST'])
@login_required
def buscar_paciente():
    dados = request.json
    cpf = re.sub(r'[^0-9]', '', dados.get('cpf', ''))
    
    if not cpf:
        return jsonify({'erro': 'CPF é obrigatório'}), 400
    
    paciente = mongo_db.pacientes.find_one({'cpf': cpf})
    
    if paciente:
        paciente['_id'] = str(paciente['_id'])
        if paciente.get('data_nascimento'):
            paciente['data_nascimento'] = str(paciente['data_nascimento'])
        
        procedimentos_formatados = []
        for proc in paciente.get('procedimentos', []):
            if isinstance(proc, dict):
                procedimentos_formatados.append(proc.get('nome', ''))
            else:
                procedimentos_formatados.append(proc)
        
        ultima_data = paciente.get('data_realizacao', '')
        if paciente.get('procedimentos'):
            for proc in paciente.get('procedimentos', []):
                if isinstance(proc, dict) and proc.get('data_realizacao'):
                    ultima_data = proc.get('data_realizacao')
        
        return jsonify({
            'encontrado': True,
            'paciente': {
                '_id': paciente.get('_id', ''),
                'nome_completo': paciente.get('nome_completo', ''),
                'data_nascimento': paciente.get('data_nascimento', ''),
                'nome_mae': paciente.get('nome_mae', ''),
                'sexo': paciente.get('sexo', ''),
                'raca_cor': paciente.get('raca_cor', ''),
                'procedimentos': procedimentos_formatados,
                'data_realizacao': ultima_data,
                'cpf': paciente.get('cpf', ''),
                'olho': paciente.get('olho', '')
            }
        })
    else:
        return jsonify({'encontrado': False})

@app.route('/api/paciente/adicionar_procedimento', methods=['POST'])
@login_required
def adicionar_procedimento():
    dados = request.json
    cpf = re.sub(r'[^0-9]', '', dados.get('cpf', ''))
    novo_procedimento = dados.get('procedimento')
    nova_data_realizacao = dados.get('data_realizacao')
    novo_olho = dados.get('olho', '')
    
    if not cpf or not novo_procedimento:
        return jsonify({'erro': 'CPF e procedimento são obrigatórios'}), 400
    
    paciente = mongo_db.pacientes.find_one({'cpf': cpf})
    if not paciente:
        return jsonify({'erro': 'Paciente não encontrado'}), 404
    
    procedimentos_atuais = paciente.get('procedimentos', [])
    
    # Convert ObjectId values to strings to avoid JSON serialization errors
    from bson import ObjectId as BsonObjectId
    for proc in procedimentos_atuais:
        if isinstance(proc, dict):
            for key, val in list(proc.items()):
                if isinstance(val, BsonObjectId):
                    proc[key] = str(val)
    
    # Allow multiple FACOEMULSIFICAÇÃO with different dates and/or eyes
    if 'FACOEMULSIFICAÇÃO' in novo_procedimento.upper():
        procedimento_existente = False
        for proc in procedimentos_atuais:
            if isinstance(proc, dict):
                if (proc.get('nome') == novo_procedimento
                        and proc.get('data_realizacao') == nova_data_realizacao
                        and proc.get('olho') == novo_olho):
                    procedimento_existente = True
                    break
    else:
        procedimento_existente = False
        for proc in procedimentos_atuais:
            if isinstance(proc, dict):
                if proc.get('nome') == novo_procedimento:
                    procedimento_existente = True
                    break
            elif isinstance(proc, str):
                if proc == novo_procedimento:
                    procedimento_existente = True
                    break
    
    if procedimento_existente:
        return jsonify({'erro': 'Este procedimento já foi registrado para este paciente'}), 400
    
    unidade_id_proc = paciente.get('unidade_id', '')
    unidade_proc = None
    if unidade_id_proc:
        unidade_proc = UnidadeExecutor.buscar_por_id(unidade_id_proc)

    novo_item = {
        'nome': novo_procedimento,
        'data_realizacao': nova_data_realizacao,
        'data_registro': datetime.now().isoformat(),
        'olho': novo_olho,
        'unidade_id': unidade_id_proc,
        'nome_estabelecimento': unidade_proc.get('nome', '') if unidade_proc else paciente.get('nome_estabelecimento', ''),
        'municipio': unidade_proc.get('municipio', '') if unidade_proc else paciente.get('municipio', ''),
        'cnes': unidade_proc.get('cnes', '') if unidade_proc else paciente.get('cnes', ''),
        'cnpj': unidade_proc.get('cnpj', '') if unidade_proc else paciente.get('cnpj', '')
    }
    procedimentos_atuais.append(novo_item)
    
    result = mongo_db.pacientes.update_one(
        {'cpf': cpf},
        {
            '$set': {
                'procedimentos': procedimentos_atuais,
                'data_atualizacao': datetime.now()
            }
        }
    )
    
    return jsonify({
        'mensagem': 'Procedimento adicionado com sucesso!',
        'procedimentos': procedimentos_atuais
    }), 200

@app.route('/api/paciente/<paciente_id>/procedimento', methods=['PATCH'])
@admin_required
def atualizar_procedimento(paciente_id):
    """Atualiza unidade de um procedimento específico"""
    from bson import ObjectId

    try:
        dados = request.json
        nome_proc = dados.get('nome_procedimento')
        nova_unidade_id = dados.get('unidade_id')

        if not nome_proc:
            return jsonify({'erro': 'nome_procedimento é obrigatório'}), 400

        paciente = mongo_db.pacientes.find_one({'_id': ObjectId(paciente_id)})
        if not paciente:
            return jsonify({'erro': 'Paciente não encontrado'}), 404

        procedimentos = paciente.get('procedimentos', [])
        indices = []
        for i, proc in enumerate(procedimentos):
            nome_proc_atual = proc.get('nome') if isinstance(proc, dict) else proc
            if nome_proc_atual == nome_proc:
                indices.append(i)

        if not indices:
            return jsonify({'erro': 'Procedimento não encontrado neste paciente'}), 404

        set_dict = {'data_atualizacao': datetime.now()}

        # Se unidade_id foi enviada, atualizar dados da unidade
        if nova_unidade_id and nova_unidade_id not in ('', 'undefined', 'null'):
            unidade = UnidadeExecutor.buscar_por_id(nova_unidade_id)
            if not unidade:
                return jsonify({'erro': 'Unidade não encontrada'}), 404
            for idx in indices:
                set_dict[f'procedimentos.{idx}.unidade_id'] = nova_unidade_id
                set_dict[f'procedimentos.{idx}.nome_estabelecimento'] = unidade.get('nome', '')
                set_dict[f'procedimentos.{idx}.municipio'] = unidade.get('municipio', '')
                set_dict[f'procedimentos.{idx}.cnes'] = unidade.get('cnes', '')
                set_dict[f'procedimentos.{idx}.cnpj'] = unidade.get('cnpj', '')

        # Se data_realizacao foi enviada, atualizar
        nova_data = dados.get('data_realizacao')
        if nova_data:
            for idx in indices:
                set_dict[f'procedimentos.{idx}.data_realizacao'] = nova_data

        # Se olho foi enviado, atualizar
        novo_olho = dados.get('olho')
        if novo_olho:
            for idx in indices:
                set_dict[f'procedimentos.{idx}.olho'] = novo_olho

        if len(set_dict) == 1:
            return jsonify({'erro': 'Nenhum campo para atualizar. Envie unidade_id, data_realizacao ou olho'}), 400

        mongo_db.pacientes.update_one(
            {'_id': ObjectId(paciente_id)},
            {'$set': set_dict}
        )

        return jsonify({'mensagem': f'Procedimento {nome_proc} atualizado com sucesso'}), 200

    except Exception as e:
        print(f"Erro ao atualizar procedimento: {e}")
        traceback.print_exc()
        return jsonify({'erro': 'Erro interno ao processar requisição'}), 500

# ========== ROTAS DA API DE PACIENTES ==========
@app.route('/api/pacientes', methods=['GET'])
@login_required
def listar_pacientes():
    """Lista pacientes - se não for admin, mostra apenas os da sua unidade"""
    usuario_tipo = session.get('usuario_tipo')
    unidade_id = session.get('unidade_id')
    
    # Se não for admin, filtra pela unidade do usuário
    if usuario_tipo != 'admin' and unidade_id:
        pacientes = list(mongo_db.pacientes.find({'unidade_id': unidade_id}, {'_id': 0}).sort('data_cadastro', -1))
    else:
        pacientes = list(mongo_db.pacientes.find({}, {'_id': 0}).sort('data_cadastro', -1))
    
    return json.loads(json_util.dumps(pacientes))

@app.route('/api/paciente', methods=['POST'])
@login_required
def cadastrar_paciente():
    dados = request.json
    
    cpf_limpo = sanitizar_cpf(dados.get('cpf', ''))
    if not cpf_limpo or not validar_cpf(cpf_limpo):
        return jsonify({'erro': 'CPF inválido'}), 400
    
    if mongo_db.pacientes.find_one({'cpf': cpf_limpo}):
        return jsonify({'erro': 'CPF já cadastrado'}), 400
    
    idade = calcular_idade(dados.get('data_nascimento'))
    
    unidade_id = session.get('unidade_id')
    unidade = None
    if unidade_id:
        unidade = UnidadeExecutor.buscar_por_id(unidade_id)
    
    procedimentos_lista = []
    for proc in dados.get('procedimentos', []):
        if not isinstance(proc, str):
            continue
        proc_obj = {
            'nome': proc,
            'data_realizacao': dados['data_realizacao'],
            'data_registro': datetime.now().isoformat(),
            'unidade_id': unidade_id,
            'nome_estabelecimento': unidade.get('nome', '') if unidade else '',
            'municipio': unidade.get('municipio', '') if unidade else '',
            'cnes': unidade.get('cnes', '') if unidade else '',
            'cnpj': unidade.get('cnpj', '') if unidade else ''
        }
        # Store olho on FACOEMULSIFICAÇÃO procedures
        if 'FACOEMULSIFICAÇÃO' in proc.upper():
            proc_obj['olho'] = dados.get('olho', '')
        procedimentos_lista.append(proc_obj)
    
    paciente = {
        'nome_estabelecimento': unidade.get('nome', '') if unidade else '',
        'municipio': unidade.get('municipio', '') if unidade else '',
        'cnes': unidade.get('cnes', '') if unidade else '',
        'cnpj': unidade.get('cnpj', '') if unidade else '',
        'nome_completo': dados['nome'].upper(),
        'data_nascimento': dados['data_nascimento'],
        'idade': idade,
        'cpf': re.sub(r'[^0-9]', '', dados['cpf']),
        'nome_mae': dados['nome_mae'].upper(),
        'sexo': dados['sexo'],
        'raca_cor': dados['raca_cor'],
        'oci_pmae': dados.get('oci_pmae', ''),
        'procedimentos': procedimentos_lista,
        'olho': dados['olho'],
        'cbo': '225265',
        'data_realizacao': dados['data_realizacao'],
        'data_cadastro': datetime.now(),
        'unidade_id': unidade_id,
        'usuario_cadastrou': session.get('usuario_nome', ''),
        'usuario_id': session.get('usuario_id', ''),
        'endereco': dados.get('endereco', ''),
        'bairro': dados.get('bairro', ''),
        'cep': dados.get('cep', ''),
        'contato': dados.get('contato', '')
    }
    
    try:
        result = mongo_db.pacientes.insert_one(paciente)
        return jsonify({
            'mensagem': 'Paciente cadastrado com sucesso',
            'id': str(result.inserted_id),
            'procedimentos': paciente['procedimentos']
        }), 201
    except Exception as e:
        return jsonify({'erro': 'Erro interno ao cadastrar paciente'}), 500

# ========== ROTAS DO DASHBOARD ==========
@app.route('/api/dashboard/unidades_stats', methods=['GET'])
@login_required
def unidades_stats():
    """Estatísticas de PROCEDIMENTOS por unidade executora"""
    
    usuario_tipo = session.get('usuario_tipo')
    unidade_id = session.get('unidade_id')
    
    # Se não for admin, mostra apenas a unidade do usuário
    if usuario_tipo != 'admin' and unidade_id:
        unidade = UnidadeExecutor.buscar_por_id(unidade_id)
        if unidade:
            # Pipeline para contar procedimentos da unidade específica
            pipeline = [
                {'$match': {'unidade_id': unidade_id}},
                {'$unwind': '$procedimentos'},
                {
                    '$group': {
                        '_id': {
                            'unidade_nome': {'$ifNull': ['$procedimentos.nome_estabelecimento', '$nome_estabelecimento']},
                            'unidade_municipio': {'$ifNull': ['$procedimentos.municipio', '$municipio']}
                        },
                        'oci': {
                            '$sum': {
                                '$cond': [
                                    {'$regexMatch': {'input': '$procedimentos.nome', 'regex': 'OCI DE AVALIAÇÃO', 'options': 'i'}},
                                    1, 0
                                ]
                            }
                        },
                        'cirurgias': {
                            '$sum': {
                                '$cond': [
                                    {'$regexMatch': {'input': '$procedimentos.nome', 'regex': 'FACOEMULSIFICAÇÃO', 'options': 'i'}},
                                    1, 0
                                ]
                            }
                        }
                    }
                },
                {
                    '$addFields': {
                        'total': {'$add': ['$oci', '$cirurgias']}
                    }
                }
            ]
            
            resultados = list(mongo_db.pacientes.aggregate(pipeline))
            
            unidades_lista = []
            for item in resultados:
                unidades_lista.append({
                    'nome': item['_id']['unidade_nome'] or unidade.get('nome', ''),
                    'municipio': item['_id']['unidade_municipio'] or unidade.get('municipio', ''),
                    'oci_oftalmologica': item['oci'],
                    'cirurgias': item['cirurgias'],
                    'total': item['total']
                })
            
            return jsonify(unidades_lista)
        else:
            return jsonify([])
    else:
        # Admin vê todas as unidades
        pipeline = [
            {'$unwind': '$procedimentos'},
            {
                '$group': {
                    '_id': {
                        'unidade_nome': {'$ifNull': ['$procedimentos.nome_estabelecimento', '$nome_estabelecimento']},
                        'unidade_municipio': {'$ifNull': ['$procedimentos.municipio', '$municipio']}
                    },
                    'oci': {
                        '$sum': {
                            '$cond': [
                                {'$regexMatch': {'input': '$procedimentos.nome', 'regex': 'OCI DE AVALIAÇÃO', 'options': 'i'}},
                                1, 0
                            ]
                        }
                    },
                    'cirurgias': {
                        '$sum': {
                            '$cond': [
                                {'$regexMatch': {'input': '$procedimentos.nome', 'regex': 'FACOEMULSIFICAÇÃO', 'options': 'i'}},
                                1, 0
                            ]
                        }
                    }
                }
            },
            {
                '$addFields': {
                    'total': {'$add': ['$oci', '$cirurgias']}
                }
            },
            {
                '$sort': {'total': -1}
            }
        ]
        
        resultados = list(mongo_db.pacientes.aggregate(pipeline))
        
        unidades_lista = []
        for item in resultados:
            unidade_nome = item['_id']['unidade_nome'] or 'Unidade não definida'
            unidade_municipio = item['_id']['unidade_municipio'] or '-'
            
            unidades_lista.append({
                'nome': unidade_nome,
                'municipio': unidade_municipio,
                'oci_oftalmologica': item['oci'],
                'cirurgias': item['cirurgias'],
                'total': item['total']
            })
        
        return jsonify(unidades_lista)
    
@app.route('/api/dashboard/procedimentos_por_unidade', methods=['GET'])
@login_required
def procedimentos_por_unidade():
    pipeline = [
        {'$unwind': '$procedimentos'},
        {
            '$group': {
                '_id': {
                    'unidade': {'$ifNull': ['$procedimentos.nome_estabelecimento', '$nome_estabelecimento']},
                    'procedimento': '$procedimentos'
                },
                'count': {'$sum': 1}
            }
        },
        {
            '$sort': {'_id.unidade': 1, 'count': -1}
        },
        {
            '$group': {
                '_id': '$_id.unidade',
                'procedimentos': {
                    '$push': {
                        'nome': '$_id.procedimento',
                        'quantidade': '$count'
                    }
                },
                'total': {'$sum': '$count'}
            }
        }
    ]
    
    resultados = list(mongo_db.pacientes.aggregate(pipeline))
    
    dados_formatados = []
    for item in resultados:
        unidade = item['_id'] or 'Unidade não definida'
        top_procedimentos = sorted(item['procedimentos'], key=lambda x: x['quantidade'], reverse=True)[:5]
        
        dados_formatados.append({
            'unidade': unidade,
            'procedimentos': top_procedimentos,
            'total': item['total']
        })
    
    return jsonify(dados_formatados)

@app.route('/api/dashboard/stats', methods=['GET'])
@login_required
def dashboard_stats():
    # Filtrar por unidade do usuário (a menos que seja admin)
    unidade_id = session.get('unidade_id')
    usuario_tipo = session.get('usuario_tipo')
    
    # Se não for admin, filtra pela unidade do usuário
    if usuario_tipo != 'admin' and unidade_id:
        query = {'unidade_id': unidade_id}
    else:
        query = {}
    
    total_pacientes = mongo_db.pacientes.count_documents(query)
    
    pipeline_procedimentos = [
        {'$match': query},
        {'$unwind': '$procedimentos'},
        {'$group': {'_id': '$procedimentos', 'count': {'$sum': 1}}},
        {'$sort': {'count': -1}},
        {'$limit': 10}
    ]
    procedimentos_count = list(mongo_db.pacientes.aggregate(pipeline_procedimentos))
    
    sexo_stats = {
        'MASCULINO': mongo_db.pacientes.count_documents({**query, 'sexo': 'MASCULINO'}),
        'FEMININO': mongo_db.pacientes.count_documents({**query, 'sexo': 'FEMININO'})
    }
    
    # Count olho at PROCEDURE level (with fallback to patient-level)
    pipeline_olho = [
        {'$match': query},
        {'$unwind': '$procedimentos'},
        {
            '$group': {
                '_id': None,
                'OD': {
                    '$sum': {
                        '$cond': [
                            {'$eq': [{'$ifNull': ['$procedimentos.olho', '$olho']}, 'OD']},
                            1, 0
                        ]
                    }
                },
                'OE': {
                    '$sum': {
                        '$cond': [
                            {'$eq': [{'$ifNull': ['$procedimentos.olho', '$olho']}, 'OE']},
                            1, 0
                        ]
                    }
                },
                'AMBOS': {
                    '$sum': {
                        '$cond': [
                            {'$eq': [{'$ifNull': ['$procedimentos.olho', '$olho']}, 'AMBOS']},
                            1, 0
                        ]
                    }
                },
                'SEM': {
                    '$sum': {
                        '$cond': [
                            {'$eq': [{'$ifNull': ['$procedimentos.olho', '$olho']}, 'SEM']},
                            1, 0
                        ]
                    }
                }
            }
        }
    ]
    olho_result = list(mongo_db.pacientes.aggregate(pipeline_olho))
    if olho_result:
        olho_stats = olho_result[0]
        olho_stats.pop('_id', None)
    else:
        olho_stats = {'OD': 0, 'OE': 0, 'AMBOS': 0, 'SEM': 0}
    
    raca_stats = {
        '01 - Branca': mongo_db.pacientes.count_documents({**query, 'raca_cor': '01'}),
        '02 - Preta': mongo_db.pacientes.count_documents({**query, 'raca_cor': '02'}),
        '03 - Parda': mongo_db.pacientes.count_documents({**query, 'raca_cor': '03'}),
        '04 - Indígena': mongo_db.pacientes.count_documents({**query, 'raca_cor': '04'})
    }
    
    # Contar PROCEDIMENTOS (não pacientes)
    pipeline_oci_procedimentos = [
        {'$match': query},
        {'$unwind': '$procedimentos'},
        {'$match': {'procedimentos.nome': {'$regex': 'OCI DE AVALIAÇÃO', '$options': 'i'}}},
        {'$count': 'total'}
    ]
    pipeline_cirurgia_procedimentos = [
        {'$match': query},
        {'$unwind': '$procedimentos'},
        {'$match': {'procedimentos.nome': {'$regex': 'FACOEMULSIFICAÇÃO', '$options': 'i'}}},
        {'$count': 'total'}
    ]
    
    oci_result = list(mongo_db.pacientes.aggregate(pipeline_oci_procedimentos))
    cirurgia_result = list(mongo_db.pacientes.aggregate(pipeline_cirurgia_procedimentos))
    
    oci_stats = {
        'OCI OFTALMOLOGICA': oci_result[0]['total'] if oci_result else 0,
        'CIRURGIAS': cirurgia_result[0]['total'] if cirurgia_result else 0
    }
    
    # Dados de OCI e Cirurgia por Raça
    oci_por_raca = {'Branca': 0, 'Preta': 0, 'Parda': 0, 'Indígena':0}
    cirurgia_por_raca = {'Branca': 0, 'Preta': 0, 'Parda': 0, 'Indígena':0}
    
    pipeline_raca_procedimentos = [
        {'$match': query},
        {'$unwind': '$procedimentos'},
        {'$match': {'procedimentos.nome': {'$regex': 'OCI DE AVALIAÇÃO|FACOEMULSIFICAÇÃO', '$options': 'i'}}},
        {'$group': {
            '_id': {
                'raca': '$raca_cor',
                'tipo': {
                    '$cond': [
                        {'$regexMatch': {'input': '$procedimentos.nome', 'regex': 'OCI DE AVALIAÇÃO', 'options': 'i'}},
                        'OCI',
                        'CIRURGIA'
                    ]
                }
            },
            'count': {'$sum': 1}
        }}
    ]
    
    mapa_raca_nome = {'01': 'Branca', '02': 'Preta', '03': 'Parda', '04': 'Indígena'}
    
    try:
        resultados = list(mongo_db.pacientes.aggregate(pipeline_raca_procedimentos))
        for item in resultados:
            raca_cod = item['_id']['raca']
            raca_nome = mapa_raca_nome.get(raca_cod, 'Outra')
            tipo = item['_id']['tipo']
            count = item['count']
            
            if tipo == 'OCI':
                oci_por_raca[raca_nome] = count
            else:
                cirurgia_por_raca[raca_nome] = count
    except Exception as e:
        print(f"Erro ao calcular procedimentos por raça: {e}")
    
    data_limite = datetime.now() - timedelta(days=30)
    ultimos_30_dias = mongo_db.pacientes.count_documents({
        **query,
        'data_cadastro': {'$gte': data_limite}
    })
    
    idade_stats = {
        '0-20': mongo_db.pacientes.count_documents({**query, 'idade': {'$lte': 20}}),
        '21-40': mongo_db.pacientes.count_documents({**query, 'idade': {'$gte': 21, '$lte': 40}}),
        '41-60': mongo_db.pacientes.count_documents({**query, 'idade': {'$gte': 41, '$lte': 60}}),
        '61-80': mongo_db.pacientes.count_documents({**query, 'idade': {'$gte': 61, '$lte': 80}}),
        '80+': mongo_db.pacientes.count_documents({**query, 'idade': {'$gte': 81}})
    }
    
    return jsonify({
        'total_pacientes': total_pacientes,
        'ultimos_30_dias': ultimos_30_dias,
        'procedimentos': procedimentos_count,
        'sexo': sexo_stats,
        'olho': olho_stats,
        'raca_cor': raca_stats,
        'oci': oci_stats,
        'idade': idade_stats,
        'oci_por_raca': oci_por_raca,
        'cirurgia_por_raca': cirurgia_por_raca,
        'usuario_tipo': usuario_tipo,
        'unidade_nome': session.get('unidade_nome', 'Todas as Unidades')
    })

# ========== ROTAS DE EXPORTAÇÃO ==========
@app.route('/api/exportar/relatorio_excel', methods=['GET'])
@admin_required
def exportar_relatorio_excel():
    """Exporta relatório Excel - pode ser filtrado por unidade via query parameter?unidade_id=xxx"""
    try:
        unidade_id = request.args.get('unidade_id')
        
        if unidade_id:
            # Se tiver unidade_id, redireciona para a função específica
            return exportar_relatorio_excel_por_unidade(unidade_id)
        
        print("[DADOS] Iniciando exportação Excel (todos os pacientes)...")
        
        df = gerar_relatorio_formatado()
        
        print("[DADOS] DataFrame gerado: {len(df)} linhas, {len(df.columns)} colunas")
        
        if df.empty:
            return jsonify({'erro': 'Nenhum dado para exportar'}), 404
        
        output = BytesIO()
        
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Relatorio PATE', index=False)
            
            worksheet = writer.sheets['Relatorio PATE']
            
            # Ajustar largura das colunas
            for i, col in enumerate(df.columns):
                try:
                    max_len = max(df[col].astype(str).map(len).max(), len(col)) + 2
                    letra = chr(65 + i) if i < 26 else chr(65 + (i // 26) - 1) + chr(65 + (i % 26))
                    worksheet.column_dimensions[letra].width = min(max_len, 50)
                except:
                    pass
            
            worksheet.freeze_panes = 'A2'
        
        output.seek(0)
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'relatorio_pate_{datetime.now().strftime("%Y%m%d_%H%M")}.xlsx'
        )
    except Exception as e:
        print("[ERRO] ERRO na exportação Excel: {str(e)}")
        traceback.print_exc()
        return jsonify({'erro': 'Erro interno ao gerar relatório'}), 500

@app.route('/api/exportar/relatorio_csv', methods=['GET'])
@admin_required
def exportar_relatorio_csv():
    """Exporta relatório CSV com tratamento de erros"""
    try:
        print("[DADOS] Iniciando exportação CSV...")
        
        df = gerar_relatorio_formatado()
        
        print("[DADOS] DataFrame gerado: {len(df)} linhas")
        
        if df.empty:
            return jsonify({'erro': 'Nenhum dado para exportar'}), 404
        
        output = BytesIO()
        df.to_csv(output, index=False, encoding='utf-8-sig', sep=';')
        output.seek(0)
        
        return send_file(
            output,
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'relatorio_pate_{datetime.now().strftime("%Y%m%d_%H%M")}.csv'
        )
    except Exception as e:
        print("[ERRO] ERRO na exportação CSV: {str(e)}")
        traceback.print_exc()
        return jsonify({'erro': 'Erro interno ao gerar relatório CSV'}), 500

# ========== ROTA DE TESTE ==========
@app.route('/api/teste/exportacao', methods=['GET'])
@login_required
def teste_exportacao():
    """Rota de teste para diagnosticar problemas de exportação"""
    try:
        # Teste 1: Contar pacientes
        total = mongo_db.pacientes.count_documents({})
        print("[OK] Total de pacientes: {total}")
        
        # Teste 2: Pegar um paciente para ver estrutura
        um_paciente = mongo_db.pacientes.find_one({})
        print("[OK] Estrutura do paciente: {list(um_paciente.keys()) if um_paciente else 'Nenhum'}")
        
        # Teste 3: Tentar gerar relatório
        df = gerar_relatorio_formatado()
        print("[OK] DataFrame gerado: {len(df)} linhas, {len(df.columns)} colunas")
        
        return jsonify({
            'status': 'ok',
            'total_pacientes': total,
            'linhas_relatorio': len(df),
            'colunas_relatorio': list(df.columns),
            'primeira_linha': df.iloc[0].to_dict() if len(df) > 0 else None
        })
    except Exception as e:
        erro_detalhado = traceback.format_exc()
        print(erro_detalhado)
        return jsonify({
            'status': 'erro',
            'erro': str(e),
            'detalhes': erro_detalhado
        }), 500
    
    # ========== ROTAS DE EXPORTAÇÃO POR UNIDADE ==========
@app.route('/api/exportar/relatorio_excel/unidade/<unidade_id>', methods=['GET'])
@admin_required
def exportar_relatorio_excel_por_unidade(unidade_id):
    """Exporta relatório Excel filtrado por unidade executora"""
    try:
        from bson import ObjectId
        
        if not unidade_id or unidade_id in ('undefined', 'null', ''):
            return jsonify({'erro': 'ID da unidade inválido'}), 400
        
        explicit_obj_id = ObjectId(unidade_id)
        
        print("[DADOS] Iniciando exportação Excel por unidade: {unidade_id}")
        
        # Buscar dados da unidade
        unidade = UnidadeExecutor.buscar_por_id(unidade_id)
        if not unidade:
            return jsonify({'erro': 'Unidade não encontrada'}), 404
        
        # Buscar pacientes: patient-level OR procedure-level matches
        pacientes = list(mongo_db.pacientes.find({
            '$or': [
                {'unidade_id': unidade_id},
                {'unidade_id': explicit_obj_id},
                {'procedimentos.unidade_id': unidade_id},
                {'procedimentos.unidade_id': explicit_obj_id}
            ]
        }))
        print("[DADOS] {len(pacientes)} pacientes encontrados para a unidade {unidade.get('nome')}")
        
        if not pacientes:
            return jsonify({'erro': f'Nenhum paciente encontrado para a unidade {unidade.get("nome")}'}), 404
        
        # Filter: only keep procedures whose effective unit matches
        pacientes_filtrados = []
        for p in pacientes:
            procs_originais = p.get('procedimentos', [])
            procs_filtrados = []
            for proc in procs_originais:
                proc_unit = proc.get('unidade_id') if isinstance(proc, dict) else None
                # Compare both as strings to handle ObjectId vs string mismatch
                proc_unit_str = str(proc_unit) if proc_unit else None
                if proc_unit_str == unidade_id or (not proc_unit and str(p.get('unidade_id', '')) == unidade_id):
                    procs_filtrados.append(proc)
            if procs_filtrados:
                p['procedimentos'] = procs_filtrados
                pacientes_filtrados.append(p)
        
        df = gerar_relatorio_formatado_por_unidade(pacientes_filtrados)
        
        if df.empty:
            return jsonify({'erro': 'Nenhum dado para exportar'}), 404
        
        output = BytesIO()
        
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name=f'Relatorio_{unidade.get("nome")[:20]}', index=False)
            
            worksheet = writer.sheets[f'Relatorio_{unidade.get("nome")[:20]}']
            
            for i, col in enumerate(df.columns):
                try:
                    max_len = max(df[col].astype(str).map(len).max(), len(col)) + 2
                    letra = chr(65 + i) if i < 26 else chr(65 + (i // 26) - 1) + chr(65 + (i % 26))
                    worksheet.column_dimensions[letra].width = min(max_len, 50)
                except:
                    pass
            
            worksheet.freeze_panes = 'A2'
        
        output.seek(0)
        
        nome_arquivo = f'relatorio_{unidade.get("nome", "unidade").replace(" ", "_")}_{datetime.now().strftime("%Y%m%d_%H%M")}.xlsx'
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=nome_arquivo
        )
    except Exception as e:
        print("[ERRO] ERRO na exportação Excel por unidade: {str(e)}")
        traceback.print_exc()
        return jsonify({'erro': 'Erro interno ao gerar relatório'}), 500

@app.route('/api/exportar/relatorio_csv/unidade/<unidade_id>', methods=['GET'])
@admin_required
def exportar_relatorio_csv_por_unidade(unidade_id):
    """Exporta relatório CSV filtrado por unidade executora"""
    try:
        from bson import ObjectId
        
        if not unidade_id or unidade_id in ('undefined', 'null', ''):
            return jsonify({'erro': 'ID da unidade inválido'}), 400
        
        explicit_obj_id = ObjectId(unidade_id)
        
        print("[DADOS] Iniciando exportação CSV por unidade: {unidade_id}")
        
        # Buscar dados da unidade
        unidade = UnidadeExecutor.buscar_por_id(unidade_id)
        if not unidade:
            return jsonify({'erro': 'Unidade não encontrada'}), 404
        
        # Buscar pacientes: patient-level OR procedure-level matches
        pacientes = list(mongo_db.pacientes.find({
            '$or': [
                {'unidade_id': unidade_id},
                {'unidade_id': explicit_obj_id},
                {'procedimentos.unidade_id': unidade_id},
                {'procedimentos.unidade_id': explicit_obj_id}
            ]
        }))
        
        if not pacientes:
            return jsonify({'erro': f'Nenhum paciente encontrado para a unidade {unidade.get("nome")}'}), 404
        
        # Filter: only keep procedures whose effective unit matches
        pacientes_filtrados = []
        for p in pacientes:
            procs_originais = p.get('procedimentos', [])
            procs_filtrados = []
            for proc in procs_originais:
                proc_unit = proc.get('unidade_id') if isinstance(proc, dict) else None
                proc_unit_str = str(proc_unit) if proc_unit else None
                if proc_unit_str == unidade_id or (not proc_unit and str(p.get('unidade_id', '')) == unidade_id):
                    procs_filtrados.append(proc)
            if procs_filtrados:
                p['procedimentos'] = procs_filtrados
                pacientes_filtrados.append(p)
        
        df = gerar_relatorio_formatado_por_unidade(pacientes_filtrados)
        
        if df.empty:
            return jsonify({'erro': 'Nenhum dado para exportar'}), 404
        
        output = BytesIO()
        df.to_csv(output, index=False, encoding='utf-8-sig', sep=';')
        output.seek(0)
        
        nome_arquivo = f'relatorio_{unidade.get("nome", "unidade").replace(" ", "_")}_{datetime.now().strftime("%Y%m%d_%H%M")}.csv'
        
        return send_file(
            output,
            mimetype='text/csv',
            as_attachment=True,
            download_name=nome_arquivo
        )
    except Exception as e:
        print("[ERRO] ERRO na exportação CSV por unidade: {str(e)}")
        traceback.print_exc()
        return jsonify({'erro': 'Erro interno ao gerar relatório CSV'}), 500

@app.route('/api/unidades/lista_para_exportar', methods=['GET'])
@login_required
def lista_unidades_para_exportar():
    """Retorna lista de unidades que têm pacientes cadastrados para exportação"""
    try:
        # Pipeline: unwind procedures, group by effective unit
        # (procedure-level override if exists, else patient-level)
        pipeline = [
            {'$match': {'unidade_id': {'$exists': True, '$ne': ''}}},
            {'$unwind': '$procedimentos'},
            {
                '$group': {
                    '_id': {
                        'unidade_id': {
                            '$toString': {
                                '$ifNull': ['$procedimentos.unidade_id', '$unidade_id']
                            }
                        }
                    },
                    'total_pacientes': {'$addToSet': '$_id'},
                    'unidade_nome': {
                        '$first': {
                            '$ifNull': ['$procedimentos.nome_estabelecimento', '$nome_estabelecimento']
                        }
                    },
                    'unidade_municipio': {
                        '$first': {
                            '$ifNull': ['$procedimentos.municipio', '$municipio']
                        }
                    }
                }
            },
            {
                '$match': {
                    '_id.unidade_id': {'$ne': None}
                }
            },
            {
                '$addFields': {
                    'total_pacientes': {'$size': '$total_pacientes'}
                }
            },
            {'$sort': {'unidade_nome': 1}}
        ]
        
        resultados = list(mongo_db.pacientes.aggregate(pipeline))
        
        unidades = []
        for item in resultados:
            uid = item['_id']['unidade_id']
            if uid:
                unidade = UnidadeExecutor.buscar_por_id(uid)
                if unidade:
                    unidades.append({
                        '_id': uid,
                        'nome': unidade.get('nome', item.get('unidade_nome', '')),
                        'municipio': unidade.get('municipio', item.get('unidade_municipio', '')),
                        'total_pacientes': item['total_pacientes']
                    })
        
        return jsonify(unidades)
    except Exception as e:
        print(f"Erro ao listar unidades: {e}")
        traceback.print_exc()
        return jsonify([])

def gerar_relatorio_formatado_por_unidade(pacientes):
    """Gera relatório para uma lista específica de pacientes"""
    
    dados_relatorio = []
    
    mapa_raca = {
        '01': 'BRANCA', 
        '02': 'PRETA', 
        '03': 'PARDA',
        '04': 'INDÍGENA'
    }
    
    for paciente in pacientes:
        nome_paciente = paciente.get('nome_completo', '').strip()
        
        procedimentos = paciente.get('procedimentos', [])
        
        if not procedimentos:
            procedimentos = ['Nenhum procedimento']
        
        for procedimento in procedimentos:
            try:
                # Extrair nome do procedimento
                if isinstance(procedimento, dict):
                    nome_proc_completo = procedimento.get('nome', '')
                    data_realizacao_proc = procedimento.get('data_realizacao', '')
                else:
                    nome_proc_completo = procedimento
                    data_realizacao_proc = paciente.get('data_realizacao', '')
                
                # Se for um dicionário aninhado, extrair corretamente
                if isinstance(nome_proc_completo, dict):
                    nome_proc_completo = nome_proc_completo.get('nome', '')
                
                if ' - ' in nome_proc_completo:
                    codigo_proc = nome_proc_completo.split(' - ')[0]
                    nome_proc = nome_proc_completo.split(' - ')[1]
                else:
                    codigo_proc = nome_proc_completo[:20]
                    nome_proc = nome_proc_completo
                
                # Formatar data da realização
                if data_realizacao_proc:
                    try:
                        data_formatada = datetime.strptime(data_realizacao_proc, '%Y-%m-%d').strftime('%d/%m/%Y')
                    except:
                        data_formatada = data_realizacao_proc
                else:
                    data_formatada = ''
                
                data_nasc = paciente.get('data_nascimento', '')
                if data_nasc:
                    try:
                        data_nasc_formatada = datetime.strptime(data_nasc, '%Y-%m-%d').strftime('%d/%m/%Y')
                    except:
                        data_nasc_formatada = data_nasc
                else:
                    data_nasc_formatada = ''
                
                cpf = paciente.get('cpf', '')
                if len(cpf) == 11 and cpf.isdigit():
                    cpf_formatado = f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"
                else:
                    cpf_formatado = cpf
                
                codigo_raca = paciente.get('raca_cor', '')
                descricao_raca = mapa_raca.get(codigo_raca, '')
                
                if codigo_raca and descricao_raca:
                    raca_formatada = f"{codigo_raca} {descricao_raca}"
                else:
                    raca_formatada = ''
                
                proc_unidade = procedimento.get('nome_estabelecimento', '') if isinstance(procedimento, dict) else ''
                proc_cnes = procedimento.get('cnes', '') if isinstance(procedimento, dict) else ''
                proc_cnpj = procedimento.get('cnpj', '') if isinstance(procedimento, dict) else ''
                proc_municipio = procedimento.get('municipio', '') if isinstance(procedimento, dict) else ''
                proc_olho = procedimento.get('olho', '') if isinstance(procedimento, dict) else ''

                linha = {
                    'DATA DA REALIZAÇÃO': data_formatada,
                    'NOME': nome_paciente,
                    'CPF': cpf_formatado,
                    'DATA DE NASCIMENTO': data_nasc_formatada,
                    'NOME DA MÃE': paciente.get('nome_mae', '').strip(),
                    'SEXO': paciente.get('sexo', ''),
                    'RAÇA': raca_formatada,
                    'ENDEREÇO': paciente.get('endereco', '').strip(),
                    'BAIRRO': paciente.get('bairro', '').strip(),
                    'CEP': paciente.get('cep', '').strip(),
                    'CONTATO': paciente.get('contato', '').strip(),
                    'CODIGO': codigo_proc,
                    'NOME_PROC': nome_proc,
                    'OLHO': proc_olho or paciente.get('olho', ''),
                    'CBO': paciente.get('cbo', '225265'),
                    'QTD': '0000001',
                    'NOME DO ESTABELECIMENTO': proc_unidade or paciente.get('nome_estabelecimento', '').strip(),
                    'CNES': proc_cnes or paciente.get('cnes', ''),
                    'CNPJ': proc_cnpj or paciente.get('cnpj', ''),
                    'MUNICIPIO': proc_municipio or paciente.get('municipio', '').strip()
                }
                dados_relatorio.append(linha)
            except Exception as e:
                print(f"Erro ao processar procedimento para {paciente.get('nome_completo')}: {e}")
                continue
    
    return pd.DataFrame(dados_relatorio)

if __name__ == '__main__':
    import sys
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    print("\n" + "="*60)
    print("SERVIDOR WEB INICIADO - PATE")
    print("="*60)
    print("MongoDB: localhost:27017")
    print("Banco: pate_santarem")
    print("Acesse no navegador: http://localhost:5002")
    print("Paginas disponiveis:")
    print("  http://localhost:5002/login     - Pagina de login")
    print("  http://localhost:5002/          - Formulario de cadastro")
    print("  http://localhost:5002/dashboard - Dashboard")
    print("  http://localhost:5002/unidades  - Unidades (Admin)")
    print("  http://localhost:5002/usuarios  - Usuarios (Admin)")
    print("  http://localhost:5002/api/teste/exportacao - Teste de exportacao")
    print("="*60 + "\n")
    
    app.run(debug=False, host='0.0.0.0', port=5002)