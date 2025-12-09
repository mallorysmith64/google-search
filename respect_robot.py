from urllib.robotparser import RobotFileParser

# Initialize the parser
# Note: The 'User-agent' you provide to the parser should be the same
# as the one your crawler uses.
parser = RobotFileParser()

# Set the URL of the robots.txt file for the target site
target_domain = "https://www.britannica.com/"
robots_txt_url = target_domain + "robots.txt"

parser.set_url(robots_txt_url)

# Fetch and parse the robots.txt file content
# This makes an HTTP request to the robots.txt file.
parser.read()

# The URL you want to crawl
url_to_check = target_domain + "some/page/to/crawl.html"

# The name of your crawler's User-Agent
your_user_agent = "MyAwesomeCrawler"

if parser.can_fetch(your_user_agent, url_to_check):
    print(f"✅ Allowed to crawl: {url_to_check}")
    # Proceed with crawling the page
else:
    print(f"🛑 Disallowed by robots.txt: {url_to_check}")
    # Skip this URL