from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count, F, Prefetch
from django.contrib import messages
from django.http import HttpResponse, JsonResponse, FileResponse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from .models import Project, Category, Post, Comment, Rating, SocialMediaContent
import instaloader
import tweepy
import requests
from facebook_scraper import get_posts
from pytube import YouTube
import os
import shutil
import glob
import logging
from concurrent.futures import ThreadPoolExecutor
import dns.resolver
import random
import time
from PIL import Image
import io
from rembg import remove
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from googletrans import Translator, LANGUAGES
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import nmap

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Proxy list
PROXY_POOL = [
    "http://103.174.102.132:80",
    "http://47.251.43.115:3128",
    "http://167.71.5.83:8080",
]

def get_random_proxy():
    """Select a random proxy from the pool."""
    return random.choice(PROXY_POOL)

def test_proxy(proxy):
    """Test if a proxy is working."""
    try:
        response = requests.get("https://www.httpbin.org/ip", proxies={"http": proxy, "https": proxy}, timeout=5)
        return response.status_code == 200
    except requests.RequestException:
        return False

# Singleton-like Instaloader instance (unchanged)
class InstaloaderSingleton:
    @classmethod
    def get_instance(cls, force_fresh=False):
        L = instaloader.Instaloader()
        SESSION_FILE = os.path.join(settings.BASE_DIR, 'instagram_session')
        
        if force_fresh or not os.path.exists(SESSION_FILE):
            cls._force_authenticate(L, SESSION_FILE)
        else:
            try:
                L.load_session_from_file(settings.INSTAGRAM_USERNAME, SESSION_FILE)
                logger.info(f"Loaded existing session for {settings.INSTAGRAM_USERNAME}")
                profile = instaloader.Profile.from_username(L.context, settings.INSTAGRAM_USERNAME)
                logger.debug("Session validated successfully")
            except Exception as e:
                logger.warning(f"Session load failed or invalid: {str(e)}. Forcing re-authentication...")
                cls._force_authenticate(L, SESSION_FILE)
        return L

    @classmethod
    def _force_authenticate(cls, instance, session_file):
        try:
            if os.path.exists(session_file):
                os.remove(session_file)
                logger.debug(f"Deleted invalid session file: {session_file}")
            instance.login(settings.INSTAGRAM_USERNAME, settings.INSTAGRAM_PASSWORD)
            instance.save_session_to_file(session_file)
            logger.info(f"Authenticated and saved new session for {settings.INSTAGRAM_USERNAME}")
        except instaloader.exceptions.TwoFactorAuthRequiredException as e:
            logger.error(f"Two-factor authentication required: {str(e)}")
            raise Exception("2FA required. Please disable 2FA or configure it manually.")
        except instaloader.exceptions.BadCredentialsException as e:
            logger.error(f"Invalid Instagram credentials: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Authentication failed: {str(e)}")
            raise

# New scraping functions
def fetch_lottery_results():
    """Scrape Kerala lottery results from statelottery.kerala.gov.in"""
    url = "https://statelottery.kerala.gov.in/index.php/lottery-result-view"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Assuming results are in a table or specific div (adjust selector based on actual HTML structure)
        result_section = soup.find('div', class_='result-view')  # Example class, adjust as needed
        if not result_section:
            logger.warning("No lottery result section found on page")
            return ["No results available (scraping failed)"]
        
        results = []
        # Example: Extracting rows from a table (adjust based on actual structure)
        for row in result_section.find_all('tr'):  # Assuming results are in a table
            cols = row.find_all('td')
            if len(cols) >= 2:
                lottery_name = cols[0].text.strip()
                winning_number = cols[1].text.strip()
                results.append(f"{lottery_name}: {winning_number}")
        
        if not results:
            logger.warning("No lottery results parsed from page")
            return ["No results available today"]
        
        logger.info(f"Scraped {len(results)} lottery results")
        return results[:5]  # Limit to top 5 results
    except requests.RequestException as e:
        logger.error(f"Failed to scrape lottery results: {str(e)}")
        return [f"Error fetching lottery results: {str(e)}"]
    except Exception as e:
        logger.error(f"Unexpected error while scraping lottery results: {str(e)}")
        return [f"Error processing lottery results: {str(e)}"]

def fetch_gold_rates():
    """Scrape gold rates from goodreturns.in"""
    url = "https://www.goodreturns.in/gold-rates/kerala.html"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Assuming gold rates are in a table or div with specific class (adjust selector)
        rate_section = soup.find('div', class_='gold_silver_table')  # Example class, adjust as needed
        if not rate_section:
            logger.warning("No gold rate section found on page")
            return {"22k": "₹6500 (Simulated)", "24k": "₹7000 (Simulated)"}
        
        rates = {}
        # Example: Extracting 22K and 24K rates (adjust based on actual structure)
        for row in rate_section.find_all('tr'):
            cols = row.find_all('td')
            if len(cols) >= 2:
                if "22 Carat" in cols[0].text:
                    rates["22k"] = cols[1].text.strip()
                elif "24 Carat" in cols[0].text:
                    rates["24k"] = cols[1].text.strip()
        
        if not rates:
            logger.warning("No gold rates parsed from page")
            return {"22k": "₹6500 (Simulated)", "24k": "₹7000 (Simulated)"}
        
        logger.info(f"Scraped gold rates: {rates}")
        return rates
    except requests.RequestException as e:
        logger.error(f"Failed to scrape gold rates: {str(e)}")
        return {"22k": f"Error: {str(e)}", "24k": f"Error: {str(e)}"}
    except Exception as e:
        logger.error(f"Unexpected error while scraping gold rates: {str(e)}")
        return {"22k": f"Error: {str(e)}", "24k": f"Error: {str(e)}"}

