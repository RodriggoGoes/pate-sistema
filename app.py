from flask import Flask, request, jsonify, send_file, render_template, session, redirect, url_for
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

# ========== CRIAÇÃO DO APP PRIMEIRO ==========
app = Flask(__name__)
CORS(app)

# ========== CONFIGURAÇÕES DE PRODUÇÃO ==========
# Desativar modo debug
DEBUG = False

# Gerar chave secreta segura (use variável de ambiente)
SECRET_KEY = os.environ.get('SECRET_KEY')
if not SECRET_KEY:
    SECRET_KEY = 'CHANGE_THIS_IN_PRODUCTION'

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
def validar_cpf(cpf):
    """Validação completa de CPF"""
    cpf = re.sub(r'[^0-9]', '', cpf)
    
    if len(cpf) != 11:
        return False
    
    if cpf == cpf[0] * 11:
        return False
    
    try:
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
    """Gera relatório EXATAMENTE no formato solicitado"""
    
    pacientes = list(mongo_db.pacientes.find({}, {'_id': 0}))
    
    dados_relatorio = []
    
    mapa_raca = {
        '01': 'BRANCA', 
        '02': 'PRETA', 
        '03': 'PARDA'
    }
    
    for paciente in pacientes:
        procedimentos = paciente.get('procedimentos', [])
        
        if not procedimentos:
            procedimentos = ['Nenhum procedimento']
        
        for procedimento in procedimentos:
            if isinstance(procedimento, dict):
                nome_proc_completo = procedimento.get('nome', '')
                data_realizacao_proc = procedimento.get('data_realizacao', '')
            else:
                nome_proc_completo = procedimento
                data_realizacao_proc = paciente.get('data_realizacao', '')
            
            if ' - ' in nome_proc_completo:
                codigo_proc = nome_proc_completo.split(' - ')[0]
                nome_proc = nome_proc_completo.split(' - ')[1]
            else:
                codigo_proc = nome_proc_completo[:20]
                nome_proc = nome_proc_completo
            
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
            
            linha = {
                'DATA DA REALIZAÇÃO': data_formatada,
                'NOME': paciente.get('nome_completo', ''),
                'CPF': cpf_formatado,
                'DATA DE NASCIMENTO': data_nasc_formatada,
                'NOME DA MÃE': paciente.get('nome_mae', ''),
                'SEXO': paciente.get('sexo', ''),
                'RAÇA': raca_formatada,
                'ENDEREÇO': paciente.get('endereco', ''),
                'BAIRRO': paciente.get('bairro', ''),
                'CEP': paciente.get('cep', ''),
                'CONTATO': paciente.get('contato', ''),
                'CODIGO': codigo_proc,
                'NOME_PROC': nome_proc,
                'CBO': paciente.get('cbo', '225265'),
                'QTD': '0000001',
                'NOME DO ESTABELECIMENTO': paciente.get('nome_estabelecimento', ''),
                'CNES': paciente.get('cnes', ''),
                'CNPJ': paciente.get('cnpj', ''),
                'MUNICIPIO': paciente.get('municipio', '')
            }
            dados_relatorio.append(linha)
    
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
    
    usuario = Usuario.colecao.find_one({'email': email})
    
    if not usuario:
        return jsonify({'erro': 'Email não encontrado'}), 404
    
    return jsonify({
        'mensagem': f'Instruções de recuperação enviadas para {email}. Verifique sua caixa de entrada.'
    }), 200

