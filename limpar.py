from pymongo import MongoClient

# Conectar
client = MongoClient('mongodb://localhost:27017/')
db = client['pate_santarem']

# Contar antes
total = db.pacientes.count_documents({})
print(f"📊 Registros atuais: {total}")

if total > 0:
    resposta = input(f"⚠️ Remover {total} registros? (s/N): ")
    if resposta.lower() == 's':
        db.pacientes.delete_many({})
        print(f"✅ {total} registros removidos! Banco está vazio.")
    else:
        print("❌ Operação cancelada.")
else:
    print("✅ Banco já está vazio!")