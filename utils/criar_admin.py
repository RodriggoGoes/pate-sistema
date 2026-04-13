from pymongo import MongoClient
import bcrypt
from datetime import datetime

def criar_admin():
    """Cria o usuário administrador inicial"""
    
    client = MongoClient('mongodb://localhost:27017/')
    db = client['pate_santarem']
    usuarios = db['usuarios']
    
    # Verificar se já existe admin
    if usuarios.find_one({'email': 'admin@pate.com'}):
        print("⚠️ Usuário admin já existe!")
        return
    
    # Criar admin
    salt = bcrypt.gensalt()
    senha_hash = bcrypt.hashpw('admin123'.encode('utf-8'), salt)
    
    admin = {
        'nome': 'Administrador',
        'email': 'admin@pate.com',
        'senha_hash': senha_hash,
        'tipo': 'admin',
        'unidade_id': '',
        'ativo': True,
        'data_cadastro': datetime.now()
    }
    
    usuarios.insert_one(admin)
    print("✅ Usuário admin criado com sucesso!")
    print("   Email: admin@pate.com")
    print("   Senha: admin123")

def criar_operador():
    """Cria um usuário operador de exemplo"""
    
    client = MongoClient('mongodb://localhost:27017/')
    db = client['pate_santarem']
    usuarios = db['usuarios']
    
    # Verificar se já existe
    if usuarios.find_one({'email': 'operador@pate.com'}):
        print("⚠️ Usuário operador já existe!")
        return
    
    # Criar operador
    salt = bcrypt.gensalt()
    senha_hash = bcrypt.hashpw('operador123'.encode('utf-8'), salt)
    
    operador = {
        'nome': 'Operador',
        'email': 'operador@pate.com',
        'senha_hash': senha_hash,
        'tipo': 'operador',
        'unidade_id': '',
        'ativo': True,
        'data_cadastro': datetime.now()
    }
    
    usuarios.insert_one(operador)
    print("✅ Usuário operador criado com sucesso!")
    print("   Email: operador@pate.com")
    print("   Senha: operador123")

if __name__ == '__main__':
    criar_admin()
    criar_operador()