def fetch_rubber_rates():
    """Scrape rubber rates from thecanarapost.com"""
    url = "https://thecanarapost.com/todays-rubber-prices-kottayam-and-international-market/"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Assuming rubber rates are in a table or specific section (adjust selector)
        rate_section = soup.find('div', class_='entry-content')  # Example class, adjust as needed
        if not rate_section:
            logger.warning("No rubber rate section found on page")
            return {"rss4": "₹170/kg (Simulated)", "rss5": "₹165/kg (Simulated)"}
        
        rates = {}
        content = rate_section.text.lower()
        # Simple text parsing (adjust based on actual structure)
        for line in content.split('\n'):
            if 'rss4' in line and 'kottayam' in line:
                rates["rss4"] = line.split('rss4')[-1].strip().split()[0]  # Extract price
            elif 'rss5' in line and 'kottayam' in line:
                rates["rss5"] = line.split('rss5')[-1].strip().split()[0]  # Extract price
        
        if not rates:
            logger.warning("No rubber rates parsed from page")
            return {"rss4": "₹170/kg (Simulated)", "rss5": "₹165/kg (Simulated)"}
        
        logger.info(f"Scraped rubber rates: {rates}")
        return rates
    except requests.RequestException as e:
        logger.error(f"Failed to scrape rubber rates: {str(e)}")
        return {"rss4": f"Error: {str(e)}", "rss5": f"Error: {str(e)}"}
    except Exception as e:
        logger.error(f"Unexpected error while scraping rubber rates: {str(e)}")
        return {"rss4": f"Error: {str(e)}", "rss5": f"Error: {str(e)}"}

# Updated index view to include scraped data
def index(request):
    logger.debug("Entering index view")
    projects = Project.objects.all().order_by('-created_at')
    categories = Category.objects.all().prefetch_related(
        Prefetch(
            'posts',
            queryset=Post.objects.select_related('category')
                .annotate(avg_rating=Avg('ratings__stars'), comment_count=Count('comments'))
                .order_by('-created_at')
        )
    )
    nav_categories = []
    main_categories = ['Python', 'Ionic', 'Node']
    for main_cat in main_categories:
        subcategories = categories.filter(name__icontains=main_cat)
        if subcategories.exists():
            nav_categories.append({'main': main_cat, 'subcategories': subcategories})

    # Fetch live data
    lottery_results = fetch_lottery_results()
    gold_rates = fetch_gold_rates()
    rubber_rates = fetch_rubber_rates()

    context = {
        'projects': projects,
        'nav_categories': nav_categories,
        'categories': categories,
        'lottery_results': lottery_results,
        'gold_rates': gold_rates,
        'rubber_rates': rubber_rates,
    }
    logger.debug("Rendering index.html with context")
    return render(request, 'index.html', context)

# Rest of your views remain unchanged
def category_detail(request, category_id):
    logger.debug(f"Entering category_detail view with category_id: {category_id}")
    category = get_object_or_404(Category, id=category_id)
    posts = category.posts.all()
    if 'q' in request.GET:
        query = request.GET['q']
        posts = posts.filter(name__icontains=query)
        logger.debug(f"Filtered posts with query: {query}")
    context = {
        'category': category,
        'posts': posts,
        'search_query': query if 'q' in request.GET else ''
    }
    logger.debug("Rendering category_detail.html with context")
    return render(request, 'category_detail.html', context)

def post_detail(request, post_id):
    logger.debug(f"Entering post_detail view with post_id: {post_id}")
    post = get_object_or_404(
        Post.objects.select_related('category')
        .annotate(avg_rating=Avg('ratings__stars'), comment_count=Count('comments')),
        id=post_id
    )
    comments = post.comments.select_related('user').order_by('-created_at')
    user_rating = None
    if request.user.is_authenticated:
        user_rating = Rating.objects.filter(post=post, user=request.user).first()
    context = {'post': post, 'comments': comments, 'user_rating': user_rating}
    logger.debug("Rendering post_detail.html with context")
    return render(request, 'post_detail.html', context)

def project_detail(request, project_id):
    logger.debug(f"Entering project_detail view with project_id: {project_id}")
    project = get_object_or_404(Project, id=project_id)
    logger.debug("Rendering project_detail.html with project")
    return render(request, 'project_detail.html', {'project': project})

@login_required
def add_comment(request, post_id):
    logger.debug(f"Entering add_comment view with post_id: {post_id}")
    if request.method == 'POST':
        post = get_object_or_404(Post, id=post_id)
        content = request.POST.get('content')
        if content:
            Comment.objects.create(post=post, user=request.user, content=content)
            messages.success(request, 'Comment added successfully!')
            logger.info(f"Comment added to post {post_id} by user {request.user}")
        else:
            messages.error(request, 'Comment cannot be empty!')
            logger.warning(f"Empty comment attempted on post {post_id}")
    logger.debug(f"Redirecting to post_detail with post_id: {post_id}")
    return redirect('post_detail', post_id=post_id)

@login_required
def rate_post(request, post_id):
    logger.debug(f"Entering rate_post view with post_id: {post_id}")
    if request.method == 'POST':
        post = get_object_or_404(Post, id=post_id)
        stars = request.POST.get('stars')
        try:
            stars = int(stars)
            if 1 <= stars <= 5:
                Rating.objects.update_or_create(post=post, user=request.user, defaults={'stars': stars})
                messages.success(request, 'Rating updated successfully!')
                logger.info(f"Rating {stars} added/updated for post {post_id} by user {request.user}")
            else:
                messages.error(request, 'Invalid rating value!')
                logger.warning(f"Invalid rating value {stars} for post {post_id}")
        except (ValueError, TypeError):
            messages.error(request, 'Invalid rating value!')
            logger.error(f"Invalid rating value type for post {post_id}: {stars}")
    logger.debug(f"Redirecting to post_detail with post_id: {post_id}")
    return redirect('post_detail', post_id=post_id)

def search(request):
    logger.debug("Entering search view")
    query = request.GET.get('q', '')
    if query:
        projects = Project.objects.filter(name__icontains=query) | Project.objects.filter(description__icontains=query)
        posts = Post.objects.filter(name__icontains=query) | Post.objects.filter(sub_heading__icontains=query) | Post.objects.filter(notes__icontains=query).annotate(
            avg_rating=Avg('ratings__stars'), comment_count=Count('comments')
        )
        logger.debug(f"Search query: {query}, found {projects.count()} projects and {posts.count()} posts")
    else:
        projects = Project.objects.none()
        posts = Post.objects.none()
        logger.debug("No search query provided")
    context = {'query': query, 'projects': projects, 'posts': posts}
    logger.debug("Rendering search_results.html with context")
    return render(request, 'search_results.html', context)

