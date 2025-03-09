# urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('category/<int:category_id>/', views.category_detail, name='category_detail'),
    path('post/<int:post_id>/', views.post_detail, name='post_detail'),
    path('project/<int:project_id>/', views.project_detail, name='project_detail'),
    path('add_comment/<int:post_id>/', views.add_comment, name='add_comment'),
    path('rate_post/<int:post_id>/', views.rate_post, name='rate_post'),
    path('search/', views.search, name='search'),
    path('delete_comment/<int:comment_id>/', views.delete_comment, name='delete_comment'),
    path('instagram_downloader/', views.instagram_downloader, name='instagram_downloader'),
    path('find_admin_panels/', views.find_admin_panels, name='find_admin_panels'),
    path('find_subdomains/', views.find_subdomains, name='find_subdomains'),
    path('generate_hashtags/', views.generate_instagram_hashtags, name='generate_hashtags'),
    path('generate_youtube_tags/', views.generate_youtube_tags, name='generate_youtube_tags'),
    path('generate_temp_email/', views.generate_temp_email, name='generate_temp_email'),
    path('image-to-png-converter/', views.image_to_png_converter, name='image_to_png_converter'),
    path('remove-background/', views.remove_background, name='remove_background'),
    path('extract-instagram-description/', views.extract_instagram_description, name='extract_instagram_description'),
    path('resize-image/', views.resize_image, name='resize_image'),
    path('image-to-pdf/', views.image_to_pdf, name='image_to_pdf'),
    path('vulnerability-scanner/', views.vulnerability_scanner, name='vulnerability_scanner'),  # New endpoint
]