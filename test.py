import mysql.connector
from fpdf import FPDF
import tkinter as tk
from tkinter import messagebox
from tkinter import ttk

def get_product_data(codigo_produto):
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="madmax00st1",
        database="FICHAS_TECNICAS"
    )
    cursor = conn.cursor()
    query = ("SELECT tipo_tubo, quantidade, tamanho, cl1 FROM produtos_v2 WHERE codigo = %s")
    cursor.execute(query, (codigo_produto,))

    tubos = {0: {}, 1: {}}
    for (tipo_tubo, quantidade, tamanho, cl1) in cursor:
        if tipo_tubo not in tubos[cl1]:
            tubos[cl1][tipo_tubo] = []
        tubos[cl1][tipo_tubo].extend([(tamanho, tamanho + 2)] * quantidade)  # Adicionar 2mm a cada tamanho

    cursor.close()
    conn.close()
    return tubos

def cortar_barras(tubos):
    barras = []
    tipo_contador = {0: {}, 1: {}}

    for cl1, tipos_tubos in tubos.items():
        limite_barra = 5700 if cl1 == 1 else 6000

        for tubo_tipo, tamanhos in tipos_tubos.items():
            tamanhos.sort(key=lambda x: x[1], reverse=True)  # Ordenar tamanhos em ordem decrescente pelo tamanho com 2mm

            tipo_contador[cl1][tubo_tipo] = tipo_contador[cl1].get(tubo_tipo, 0) + 1

            while tamanhos:
                barra_atual = []
                comprimento_restante = limite_barra

                for tamanho_real, tamanho_com_folga in tamanhos[:]:
                    if tamanho_com_folga <= comprimento_restante:
                        barra_atual.append(tamanho_real)
                        comprimento_restante -= tamanho_com_folga
                        tamanhos.remove((tamanho_real, tamanho_com_folga))

                barras.append((tubo_tipo, barra_atual, comprimento_restante, tipo_contador[cl1][tubo_tipo], cl1))
                tipo_contador[cl1][tubo_tipo] += 1

    return barras

def calcular_percentual_sobra(comprimento_barra, sobra):
    return (sobra / comprimento_barra) * 100

def gerar_pdf(barras_cortadas, codigo_produto, quantidade, numero_pedido, item):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    # Título
    pdf.cell(200, 10, f"Relatório de Cortes para o Produto {codigo_produto} (Quantidade: {quantidade})", ln=True, align='C')
    pdf.ln(10)

    desperdicio_por_tipo = {}
    cortes_por_tipo = {}
    consumo_por_tipo = {}

    for idx, (tipo, cortes, sobra, barra_id, cl1) in enumerate(barras_cortadas):
        comprimento_barra = 5700 if cl1 == 1 else 6000
        percentual_sobra = calcular_percentual_sobra(comprimento_barra, sobra)
        # Detalhes da barra
        detalhes_barra = f"Barra {barra_id} ({tipo}, CL1={cl1}): Cortes = {cortes}, Sobra = {sobra} mm ({percentual_sobra:.2f}%)"
        pdf.multi_cell(0, 10, detalhes_barra, border=0)

        # Acumular dados para cálculo da média de desperdício
        if tipo not in desperdicio_por_tipo:
            desperdicio_por_tipo[tipo] = 0
            cortes_por_tipo[tipo] = 0
            consumo_por_tipo[tipo] = 0
        desperdicio_por_tipo[tipo] += sobra
        cortes_por_tipo[tipo] += 1
        consumo_por_tipo[tipo] += 1

    pdf.ln(10)

    # Calcular e imprimir a média de desperdício por tipo de tubo
    for tipo, desperdicio_total in desperdicio_por_tipo.items():
        media_desperdicio = desperdicio_total / cortes_por_tipo[tipo]
        comprimento_barra = 5700 if cl1 == 1 else 6000
        percentual_media_desperdicio = calcular_percentual_sobra(comprimento_barra, media_desperdicio)
        detalhes_media = f"Média de desperdício para {tipo}: {media_desperdicio:.2f} mm ({percentual_media_desperdicio:.2f}%)"
        pdf.multi_cell(0, 10, detalhes_media, border=0)

    pdf.ln(10)

    # Imprimir o total de consumo por tipo de tubo
    for tipo, consumo_total in consumo_por_tipo.items():
        detalhes_consumo = f"Total de consumo para {tipo}: {consumo_total} unidades"
        pdf.multi_cell(0, 10, detalhes_consumo, border=0)

    # Nome do arquivo PDF
    nome_arquivo = f"{numero_pedido}_{item}.pdf"
    pdf.output(nome_arquivo)
    return nome_arquivo