@login_required
def delete_comment(request, comment_id):
    logger.debug(f"Entering delete_comment view with comment_id: {comment_id}")
    comment = get_object_or_404(Comment, id=comment_id)
    if request.user == comment.user or request.user.is_staff:
        post_id = comment.post.id
        comment.delete()
        messages.success(request, 'Comment deleted successfully!')
        logger.info(f"Comment {comment_id} deleted by user {request.user}")
        return redirect('post_detail', post_id=post_id)
    messages.error(request, 'You do not have permission to delete this comment!')
    logger.warning(f"User {request.user} lacks permission to delete comment {comment_id}")
    return redirect('post_detail', post_id=comment.post.id)

def instagram_downloader(request):
    logger.debug("Entering instagram_downloader view")
    if request.method == 'POST':
        platform = request.POST.get('platform')
        url = request.POST.get(f'{platform}_url')
        logger.debug(f"Processing {platform} download with URL: {url}")
        if not url:
            messages.error(request, f'Please provide a valid {platform.capitalize()} URL.')
            logger.warning(f"No URL provided for {platform} download")
            return render(request, 'instagram_downloader.html', get_context())

        temp_dir = 'temp_downloads'
        os.makedirs(temp_dir, exist_ok=True)
        logger.debug(f"Created temp directory: {temp_dir}")

        try:
            if platform == 'instagram':
                L = InstaloaderSingleton.get_instance()
                content_type = None
                filename = None

                if '/p/' in url or '/tv/' in url:
                    content_type = 'post'
                    shortcode = url.split('/')[-2]
                    post = instaloader.Post.from_shortcode(L.context, shortcode)
                    L.download_post(post, target=temp_dir)
                    possible_files = glob.glob(f"{temp_dir}/{shortcode}*.jp*g") + glob.glob(f"{temp_dir}/{shortcode}*.mp4")
                    logger.debug(f"Files found for Instagram post: {possible_files}")
                    if possible_files:
                        filename = possible_files[0]
                    else:
                        raise FileNotFoundError(f"No files found for Instagram post {shortcode}")

                elif '/reel/' in url:
                    content_type = 'reel'
                    shortcode = url.split('/')[-2]
                    post = instaloader.Post.from_shortcode(L.context, shortcode)
                    L.download_post(post, target=temp_dir)
                    possible_files = glob.glob(f"{temp_dir}/{shortcode}*.mp4") or glob.glob(f"{temp_dir}/*.mp4")
                    logger.debug(f"Files found for Instagram reel: {possible_files}")
                    if possible_files:
                        filename = possible_files[0]
                    else:
                        raise FileNotFoundError(f"No video file found for Instagram reel {shortcode}")

                elif '/stories/' in url:
                    content_type = 'story'
                    username = url.split('/stories/')[1].split('/')[0]
                    profile = instaloader.Profile.from_username(L.context, username)
                    for story in L.get_stories([profile.userid]):
                        for item in story.get_items():
                            L.download_storyitem(item, target=temp_dir)
                            possible_files = glob.glob(f"{temp_dir}/*.mp4") + glob.glob(f"{temp_dir}/*.jp*g")
                            logger.debug(f"Files found for Instagram story: {possible_files}")
                            if possible_files:
                                filename = possible_files[0]
                                break
                        break
                    if not filename:
                        raise FileNotFoundError(f"No story files found for {username}")

                else:  # Profile picture
                    content_type = 'dp'
                    username = url.split('/')[-2] if url.endswith('/') else url.split('/')[-1]
                    profile = instaloader.Profile.from_username(L.context, username)
                    L.download_profilepic(profile)
                    possible_files = glob.glob(f"{username}/*.jp*g")
                    logger.debug(f"Files found for Instagram profile picture: {possible_files}")
                    if possible_files:
                        filename = possible_files[0]
                    else:
                        raise FileNotFoundError(f"No profile picture found for {username}")

                if not filename or not os.path.exists(filename):
                    raise FileNotFoundError(f"Instagram content not found at {filename or 'unknown path'}")

            elif platform == 'twitter':
                auth = tweepy.OAuthHandler(settings.TWITTER_API_KEY, settings.TWITTER_API_SECRET)
                auth.set_access_token(settings.TWITTER_ACCESS_TOKEN, settings.TWITTER_ACCESS_TOKEN_SECRET)
                api = tweepy.API(auth)
                tweet_id = url.split('/')[-1].split('?')[0]
                logger.debug(f"Fetching Twitter post with ID: {tweet_id}")
                tweet = api.get_status(tweet_id, tweet_mode='extended')

                content_type = None
                filename = None
                if 'media' in tweet.entities:
                    for media in tweet.extended_entities['media']:
                        if media['type'] == 'video' or media['type'] == 'animated_gif':
                            video_info = media['video_info']
                            variants = video_info['variants']
                            video_url = max(variants, key=lambda v: v.get('bitrate', 0))['url']
                            content_type = 'video'
                        elif media['type'] == 'photo':
                            video_url = media['media_url_https']
                            content_type = 'image'
                        break

                    filename = os.path.join(temp_dir, f"twitter_{tweet_id}{'.mp4' if content_type == 'video' else '.jpg'}")
                    response = requests.get(video_url, stream=True)
                    if response.status_code == 200:
                        with open(filename, 'wb') as f:
                            shutil.copyfileobj(response.raw, f)
                        logger.info(f"Twitter content downloaded: {filename}")
                    else:
                        raise FileNotFoundError(f"Failed to download Twitter content from {video_url}")

                if not filename or not os.path.exists(filename):
                    raise FileNotFoundError(f"No media found in Twitter post {tweet_id}")

            elif platform == 'facebook':
                post_id = url.split('/')[-1].split('?')[0]
                logger.debug(f"Fetching Facebook post with ID: {post_id}")
                posts = get_posts(post_ids=[post_id], credentials=(settings.FACEBOOK_USERNAME, settings.FACEBOOK_PASSWORD))

                content_type = None
                filename = None
                for post in posts:
                    if 'video' in post and post['video']:
                        video_url = post['video']
                        content_type = 'video'
                    elif 'image' in post and post['image']:
                        video_url = post['image']
                        content_type = 'image'
                    else:
                        raise FileNotFoundError(f"No downloadable media found in Facebook post {post_id}")

                    filename = os.path.join(temp_dir, f"facebook_{post_id}{'.mp4' if content_type == 'video' else '.jpg'}")
                    response = requests.get(video_url, stream=True)
                    if response.status_code == 200:
                        with open(filename, 'wb') as f:
                            shutil.copyfileobj(response.raw, f)
                        logger.info(f"Facebook content downloaded: {filename}")
                    else:
                        raise FileNotFoundError(f"Failed to download Facebook content from {video_url}")
                    break

                if not filename or not os.path.exists(filename):
                    raise FileNotFoundError(f"No media found in Facebook post {post_id}")

            elif platform == 'youtube':
                yt = YouTube(url)
                stream = yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc().first()
                if not stream:
                    raise FileNotFoundError(f"No suitable video stream found for YouTube URL {url}")
                content_type = 'video'
                filename = os.path.join(temp_dir, f"youtube_{yt.video_id}.mp4")
                stream.download(output_path=temp_dir, filename=f"youtube_{yt.video_id}.mp4")
                logger.info(f"YouTube content downloaded: {filename}")

            with open(filename, 'rb') as f:
                file_content = f.read()
            content_type_header = 'video/mp4' if filename.endswith('.mp4') else 'image/jpeg'
            response = HttpResponse(
                file_content,
                content_type=content_type_header,
                headers={'Content-Disposition': f'attachment; filename="{os.path.basename(filename)}"'}
            )

            SocialMediaContent.objects.create(
                user=request.user if request.user.is_authenticated else None,
                platform=platform,
                url=url,
                content_type=content_type,
            )
            messages.success(request, f'{platform.capitalize()} content downloaded successfully!')
            logger.info(f"{platform.capitalize()} content downloaded and saved: {filename}")

            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
                logger.debug(f"Cleaned up temp directory: {temp_dir}")
            if platform == 'instagram' and 'username' in locals() and os.path.exists(username):
                shutil.rmtree(username)
                logger.debug(f"Cleaned up Instagram username directory: {username}")

            return response

        except instaloader.exceptions.ConnectionException as e:
            messages.error(request, f'Instagram connection error: {str(e)}')
            logger.error(f"Instagram connection error: {str(e)}")
        except instaloader.exceptions.BadCredentialsException as e:
            messages.error(request, f'Invalid Instagram credentials: {str(e)}')
            logger.error(f"BadCredentialsException: {str(e)}")
        except tweepy.TweepyException as e:
            messages.error(request, f'Twitter API error: {str(e)}')
            logger.error(f"TweepyException: {str(e)}")
        except FileNotFoundError as e:
            messages.error(request, f'Error downloading {platform.capitalize()} content: {str(e)}')
            logger.error(f"FileNotFoundError: {str(e)}")
        except Exception as e:
            messages.error(request, f'Error downloading {platform.capitalize()} content: {str(e)}')
            logger.error(f"Unexpected error: {str(e)}")
        finally:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
                logger.debug(f"Finally cleaned up temp directory: {temp_dir}")
            if 'username' in locals() and platform == 'instagram' and os.path.exists(username):
                shutil.rmtree(username)
                logger.debug(f"Finally cleaned up Instagram username directory: {username}")
            logger.debug("Rendering instagram_downloader.html with context after exception")
            return render(request, 'instagram_downloader.html', get_context())

    logger.debug("Rendering instagram_downloader.html with context for GET request")
    return render(request, 'instagram_downloader.html', get_context())

