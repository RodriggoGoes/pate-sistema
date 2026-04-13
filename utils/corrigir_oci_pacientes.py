from pymongo import MongoClient
from datetime import datetime

def corrigir_oci_pacientes():
    """Corrige o campo oci_pmae para todos os pacientes baseado nos procedimentos"""
    
    client = MongoClient('mongodb://localhost:27017/')
    db = client['pate_santarem']
    pacientes = db['pacientes']
    
    count = 0
    for paciente in pacientes.find():
        procedimentos = paciente.get('procedimentos', [])
        oci_atual = paciente.get('oci_pmae', '')
        novo_oci = oci_atual
        
        # Verificar procedimentos
        for proc in procedimentos:
            if isinstance(proc, dict):
                nome_proc = proc.get('nome', '')
            else:
                nome_proc = proc
            
            # Se for facoemulsificação
            if 'FACOEMULSIFICAÇÃO' in nome_proc.upper():
                novo_oci = '04.05.05.037-2'
                break
            # Se for avaliação inicial
            elif 'CONSULTA' in nome_proc.upper() or 'TESTE' in nome_proc.upper() or 'MAPEAMENTO' in nome_proc.upper() or 'BIOMICROSCOPIA' in nome_proc.upper() or 'TONOMETRIA' in nome_proc.upper():
                if novo_oci != '04.05.05.037-2':  # Não sobrescrever se já for cirurgia
                    novo_oci = '09.05.01.003-5'
        
        # Se mudou, atualizar
        if novo_oci != oci_atual and novo_oci:
            pacientes.update_one(
                {'_id': paciente['_id']},
                {'$set': {'oci_pmae': novo_oci}}
            )
            count += 1
            tipo = "CIRURGIA" if novo_oci == '04.05.05.037-2' else "OCI OFTALMOLÓGICA"
            print(f"✅ Corrigido: {paciente['nome_completo']} -> {tipo}")
    
    print(f"\n📊 Total de pacientes corrigidos: {count}")

if __name__ == '__main__':
    corrigir_oci_pacientes()