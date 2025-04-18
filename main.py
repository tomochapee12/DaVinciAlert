import os
import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime

# 送信する本文の最大文字数
MAX_BODY_LENGTH = 400


def scrape_news():
    """
    FGOニュース一覧ページから最新ニュースを取得
    """
    url = "https://news.fate-go.jp/"
    response = requests.get(url)
    response.encoding = response.apparent_encoding
    soup = BeautifulSoup(response.text, 'html.parser')

    news_list = []
    for item in soup.select('ul.list_news li'):
        date_str = item.find('p', class_='date').get_text(strip=True)
        title = item.find('p', class_='title').get_text(strip=True)
        link = item.find('a')['href']
        if not link.startswith('http'):
            link = f"https://news.fate-go.jp/{link.lstrip('/')}"

        content, banner_url = get_article_content(link)
        news_list.append({
            'date': date_str,
            'title': title,
            'url': link,
            'content': content,
            'banner': banner_url
        })

    return news_list


def get_article_content(article_url):
    """
    記事本文テキストとalt="TOPバナー"の画像URLを取得して返す
    """
    response = requests.get(article_url)
    response.encoding = response.apparent_encoding
    soup = BeautifulSoup(response.text, 'html.parser')
    article = soup.find('div', class_='article')
    if not article:
        return '', None

    # TOPバナー画像取得
    banner_url = None
    img_tag = article.find('img', alt='TOPバナー')
    if img_tag and img_tag.get('src'):
        src = img_tag['src']
        if not src.startswith('http'):
            src = f"https://news.fate-go.jp/{src.lstrip('/')}"
        banner_url = src

    raw_text = article.get_text(separator='\n', strip=True)
    lines = raw_text.split('\n')
    body_lines = lines[2:] if len(lines) > 2 else lines
    text_body = '\n'.join(body_lines)

    return text_body, banner_url


def check_new_news(news_list):
    """ 
    未通知のニュースを取得し、ステートを更新
    """
    try:
        with open('last_checked.txt', 'r', encoding='utf-8') as f:
            last = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        last = {'date': '', 'title': ''}

    new_news = []
    for news in news_list:
        if news['date'] == last.get('date') and news['title'] == last.get('title'):
            break
        new_news.append(news)

    if new_news:
        with open('last_checked.txt', 'w', encoding='utf-8') as f:
            json.dump({'date': new_news[0]['date'], 'title': new_news[0]['title']}, f, ensure_ascii=False)

    return new_news


def send_to_discord(news_list):
    webhook_url = os.getenv('DISCORD_WEBHOOK')
    if not webhook_url:
        print("[ERROR] DISCORD_WEBHOOK が設定されていません")
        return
    else:
        print("[DEBUG] Webhook URL は設定されています")

    for news in reversed(news_list):
        body = news['content']
        if len(body) > MAX_BODY_LENGTH:
            body = body[:MAX_BODY_LENGTH] + '(以下省略)'

        msg = (
            f"## {news['title']}\n"
            f"**掲載日**: {news['date']}\n"
            f"{body}\n"
            f"詳細: <{news['url']}>"
        )

        print(f"[DEBUG] 送信内容:\n{msg}")

        resp = requests.post(webhook_url, json={'content': msg, 'allowed_mentions': {'parse': []}})
        print(f"[DEBUG] テキスト送信ステータス: {resp.status_code}")
        if resp.status_code != 204:
            print(f"[ERROR] テキスト送信失敗: {resp.status_code}, {resp.text}")

        if news['banner']:
            try:
                img_data = requests.get(news['banner']).content
                files = {'file': ('banner.png', img_data)}
                data = {'payload_json': json.dumps({'allowed_mentions': {'parse': []}})}
                resp_img = requests.post(webhook_url, files=files, data=data)
                print(f"[DEBUG] 画像送信ステータス: {resp_img.status_code}")
                if resp_img.status_code != 204:
                    print(f"[ERROR] 画像送信失敗: {resp_img.status_code}, {resp_img.text}")
            except Exception as e:
                print(f"[ERROR] 画像取得または送信で例外: {e}")



if __name__ == '__main__':
    all_news = scrape_news()
    new_news = check_new_news(all_news)
    if new_news:
        send_to_discord(new_news)