def get_context():
    logger.debug("Entering get_context helper function")
    instagram_count = SocialMediaContent.objects.filter(platform='instagram').count()
    twitter_count = SocialMediaContent.objects.filter(platform='twitter').count()
    facebook_count = SocialMediaContent.objects.filter(platform='facebook').count()
    youtube_count = SocialMediaContent.objects.filter(platform='youtube').count()
    context = {
        'instagram_count': instagram_count,
        'twitter_count': twitter_count,
        'facebook_count': facebook_count,
        'youtube_count': youtube_count,
    }
    logger.debug(f"Returning context: {context}")
    return context

def find_admin_panels(request):
    logger.debug("Entering find_admin_panels view")
    if request.method == 'POST':
        logger.debug("Received POST request to find admin panels")
        
        base_url = request.POST.get('url', '').strip()
        logger.debug(f"Base URL received: {base_url}")
        
        if not base_url:
            logger.warning("No URL provided in the request")
            return JsonResponse({'error': 'Please provide a valid URL'}, status=400)

        if not base_url.startswith(('http://', 'https://')):
            base_url = 'http://' + base_url
            logger.debug(f"Added 'http://' prefix to URL: {base_url}")
        if not base_url.endswith('/'):
            base_url += '/'
            logger.debug(f"Added trailing '/' to URL: {base_url}")

        admin_paths = [
            'admin', 'administrator', 'login', 'admin_login', 'adminlogin',
            'admin_area', 'admin_panel', 'controlpanel', 'cp', 'wp-admin',
            'dashboard', 'admin_dashboard', 'admincp', 'mod', 'moderator',
            'user', 'login.php', 'admin.php', 'dashboard.php', 'cpanel',
            'admin_area/admin', 'admin_area/login', 'siteadmin', 'admincontrol',
            'adm', 'manage', 'management', 'sysadmin', 'root', 'superadmin',
            'admin1', 'admin2', 'admin3', 'admins', 'panel', 'control',
            'backend', 'secure', 'portal', 'admin_portal', 'loginpanel',
            'admin_login.php', 'admin_area.php', 'admincontrol.php'
        ]
        logger.debug(f"Admin paths to check: {len(admin_paths)} paths")

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        logger.debug(f"Request headers set: {headers}")

        def check_url(url):
            logger.debug(f"Checking URL: {url}")
            try:
                response = requests.get(url, headers=headers, timeout=5, allow_redirects=True)
                status = response.status_code
                logger.debug(f"Received response for {url} - Status: {status}")
                
                if status == 200:
                    content = response.text.lower()
                    if any(keyword in content for keyword in ['login', 'sign in', 'username', 'password', 'admin']):
                        logger.debug(f"Login page detected at {url}")
                        return f"[FOUND LOGIN] {url} - Status: 200 (Accessible, likely a login page)"
                    return f"[FOUND] {url} - Status: 200 (Accessible)"
                elif status == 403:
                    return f"[RESTRICTED] {url} - Status: 403 (Forbidden)"
                elif status == 401:
                    return f"[AUTH REQUIRED] {url} - Status: 401 (Authentication Required)"
                elif status in (301, 302):
                    redirect_url = response.headers.get('Location', 'unknown')
                    logger.debug(f"Redirect detected for {url} to {redirect_url}")
                    if 'login' in redirect_url.lower() or 'admin' in redirect_url.lower():
                        return f"[REDIRECT LOGIN] {url} - Status: {status} (Redirects to {redirect_url})"
                    return f"[REDIRECT] {url} - Status: {status} (Redirects to {redirect_url})"
                logger.debug(f"URL {url} returned status {status} - skipping")
                return None
            except requests.RequestException as e:
                logger.error(f"Failed to connect to {url}: {str(e)}")
                return f"[ERROR] {url} - Failed to connect: {str(e)}"

        urls_to_check = [base_url + path.lstrip('/') for path in admin_paths]
        logger.debug(f"Generated {len(urls_to_check)} URLs to check")

        results = []
        logger.debug("Starting concurrent URL checks with ThreadPoolExecutor")
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_url = {executor.submit(check_url, url): url for url in urls_to_check}
            logger.debug(f"Submitted {len(future_to_url)} tasks to executor")
            
            for future in future_to_url:
                result = future.result()
                if result:
                    logger.debug(f"Result for {future_to_url[future]}: {result}")
                    results.append(result)

        if results:
            logger.info(f"Found {len(results)} significant results")
        else:
            logger.info("No significant results found; all URLs either 404 or skipped")
        
        response_data = {'results': results if results else ['No admin panels found or all returned 404.']}
        logger.debug(f"Returning response: {response_data}")
        return JsonResponse(response_data)
    
    logger.warning("Invalid request method received; expected POST")
    return JsonResponse({'error': 'Invalid request method'}, status=405)

