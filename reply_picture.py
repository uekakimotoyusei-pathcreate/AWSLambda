import requests
import os
import json
import boto3
from io import BytesIO

def sendMessage(header, userId, messageType, text):
    pushUrl = 'https://api.line.me/v2/bot/message/push'
    postData = {
            'to': userId,
            'messages': [
                {
                    'type': messageType,
                    'text': text
                }
            ]
        }
        
    requests.post(pushUrl, headers=header, data=json.dumps(postData))
    
def sendImage(header, userId, messageType, imageUrl):
    pushUrl = 'https://api.line.me/v2/bot/message/push'
    print('イメージURL\n' + imageUrl)
    postData = {
        'to': userId,
        'messages': [
            {
                "type": messageType,
                "originalContentUrl": imageUrl,
                "previewImageUrl": imageUrl
            }
        ]
    }
        
    requests.post(pushUrl, headers=header, data=json.dumps(postData))
    
def searchProcess(header, messageId, userId):
    imageFile = requests.get('https://api-data.line.me/v2/bot/message/'+ messageId +'/content',headers=header) #Imagecontent取得
    imageBin = BytesIO(imageFile.content)
    image = imageBin.getvalue()  # 画像取得
    
    try:
        postBucket = 'xxxxxx''
        getBucket = 'xxxxxxx'
        threshold = 70
        maxFaces = 3
        fileName = messageId + '.jpeg'  # メッセージID+jpegをファイル名
        
        #一度投稿された写真をS3にアップ
        s3 = boto3.client('s3')
        # s３へのput処理
        s3.put_object(Bucket = postBucket, Body = image, Key = fileName)
        
        rekognition = boto3.client('rekognition')
        
        rekoResponse = rekognition.search_faces_by_image(CollectionId = 'registeredFace',
                                                    Image = {'S3Object':{'Bucket':postBucket,'Name':fileName}},
                                                    FaceMatchThreshold = threshold,
                                                    MaxFaces = maxFaces)
                                                    
        targetFileName = rekoResponse['FaceMatches'][0]['Face']['ExternalImageId']
        print(targetFileName)
        
        # S3へアップロードした画像の署名付きURLを取得する
        s3ImageUrl = s3.generate_presigned_url(
            ClientMethod = 'get_object',
            Params       = {'Bucket': getBucket, 'Key': targetFileName},
            ExpiresIn    = 120,
            HttpMethod   = 'GET'
        )
        
        #投稿した写真は用済みなので削除する
        s3.delete_object(Bucket = postBucket, Key = fileName)
    
    except Exception as e:
        sendMessage(header, userId, 'text', "処理に失敗しました。\n人物が登録されていない可能性があります\n登録後に再度やり直してください。")
        print('registProcess 例外エラー')
        raise Exception(e)
        
    return s3ImageUrl
    
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
        sendMessage(header, userId, 'text', '画像のみを送信してください。')
        return False
        
    s3ImageUrl = searchProcess(header, messageId, userId)
    #LINEに画像を送信する
    sendImage(header, userId, 'image', s3ImageUrl)
    sendMessage(header, userId, 'text', '似ている人物が見つかりました。')
    
    return {
        'statusCode': 200,
        'body': json.dumps('Hello from Lambda!')
    }