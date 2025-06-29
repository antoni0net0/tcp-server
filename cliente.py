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



class ChatWindow:
    def __init__(self, client_socket, root):
        self.window = tk.Toplevel(root)
        self.window.title("Chat com Servidor")
        self.client_socket = client_socket
        self.running = True

        self.chat_log = scrolledtext.ScrolledText(self.window, state='disabled', width=50, height=20)
        self.chat_log.pack()

        self.chat_entry = tk.Entry(self.window, width=50)
        self.chat_entry.pack()
        self.chat_entry.bind("<Return>", self.send_message)

        # Fecha a referência global ao fechar a janela
        self.window.protocol("WM_DELETE_WINDOW", self.close_window)

        # Thread para receber mensagens
        self.receive_thread = threading.Thread(target=self.receber_mensagens, daemon=True)
        self.receive_thread.start()

    def receber_mensagens(self):
        while self.running:
            try:
                resposta = self.client_socket.recv(1024).decode('utf-8')
                if not resposta:
                    break
                if resposta.startswith("Chat "):
                    resposta = resposta[5:]
                self.chat_log.config(state='normal')
                self.chat_log.insert(tk.END, f"Servidor: {resposta}\n")
                self.chat_log.config(state='disabled')
                if resposta.lower().startswith("sair"):
                    break
            except Exception:
                break
        self.close_window()

    def send_message(self, event):
        mensagem = self.chat_entry.get()
        if not mensagem.strip():
            return
        try:
            # Sempre envie com delimitador \n
            self.client_socket.send(f"Chat {mensagem}\n".encode('utf-8'))
            self.chat_log.config(state='normal')
            self.chat_log.insert(tk.END, f"Você: {mensagem}\n")
            self.chat_log.config(state='disabled')
            self.chat_entry.delete(0, tk.END)
            if mensagem.lower() == 'sair':
                self.client_socket.send("Sair\n".encode('utf-8'))
                self.running = False
                self.close_window()
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao enviar mensagem: {e}")

    def close_window(self):
        self.running = False
        try:
            self.window.destroy()
        except Exception:
            pass
        if hasattr(iniciar_chat, 'chat_window'):
            iniciar_chat.chat_window = None

# Função para iniciar o chat (garante só uma janela)
def iniciar_chat(client_socket):
    global root
    if hasattr(iniciar_chat, 'chat_window') and iniciar_chat.chat_window is not None:
        try:
            if iniciar_chat.chat_window.window.winfo_exists():
                iniciar_chat.chat_window.window.lift()
                return
        except Exception:
            pass
    iniciar_chat.chat_window = ChatWindow(client_socket, root)

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
    ip_port_root.geometry("420x260")
    ip_port_root.configure(bg="#222831")

    title_label = tk.Label(ip_port_root, text="Cliente TCP", font=("Segoe UI", 18, "bold"), fg="#00adb5", bg="#222831")
    title_label.pack(pady=(15, 5))

    frame = tk.Frame(ip_port_root, bg="#222831")
    frame.pack(pady=5)

    tk.Label(frame, text="Endereço IP do Servidor:", fg="#eeeeee", bg="#222831", font=("Segoe UI", 10)).grid(row=0, column=0, sticky="w", pady=2)
    ip_entry = tk.Entry(frame, font=("Segoe UI", 10), width=18)
    ip_entry.insert(0, "127.0.0.1")
    ip_entry.grid(row=0, column=1, pady=2, padx=5)

    tk.Label(frame, text="Porta:", fg="#eeeeee", bg="#222831", font=("Segoe UI", 10)).grid(row=1, column=0, sticky="w", pady=2)
    port_entry = tk.Entry(frame, font=("Segoe UI", 10), width=8)
    port_entry.insert(0, "9999")
    port_entry.grid(row=1, column=1, pady=2, padx=5, sticky="w")

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
        root.geometry("600x480")
        root.configure(bg="#222831")

        title = tk.Label(root, text="Cliente TCP", font=("Segoe UI", 18, "bold"), fg="#00adb5", bg="#222831")
        title.pack(pady=(15, 5))

        button_frame = tk.Frame(root, bg="#222831")
        button_frame.pack(pady=10)

        sair_button = tk.Button(button_frame, text="Sair", command=lambda: handle_sair(client_socket), font=("Segoe UI", 12), bg="#393e46", fg="#eeeeee", width=12, relief="flat", activebackground="#00adb5", activeforeground="#222831")
        sair_button.grid(row=0, column=0, padx=10, pady=5)

        arquivo_button = tk.Button(button_frame, text="Arquivo", command=lambda: handle_arquivo(client_socket), font=("Segoe UI", 12), bg="#393e46", fg="#eeeeee", width=12, relief="flat", activebackground="#00adb5", activeforeground="#222831")
        arquivo_button.grid(row=0, column=1, padx=10, pady=5)

        chat_button = tk.Button(button_frame, text="Chat", command=lambda: iniciar_chat(client_socket), font=("Segoe UI", 12), bg="#393e46", fg="#eeeeee", width=12, relief="flat", activebackground="#00adb5", activeforeground="#222831")
        chat_button.grid(row=0, column=2, padx=10, pady=5)

        # Área de log para feedback
        log_frame = tk.Frame(root, bg="#222831")
        log_frame.pack(pady=10)
        log_label = tk.Label(log_frame, text="Log de Operações", font=("Segoe UI", 10, "bold"), fg="#00adb5", bg="#222831")
        log_label.pack(anchor="w")
        log_text = scrolledtext.ScrolledText(log_frame, state='disabled', width=80, height=18, font=("Consolas", 11), bg="#393e46", fg="#eeeeee", relief="flat")
        log_text.pack()

        # Redirecionar prints para o log
        class PrintLogger:
            def write(self, msg):
                log_text.config(state='normal')
                log_text.insert(tk.END, msg)
                log_text.see(tk.END)
                log_text.config(state='disabled')
            def flush(self):
                pass
        import sys
        sys.stdout = PrintLogger()
        sys.stderr = PrintLogger()

        root.mainloop()

    conectar_button = tk.Button(ip_port_root, text="Conectar", command=conectar, font=("Segoe UI", 12, "bold"), bg="#00adb5", fg="#222831", relief="flat", width=15)
    conectar_button.pack(pady=18)
    ip_port_root.mainloop()

if __name__ == "__main__":
    main()
