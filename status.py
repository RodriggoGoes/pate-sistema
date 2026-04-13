import requests
import time
import os
from datetime import datetime

def limpar_tela():
    os.system('cls' if os.name == 'nt' else 'clear')

def verificar_servidor():
    try:
        response = requests.get('http://localhost:5002/login', timeout=5)
        if response.status_code == 200:
            return True, "✅ ONLINE"
        return False, f"⚠️ ERRO {response.status_code}"
    except requests.ConnectionError:
        return False, "❌ OFFLINE"
    except Exception as e:
        return False, f"❌ ERRO: {str(e)[:30]}"

def obter_ip():
    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "não disponível"

def main():
    while True:
        limpar_tela()
        print("="*50)
        print("📊 MONITORAMENTO PATE - EM TEMPO REAL")
        print("="*50)
        print(f"🕐 {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        print(f"🌐 IP Local: {obter_ip()}:5002")
        print("-"*50)
        
        status, mensagem = verificar_servidor()
        print(f"📡 Servidor: {mensagem}")
        
        if status:
            print("\n📋 Links de acesso:")
            print(f"   🔗 http://localhost:5002/login")
            print(f"   🔗 http://{obter_ip()}:5002/login")
        
        print("\n" + "-"*50)
        print("🔍 Pressione Ctrl+C para sair")
        print("🔄 Atualizando a cada 30 segundos...")
        
        time.sleep(30)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Monitoramento encerrado!")