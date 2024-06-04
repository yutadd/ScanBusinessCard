import time
import cv2
import streamlit as st
from PIL import Image  # 追加
import numpy as np
import pytesseract
from openai import OpenAI
from ultralytics import YOLO 
# TODO: ai-prog-4にインストールされたlabelImgを使って名刺を切り抜く処理をアップグレード中
import os

# ./tmpディレクトリがなかったら作る
if not os.path.exists('./tmp'):
    os.makedirs('./tmp')
# 画像アップロード
uploaded_file = st.file_uploader("画像をアップロードしてください", type=["jpg", "jpeg", "png"])
if uploaded_file is not None:
    # 画像を表示
    image = Image.open(uploaded_file)
    st.image(image, caption='アップロードされた画像。', width=300,use_column_width=True)
        # 画像をRGB形式に変換
    if image.mode == 'RGBA':
        image = image.convert('RGB')
    # 画像をOpenCV形式に変換
    img_array = np.array(image)
    st.write("画像の形状:", img_array.shape)
    model = YOLO('data//best.pt')  # 事前に学習したモデルのパスを指定
    results = model(img_array)
    # 切り取った名刺を表示
    image_count=0
    for result in results:
        boxes = result.boxes.xyxy.cpu().numpy()
        confidences = result.boxes.conf.cpu().numpy()
        labels = result.boxes.cls.cpu().numpy()
        names=result.names
        for box, confidence, label in zip(boxes, confidences, labels):
            if confidence >= 0.8 and names[label] == 'meishi':
                x1, y1, x2, y2 = map(int, box)
                business_card = img_array[y1:y2, x1:x2]
                # 切り取った名刺を表示
                st.image(business_card, caption='切り取られた名刺。', width=150, use_column_width=True)
                output_path = "./tmp/output" + str(image_count) + ".png"
                cv2.imwrite(output_path, business_card)
                st.write(f"切り取られた名刺が {output_path} に保存されました。")
                image_count += 1
            else:
                print("{0},{1}".format(confidence,names[label]))

    
    print("detected "+str(image_count)+" cards")
    client = OpenAI()
    thread=client.beta.threads.create()
    files=[]
    for a in range(image_count):
        file=client.files.create(file=open("./tmp/output"+str(a)+".png","rb"),purpose="assistants")
        if file is not None:
            files.append({"type":"image_file","image_file":{"file_id":file.id}})
        else:
            print("con't read file")
    if len(files)>0:
        GPT_answer_placeholder = st.text("GPT:計算中")  # プレースホルダーを作成
        tesseract_answer_placeholder=st.text("tesseract:計算中")
        import pytesseract
        from PIL import Image

        # pytesseractの設定
        pytesseract.pytesseract.tesseract_cmd = r'D:\tesseractOCR\tesseract.exe'  # Tesseractのパスを指定

        ocr_results = []
        for a in range(image_count):
            image_path = "./tmp/output" + str(a) + ".png"
            text = pytesseract.image_to_string(Image.open(image_path), lang='jpn')
            ocr_results.append(text)
            tesseract_answer_placeholder.text("tesseract:出力なし" if (text is None or text=="") else text)
        if not ocr_results:
            tesseract_answer_placeholder.text("tesseract:OCR処理に失敗しました。")
        # =================================
        assistant=client.beta.assistants.retrieve(assistant_id="asst_1Y5PWnS8cy8pDUzIyefSJtJT")
        print(files,"←thread object")
        run = client.beta.threads.create_and_run(
            assistant_id="asst_1Y5PWnS8cy8pDUzIyefSJtJT",
            thread={
                "messages": [
                    {"role": "user", "content": files}
                ]
            }
        )
        print(run.status)
        GPT_answer_placeholder.text("GPT:処理しています")
        while(run.status=="queued"):
            GPT_answer_placeholder.text("GPT:処理のキューに入りました")
            time.sleep(1)
            run = client.beta.threads.runs.retrieve(thread_id=run.thread_id, run_id=run.id)
            print(run.status)
        while run.status=="in_progress":
            GPT_answer_placeholder.text("GPT:処理しています")
            run = client.beta.threads.runs.retrieve(thread_id=run.thread_id, run_id=run.id)
            print(run.status)
            time.sleep(1)
        if run.status=="completed":
            messages = client.beta.threads.messages.list(thread_id=run.thread_id)
            if messages.data[0].content[0].text.value:
                GPT_answer_placeholder.text("GPT:"+messages.data[0].content[0].text.value)
            else:
                GPT_answer_placeholder.text("GPT:messages.data[0].content[0].textの中身が空っぽです")
                print(messages[0])
        else:
            st.error(run.status)
            st.error(run.last_error)
    else:
        st.text("No files readed")
        print("No files readed")
