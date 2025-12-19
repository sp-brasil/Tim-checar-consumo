import os
import re
import pdfplumber
from flask import Flask, request, jsonify

app = Flask(__name__)

def parse_text(text):
    """
    Versão 10: Busca Global. Ignora quebras de linha e foca na proximidade de dados.
    """
    # 1. Pré-processamento: remove aspas e limpa espaços excessivos
    clean_text = re.sub(r'\s+', ' ', text.replace('"', '').replace("'", ""))
    
    # 2. Extração do Telefone (Busca qualquer número de 10-13 dígitos após 'No.')
    phone_number = "Não encontrado"
    phone_match = re.search(r'No\.\s*\+?(55)?(\d{10,11})', clean_text)
    if phone_match:
        phone_number = phone_match.group(2) # Pega apenas o número principal

    # 3. Volume do Cabeçalho como Fallback (Backup de segurança)
    header_total = 0.0
    header_match = re.search(r'Volume total:\s*([\d,.]+)', clean_text, re.IGNORECASE)
    if header_match:
        try:
            header_total = float(header_match.group(1).replace(',', ''))
        except: pass

    # 4. Soma de Consumo por Proximidade (Data -> Próximo MB)
    total_sum = 0.0
    chile_sum = 0.0
    
    # Encontra todas as datas no arquivo
    all_dates = list(re.finditer(r'\d{2}/\d{2}/\d{4}', clean_text))
    
    for i in range(len(all_dates)):
        start_idx = all_dates[i].start()
        # Define o fim da busca como a próxima data ou 200 caracteres à frente
        end_idx = all_dates[i+1].start() if i+1 < len(all_dates) else start_idx + 200
        
        chunk = clean_text[start_idx:end_idx].lower()
        
        # Ignora a data de emissão no topo do arquivo
        if i == 0 and ("detalhamento" in chunk or "roaming" in chunk):
            continue

        # Busca o primeiro valor de MB que aparecer após a data
        mb_match = re.search(r'([\d.]+)\s*mb', chunk)
        if mb_match:
            try:
                val = float(mb_match.group(1))
                total_sum += val
                if 'chile' in chunk:
                    chile_sum += val
            except: pass

    # 5. Lógica de Decisão
    # Se a soma deu zero (ex: tabela ilegível), usa o valor do cabeçalho
    final_total = total_sum if total_sum > 0 else header_total
    
    return [{
        "numero": phone_number,
        "consumo_total": f"{final_total:.2f}".replace('.', ','),
        "consumo_chile": f"{chile_sum:.2f}".replace('.', ',')
    }]

@app.route('/processar', methods=['POST'])
def process_pdf():
    if 'file' not in request.files:
        return jsonify({"dados": []}), 200
    file = request.files['file']
    try:
        with pdfplumber.open(file) as pdf:
            full_text = ""
            for page in pdf.pages:
                full_text += (page.extract_text() or "") + "\n"
            
            # Executa a extração
            dados = parse_text(full_text)
            return jsonify({"dados": dados}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=int(os.environ.get("PORT", 5000)))
