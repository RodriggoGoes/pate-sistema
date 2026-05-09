import os
from pymongo import MongoClient

MONGO_URI = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/pate_santarem')
client = MongoClient(MONGO_URI)
db = client.get_default_database()
if db.name == 'test' or not os.environ.get('MONGO_URI'):
    db = client['pate_santarem']
mongo_db = db

# Criar índices
try:
    existing = list(db.pacientes.list_indexes())
    existing_names = [idx['name'] for idx in existing]
    if 'cpf_1' in existing_names:
        db.pacientes.drop_index('cpf_1')
    db.pacientes.create_index("cpf", unique=True, sparse=True)
    if 'data_realizacao_1' not in existing_names:
        db.pacientes.create_index("data_realizacao")
    if 'data_cadastro_1' not in existing_names:
        db.pacientes.create_index("data_cadastro")
    if 'oci_pmae_1' not in existing_names:
        db.pacientes.create_index("oci_pmae")
    print("[OK] Indices criados/verificados com sucesso")
except Exception as e:
    print(f"[!] Erro nos indices: {e}")

print(f"[OK] Conectado ao MongoDB em localhost:27017")
print(f"[DB] Banco de dados: {db.name}")