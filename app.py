import os
import re
import pdfplumber
from flask import Flask, request, jsonify

app = Flask(__name__)

def parse_text(text):
    """
    Versão 8: Abordagem de fluxo contínuo. Busca o consumo em uma 'janela' 
    após cada data, ignorando quebras de linha e aspas.
    """
    # 1. Limpeza de aspas para evitar quebras no regex
    text = text.replace('"', '').replace("'", "")
    
    # 2. Extração do Telefone (Padrão: No. +55...)
    phone_pattern = re.compile(r'No\.\s*(\+?\d+)')
    phone_match = phone_pattern.search(text)
    phone_number = "Não encontrado"
    if phone_match:
        phone_raw = phone_match.group(1)
        phone_number = phone_raw[3:] if phone_raw.startswith("+55") else phone_raw
    
    # 3. Volume do Cabeçalho como Backup (Ex: 7997.42MB)
    header_volume = 0.0
    header_match = re.search(r'Volume total:\s*([\d,.]+)', text, re.IGNORECASE)
    if header_match:
        try:
            header_volume = float(header_match.group(1).replace(',', ''))
        except: pass

    # 4. Processamento por 'Janelas' de Data
    total_sum = 0.0
    chile_sum = 0.0
    
    # Localiza todas as datas (DD/MM/AAAA) e suas posições no texto
    date_matches = list(re.finditer(r'(\d{2}/\d{2}/\d{4})', text))
    
    for i in range(len(date_matches)):
        start_pos = date_matches[i].start()
        # A janela vai desta data até a próxima data (ou fim do texto)
        end_pos = date_matches[i+1].start() if i+1 < len(date_matches) else len(text)
        window_text = text[start_pos:end_pos].lower()
        
        # Ignora a primeira data se for a do cabeçalho (geralmente isolada no topo)
        if i == 0 and "detalhamento" not in window_text:
             # Se a primeira data for apenas a data de emissão do relatório, pulamos
             if "roaming" in window_text or "detalhamento" in window_text:
                 continue

        # Busca valores de MB dentro desta janela (ex: 48.99mb ou 48.99 mb)
        mb_match = re.search(r'([\d.]+)\s*mb', window_text)
        if mb_match:
            try:
                valor = float(mb_match.group(1))
                total_sum += valor
                if 'chile' in window_text:
                    chile_sum += valor
            except: pass

    # 5. Validação e Formatação
    # Se a soma das janelas falhar, usamos o cabeçalho como valor total
    final_total = total_sum if total_sum > 0 else header_volume
    
    formatted_total = f"{final_total:.2f}".replace('.', ',')
    formatted_chile = f"{chile_sum:.2f}".replace('.', ',')

    return [{
        "numero": phone_number,
        "consumo_total": formatted_total,
        "consumo_chile": formatted_chile
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
            if not full_text.strip():
                return jsonify({"error": "PDF sem texto extraível"}), 500
            return jsonify({"dados": parse_text(full_text)}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=int(os.environ.get("PORT", 5000)))
