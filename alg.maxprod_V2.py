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
            tamanhos.sort(key=lambda x: x[1],
                          reverse=True)  # Ordenar tamanhos em ordem decrescente pelo tamanho com 2mm

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


def gerar_analise_producao_pdf(lotes, codigo_produto, numero_pedido, item):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    # Título
    pdf.cell(200, 10, f"Análise de Produção para o Produto {codigo_produto}", ln=True, align='C')
    pdf.ln(10)

    for lote in lotes:
        pdf.cell(200, 10,
                 f"Lote de {lote['intervalo']}: ideal de {lote['ideal']} peças com desperdício de {lote['desperdicio']:.2f}%",
                 ln=True)
        pdf.ln(5)

    melhor_lote = min(lotes, key=lambda x: x['desperdicio'])
    pdf.ln(10)
    pdf.cell(200, 10,
             f"Em resumo, o ideal para produzir com menor desperdício é de {melhor_lote['ideal']} peças com o percentual de {melhor_lote['desperdicio']:.2f}%",
             ln=True)

    pdf.ln(10)
    pdf.cell(200, 10, f"Quantidade de barras gastas por tipo de tubo para o melhor lote:", ln=True)
    pdf.ln(10)

    for tipo, qtd in melhor_lote['barras_por_tipo'].items():
        pdf.cell(200, 10, f"Tipo {tipo}: {qtd} barras", ln=True)
        pdf.ln(5)

    # Nome do arquivo PDF
    nome_arquivo = f"{numero_pedido}_{item}.pdf"
    pdf.output(nome_arquivo)
    return nome_arquivo


def calcular_lotes(codigo_produto):
    produto_data = get_product_data(codigo_produto)
    lotes = []

    intervalos = [(1, 25), (26, 50), (51, 75), (76, 100)]

    for intervalo in intervalos:
        melhor_lote = {'quantidade': intervalo, 'ideal': 0, 'desperdicio': float('inf'), 'barras_por_tipo': {}}

        for quantidade in range(intervalo[0], intervalo[1] + 1):
            tubos = {0: {}, 1: {}}
            for cl1, tipos in produto_data.items():
                for tipo, tamanhos in tipos.items():
                    if tipo not in tubos[cl1]:
                        tubos[cl1][tipo] = []
                    tubos[cl1][tipo].extend(tamanhos * quantidade)

            barras_cortadas = cortar_barras(tubos)
            desperdicio_total = sum(sobra for tipo, cortes, sobra, barra_id, cl1 in barras_cortadas)
            comprimento_total = sum(
                5700 if cl1 == 1 else 6000 for tipo, cortes, sobra, barra_id, cl1 in barras_cortadas)
            percentual_desperdicio = (desperdicio_total / comprimento_total) * 100

            if percentual_desperdicio < melhor_lote['desperdicio']:
                melhor_lote['ideal'] = quantidade
                melhor_lote['desperdicio'] = percentual_desperdicio
                melhor_lote['barras_por_tipo'] = {tipo: sum(1 for t, c, s, b, cl in barras_cortadas if t == tipo) for
                                                  tipo in set(t for t, c, s, b, cl in barras_cortadas)}

        lotes.append({
            'intervalo': f"{intervalo[0]} a {intervalo[1]}",
            'ideal': melhor_lote['ideal'],
            'desperdicio': melhor_lote['desperdicio'],
            'barras_por_tipo': melhor_lote['barras_por_tipo']
        })

    return lotes


def main():
    def processar_dados():
        codigo_produto = codigo_entry.get()
        numero_pedido = pedido_entry.get()
        item = item_entry.get()

        lotes = calcular_lotes(codigo_produto)
        nome_arquivo = gerar_analise_producao_pdf(lotes, codigo_produto, numero_pedido, item)
        messagebox.showinfo("Sucesso", f"PDF gerado com sucesso: {nome_arquivo}")

    root = tk.Tk()
    root.title("Amplio Móveis Exteriores")
    root.geometry("400x300")

    root.columnconfigure(0, weight=1)
    root.columnconfigure(1, weight=3)

    title_label = tk.Label(root, text="Novo cálculo produtivo", font=("Helvetica", 16))
    title_label.grid(row=0, column=0, columnspan=2, pady=10)

    tk.Label(root, text="Código do Produto:").grid(row=1, column=0, sticky=tk.E, padx=10, pady=5)
    codigo_entry = tk.Entry(root)
    codigo_entry.grid(row=1, column=1, pady=5, sticky=tk.W + tk.E, padx=(0, 20))

    tk.Label(root, text="Número do Pedido:").grid(row=2, column=0, sticky=tk.E, padx=10, pady=5)
    pedido_entry = tk.Entry(root)
    pedido_entry.grid(row=2, column=1, pady=5, sticky=tk.W + tk.E, padx=(0, 20))

    tk.Label(root, text="Item:").grid(row=3, column=0, sticky=tk.E, padx=10, pady=5)
    item_entry = tk.Entry(root)
    item_entry.grid(row=3, column=1, pady=5, sticky=tk.W + tk.E, padx=(0, 20))

    button_frame = tk.Frame(root)
    button_frame.grid(row=4, column=0, columnspan=2, pady=10)

    tk.Button(button_frame, text="Cancelar", command=root.quit).pack(side=tk.LEFT, padx=5)
    tk.Button(button_frame, text="Confirmar", command=processar_dados).pack(side=tk.LEFT, padx=5)

    root.mainloop()


if __name__ == "__main__":
    main()