def find_subdomains(request):
    logger.debug("Entering find_subdomains view")
    if request.method == 'POST':
        logger.debug("Received POST request to find subdomains")
        
        domain = request.POST.get('domain', '').strip()
        logger.debug(f"Domain received: {domain}")
        
        if not domain:
            logger.warning("No domain provided in the request")
            return JsonResponse({'error': 'Please provide a valid domain'}, status=400)

        if domain.startswith(('http://', 'https://')):
            domain = domain.split('://')[1]
            logger.debug(f"Removed protocol from domain: {domain}")
        domain = domain.split('/')[0]
        logger.debug(f"Normalized domain: {domain}")

        subdomain_prefixes = [
            'www', 'mail', 'ftp', 'blog', 'shop', 'dev', 'test', 'api', 'secure', 'admin',
            'login', 'portal', 'app', 'web', 'staging', 'beta', 'support', 'docs', 'forum',
            'news', 'store', 'dashboard', 'cpanel', 'manage', 'auth', 'ssl', 'vpn', 'remote',
            'git', 'ci', 'cdn', 'media', 'static', 'images', 'download', 'signup', 'members'
        ]
        logger.debug(f"Subdomain prefixes to check: {len(subdomain_prefixes)} prefixes")

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        logger.debug(f"Request headers set: {headers}")

        def check_subdomain(subdomain):
            full_domain = f"{subdomain}.{domain}"
            logger.debug(f"Checking subdomain: {full_domain}")
            try:
                answers = dns.resolver.resolve(full_domain, 'A')
                ip_addresses = [answer.to_text() for answer in answers]
                logger.debug(f"DNS resolved {full_domain} to IPs: {ip_addresses}")
                
                response = requests.get(f"https://{full_domain}", headers=headers, timeout=5, allow_redirects=True)
                status = response.status_code
                logger.debug(f"Received response for {full_domain} - Status: {status}")
                
                if status == 200:
                    return f"[FOUND] {full_domain} - Status: 200 (Accessible, IP: {', '.join(ip_addresses)})"
                elif status in (301, 302):
                    redirect_url = response.headers.get('Location', 'unknown')
                    return f"[REDIRECT] {full_domain} - Status: {status} (Redirects to {redirect_url}, IP: {', '.join(ip_addresses)})"
                elif status == 403:
                    return f"[RESTRICTED] {full_domain} - Status: 403 (Forbidden, IP: {', '.join(ip_addresses)})"
                elif status == 401:
                    return f"[AUTH REQUIRED] {full_domain} - Status: 401 (Authentication Required, IP: {', '.join(ip_addresses)}]"
                return None
            except dns.resolver.NXDOMAIN:
                logger.debug(f"Subdomain {full_domain} does not exist (NXDOMAIN)")
                return None
            except dns.resolver.NoAnswer:
                logger.debug(f"No DNS answer for {full_domain}")
                return None
            except requests.RequestException as e:
                logger.error(f"Failed to connect to {full_domain}: {str(e)}")
                return f"[ERROR] {full_domain} - Failed to connect: {str(e)}"

        subdomains_to_check = subdomain_prefixes
        logger.debug(f"Generated {len(subdomains_to_check)} subdomains to check")

        results = []
        logger.debug("Starting concurrent subdomain checks with ThreadPoolExecutor")
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_subdomain = {executor.submit(check_subdomain, subdomain): subdomain for subdomain in subdomains_to_check}
            logger.debug(f"Submitted {len(future_to_subdomain)} tasks to executor")
            
            for future in future_to_subdomain:
                result = future.result()
                if result:
                    logger.debug(f"Result for {future_to_subdomain[future]}.{domain}: {result}")
                    results.append(result)

        if results:
            logger.info(f"Found {len(results)} active subdomains")
        else:
            logger.info("No active subdomains found")
        
        response_data = {'results': results if results else ['No subdomains found']}
        logger.debug(f"Returning response: {response_data}")
        return JsonResponse(response_data)
    
    logger.warning("Invalid request method received; expected POST")
    return JsonResponse({'error': 'Invalid request method'}, status=405)

