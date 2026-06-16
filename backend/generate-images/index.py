import json
import os
import http.client
import ssl
import base64
import urllib.request
import traceback
import boto3


def generate_image_fal(prompt: str, api_key: str) -> bytes:
    """Генерирует изображение через fal.ai FLUX и возвращает байты."""
    payload = json.dumps({
        'prompt': prompt,
        'image_size': 'landscape_4_3',
        'num_inference_steps': 28,
        'num_images': 1,
        'enable_safety_checker': True,
    }).encode('utf-8')

    ctx = ssl.create_default_context()
    conn = http.client.HTTPSConnection('fal.run', timeout=90, context=ctx)
    conn.request(
        'POST',
        '/fal-ai/flux/dev',
        body=payload,
        headers={
            'Authorization': f'Key {api_key}',
            'Content-Type': 'application/json',
            'Content-Length': str(len(payload)),
        },
    )
    resp = conn.getresponse()
    resp_body = resp.read().decode('utf-8')
    conn.close()

    if resp.status != 200:
        raise Exception(f'fal.ai error {resp.status}: {resp_body[:300]}')

    data = json.loads(resp_body)
    img_url = data['images'][0]['url']

    # Скачиваем картинку
    with urllib.request.urlopen(img_url, timeout=30) as r:
        return r.read()


def upload_to_s3(img_bytes: bytes, key: str) -> str:
    """Загружает картинку в S3 и возвращает CDN URL."""
    access_key = os.environ['AWS_ACCESS_KEY_ID']
    secret_key = os.environ['AWS_SECRET_ACCESS_KEY']

    s3 = boto3.client(
        's3',
        endpoint_url='https://bucket.poehali.dev',
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
    )
    s3.put_object(
        Bucket='files',
        Key=key,
        Body=img_bytes,
        ContentType='image/jpeg',
    )
    return f'https://cdn.poehali.dev/projects/{access_key}/bucket/{key}'


def handler(event: dict, context) -> dict:
    '''Генерирует изображения для разворотов фотокниги через FLUX и сохраняет в S3.
    Принимает: spreads — список разворотов с heading/caption/text, book_id — уникальный ID сессии.
    Возвращает: список image_urls по одному на разворот.'''
    cors = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Max-Age': '86400',
    }

    if event.get('httpMethod') == 'OPTIONS':
        return {'statusCode': 200, 'headers': cors, 'body': ''}

    if event.get('httpMethod') != 'POST':
        return {'statusCode': 405, 'headers': {**cors, 'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'Method not allowed'})}

    try:
        body     = json.loads(event.get('body') or '{}')
        spreads  = body.get('spreads', [])
        book_id  = body.get('book_id', 'default')
        title    = body.get('title', '')

        if not spreads:
            return {'statusCode': 400, 'headers': {**cors, 'Content-Type': 'application/json'},
                    'body': json.dumps({'error': 'Передайте spreads'})}

        fal_key = os.environ.get('FAL_API_KEY', '')
        if not fal_key:
            return {'statusCode': 500, 'headers': {**cors, 'Content-Type': 'application/json'},
                    'body': json.dumps({'error': 'FAL_API_KEY не настроен'})}

        image_urls = []
        for i, spread in enumerate(spreads):
            heading = spread.get('heading', '')
            caption = spread.get('caption', '')
            text    = spread.get('text', '')

            # Составляем промпт на английском для лучшего качества
            prompt = (
                f'Photo book spread illustration for "{title}". '
                f'Scene: {heading}. {caption}. {text[:120]}. '
                'Beautiful warm photography style, soft natural light, '
                'cinematic composition, high quality, emotional, cozy atmosphere.'
            )

            print(f'[INFO] Generating image {i+1}/{len(spreads)}: {heading[:50]}')
            try:
                img_bytes = generate_image_fal(prompt, fal_key)
                s3_key    = f'photobooks/{book_id}/spread_{i+1}.jpg'
                url       = upload_to_s3(img_bytes, s3_key)
                image_urls.append(url)
                print(f'[INFO] Image {i+1} uploaded: {url}')
            except Exception as e:
                print(f'[WARN] Image {i+1} failed: {e}')
                image_urls.append(None)

        return {
            'statusCode': 200,
            'headers': {**cors, 'Content-Type': 'application/json'},
            'body': json.dumps({'image_urls': image_urls}, ensure_ascii=False),
        }

    except Exception as e:
        print(f'[ERROR] {e}\n{traceback.format_exc()}')
        return {'statusCode': 500, 'headers': {**cors, 'Content-Type': 'application/json'},
                'body': json.dumps({'error': str(e)})}
