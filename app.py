import os
import re
import pdfplumber
from flask import Flask, request, jsonify

app = Flask(__name__)

def parse_text(text):
    """
    Versão 9: Lógica de 'Estado'. Identifica uma data e busca o valor 
    de consumo nas linhas subsequentes até encontrar um MB.
    """
    # 1. Limpeza de caracteres que sujam a extração de tabelas
    text = text.replace('"', '').replace("'", "")
    lines = text.split('\n')
    
    # 2. Extração do Telefone
    phone_number = "Não encontrado"
    phone_match = re.search(r'No\.\s*(\+?\d+)', text)
    if phone_match:
        raw = phone_match.group(1)
        phone_number = raw[3:] if raw.startswith("+55") else raw

    # 3. Volume do Cabeçalho como Fallback Absoluto (Ex: 7997.42MB)
    header_total = 0.0
    header_match = re.search(r'Volume total:\s*([\d,.]+)', text, re.IGNORECASE)
    if header_match:
        try:
            header_total = float(header_match.group(1).replace(',', ''))
        except: pass

    # 4. Processamento de Linhas com 'Memória'
    total_sum = 0.0
    chile_sum = 0.0
    procurando_consumo = False
    linha_com_chile = False

    for line in lines:
        line_clean = line.lower().strip()
        
        # Identifica se a linha tem uma DATA (DD/MM/AAAA)
        data_match = re.search(r'\d{2}/\d{2}/\d{4}', line_clean)
        
        if data_match:
            procurando_consumo = True
            linha_com_chile = 'chile' in line_clean
            # Verifica se já tem MB na mesma linha da data
            mb_na_linha = re.search(r'([\d.]+)\s*mb', line_clean)
            if mb_na_linha:
                val = float(mb_na_linha.group(1))
                total_sum += val
                if linha_com_chile: chile_sum += val
                procurando_consumo = False # Já achou, desliga o alerta
            continue

        # Se estiver em alerta (achou data antes), procura o MB nesta linha
        if procurando_consumo:
            if 'chile' in line_clean: linha_com_chile = True
            
            mb_match = re.search(r'([\d.]+)\s*mb', line_clean)
            if mb_match:
                try:
                    val = float(mb_match.group(1))
                    total_sum += val
                    if linha_com_chile: chile_sum += val
                    procurando_consumo = False # Valor encontrado, desliga alerta
                except: pass

    # 5. Validação Final
    # Se a soma das linhas for muito discrepante ou zero, usa o cabeçalho
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
            return jsonify({"dados": parse_text(full_text)}), 200
    except Exception as e:
        # Retorna o erro real para ajudar no debug
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=int(os.environ.get("PORT", 5000)))
