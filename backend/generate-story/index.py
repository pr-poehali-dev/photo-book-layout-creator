import json
import os
import http.client
import ssl
import traceback


def handler(event: dict, context) -> dict:
    '''Генерирует историю и тексты для разворотов фотокниги по описанию клиента (ТЗ) через OpenAI.'''
    cors = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Max-Age': '86400',
    }

    if event.get('httpMethod') == 'OPTIONS':
        return {'statusCode': 200, 'headers': cors, 'body': ''}

    if event.get('httpMethod') != 'POST':
        return {'statusCode': 405, 'headers': {**cors, 'Content-Type': 'application/json'}, 'body': json.dumps({'error': 'Method not allowed'})}

    try:
        body = json.loads(event.get('body') or '{}')
        brief = (body.get('brief') or '').strip()
        spreads = max(1, min(int(body.get('spreads') or 5), 12))

        if not brief:
            return {'statusCode': 400, 'headers': {**cors, 'Content-Type': 'application/json'}, 'body': json.dumps({'error': 'Опишите вашу историю'})}

        api_key = os.environ.get('OPENROUTER_API_KEY', '')
        print(f'[DEBUG] api_key present: {bool(api_key)}, length: {len(api_key)}')

        if not api_key:
            return {'statusCode': 500, 'headers': {**cors, 'Content-Type': 'application/json'}, 'body': json.dumps({'error': 'OPENROUTER_API_KEY не настроен'})}

        system_prompt = (
            'Ты — редактор фотокниг. По техническому заданию клиента создаёшь макет книги. '
            'Верни строго JSON-объект без markdown. Формат: '
            '{"title": "название книги", "intro": "вступление 1-2 предложения", '
            '"spreads": [{"heading": "заголовок разворота", "caption": "подпись к фото 1 предложение", '
            '"text": "тёплый текст разворота 2-3 предложения"}]}. '
            f'Сделай ровно {spreads} разворотов. Пиши на русском, тепло и душевно.'
        )

        payload = json.dumps({
            'model': 'gpt-4o-mini',
            'messages': [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': brief},
            ],
            'temperature': 0.8,
            'response_format': {'type': 'json_object'},
        }).encode('utf-8')

        print(f'[DEBUG] Sending request to OpenRouter, payload size: {len(payload)}')
        ctx = ssl.create_default_context()
        conn = http.client.HTTPSConnection('openrouter.ai', timeout=55, context=ctx)
        conn.request(
            'POST',
            '/api/v1/chat/completions',
            body=payload,
            headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json',
                'Content-Length': str(len(payload)),
                'HTTP-Referer': 'https://poehali.dev',
                'X-Title': 'Фотокнига',
            },
        )
        resp = conn.getresponse()
        resp_body = resp.read().decode('utf-8')
        conn.close()
        print(f'[DEBUG] OpenRouter response status: {resp.status}')

        if resp.status != 200:
            print(f'[ERROR] OpenRouter error body: {resp_body[:500]}')
            return {
                'statusCode': 502,
                'headers': {**cors, 'Content-Type': 'application/json'},
                'body': json.dumps({'error': f'Ошибка OpenAI {resp.status}: {resp_body[:500]}'}),
            }

        data = json.loads(resp_body)
        content = data['choices'][0]['message']['content']
        story = json.loads(content)

        return {
            'statusCode': 200,
            'headers': {**cors, 'Content-Type': 'application/json'},
            'body': json.dumps(story, ensure_ascii=False),
        }

    except Exception as e:
        tb = traceback.format_exc()
        print(f'[ERROR] {e}\n{tb}')
        return {
            'statusCode': 500,
            'headers': {**cors, 'Content-Type': 'application/json'},
            'body': json.dumps({'error': str(e)}),
        }