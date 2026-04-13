from database import mongo_db
from datetime import datetime
import bcrypt

class Usuario:
    """Model para gerenciar usuários do sistema"""
    
    colecao = mongo_db.usuarios
    
    @staticmethod
    def criar(usuario):
        """Cria um novo usuário"""
        # Criptografar senha
        salt = bcrypt.gensalt()
        usuario['senha_hash'] = bcrypt.hashpw(usuario['senha'].encode('utf-8'), salt)
        usuario.pop('senha', None)
        usuario['data_cadastro'] = datetime.now()
        usuario['ativo'] = True
        
        return Usuario.colecao.insert_one(usuario)
    
    @staticmethod
    def autenticar(email, senha):
        """Autentica um usuário"""
        usuario = Usuario.colecao.find_one({'email': email, 'ativo': True})
        
        if usuario and bcrypt.checkpw(senha.encode('utf-8'), usuario['senha_hash']):
            return usuario
        return None
    
    @staticmethod
    def listar():
        """Lista todos os usuários"""
        return list(Usuario.colecao.find({}, {'senha_hash': 0}))
    
    @staticmethod
    def buscar_por_id(usuario_id):
        """Busca usuário por ID"""
        from bson import ObjectId
        return Usuario.colecao.find_one({'_id': ObjectId(usuario_id)}, {'senha_hash': 0})
    
    @staticmethod
    def atualizar_permissao(usuario_id, tipo):
        """Atualiza o tipo de usuário"""
        from bson import ObjectId
        return Usuario.colecao.update_one(
            {'_id': ObjectId(usuario_id)},
            {'$set': {'tipo': tipo}}
        )
    
    @staticmethod
    def desativar(usuario_id):
        """Desativa um usuário"""
        from bson import ObjectId
        return Usuario.colecao.update_one(
            {'_id': ObjectId(usuario_id)},
            {'$set': {'ativo': False}}
        )