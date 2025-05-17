# -*- coding: utf-8 -*-
"""
Created on Mon Apr  7 18:35:30 2025

@author: Luciano Lulio
"""

from flask import Flask, render_template, request, send_from_directory
import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
from math import ceil
from datetime import datetime
import os

app = Flask(__name__)

# Verificação de data de expiração
data_expiracao = datetime(2026, 6, 1)
data_atual = datetime.now()
if data_atual > data_expiracao:
    raise Exception("Licença vencida. Contato: Luciano Lulio – 17 981213377")

def extrair_campos_descricao(descricao):
    dados = {}
    match_barra = re.search(r"Código de barras:\s*(\d+)", descricao)
    dados["barra"] = match_barra.group(1) if match_barra else "N/A"

    match_peso = re.search(r"Peso do Produto:\s*([\d,]+)g", descricao)
    if match_peso:
        peso_gramas = float(match_peso.group(1).replace(",", "."))
        dados["peso"] = round(peso_gramas / 1000, 3)
    else:
        dados["peso"] = "N/A"

    match_medidas = re.search(r"L:\s*([\d,]+)\s*x\s*C:\s*([\d,]+)\s*x\s*A:\s*([\d,]+)", descricao)
    if match_medidas:
        dados["largura"] = ceil(float(match_medidas.group(1).replace(",", ".")))
        dados["comprimento"] = ceil(float(match_medidas.group(2).replace(",", ".")))
        dados["altura"] = ceil(float(match_medidas.group(3).replace(",", ".")))
    else:
        dados["largura"] = dados["comprimento"] = dados["altura"] = "N/A"

    return dados

def extrair_dados_produto(link_produto):
    produto_response = requests.get(link_produto)
    if produto_response.status_code == 200:
        produto_soup = BeautifulSoup(produto_response.content, 'html.parser')
        nome = produto_soup.find('div', class_='title-icon').text.strip()
        preco_anterior = produto_soup.find('div', class_='valor_anterior')
        preco_anterior = preco_anterior.text.replace('De:', '').strip() if preco_anterior else 'N/A'

        valor_div = produto_soup.find('div', class_='valor_anterior')
        preco = valor_div.find_next_sibling('div', class_='valor').text.strip() if valor_div else 'N/A'

        descricao = produto_soup.find('div', class_='descricao')
        descricao = descricao.text.strip().replace('\r', ' ') if descricao else 'N/A'

        campos_extraidos = extrair_campos_descricao(descricao)

        imagens = produto_soup.find_all('div', class_=['item zoomer', 'item zoomer active'])
        fotos_produto = ','.join([img.find('a')['href'] for img in imagens])

        ref = produto_soup.find('div', class_='ref').text.strip() if produto_soup.find('div', class_='ref') else 'N/A'
        categoria = produto_soup.find('div', class_='bread').find_all('a')[-2].text.strip() if produto_soup.find('div', class_='bread') else 'N/A'

        return {
            'Categoria': categoria,
            'Ref': ref,
            'Nome': nome,
            'Preço Anterior': preco_anterior,
            'Preço': preco,
            'Descrição': descricao,
            'Fotos': fotos_produto,
            'linkProduto': link_produto,
            **campos_extraidos
        }
    return None

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        links = request.form['links'].splitlines()
        dados_coletados = []

        for link in links:
            if link.strip():
                dados = extrair_dados_produto(link.strip())
                if dados:
                    dados_coletados.append(dados)

        if dados_coletados:
            df = pd.DataFrame(dados_coletados)
            caminho_excel = os.path.join('static', 'lista_produtos.xlsx')
            df.to_excel(caminho_excel, index=False)
            return render_template('sucesso.html', arquivo='lista_produtos.xlsx')
        else:
            return "Nenhum dado válido foi encontrado."

    return render_template('index.html')

@app.route('/download/<arquivo>')
def download(arquivo):
    return send_from_directory('static', arquivo, as_attachment=True)