@app.route('/api/registro', methods=['POST'])
def registrar_usuario():
    dados = request.json
    
    if not dados.get('nome'):
        return jsonify({'erro': 'Nome é obrigatório'}), 400
    if not dados.get('email'):
        return jsonify({'erro': 'Email é obrigatório'}), 400
    if not dados.get('senha'):
        return jsonify({'erro': 'Senha é obrigatória'}), 400
    
    from models.usuario import Usuario as UsuarioModel
    if UsuarioModel.colecao.find_one({'email': dados['email']}):
        return jsonify({'erro': 'Email já cadastrado'}), 400
    
    usuario = {
        'nome': dados['nome'],
        'email': dados['email'],
        'senha': dados['senha'],
        'tipo': dados.get('tipo', 'operador'),
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
    email = dados.get('email')
    senha = dados.get('senha')
    
    usuario = Usuario.autenticar(email, senha)
    
    if usuario:
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

@app.route('/api/unidades/<unidade_id>/desativar', methods=['DELETE'])
@admin_required
def desativar_unidade(unidade_id):
    result = UnidadeExecutor.desativar(unidade_id)
    
    if result.modified_count > 0:
        return jsonify({'mensagem': 'Unidade desativada com sucesso'})
    else:
        return jsonify({'erro': 'Unidade não encontrada'}), 404

# ========== EDIÇÃO E BUSCAS DE PACIENTES ==========
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
    
    if not cpf or not novo_procedimento:
        return jsonify({'erro': 'CPF e procedimento são obrigatórios'}), 400
    
    paciente = mongo_db.pacientes.find_one({'cpf': cpf})
    if not paciente:
        return jsonify({'erro': 'Paciente não encontrado'}), 404
    
    procedimentos_atuais = paciente.get('procedimentos', [])
    
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
    
    novo_item = {
        'nome': novo_procedimento,
        'data_realizacao': nova_data_realizacao,
        'data_registro': datetime.now().isoformat()
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

# ========== ROTAS DA API DE PACIENTES ==========
@app.route('/api/pacientes', methods=['GET'])
@login_required
def listar_pacientes():
    pacientes = list(mongo_db.pacientes.find({}, {'_id': 0}).sort('data_cadastro', -1))
    return json.loads(json_util.dumps(pacientes))

@app.route('/api/paciente', methods=['POST'])
@login_required
def cadastrar_paciente():
    dados = request.json
    
    if not dados.get('cpf') or not validar_cpf(dados['cpf']):
        return jsonify({'erro': 'CPF inválido'}), 400
    
    if mongo_db.pacientes.find_one({'cpf': dados['cpf']}):
        return jsonify({'erro': 'CPF já cadastrado'}), 400
    
    idade = calcular_idade(dados.get('data_nascimento'))
    
    unidade_id = session.get('unidade_id')
    unidade = None
    if unidade_id:
        unidade = UnidadeExecutor.buscar_por_id(unidade_id)
    
    procedimentos_lista = []
    for proc in dados['procedimentos']:
        procedimentos_lista.append({
            'nome': proc,
            'data_realizacao': dados['data_realizacao'],
            'data_registro': datetime.now().isoformat()
        })
    
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
        return jsonify({'erro': f'Erro ao salvar: {str(e)}'}), 500

# ========== ROTAS DO DASHBOARD ==========
@app.route('/api/dashboard/unidades_stats', methods=['GET'])
@login_required
def unidades_stats():
    pipeline = [
        {
            '$group': {
                '_id': {
                    'unidade_nome': '$nome_estabelecimento',
                    'unidade_municipio': '$municipio',
                    'oci_pmae': '$oci_pmae'
                },
                'count': {'$sum': 1}
            }
        }
    ]
    
    resultados = list(mongo_db.pacientes.aggregate(pipeline))
    
    unidades_dict = {}
    for item in resultados:
        unidade_nome = item['_id']['unidade_nome'] or 'Unidade não definida'
        unidade_municipio = item['_id']['unidade_municipio'] or ''
        oci_tipo = item['_id']['oci_pmae']
        count = item['count']
        
        chave = unidade_nome
        if chave not in unidades_dict:
            unidades_dict[chave] = {
                'nome': unidade_nome,
                'municipio': unidade_municipio,
                'oci_oftalmologica': 0,
                'cirurgias': 0,
                'total': 0
            }
        
        if oci_tipo == '09.05.01.003-5':
            unidades_dict[chave]['oci_oftalmologica'] = count
        elif oci_tipo == '04.05.05.037-2':
            unidades_dict[chave]['cirurgias'] = count
        
        unidades_dict[chave]['total'] += count
    
    unidades_lista = []
    for unidade_id, dados in unidades_dict.items():
        unidades_lista.append({
            'nome': dados['nome'],
            'municipio': dados['municipio'],
            'oci_oftalmologica': dados['oci_oftalmologica'],
            'cirurgias': dados['cirurgias'],
            'total': dados['total']
        })
    
    unidades_lista.sort(key=lambda x: x['total'], reverse=True)
    
    return jsonify(unidades_lista)

@app.route('/api/dashboard/procedimentos_por_unidade', methods=['GET'])
@login_required
def procedimentos_por_unidade():
    pipeline = [
        {'$unwind': '$procedimentos'},
        {
            '$group': {
                '_id': {
                    'unidade': '$nome_estabelecimento',
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
    total_pacientes = mongo_db.pacientes.count_documents({})
    
    pipeline_procedimentos = [
        {'$unwind': '$procedimentos'},
        {'$group': {'_id': '$procedimentos', 'count': {'$sum': 1}}},
        {'$sort': {'count': -1}},
        {'$limit': 10}
    ]
    procedimentos_count = list(mongo_db.pacientes.aggregate(pipeline_procedimentos))
    
    sexo_stats = {
        'MASCULINO': mongo_db.pacientes.count_documents({'sexo': 'MASCULINO'}),
        'FEMININO': mongo_db.pacientes.count_documents({'sexo': 'FEMININO'})
    }
    
    olho_stats = {
        'OD': mongo_db.pacientes.count_documents({'olho': 'OD'}),
        'OE': mongo_db.pacientes.count_documents({'olho': 'OE'}),
        'AMBOS': mongo_db.pacientes.count_documents({'olho': 'AMBOS'}),
        'SEM': mongo_db.pacientes.count_documents({'olho': 'SEM'})
    }
    
    raca_stats = {
        '01 - Branca': mongo_db.pacientes.count_documents({'raca_cor': '01'}),
        '02 - Preta': mongo_db.pacientes.count_documents({'raca_cor': '02'}),
        '03 - Parda': mongo_db.pacientes.count_documents({'raca_cor': '03'})
    }
    
    oci_stats = {
        'OCI OFTALMOLOGICA': mongo_db.pacientes.count_documents({'oci_pmae': '09.05.01.003-5'}),
        'CIRURGIAS': mongo_db.pacientes.count_documents({'oci_pmae': '04.05.05.037-2'})
    }
    
    data_limite = datetime.now() - timedelta(days=30)
    ultimos_30_dias = mongo_db.pacientes.count_documents({
        'data_cadastro': {'$gte': data_limite}
    })
    
    idade_stats = {
        '0-20': mongo_db.pacientes.count_documents({'idade': {'$lte': 20}}),
        '21-40': mongo_db.pacientes.count_documents({'idade': {'$gte': 21, '$lte': 40}}),
        '41-60': mongo_db.pacientes.count_documents({'idade': {'$gte': 41, '$lte': 60}}),
        '61-80': mongo_db.pacientes.count_documents({'idade': {'$gte': 61, '$lte': 80}}),
        '80+': mongo_db.pacientes.count_documents({'idade': {'$gte': 81}})
    }
    
    return jsonify({
        'total_pacientes': total_pacientes,
        'ultimos_30_dias': ultimos_30_dias,
        'procedimentos': procedimentos_count,
        'sexo': sexo_stats,
        'olho': olho_stats,
        'raca_cor': raca_stats,
        'oci': oci_stats,
        'idade': idade_stats
    })

# ========== EXPORTAÇÃO ==========
@app.route('/api/exportar/relatorio_excel', methods=['GET'])
@login_required
def exportar_relatorio_excel():
    df = gerar_relatorio_formatado()
    
    if df.empty:
        return jsonify({'erro': 'Nenhum dado para exportar'}), 404
    
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Relatorio PATE', index=False)
        
        worksheet = writer.sheets['Relatorio PATE']
        column_widths = {
            'A': 20, 'B': 45, 'C': 15, 'D': 20, 'E': 45,
            'F': 10, 'G': 12, 'H': 15, 'I': 60, 'J': 10,
            'K': 10, 'L': 50, 'M': 15, 'N': 20, 'O': 30
        }
        for col_letter, width in column_widths.items():
            worksheet.column_dimensions[col_letter].width = width
        worksheet.freeze_panes = 'A2'
        worksheet.auto_filter.ref = worksheet.dimensions
    
    output.seek(0)
    
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f'relatorio_pate_{datetime.now().strftime("%Y%m%d_%H%M")}.xlsx'
    )

@app.route('/api/exportar/relatorio_csv', methods=['GET'])
@login_required
def exportar_relatorio_csv():
    df = gerar_relatorio_formatado()
    
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

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🚀 SERVIDOR WEB INICIADO - PATE")
    print("="*60)
    print(f"📍 MongoDB: localhost:27017")
    print(f"📍 Banco: pate_santarem")
    print(f"📍 Acesse no navegador: http://localhost:5002")
    print("\n📋 Páginas disponíveis:")
    print("  http://localhost:5002/login     - Página de login")
    print("  http://localhost:5002/          - Formulário de cadastro")
    print("  http://localhost:5002/dashboard - Dashboard")
    print("  http://localhost:5002/unidades  - Unidades (Admin)")
    print("  http://localhost:5002/usuarios  - Usuários (Admin)")
    print("\n📌 Configure as credenciais de acesso via variáveis de ambiente")
    print("="*60 + "\n")
    
    app.run(debug=True, host='0.0.0.0', port=5002)