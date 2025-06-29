import socket
import threading
import os

HOST = '127.0.0.1'
PORT = 8080  # Porta acima de 1024

def handle_client(conn, addr):
    try:
        request = conn.recv(1024).decode('utf-8')
        if not request:
            conn.close()
            return
        # Exemplo: GET /pagina.html HTTP/1.0
        linha = request.split('\r\n')[0]
        partes = linha.split()
        if len(partes) < 2 or partes[0] != 'GET':
            resposta = 'HTTP/1.0 400 Bad Request\r\n\r\nBad Request'
            conn.sendall(resposta.encode('utf-8'))
            conn.close()
            return
        caminho = partes[1].lstrip('/')
        if caminho == '' or (os.path.exists(caminho) and os.path.isdir(caminho)):
            # Listar arquivos da pasta
            pasta = caminho if caminho else '.'
            try:
                arquivos = os.listdir(pasta)
                links = ''
                for nome in arquivos:
                    if os.path.isdir(os.path.join(pasta, nome)):
                        links += f'<li><a href="/{nome}/">{nome}/</a></li>'
                    else:
                        links += f'<li><a href="/{nome}">{nome}</a></li>'
                conteudo = f'<html><body><h1>Arquivos em /{caminho}</h1><ul>{links}</ul></body></html>'
                resposta = f'HTTP/1.0 200 OK\r\nContent-Type: text/html\r\n\r\n{conteudo}'
                conn.sendall(resposta.encode('utf-8'))
            except Exception:
                resposta = 'HTTP/1.0 500 Internal Server Error\r\nContent-Type: text/html\r\n\r\n<h1>500 Internal Server Error</h1>'
                conn.sendall(resposta.encode('utf-8'))
            conn.close()
            return
        if not os.path.exists(caminho) or not os.path.isfile(caminho):
            resposta = 'HTTP/1.0 404 Not Found\r\nContent-Type: text/html\r\n\r\n<h1>404 Not Found</h1>'
            conn.sendall(resposta.encode('utf-8'))
            conn.close()
            return
        # Determina o tipo de conteúdo
        if caminho.endswith('.html'):
            content_type = 'text/html'
            with open(caminho, 'r', encoding='utf-8') as f:
                conteudo = f.read()
            resposta = f'HTTP/1.0 200 OK\r\nContent-Type: {content_type}\r\n\r\n{conteudo}'
            conn.sendall(resposta.encode('utf-8'))
        elif caminho.endswith('.jpg') or caminho.endswith('.jpeg'):
            content_type = 'image/jpeg'
            with open(caminho, 'rb') as f:
                conteudo = f.read()
            header = f'HTTP/1.0 200 OK\r\nContent-Type: {content_type}\r\n\r\n'.encode('utf-8')
            conn.sendall(header + conteudo)
        elif caminho.endswith('.txt'):
            content_type = 'text/plain'
            with open(caminho, 'r', encoding='utf-8') as f:
                conteudo = f.read()
            resposta = f'HTTP/1.0 200 OK\r\nContent-Type: {content_type}\r\n\r\n{conteudo}'
            conn.sendall(resposta.encode('utf-8'))
        else:
            resposta = 'HTTP/1.0 415 Unsupported Media Type\r\nContent-Type: text/html\r\n\r\n<h1>415 Unsupported Media Type</h1>'
            conn.sendall(resposta.encode('utf-8'))
        conn.close()
    except Exception as e:
        try:
            resposta = 'HTTP/1.0 500 Internal Server Error\r\nContent-Type: text/html\r\n\r\n<h1>500 Internal Server Error</h1>'
            conn.sendall(resposta.encode('utf-8'))
        except:
            pass
        conn.close()

def main():
    print(f'Servidor HTTP rodando em http://{HOST}:{PORT}')
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, PORT))
        s.listen(5)
        while True:
            conn, addr = s.accept()
            threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()

if __name__ == '__main__':
    main()
