from waitress import serve
from app import app
import socket

def obter_ip_local():
    """Obtém o IP local da máquina"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

# Configurações do servidor
HOST = '0.0.0.0'  # Aceita conexões de qualquer lugar
PORTA = 5002
IP_LOCAL = obter_ip_local()

print("="*60)
print("🚀 PATE - SISTEMA EM PRODUÇÃO")
print("="*60)
print(f"📍 Servidor iniciado em: {IP_LOCAL}:{PORTA}")
print(f"📍 Acesso local: http://localhost:{PORTA}")
print(f"📍 Acesso rede: http://{IP_LOCAL}:{PORTA}")
print("="*60)
print("📋 Páginas disponíveis:")
print(f"   - Login: http://{IP_LOCAL}:{PORTA}/login")
print(f"   - Cadastro: http://{IP_LOCAL}:{PORTA}/")
print(f"   - Dashboard: http://{IP_LOCAL}:{PORTA}/dashboard")
print("="*60)
print("🔑 Credenciais padrão:")
print("   Admin: admin@pate.com / admin123")
print("   Operador: operador@pate.com / operador123")
print("="*60)
print("📌 Pressione Ctrl+C para parar o servidor")
print("="*60 + "\n")

# Iniciar servidor
serve(app, host=HOST, port=PORTA, threads=4, connection_limit=100)