def generate_instagram_hashtags(request):
    logger.debug("Entering generate_instagram_hashtags view")
    if request.method == 'POST':
        logger.debug("Received POST request to generate Instagram hashtags")
        
        keywords = request.POST.get('keywords', '').strip()
        logger.debug(f"Keywords received: {keywords}")
        
        if not keywords:
            logger.warning("No keywords provided in the request")
            return JsonResponse({'error': 'Please provide keywords to generate hashtags'}, status=400)

        keyword_list = keywords.split()
        logger.debug(f"Keyword list: {keyword_list}")

        hashtags = [f"#{keyword.lower()}" for keyword in keyword_list]
        additional_hashtags = [
            '#instagood', '#trending', '#explore', '#photooftheday', '#love',
            f"#insta{keyword_list[0].lower()}", f"#best{keyword_list[0].lower()}",
            f"#{'-'.join(keyword_list).lower()}"
        ]
        
        final_hashtags = list(set(hashtags + additional_hashtags))[:10]
        logger.debug(f"Generated hashtags: {final_hashtags}")

        response_data = {
            'hashtags': final_hashtags,
            'message': 'Copy and paste these into your Instagram post!'
        }
        logger.debug(f"Returning response: {response_data}")
        return JsonResponse(response_data)
    
    logger.warning("Invalid request method received; expected POST")
    return JsonResponse({'error': 'Invalid request method'}, status=405)

def generate_youtube_tags(request):
    logger.debug("Entering generate_youtube_tags view")
    if request.method == 'POST':
        logger.debug("Received POST request to generate YouTube tags")
        
        topic = request.POST.get('topic', '').strip()
        logger.debug(f"Topic received: {topic}")
        
        if not topic:
            logger.warning("No topic provided in the request")
            return JsonResponse({'error': 'Please provide a video topic to generate tags'}, status=400)

        keyword_list = topic.split()
        logger.debug(f"Keyword list: {keyword_list}")

        tags = [f"#{keyword.lower()}" for keyword in keyword_list]
        additional_tags = [
            '#youtube', '#video', '#tutorial', '#trending', '#subscribe',
            f"#yt{keyword_list[0].lower()}", f"#viral{keyword_list[0].lower()}",
            f"#{'-'.join(keyword_list).lower()}"
        ]
        
        final_tags = list(set(tags + additional_tags))[:8]
        logger.debug(f"Generated tags: {final_tags}")

        response_data = {
            'tags': final_tags,
            'message': 'Copy and paste these into your YouTube video description!'
        }
        logger.debug(f"Returning response: {response_data}")
        return JsonResponse(response_data)
    
    logger.warning("Invalid request method received; expected POST")
    return JsonResponse({'error': 'Invalid request method'}, status=405)

def generate_temp_email(request):
    logger.debug("Entering generate_temp_email view")
    if request.method == 'POST':
        logger.debug("Received POST request to generate temporary email")
        
        api_url = 'https://www.1secmail.com/api/v1/?action=genRandomMailbox&count=1'
        try:
            response = requests.get(api_url, timeout=5)
            response.raise_for_status()
            data = response.json()
            if isinstance(data, list) and data:
                email = data[0]
                logger.debug(f"Generated email: {email}")
                response_data = {
                    'email': email,
                    'message': 'Use this email for temporary access. Check https://www.1secmail.com/ for inbox.'
                }
            else:
                raise ValueError("Invalid response from 1secmail API")
        except (requests.RequestException, ValueError) as e:
            logger.error(f"Failed to fetch temp email from 1secmail API: {str(e)}")
            random_string = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=8))
            email = f"{random_string}@1secmail.com"
            response_data = {
                'email': email,
                'message': 'Mock email generated due to API failure. Use https://www.1secmail.com/ for a real email.'
            }
        
        logger.debug(f"Returning response: {response_data}")
        return JsonResponse(response_data)
    
    logger.warning("Invalid request method received; expected POST")
    return JsonResponse({'error': 'Invalid request method'}, status=405)

def image_to_png_converter(request):
    logger.debug("Entering image_to_png_converter view")
    
    if request.method == 'POST' and request.FILES.get('image'):
        try:
            uploaded_file = request.FILES['image']
            logger.debug(f"Received image file: {uploaded_file.name}")
            
            img = Image.open(uploaded_file)
            if img.mode != 'RGBA':
                img = img.convert('RGBA')
            
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            buffer.seek(0)
            
            filename = f"{uploaded_file.name.rsplit('.', 1)[0]}_converted.png"
            response = FileResponse(
                buffer,
                as_attachment=True,
                filename=filename,
                content_type='image/png'
            )
            
            logger.info(f"Successfully converted {uploaded_file.name} to PNG")
            messages.success(request, 'Image successfully converted to PNG!')
            return response
            
        except Exception as e:
            logger.error(f"Error converting image: {str(e)}")
            messages.error(request, f'Error converting image: {str(e)}')
            return render(request, 'index.html')
    
    logger.debug("Rendering index.html for GET request")
    return render(request, 'index.html')

