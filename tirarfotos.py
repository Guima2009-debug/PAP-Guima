import cv2
import os
import time

# Criar a pasta se ela não existir
if not os.path.exists('fotos_treino'):
    os.makedirs('fotos_treino')

# Carrega o detetor de rostos
detector_rostos = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

# Liga a webcam
webcam = cv2.VideoCapture(0)

# =========================================================================
# ATENÇÃO: Muda este ID para cada nova pessoa! (Tu és o 1, o próximo é o 2...)
# =========================================================================
id_utilizador = 2  
contador = 0
total_fotos = 30  

print(f"Prepara-te para registar o Utilizador ID {id_utilizador}!")
print("Olha para a câmara e mexe ligeiramente a cabeça.")

# Variável para dar um pequeno intervalo de tempo entre capturas (evita tirar 30 fotos iguais em 1 segundo)
ultimo_tempo_foto = time.time()

while True:
    sucesso, frame = webcam.read()
    if not sucesso:
        print("Erro: Não foi possível aceder à webcam.")
        break

    imagem_cinzenta = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    rostos = detector_rostos.detectMultiScale(imagem_cinzenta, scaleFactor=1.3, minNeighbors=5)

    agora = time.time()

    for (x, y, largura, altura) in rostos:
        # Só tira foto se já tiver passado 0.1 segundos desde a última (dá tempo para mexeres a cabeça)
        if agora - ultimo_tempo_foto > 0.1 and contador < total_fotos:
            contador += 1
            
            # Recorta apenas a região do rosto
            rosto_recortado = imagem_cinzenta[y:y+altura, x:x+largura]
            
            # Guarda a foto na pasta com o padrão exato que o teu reconhecedor lê
            caminho_foto = f"fotos_treino/utilizador.{id_utilizador}.{contador}.jpg"
            cv2.imwrite(caminho_foto, rosto_recortado)
            
            ultimo_tempo_foto = agora

        # Desenha o quadrado azul e o progresso no ecrã
        cv2.rectangle(frame, (x, y), (x + largura, y + altura), (255, 0, 0), 2)
        cv2.putText(frame, f"Foto {contador}/{total_fotos}", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)

    # MOSTRAR JANELA: Sempre ativa a 30fps
    cv2.imshow('PAP - Registo de Novo Utilizador', frame)

    # O segredo está aqui: o waitKey(1) controla a janela principal cá fora!
    tecla = cv2.waitKey(1) & 0xFF
    
    # Condição de saída: Termina se chegar às fotos pretendidas ou se premires 'q'
    if contador >= total_fotos or tecla == ord('q'):
        break

print(f"\n[SUCESSO]: {contador} fotos guardadas com sucesso para o ID {id_utilizador}!")
webcam.release()
cv2.destroyAllWindows()