import socket
import threading
import os
import hashlib
import tkinter as tk
from tkinter import scrolledtext, simpledialog, messagebox
import time  # Import time module
import sys

def calcular_hash(arquivo):
    sha256 = hashlib.sha256()
    with open(arquivo, 'rb') as f:
        for bloco in iter(lambda: f.read(4096), b''):
            sha256.update(bloco)
    return sha256.hexdigest()


# Use o endereço do cliente como chave para garantir unicidade por cliente
chat_windows = {}

def handle_client(client_socket, client_address):
    print(f"Conexão de {client_address} estabelecida.")
    global chat_windows

    buffer = ""
    while True:
        try:
            request = client_socket.recv(1024).decode('utf-8')

            #data = client_socket.recv(1024).decode('utf-8')
            #if not data:
            #    break
            #buffer += data
            #while '\n' in buffer:
            #request, buffer = buffer.split('\n', 1)
            if not request:
                continue
            if request.startswith("Sair"):
                print(f"Cliente {client_address} desconectado.")
                if client_address in chat_windows:
                    chat_windows[client_address].display_message("Cliente saiu do chat.\n")
                    chat_windows[client_address].close_window()
                    del chat_windows[client_address]
                return
            elif request.startswith("Arquivo"):
                parts = request.split(' ', 1)
                threading.Thread(target=send_archive,args=(parts, client_socket, client_address)).start() ##vou retirar o args= e passar direto para a função
                #send_archive(parts,client_socket,client_address)
            elif request.startswith("Chat"):
                if client_address not in chat_windows:
                    chat_windows[client_address] = ChatWindow(server_root, client_socket, client_address)
                # Exibe a mensagem recebida na janela do chat
                chat_windows[client_address].display_message(f"Cliente: {request[5:]}\n")
                # Também exibe no log principal do servidor:
                broadcast_log.config(state='normal')
                broadcast_log.insert(tk.END, f"[Chat] {client_address}: {request[5:]}\n")
                broadcast_log.config(state='disabled')
                broadcast_log.see(tk.END)
        except ConnectionResetError:
            print(f"Conexão com {client_address} foi perdida.")
            break

    client_socket.close()
    clients.remove(client_socket)
    if client_address in chat_windows:
        chat_windows[client_address].close_window()
        del chat_windows[client_address]
        
def send_archive(parts, client_socket, client_address):
    if len(parts) == 2: ##aqui era dois mas me pareceu meio estranho AUGUSTO
        nome_arquivo = parts[1]
        if os.path.exists(nome_arquivo):
            tamanho_arquivo = os.path.getsize(nome_arquivo)
            hash_arquivo = calcular_hash(nome_arquivo)

            metadados = f"Nome: {nome_arquivo}\nTamanho: {tamanho_arquivo}\nHash: {hash_arquivo}\nStatus: ok\n"
            client_socket.send(metadados.encode('utf-8'))

            confirmacao = client_socket.recv(1024).decode('utf-8')
            if confirmacao == "Pronto para receber":
                with open(nome_arquivo, 'rb') as f:
                    parte_numero = 1
                    while True:
                        dados = f.read(4096)
                        if not dados:
                            break
                        client_socket.sendall(dados)
                        print(f"Enviando parte {parte_numero} para {client_address}: {dados[:10]}... ({len(dados)} bytes)")
                        parte_numero += 1
                client_socket.send("EOF".encode('utf-8'))
                print(f"Envio do arquivo {nome_arquivo} completo para {client_address}")
        else:
            client_socket.send("Status: arquivo inexistente\n".encode('utf-8'))
                
