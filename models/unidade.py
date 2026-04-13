from database import mongo_db
from datetime import datetime
from bson import ObjectId

class UnidadeExecutor:
    """Model para gerenciar unidades executoras"""
    
    colecao = mongo_db.unidades_executoras
    
    @staticmethod
    def criar(unidade):
        """Cria uma nova unidade executora"""
        unidade['data_cadastro'] = datetime.now()
        unidade['ativa'] = unidade.get('ativa', True)
        return UnidadeExecutor.colecao.insert_one(unidade)
    
    @staticmethod
    def listar(apenas_ativas=True):
        """Lista todas as unidades executoras"""
        query = {'ativa': True} if apenas_ativas else {}
        return list(UnidadeExecutor.colecao.find(query, {'_id': 0}))
    
    @staticmethod
    def listar_com_id():
        """Lista unidades com ID para seleção"""
        unidades = list(UnidadeExecutor.colecao.find({'ativa': True}))
        for unidade in unidades:
            unidade['_id'] = str(unidade['_id'])
        return unidades
    
    @staticmethod
    def buscar_por_id(unidade_id):
        """Busca unidade por ID"""
        return UnidadeExecutor.colecao.find_one({'_id': ObjectId(unidade_id)})
    
    @staticmethod
    def buscar_por_nome(nome):
        """Busca unidade por nome"""
        return UnidadeExecutor.colecao.find_one({'nome': nome})
    
    @staticmethod
    def atualizar(unidade_id, dados):
        """Atualiza uma unidade"""
        return UnidadeExecutor.colecao.update_one(
            {'_id': ObjectId(unidade_id)},
            {'$set': dados}
        )
    
    @staticmethod
    def desativar(unidade_id):
        """Desativa uma unidade"""
        return UnidadeExecutor.colecao.update_one(
            {'_id': ObjectId(unidade_id)},
            {'$set': {'ativa': False}}
        )
    
    @staticmethod
    def get_unidade_padrao():
        """Retorna a primeira unidade ativa"""
        unidade = UnidadeExecutor.colecao.find_one({'ativa': True})
        if not unidade:
            padrao = {
                'nome': 'HOSPITAL MUNICIPAL DE SANTARÉM - Drº ALBERTO TOLENTINO',
                'municipio': 'SANTARÉM',
                'cnes': '2329905',
                'cnpj': '',
                'endereco': '',
                'telefone': '',
                'responsavel': '',
                'ativa': True,
                'data_cadastro': datetime.now()
            }
            UnidadeExecutor.colecao.insert_one(padrao)
            return padrao
        return unidade