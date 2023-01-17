import re
import requests
from bs4 import BeautifulSoup

base_url = 'https://blogmaverick.com'
last_page = 93
for page in range(1, last_page + 1):
    
    page_url = base_url + '/page/' + str(page)
    source_code = requests.get(page_url)
    soup = BeautifulSoup(source_code.content, "html.parser")

    blog_links = soup.find_all('a', {'class', 'read-more-button'})
    for blog_link in blog_links:
        print("hey")
        blog_source_code = requests.get(blog_link['href'])
        blog_soup = BeautifulSoup(blog_source_code.content, "html.parser")
        
        title = re.sub(r'[^a-zA-Z0-9]', '', blog_soup.find('h1', {'class', 'entry-title'}).getText())
        body = blog_soup.find('div', {'class', 'entry-content'})

        with open(title + '.txt', 'w') as f:
            paragraphs = body.findChildren('p', recursive=False)
            for paragraph in paragraphs:
                f.write(paragraph.getText() + '\n')