def remove_background(request):
    logger.debug("Entering remove_background view")
    
    if request.method == 'POST' and request.FILES.get('image'):
        try:
            uploaded_file = request.FILES['image']
            logger.debug(f"Received image file for background removal: {uploaded_file.name}")
            
            img = Image.open(uploaded_file)
            output_img = remove(img)
            
            buffer = io.BytesIO()
            output_img.save(buffer, format='PNG')
            buffer.seek(0)
            
            filename = f"{uploaded_file.name.rsplit('.', 1)[0]}_no_bg.png"
            response = FileResponse(
                buffer,
                as_attachment=True,
                filename=filename,
                content_type='image/png'
            )
            
            logger.info(f"Successfully removed background from {uploaded_file.name}")
            messages.success(request, 'Background removed successfully!')
            return response
            
        except Exception as e:
            logger.error(f"Error removing background: {str(e)}")
            messages.error(request, f'Error removing background: {str(e)}')
            return render(request, 'index.html')
    
    logger.debug("Rendering index.html for GET request")
    return render(request, 'index.html')

def extract_instagram_description(request):
    logger.debug("Entering extract_instagram_description view")
    
    if request.method == 'POST':
        url = request.POST.get('url', '').strip()
        logger.debug(f"Received Instagram URL: {url}")
        
        if not url:
            logger.warning("No URL provided")
            return JsonResponse({'error': 'Please provide a valid Instagram URL'}, status=400)

        try:
            L = InstaloaderSingleton.get_instance()
            
            if '/p/' in url or '/reel/' in url or '/tv/' in url:
                shortcode = url.split('/')[-2]
                post = instaloader.Post.from_shortcode(L.context, shortcode)
                description = post.caption or "No description available"
                logger.debug(f"Extracted description: {description}")
                return JsonResponse({'description': description})
            else:
                logger.warning(f"Invalid Instagram URL format: {url}")
                return JsonResponse({'error': 'Invalid Instagram URL format. Use a post or reel URL.'}, status=400)
                
        except instaloader.exceptions.InstaloaderException as e:
            logger.error(f"Instaloader error: {str(e)}")
            return JsonResponse({'error': f'Error fetching description: {str(e)}'}, status=500)
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return JsonResponse({'error': f'Unexpected error: {str(e)}'}, status=500)
    
    logger.warning("Invalid request method received; expected POST")
    return JsonResponse({'error': 'Invalid request method'}, status=405)

def resize_image(request):
    logger.debug("Entering resize_image view")
    
    if request.method == 'POST' and request.FILES.get('image'):
        try:
            uploaded_file = request.FILES['image']
            width = int(request.POST.get('width'))
            height = int(request.POST.get('height'))
            logger.debug(f"Received image file: {uploaded_file.name}, width: {width}, height: {height}")
            
            if width <= 0 or height <= 0:
                raise ValueError("Width and height must be positive numbers")
            
            img = Image.open(uploaded_file)
            resized_img = img.resize((width, height), Image.Resampling.LANCZOS)
            
            buffer = io.BytesIO()
            resized_img.save(buffer, format='PNG')
            buffer.seek(0)
            
            filename = f"{uploaded_file.name.rsplit('.', 1)[0]}_resized.png"
            response = FileResponse(
                buffer,
                as_attachment=True,
                filename=filename,
                content_type='image/png'
            )
            
            logger.info(f"Successfully resized {uploaded_file.name} to {width}x{height}")
            messages.success(request, 'Image resized successfully!')
            return response
            
        except ValueError as e:
            logger.error(f"Invalid input: {str(e)}")
            messages.error(request, f'Error resizing image: {str(e)}')
            return render(request, 'index.html')
        except Exception as e:
            logger.error(f"Error resizing image: {str(e)}")
            messages.error(request, f'Error resizing image: {str(e)}')
            return render(request, 'index.html')
    
    logger.debug("Rendering index.html for GET request")
    return render(request, 'index.html')

def image_to_pdf(request):
    logger.debug("Entering image_to_pdf view")
    
    if request.method == 'POST' and request.FILES.getlist('images'):
        try:
            images = request.FILES.getlist('images')
            logger.debug(f"Received {len(images)} image files for PDF conversion")
            
            buffer = io.BytesIO()
            c = canvas.Canvas(buffer, pagesize=letter)
            width, height = letter
            
            for img_file in images:
                img = Image.open(img_file)
                img_width, img_height = img.size
                scale = min(width / img_width, height / img_height)
                new_width = img_width * scale
                new_height = img_height * scale
                x = (width - new_width) / 2
                y = (height - new_height) / 2
                
                if img.mode == 'RGBA':
                    img = img.convert('RGB')
                
                temp_img_path = os.path.join(settings.MEDIA_ROOT, 'temp_image.jpg')
                img.save(temp_img_path, 'JPEG')
                c.drawImage(temp_img_path, x, y, new_width, new_height)
                c.showPage()
                os.remove(temp_img_path)
            
            c.save()
            buffer.seek(0)
            
            response = FileResponse(
                buffer,
                as_attachment=True,
                filename='converted_images.pdf',
                content_type='application/pdf'
            )
            
            logger.info(f"Successfully converted {len(images)} images to PDF")
            messages.success(request, 'Images converted to PDF successfully!')
            return response
            
        except Exception as e:
            logger.error(f"Error converting images to PDF: {str(e)}")
            messages.error(request, f'Error converting images to PDF: {str(e)}')
            return render(request, 'index.html')
    
    logger.debug("Rendering index.html for GET request")
    return render(request, 'index.html')

