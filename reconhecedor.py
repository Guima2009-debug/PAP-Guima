import os
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
from supabase import create_client

BASE_DIR = Path(__file__).resolve().parent
PASTA_TREINO = BASE_DIR / "fotos_treino"
TABELA_ACESSOS = os.getenv("SUPABASE_TABLE", "log_acesso") # Usar log_acesso como vimos
CACIFO_ID = int(os.getenv("CACIFO_ID", "1")) # Qual cacifo esta camera controla por defeito


def criar_cliente_supabase():
    """Cria o cliente Supabase usando variaveis de ambiente."""
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")

    if not supabase_url or not supabase_key:
        raise RuntimeError(
            "Configura SUPABASE_URL e SUPABASE_KEY antes de executar o reconhecedor."
        )

    return create_client(supabase_url, supabase_key)


def registar_acesso_supabase(supabase, nome_utilizador, status, cacifo_id=CACIFO_ID):
    """Regista um acesso na tabela do Supabase."""
    registo = {
        "data_hora": datetime.now().isoformat(),
        "nome_utilizador": nome_utilizador,
        "status": status,
        "cacifo_id": cacifo_id,
    }

    supabase.table(TABELA_ACESSOS).insert(registo).execute()


def obter_dados_treino(pasta):
    """Le as fotos de treino e devolve as imagens e ids dos utilizadores."""
    caminhos_fotos = [
        pasta / ficheiro
        for ficheiro in os.listdir(pasta)
        if ficheiro.lower().endswith(".jpg")
    ]

    amostras_rostos = []
    ids = []

    for caminho_foto in caminhos_fotos:
        imagem_rosto = cv2.imread(str(caminho_foto), cv2.IMREAD_GRAYSCALE)
        id_utilizador = int(caminho_foto.name.split(".")[1])
        amostras_rostos.append(imagem_rosto)
        ids.append(id_utilizador)

    return amostras_rostos, np.array(ids)


def main():
    supabase = criar_cliente_supabase()

    detector_rostos = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )
    reconhecedor = cv2.face.LBPHFaceRecognizer_create()

    print("A treinar o sistema com as tuas fotos... Aguarda um momento.")
    rostos, ids = obter_dados_treino(PASTA_TREINO)
    reconhecedor.train(rostos, ids)
    print("Treino concluido com sucesso!")

    # =========================================================================
    # ATENÇÃO: Atualiza aqui os nomes para as pessoas reais!
    # =========================================================================
    nomes = {
        1: "Rodrigo",  # ID 1 -> Cacifo 1
        2: "Afonso",  # ID 2 -> Cacifo 2 (Muda "Pessoa2" para o nome real)
        3: "Desconhecido"
    }
    
    # Variaveis de controlo inteligentes para evitar spam na base de dados
    ultimo_registo_tempo = None
    ultimo_status = ""

    webcam = cv2.VideoCapture(0)

    while True:
        sucesso, frame = webcam.read()
        if not sucesso:
            break

        imagem_cinzenta = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        rostos_detetados = detector_rostos.detectMultiScale(
            imagem_cinzenta,
            scaleFactor=1.3,
            minNeighbors=5,
        )

        for (x, y, largura, altura) in rostos_detetados:
            rosto_recortado = imagem_cinzenta[y : y + altura, x : x + largura]
            id_previsto, confianca = reconhecedor.predict(rosto_recortado)

            if confianca < 60:
                nome_base = nomes.get(id_previsto, "Desconhecido")
                
                # LOGICA DINAMICA DE TEXTO NA TELA:
                # Mostra o ID previsto como o numero do cacifo
                if nome_base != "Desconhecido":
                    nome_utilizador = f"{nome_base} (Cacifo {id_previsto})"
                else:
                    nome_utilizador = nome_base
                
                cor_quadrado = (0, 255, 0) # Verde
                texto_status = f"Acesso Autorizado: {confianca:.1f}%"
                status = "AUTORIZADO"
            else:
                nome_utilizador = "Desconhecido"
                cor_quadrado = (0, 0, 255) # Vermelho
                texto_status = "Acesso Negado!"
                status = "NEGADO"

            # Desenha o quadrado e os textos na tela da camera
            cv2.rectangle(frame, (x, y), (x + largura, y + altura), cor_quadrado, 2)
            cv2.putText(frame, nome_utilizador, (x, y - 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, cor_quadrado, 2)
            cv2.putText(frame, texto_status, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, cor_quadrado, 1)

            agora = datetime.now()
            
            # LOGICA DE ENVIO SEGURO (INTELIGENTE):
            deve_gravar = False
            if ultimo_registo_tempo is None or status != ultimo_status:
                deve_gravar = True
            elif (agora - ultimo_registo_tempo).total_seconds() > 5:
                deve_gravar = True

            if deve_gravar:
                try:
                    # Envia o nome limpo (sem o texto do cacifo) para a base de dados ficar organizada
                    nome_para_banco = nomes.get(id_previsto, "Desconhecido") if status == "AUTORIZADO" else "Desconhecido"
                    
                    # =========================================================================
                    # LOGICA DINAMICA DE ENVIO PARA O SUPABASE:
                    # Se for autorizado, o cacifo_id passa a ser o proprio ID da pessoa (1 ou 2)
                    # =========================================================================
                    cacifo_dinamico = id_previsto if status == "AUTORIZADO" else CACIFO_ID
                    
                    registar_acesso_supabase(
                        supabase=supabase,
                        nome_utilizador=nome_para_banco,
                        status=status,
                        cacifo_id=cacifo_dinamico, # Envia o cacifo correto!
                    )
                    ultimo_registo_tempo = agora
                    ultimo_status = status
                    print(f"[LOG SUPABASE]: {nome_para_banco} -> {status} no Cacifo {cacifo_dinamico}")
                except Exception as erro:
                    print(f"[ERRO SUPABASE]: Nao foi possivel guardar o log: {erro}")

        cv2.imshow("PAP - Sistema de Seguranca Facial", frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    webcam.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()