from pymongo import MongoClient

MONGO_URI = "mongodb://localhost:27017/"
client = MongoClient(MONGO_URI)
db = client['pate_santarem']
mongo_db = db

# Criar índices
try:
    db.pacientes.create_index("cpf", unique=True)
    db.pacientes.create_index("data_realizacao")
    db.pacientes.create_index("data_cadastro")
    db.pacientes.create_index("oci_pmae")
    print("✅ Índices criados/verificados com sucesso")
except Exception as e:
    print(f"⚠️ Erro nos índices: {e}")

print(f"✅ Conectado ao MongoDB em localhost:27017")
print(f"📊 Banco de dados: {db.name}")