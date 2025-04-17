import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime

def scrape_news():
    url = "https://news.fate-go.jp/"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    news_list = []
    for item in soup.select('ul.list_news li'):
        date_str = item.find('p', class_='date').get_text(strip=True)
        title = item.find('p', class_='title').get_text(strip=True)
        link = item.find('a')['href']
        
        # 相対URLを絶対URLに変換
        if not link.startswith('http'):
            link = f"https://news.fate-go.jp{link.lstrip('/')}"
        
        # 詳細ページの内容取得
        content = get_article_content(link)
        
        news_list.append({
            'date': date_str,
            'title': title,
            'url': link,
            'content': content
        })
    
    return news_list

def get_article_content(article_url):
    response = requests.get(article_url)
    soup = BeautifulSoup(response.text, 'html.parser')
    article = soup.find('div', class_='article')
    
    content = []
    for element in article.find_all(recursive=False):
        # 画像処理
        if element.img:
            img_url = element.img['src']
            if not img_url.startswith('http'):
                img_url = f"https://news.fate-go.jp{img_url.lstrip('/')}"
            content.append(f"![image]({img_url})")
        
        # 見出し処理
        elif element.find(class_='strong'):
            text = element.get_text(strip=True).replace('◆', '').strip()
            content.append(f"__**{text}**__")
        
        # テキスト処理
        elif element.name == 'p':
            text = element.get_text(strip=True)
            if 'notice' in element.get('class', []):
                content.append(f"・{text}")
            else:
                content.append(text)
        
        # ボタンリンク
        elif element.find(class_='btn_wrap'):
            link = element.find('a')['href']
            text = element.get_text(strip=True)
            content.append(f"[{text}]({link})")
    
    return '\n'.join(content)

def check_new_news(news_list):
    last_checked = load_last_checked()
    new_news = []
    
    for news in news_list:
        if news['url'] == last_checked:
            break
        new_news.append(news)
    
    if new_news:
        save_last_checked(new_news[0]['url'])
    
    return new_news

def load_last_checked():
    try:
        with open('last_checked.txt', 'r') as f:
            return f.read().strip()
    except FileNotFoundError:
        return ""

def save_last_checked(url):
    with open('last_checked.txt', 'w') as f:
        f.write(url)

def send_to_discord(news_list):
    webhook_url = os.getenv('DISCORD_WEBHOOK')
    
    for news in reversed(news_list):
        message = (
            f"## {news['title']}\n"
            f"**掲載日**: {news['date']}\n"
            f"{news['content']}\n"
            f"詳細: {news['url']}"
        )
        
        requests.post(webhook_url, json={
            "content": message,
            "allowed_mentions": {"parse": []}
        })

if __name__ == "__main__":
    all_news = scrape_news()
    new_news = check_new_news(all_news)
    if new_news:
        send_to_discord(new_news)