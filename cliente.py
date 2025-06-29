import os
import socket
import threading
import hashlib
import tkinter as tk
from tkinter import filedialog, scrolledtext, messagebox

def calcular_hash(arquivo):
    sha256 = hashlib.sha256()
    with open(arquivo, 'rb') as f:
        for bloco in iter(lambda: f.read(4096), b''):
            sha256.update(bloco)
    return sha256.hexdigest()

def receber_arquivo(client_socket, nome_arquivo):
    dados = b''
    parte_numero = 1
    while True:
        parte = client_socket.recv(4096)
        aux = parte.decode('utf-8')
        if aux.endswith("EOF"):
            aux = aux[:-3]
            dados += aux.encode('utf-8')
            print("Recebido EOF")
            break
        dados += parte
        print(f"Recebendo parte {parte_numero}: {parte[:10]}... ({len(parte)} bytes)")
        parte_numero += 1

    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        novo_nome_arquivo = os.path.join(script_dir, f"recebido_{nome_arquivo}")

        print(f"Tentando salvar o arquivo em {novo_nome_arquivo}")
        with open(novo_nome_arquivo, 'wb') as f:
            f.write(dados)
        print(f"Arquivo salvo como {novo_nome_arquivo}")
    except Exception as e:
        print(f"Erro ao salvar o arquivo: {e}")
    
    return novo_nome_arquivo

def enviar_mensagens(chat_window):
    while True:
        mensagem = chat_window.chat_entry.get()
        chat_window.chat_entry.delete(0, tk.END)
        if mensagem.lower() == 'sair':
            chat_window.client_socket.send("Sair".encode('utf-8'))
            chat_window.window.destroy()
            break
        chat_window.client_socket.send(f"Chat {mensagem}".encode('utf-8'))
        chat_window.chat_log.insert(tk.END, f"Você: {mensagem}\n")

def receber_mensagens(chat_window):
    while True:
        resposta = chat_window.client_socket.recv(1024).decode('utf-8')
        if not resposta:
            break
        if resposta.startswith("Chat "):
            resposta = resposta[5:]
        chat_window.chat_log.config(state='normal')
        chat_window.chat_log.insert(tk.END, f"Servidor: {resposta}\n")
        chat_window.chat_log.config(state='disabled')

def iniciar_chat(client_socket):
    chat_window = ChatWindow(client_socket)
    receber_thread = threading.Thread(target=receber_mensagens, args=(chat_window,))
    receber_thread.start()

class ChatWindow:
    def __init__(self, client_socket):
        self.window = tk.Toplevel(root)
        self.window.title("Chat com Servidor")
        self.client_socket = client_socket

        self.chat_log = scrolledtext.ScrolledText(self.window, state='disabled', width=50, height=20)
        self.chat_log.pack()

        self.chat_entry = tk.Entry(self.window, width=50)
        self.chat_entry.pack()
        self.chat_entry.bind("<Return>", self.send_message)

    def send_message(self, event):
        mensagem = self.chat_entry.get()
        self.client_socket.send(f"Chat {mensagem}".encode('utf-8'))
        self.chat_log.config(state='normal')
        self.chat_log.insert(tk.END, f"Você: {mensagem}\n")
        self.chat_log.config(state='disabled')
        self.chat_entry.delete(0, tk.END)
        if mensagem.lower() == 'sair':
            self.client_socket.send("Sair".encode('utf-8'))
            self.window.destroy()

def handle_arquivo(client_socket):
    # Nova interface: seleção de arquivo
    file_path = filedialog.askopenfilename(title="Selecione o arquivo para baixar do servidor",
                                           filetypes=[("Todos os arquivos", "*.*")])
    if not file_path:
        return
    nome_arquivo = os.path.basename(file_path)
    client_socket.send(f"Arquivo {nome_arquivo}".encode('utf-8'))
    resposta = client_socket.recv(1024).decode('utf-8')
    print(f"Resposta do Servidor: {resposta}")
    messagebox.showinfo("Resposta do Servidor", resposta)

    if "Status: ok" in resposta:
        client_socket.send("Pronto para receber".encode('utf-8'))

        def thread_receber_arquivo():
            novo_nome_arquivo = receber_arquivo(client_socket, nome_arquivo)
            hash_local = calcular_hash(novo_nome_arquivo)
            hash_remoto = resposta.split('Hash: ')[1].split('\n')[0]

            if hash_local == hash_remoto:
                print(f"Arquivo recebido com sucesso como {novo_nome_arquivo} e a integridade foi verificada.")
                messagebox.showinfo("Arquivo", f"Arquivo recebido com sucesso como {novo_nome_arquivo} e a integridade foi verificada.")
            else:
                print("Falha na verificação de integridade do arquivo.")
                messagebox.showerror("Arquivo", "Falha na verificação de integridade do arquivo.")

        threading.Thread(target=thread_receber_arquivo).start()
    else:
        messagebox.showerror("Arquivo", "Arquivo não encontrado no servidor.")

def handle_sair(client_socket):
    client_socket.send("Sair".encode('utf-8'))
    client_socket.close()
    root.destroy()

def main():
    global root
    # Janela para pedir IP e porta
    ip_port_root = tk.Tk()
    ip_port_root.title("Conectar ao Servidor TCP")
    ip_port_root.geometry("300x150")

    tk.Label(ip_port_root, text="Endereço IP do Servidor:").pack(pady=5)
    ip_entry = tk.Entry(ip_port_root)
    ip_entry.insert(0, "127.0.0.1")
    ip_entry.pack(pady=2)

    tk.Label(ip_port_root, text="Porta:").pack(pady=5)
    port_entry = tk.Entry(ip_port_root)
    port_entry.insert(0, "9999")
    port_entry.pack(pady=2)

    def conectar():
        ip = ip_entry.get()
        try:
            port = int(port_entry.get())
        except ValueError:
            messagebox.showerror("Erro", "Porta inválida!")
            return
        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.connect((ip, port))
        except Exception as e:
            messagebox.showerror("Erro", f"Não foi possível conectar: {e}")
            return
        ip_port_root.destroy()
        print("Conectado ao servidor.")

        # Janela principal
        global root
        root = tk.Tk()
        root.title("Cliente TCP")
        root.geometry("400x300")

        sair_button = tk.Button(root, text="Sair", command=lambda: handle_sair(client_socket))
        sair_button.pack(pady=10)

        arquivo_button = tk.Button(root, text="Arquivo", command=lambda: handle_arquivo(client_socket))
        arquivo_button.pack(pady=10)

        chat_button = tk.Button(root, text="Chat", command=lambda: iniciar_chat(client_socket))
        chat_button.pack(pady=10)

        root.mainloop()

    conectar_button = tk.Button(ip_port_root, text="Conectar", command=conectar)
    conectar_button.pack(pady=10)
    ip_port_root.mainloop()

if __name__ == "__main__":
    main()