def main():
    # Função para processar os dados de entrada
    def processar_dados():
        codigo_produto = codigo_entry.get()
        quantidade = int(quantidade_entry.get())
        numero_pedido = pedido_entry.get()
        item = item_entry.get()

        # Buscar dados do produto no banco de dados
        produto_data = get_product_data(codigo_produto)

        # Multiplicar tamanhos pelo número de produtos a serem produzidos
        tubos = {0: {}, 1: {}}
        for cl1, tipos in produto_data.items():
            for tipo, tamanhos in tipos.items():
                if tipo not in tubos[cl1]:
                    tubos[cl1][tipo] = []
                tubos[cl1][tipo].extend(tamanhos * quantidade)

        # Calcular a melhor combinação de cortes
        barras_cortadas = cortar_barras(tubos)

        # Gerar PDF com o resultado
        nome_arquivo = gerar_pdf(barras_cortadas, codigo_produto, quantidade, numero_pedido, item)
        messagebox.showinfo("Sucesso", f"PDF gerado com sucesso: {nome_arquivo}")

    # Criar a janela principal
    root = tk.Tk()
    root.title("Amplio Móveis Exteriores")
    root.geometry("400x300")

    # Configurar o grid
    root.columnconfigure(0, weight=1)
    root.columnconfigure(1, weight=3)

    # Título
    title_label = tk.Label(root, text="Novo cálculo produtivo", font=("Helvetica", 16))
    title_label.grid(row=0, column=0, columnspan=2, pady=10)

    # Campos de entrada
    tk.Label(root, text="Código do Produto:").grid(row=1, column=0, sticky=tk.E, padx=10, pady=5)
    codigo_entry = tk.Entry(root)
    codigo_entry.grid(row=1, column=1, pady=5, sticky=tk.W+tk.E, padx=(0, 20))

    tk.Label(root, text="Quantidade:").grid(row=2, column=0, sticky=tk.E, padx=10, pady=5)
    quantidade_entry = tk.Entry(root)
    quantidade_entry.grid(row=2, column=1, pady=5, sticky=tk.W+tk.E, padx=(0, 20))

    tk.Label(root, text="Número do Pedido:").grid(row=3, column=0, sticky=tk.E, padx=10, pady=5)
    pedido_entry = tk.Entry(root)
    pedido_entry.grid(row=3, column=1, pady=5, sticky=tk.W+tk.E, padx=(0, 20))

    tk.Label(root, text="Item:").grid(row=4, column=0, sticky=tk.E, padx=10, pady=5)
    item_entry = tk.Entry(root)
    item_entry.grid(row=4, column=1, pady=5, sticky=tk.W+tk.E, padx=(0, 20))

    # Botões
    button_frame = tk.Frame(root)
    button_frame.grid(row=5, column=0, columnspan=2, pady=10)

    tk.Button(button_frame, text="Cancelar", command=root.quit).pack(side=tk.LEFT, padx=5)
    tk.Button(button_frame, text="Confirmar", command=processar_dados).pack(side=tk.LEFT, padx=5)

    # Iniciar o loop principal da interface gráfica
    root.mainloop()

if __name__ == "__main__":
    main()