@csrf_exempt
def vulnerability_scanner(request):
    logger.debug("Entering vulnerability_scanner view")
    if request.method == 'POST':
        url = request.POST.get('url', '').strip()
        logger.debug(f"URL received for scanning: {url}")

        if not url:
            logger.warning("No URL provided for vulnerability scan")
            return JsonResponse({'error': 'Please provide a valid URL'}, status=400)

        if not url.startswith(('http://', 'https://')):
            url = 'http://' + url
            logger.debug(f"Added 'http://' prefix to URL: {url}")

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

        # Initialize results
        scan_results = {
            "url": url,
            "steps": [],
            "vulnerabilities": []
        }

        # Step 1: Select and test a proxy
        proxy = get_random_proxy()
        scan_results["steps"].append(f"Step 1: Selecting proxy - {proxy}")
        if not test_proxy(proxy):
            scan_results["steps"].append(f"Proxy {proxy} failed, falling back to direct request")
            proxies = None
        else:
            scan_results["steps"].append(f"Proxy {proxy} is working")
            proxies = {"http": proxy, "https": proxy}

        # Step 2: Nmap scan
        try:
            nm = nmap.PortScanner()
            hostname = urlparse(url).hostname
            scan_results["steps"].append(f"Step 2: Starting Nmap scan on {hostname}")
            # Check if Nmap is available
            if not nm.nmap_version():
                raise nmap.PortScannerError("Nmap not found in PATH")
            # Perform a basic scan (-sV for service version, -p 1-1000 for top 1000 ports for speed)
            nm.scan(hostname, arguments='-sV -p 1-1000')
            scan_results["steps"].append(f"Nmap scan completed on {hostname}")

            if hostname in nm.all_hosts():
                host_info = nm[hostname]
                open_ports = []
                for proto in host_info.all_protocols():
                    ports = host_info[proto].keys()
                    for port in ports:
                        state = host_info[proto][port]['state']
                        service = host_info[proto][port].get('name', 'unknown')
                        version = host_info[proto][port].get('version', '')
                        if state == 'open':
                            open_ports.append(f"Port {port}/{proto} open - Service: {service} {version}")
                            if service in ['http', 'apache', 'nginx'] and version:
                                scan_results["vulnerabilities"].append(f"Potentially vulnerable service: {service} {version} on port {port}")
                if open_ports:
                    scan_results["steps"].append(f"Found open ports: {', '.join(open_ports)}")
                else:
                    scan_results["steps"].append("No open ports found in the scanned range")
            else:
                scan_results["steps"].append(f"No Nmap results for {hostname}")
        except nmap.PortScannerError as e:
            logger.error(f"Nmap scan failed: {str(e)}")
            scan_results["steps"].append(f"Step 2: Nmap scan failed - Error: {str(e)}. Ensure Nmap is installed and in PATH.")
        except Exception as e:
            logger.error(f"Unexpected error during Nmap scan: {str(e)}")
            scan_results["steps"].append(f"Step 2: Nmap scan error - {str(e)}")

        # Step 3: Initial HTTP request to check accessibility
        try:
            response = requests.get(url, headers=headers, proxies=proxies, timeout=10, allow_redirects=True)
            response.raise_for_status()
            scan_results["steps"].append(f"Step 3: URL is accessible - Status Code: {response.status_code}")
            content = response.text
        except requests.RequestException as e:
            logger.error(f"Failed to access URL {url}: {str(e)}")
            scan_results["steps"].append(f"Step 3: Failed to access URL - Error: {str(e)}")
            return JsonResponse(scan_results)

        # Step 4: SQL Injection test
        payloads = ["' OR 1=1 --", "1; DROP TABLE users --"]
        for payload in payloads:
            test_url = f"{url}?id={payload}" if '?' in url else f"{url}?test={payload}"
            scan_results["steps"].append(f"Step 4a: Testing SQL Injection with payload: {payload}")
            try:
                resp = requests.get(test_url, headers=headers, proxies=proxies, timeout=5)
                if "sql" in resp.text.lower() or "mysql" in resp.text.lower() or "error" in resp.text.lower():
                    scan_results["vulnerabilities"].append(f"Potential SQL Injection vulnerability detected at {test_url}")
            except requests.RequestException:
                scan_results["steps"].append(f"Failed to test {test_url}")

        # Step 5: XSS test (fixed truncation)
        xss_payloads = ["<script>alert('xss')</script>", "<img src=x onerror=alert('xss')>"]
        for payload in xss_payloads:
            test_url = f"{url}?q={payload}" if '?' in url else f"{url}?search={payload}"
            scan_results["steps"].append(f"Step 5b: Testing XSS with payload: {payload}")
            try:
                resp = requests.get(test_url, headers=headers, proxies=proxies, timeout=5)
                if payload in resp.text:
                    scan_results["vulnerabilities"].append(f"Potential XSS vulnerability detected at {test_url}")
            except requests.RequestException:
                scan_results["steps"].append(f"Failed to test {test_url}")

        # Step 6: Open Redirect test
        redirect_payload = "https://evil.com"
        test_url = f"{url}?redirect={redirect_payload}"
        scan_results["steps"].append(f"Step 6: Testing Open Redirect with payload: {redirect_payload}")
        try:
            resp = requests.get(test_url, headers=headers, proxies=proxies, timeout=5, allow_redirects=False)
            if resp.status_code in (301, 302) and redirect_payload in resp.headers.get('Location', ''):
                scan_results["vulnerabilities"].append(f"Open Redirect vulnerability detected at {test_url}")
        except requests.RequestException:
            scan_results["steps"].append(f"Failed to test {test_url}")

        # Step 7: Form analysis
        soup = BeautifulSoup(content, 'html.parser')
        forms = soup.find_all('form')
        scan_results["steps"].append(f"Step 7: Found {len(forms)} forms on the page")
        for form in forms:
            action = form.get('action', url)
            method = form.get('method', 'get').lower()
            inputs = [inp.get('name') for inp in form.find_all('input') if inp.get('name')]
            scan_results["steps"].append(f"Form detected - Action: {action}, Method: {method}, Inputs: {inputs}")
            if method == 'get':
                scan_results["vulnerabilities"].append(f"Potential insecure form (GET method) at {action}")

        # Finalize results
        if not scan_results["vulnerabilities"]:
            scan_results["vulnerabilities"].append("No obvious vulnerabilities detected (further manual testing recommended)")

        logger.info(f"Vulnerability scan completed for {url}")
        return JsonResponse(scan_results)

    logger.warning("Invalid request method received; expected POST")
    return JsonResponse({'error': 'Invalid request method'}, status=405)

def handler404(request, exception):
    logger.debug("Handling 404 error")
    return render(request, '404.html', status=404)

def handler500(request):
    logger.debug("Handling 500 error")
    return render(request, '500.html', status=500)