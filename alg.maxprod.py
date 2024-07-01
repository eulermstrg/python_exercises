import mysql.connector
from fpdf import FPDF


def get_product_data(codigo_produto):
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="madmax00st1",
        database="FICHAS_TECNICAS"
    )
    cursor = conn.cursor()
    query = ("SELECT tipo_tubo, quantidade, tamanho FROM produtos WHERE codigo = %s")
    cursor.execute(query, (codigo_produto,))

    tubos = {}
    for (tipo_tubo, quantidade, tamanho) in cursor:
        if tipo_tubo not in tubos:
            tubos[tipo_tubo] = []
        tubos[tipo_tubo].extend([tamanho + 2] * quantidade)  # Adiciona 2mm a cada tamanho

    cursor.close()
    conn.close()
    return tubos


def cortar_barras(tubos, comprimento_barra):
    barras = []
    tipo_contador = {}

    for tubo_tipo, tamanhos in tubos.items():
        tamanhos.sort(reverse=True)  # Ordenar tamanhos em ordem decrescente
        tipo_contador[tubo_tipo] = tipo_contador.get(tubo_tipo, 0) + 1
        while tamanhos:
            barra_atual = []
            comprimento_restante = comprimento_barra

            for tamanho in tamanhos[:]:
                if tamanho <= comprimento_restante:
                    barra_atual.append(tamanho)
                    comprimento_restante -= tamanho
                    tamanhos.remove(tamanho)

            barras.append((tubo_tipo, barra_atual, comprimento_restante, tipo_contador[tubo_tipo]))
            tipo_contador[tubo_tipo] += 1

    return barras


def calcular_percentual_sobra(comprimento_barra, sobra):
    return (sobra / comprimento_barra) * 100


def calcular_desperdicio_total(barras_cortadas, comprimento_barra):
    total_sobra = sum(sobra for _, _, sobra, _ in barras_cortadas)
    total_barras = len(barras_cortadas)
    desperdicio_total = (total_sobra / (total_barras * comprimento_barra)) * 100
    return desperdicio_total


def analisar_intervalos(codigo_produto, intervalos):
    comprimento_barra = 6000
    produto_data = get_product_data(codigo_produto)
    resultados = []

    for (inicio, fim) in intervalos:
        melhor_quantidade = None
        menor_desperdicio = float('inf')

        for quantidade in range(inicio, fim + 1):
            tubos = {}
            for tipo, tamanhos in produto_data.items():
                tubos[tipo] = tamanhos * quantidade

            barras_cortadas = cortar_barras(tubos, comprimento_barra)
            desperdicio_total = calcular_desperdicio_total(barras_cortadas, comprimento_barra)

            if desperdicio_total < menor_desperdicio:
                menor_desperdicio = desperdicio_total
                melhor_quantidade = quantidade

        resultados.append((inicio, fim, melhor_quantidade, menor_desperdicio))

    return resultados


def gerar_pdf(resultados, codigo_produto):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    # Título
    pdf.cell(200, 10, f"Análise de Produção para o Produto {codigo_produto}", ln=True, align='C')
    pdf.ln(10)

    # Resultados
    for inicio, fim, quantidade, desperdicio in resultados:
        detalhes = f"Lote de {inicio} a {fim}: ideal de {quantidade} peças com desperdício de {desperdicio:.2f}%"
        pdf.multi_cell(0, 10, detalhes, border=0)

    # Melhor resultado
    melhor_lote = min(resultados, key=lambda x: x[3])
    melhor_detalhes = (f"\nEm resumo, o ideal para produzir com menor desperdício é de "
                       f"{melhor_lote[2]} peças com o percentual de {melhor_lote[3]:.2f}%")
    pdf.multi_cell(0, 10, melhor_detalhes, border=0)

    # Nome do arquivo PDF
    nome_arquivo = f"analise_{codigo_produto}.pdf"
    pdf.output(nome_arquivo)
    return nome_arquivo


def main():
    codigo_produto = input("Digite o código do produto: ")

    intervalos = [(1, 25), (26, 50), (51, 75), (76, 100)]

    resultados = analisar_intervalos(codigo_produto, intervalos)

    nome_arquivo = gerar_pdf(resultados, codigo_produto)
    print(f"PDF gerado com sucesso: {nome_arquivo}")


if __name__ == "__main__":
    main()