class ChatWindow:
    def __init__(self, root, client_socket, client_address):
        self.client_socket = client_socket
        self.client_address = client_address
        self.running = True

        self.window = tk.Toplevel(root)
        self.window.title(f"Chat com {client_address}")

        self.chat_log = scrolledtext.ScrolledText(self.window, state='disabled', width=50, height=20)
        self.chat_log.pack()

        self.chat_entry = tk.Entry(self.window, width=50)
        self.chat_entry.pack()
        self.chat_entry.bind("<Return>", self.send_message)

        # Não crie thread para ouvir mensagens aqui! Tudo será tratado no handle_client

    def display_message(self, message):
        # Garante que a atualização do chat_log ocorra na thread principal do Tkinter
        def update_log():
            self.chat_log.config(state='normal')
            self.chat_log.insert(tk.END, message)
            self.chat_log.config(state='disabled')
        self.window.after(0, update_log)

    def send_message(self, event):
        mensagem = self.chat_entry.get()
        if mensagem.strip() == '':
            return
        try:
            self.client_socket.send(f"Chat {mensagem}".encode('utf-8'))
            self.display_message(f"Você: {mensagem}\n")
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao enviar mensagem: {e}")
        self.chat_entry.delete(0, tk.END)
        if mensagem.lower() == 'sair':
            self.client_socket.send("Sair".encode('utf-8'))
            self.running = False
            self.window.destroy()

    def close_window(self):
        self.running = False
        self.window.destroy()

def broadcast_message(message):
    for client in clients:
        try:
            client.send(f"Broadcast: {message}\n".encode('utf-8'))
        except:
            client.close()
            clients.remove(client)

def start_server():
    global clients, server_root
    clients = []

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(('0.0.0.0', 9999))
    server.listen(5)
    print("Servidor escutando na porta 9999...")

    while True:
        client_socket, client_address = server.accept()
        clients.append(client_socket)
        client_handler = threading.Thread(target=handle_client, args=(client_socket, client_address))
        client_handler.start()

def enviar_broadcast(event=None):
    mensagem = broadcast_entry.get()
    broadcast_entry.delete(0, tk.END)
    broadcast_message(mensagem)
    broadcast_log.config(state='normal')
    broadcast_log.insert(tk.END, f"Você: {mensagem}\n")
    broadcast_log.config(state='disabled')


# Função para encerrar o servidor de forma limpa
def sair_servidor():
    print("Encerrando servidor...")
    for client in clients:
        try:
            client.send("Sair".encode('utf-8'))
            client.close()
        except:
            pass
    try:
        server_root.destroy()
    except:
        pass
    os._exit(0)  # Encerra imediatamente o processo

if __name__ == "__main__":
    server_root = tk.Tk()
    server_root.title("Servidor TCP")
    server_root.geometry("800x600")
    server_root.configure(bg="#222831")

    title = tk.Label(server_root, text="Servidor TCP", font=("Segoe UI", 22, "bold"), fg="#00adb5", bg="#222831")
    title.pack(pady=(18, 8))

    broadcast_frame = tk.Frame(server_root, bg="#222831")
    broadcast_frame.pack(pady=10)

    broadcast_log = scrolledtext.ScrolledText(broadcast_frame, state='disabled', width=70, height=18, font=("Consolas", 11), bg="#393e46", fg="#eeeeee", relief="flat")
    broadcast_log.pack(pady=5)

    entry_frame = tk.Frame(broadcast_frame, bg="#222831")
    entry_frame.pack(pady=5)
    broadcast_entry = tk.Entry(entry_frame, width=55, font=("Segoe UI", 12), bg="#eeeeee", fg="#222831", relief="flat")
    broadcast_entry.grid(row=0, column=0, padx=5)
    send_btn = tk.Button(entry_frame, text="Enviar Broadcast", command=enviar_broadcast, font=("Segoe UI", 11, "bold"), bg="#00adb5", fg="#222831", relief="flat", width=18)
    send_btn.grid(row=0, column=1, padx=5)
    broadcast_entry.bind("<Return>", enviar_broadcast)

    # Botão Sair
    sair_btn = tk.Button(server_root, text="Sair", command=sair_servidor, font=("Segoe UI", 12, "bold"), bg="#ff2e63", fg="#eeeeee", relief="flat", width=12)
    sair_btn.pack(pady=10)

    # Handler para fechar a janela
    server_root.protocol("WM_DELETE_WINDOW", sair_servidor)

    threading.Thread(target=start_server).start()
    server_root.mainloop()
