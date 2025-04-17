import os
import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime

# 送信する本文の最大文字数
MAX_BODY_LENGTH = 400


def scrape_news():
    """
    Fate/GO ニュース一覧ページから最新ニュースを取得
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

    # 全テキストを改行区切りで取り、最初の2行（日付とタイトル）を除去
    raw_text = article.get_text(separator='\n', strip=True)
    lines = raw_text.split('\n')
    body_lines = lines[2:] if len(lines) > 2 else lines
    text_body = '\n'.join(body_lines)

    return text_body, banner_url


def check_new_news(news_list):
    """ 未通知のニュースを取得し、ステートを更新 """
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
    """ Discord にまとめて通知 (テキスト + 画像をファイルとして送信) """
    webhook_url = os.getenv('DISCORD_WEBHOOK')
    if not webhook_url:
        print("[ERROR] DISCORD_WEBHOOK が設定されていません")
        return False

    for news in reversed(news_list):
        # 本文の長さ制限
        body = news['content']
        if len(body) > MAX_BODY_LENGTH:
            body = body[:MAX_BODY_LENGTH] + "(以下省略)"

        # テキストメッセージ送信
        text_payload = {
            'content': (
                f"## {news['title']}\n"
                f"**掲載日**: {news['date']}\n"
                f"{body}\n"
                f"詳細: <{news['url']}>"
            ),
            'allowed_mentions': {'parse': []}
        }
        resp_text = requests.post(webhook_url, json=text_payload)
        if not resp_text.ok:
            print(f"[ERROR] Discord テキスト通知失敗: {resp_text.status_code} {resp_text.text}")

        # 画像をファイルとして送信（リンクではなく直接投稿）
        banner_url = news.get('banner')
        if banner_url:
            img_resp = requests.get(banner_url)
            if img_resp.ok:
                # Discord multipart の場合、payload_json でメタ情報を渡す
                payload_json = {'allowed_mentions': {'parse': []}}
                files = {'file': ('banner.png', img_resp.content)}
                resp_img = requests.post(
                    webhook_url,
                    files=files,
                    data={'payload_json': json.dumps(payload_json)}
                )
                if not resp_img.ok:
                    print(f"[ERROR] Discord 画像通知失敗: {resp_img.status_code} {resp_img.text}")
            else:
                print(f"[ERROR] バナー画像取得失敗: {img_resp.status_code}")

    return True


if __name__ == '__main__':
    all_news = scrape_news()
    new_news = check_new_news(all_news)
    if new_news:
        send_to_discord(new_news)
