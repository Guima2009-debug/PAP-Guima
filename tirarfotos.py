import cv2
import os

# Criar a pasta se ela não existir
if not os.path.exists('fotos_treino'):
    os.makedirs('fotos_treino')

# Carrega o detetor de rostos
detector_rostos = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

# Liga a webcam
webcam = cv2.VideoCapture(0)

# Define o ID do utilizador (Tu vais ser o ID 1)
id_utilizador = 1
contador = 0
total_fotos = 30 # Vamos tirar 30 fotos para ele aprender bem

print("Prepara-te! Olha para a câmara e mexe ligeiramente a cabeça.")
print("A tirar fotos automaticamente...")

while True:
    sucesso, frame = webcam.read()
    if not sucesso:
        break

    imagem_cinzenta = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    rostos = detector_rostos.detectMultiScale(imagem_cinzenta, scaleFactor=1.3, minNeighbors=5)

    for (x, y, largura, altura) in rostos:
        contador += 1
        
        # Recorta apenas a região do rosto
        rosto_recortado = imagem_cinzenta[y:y+altura, x:x+largura]
        
        # Guarda a foto na pasta com um nome padronizado: utilizador.ID.numero_da_foto.jpg
        caminho_foto = f"fotos_treino/utilizador.{id_utilizador}.{contador}.jpg"
        cv2.imwrite(caminho_foto, rosto_recortado)

        # Desenha o quadrado no ecrã para veres o progresso
        cv2.rectangle(frame, (x, y), (x + largura, y + altura), (255, 0, 0), 2)
        cv2.putText(frame, f"Foto {contador}/{total_fotos}", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)
        
        cv2.imshow('A Criar Base de Dados', frame)
        cv2.waitKey(100) # Pequena pausa entre fotos (100ms)

    # Para quando chegar às 30 fotos ou se premires 'q'
    if contador >= total_fotos or (cv2.waitKey(1) & 0xFF == ord('q')):
        break

print(f"\nSucesso! {contador} fotos guardadas na pasta 'fotos_treino'.")
webcam.release()
cv2.destroyAllWindows()