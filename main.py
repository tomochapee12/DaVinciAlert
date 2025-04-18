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
    未通知のニュースを取得
    """
    try:
        with open('last_checked.txt', 'r', encoding='utf-8') as f:
            last = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        last = {'date': '', 'title': ''}
        
    print(f"[DEBUG] last_checked.txt の内容: {last}")
    
    new_news = []
    for news in news_list:
        if news['date'] == last.get('date') and news['title'] == last.get('title'):
            break
        new_news.append(news)
    
    print(f"[DEBUG] 新着ニュース件数: {len(new_news)}")
    
    # 最終チェック情報の更新はここでは行わない
    # 実際に通知した後に更新する
    return new_news

def update_last_checked(news):
    """
    最終チェック情報を更新する関数
    """
    if news:  # newsリストが空でない場合のみ更新
        with open('last_checked.txt', 'w', encoding='utf-8') as f:
            json.dump({'date': news[0]['date'], 'title': news[0]['title']}, f, ensure_ascii=False)
        print(f"[INFO] last_checked.txt を更新しました: {news[0]['date']} - {news[0]['title']}")

def send_to_discord(news_list):
    """ 
    Discord にまとめて通知
    """
    webhook_url = os.getenv('DISCORD_WEBHOOK')
    if not webhook_url:
        print("[ERROR] DISCORD_WEBHOOK が設定されていません")
        return False
    
    if not news_list:
        print("[INFO] 新着ニュースはありません")
        return False
    
    success = True
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
        
        try:
            response = requests.post(webhook_url, json={'content': msg, 'allowed_mentions': {'parse': []}})
            response.raise_for_status()
            
            if news['banner']:
                img_data = requests.get(news['banner']).content
                files = {'file': ('banner.png', img_data)}
                data = {'payload_json': json.dumps({'allowed_mentions': {'parse': []}})}
                response = requests.post(webhook_url, files=files, data=data)
                response.raise_for_status()
                
            print(f"[INFO] 通知しました: {news['date']} - {news['title']}")
        except Exception as e:
            print(f"[ERROR] 通知に失敗しました: {e}")
            success = False
    
    return success

if __name__ == '__main__':
    all_news = scrape_news()
    new_news = check_new_news(all_news)
    
    # 通知に成功した場合のみ、最終チェック情報を更新
    if send_to_discord(new_news):
        update_last_checked(new_news)
