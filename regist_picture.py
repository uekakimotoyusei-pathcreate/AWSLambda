import requests
import os
import json
import boto3
from io import BytesIO

def sendMessage(header, userId, text):
    postData = {
        'to': userId,
        'messages': [
            {
                'type': 'text',
                'text': text
            }
        ]
    }
    
    pushUrl = 'https://api.line.me/v2/bot/message/push'
    requests.post(pushUrl, headers=header, data=json.dumps(postData))

def registProcess(header, messageId):
    imageFile = requests.get('https://api-data.line.me/v2/bot/message/'+ messageId +'/content',headers = header) #Imagecontent取得
    imageBin = BytesIO(imageFile.content)
    image = imageBin.getvalue()  # 画像取得
    registBucket = 'xxxxxx'
    
    try:
        S3 = boto3.client('s3')
        fileName = messageId + '.jpeg'  # メッセージID+jpegをファイル名
        # s３へのput処理
        S3.put_object(Bucket = registBucket,
                     Body = image, # 写真
                     Key = fileName)  # ファイル名
                     
        client=boto3.client('rekognition')

        response=client.index_faces(CollectionId = 'registeredFace',
                                    Image = {'S3Object':{'Bucket':registBucket,'Name':fileName}},
                                    ExternalImageId = fileName,
                                    MaxFaces = 1,
                                    QualityFilter = "AUTO",
                                    DetectionAttributes = ['ALL'])
    except Exception as e:
        print('registProcess 例外エラー')
        raise Exception(e)
        
    return True
    
def lambda_handler(event, context):
    e = json.loads(event['body'])
    print(json.dumps(e))
    
    messageType = e["events"][0]["message"]["type"]
    userId = e['events'][0]['source']['userId']
    messageId = e['events'][0]['message']['id']  # メッセージID
    header = {
        'Content-type':
        'application/json',
        'Authorization':
        'Bearer ' + os.environ.get("CHANNEL_ACCESS_TOKEN")
    }
    
    if messageType != "image":
        #LINEに警告メッセージを送信して処理を終了する
        sendMessage(header, userId, '画像のみを送信してください。')
        return False
    
    #画像を登録する
    if registProcess(header, messageId) is not True:
        #LINEに処理の失敗を送信する
        sendMessage(header, userId, '処理に失敗しました。やり直してください。')
                 
    sendMessage(header, userId, '投稿された写真を登録しました。')
    
    return {
        "isBase64Encoded": "true",
        "statusCode": 200,
        "headers": {},
        "body": json.dumps(event)
    }
